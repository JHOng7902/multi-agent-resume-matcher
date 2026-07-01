import re
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from openai import OpenAI

from prompts import (
    FINAL_REPORT_PROMPT,
    GAP_ANALYSIS_PROMPT,
    INTERVIEW_PREPARATION_PROMPT,
    JOB_DESCRIPTION_ANALYZER_PROMPT,
    RESUME_ANALYZER_PROMPT,
    RESUME_IMPROVEMENT_PROMPT,
    SKILL_MATCHING_PROMPT,
)
from usage import build_agent_usage, summarize_usage


DEEPSEEK_BASE_URL = "https://api.deepseek.com"

DEFAULT_MAX_TOKENS = 1000

# Per-agent output caps. Generation time scales with output length, so keeping
# these tight is the main speed lever. The final report gets more room.
AGENT_MAX_TOKENS = {
    "Resume Analyzer Agent": 1200,
    "Job Description Analyzer Agent": 1200,
    "Skill Matching Agent": 1700,
    "Gap Analysis Agent": 1200,
    "Resume Improvement Agent": 1300,
    "Interview Preparation Agent": 1150,
    "Final Report Agent": 1700,
}

# When a response comes back empty, retry once with this much room so a model
# that spends its budget on reasoning tokens still returns visible content.
RETRY_MAX_TOKENS = 3000


def create_deepseek_client(api_key: str, base_url: str = DEEPSEEK_BASE_URL):
    return OpenAI(api_key=api_key, base_url=base_url)


_EMPTY_BULLET = re.compile(r"^\s*(?:[-*•‣◦]|\d+[.)])\s*$")


def _tidy(text: str) -> str:
    """Drop trailing blank lines and empty bullet markers left by truncation."""
    lines = text.split("\n")
    while lines and (not lines[-1].strip() or _EMPTY_BULLET.match(lines[-1])):
        lines.pop()
    return "\n".join(lines).strip()


def _extract_content(response) -> str:
    choices = getattr(response, "choices", None) or []
    if not choices:
        return ""
    message = choices[0].message
    content = (getattr(message, "content", None) or "").strip()
    if not content:
        # Some DeepSeek models place text in reasoning_content when content is blank.
        content = (getattr(message, "reasoning_content", None) or "").strip()
    return content


def _is_truncated(response) -> bool:
    choices = getattr(response, "choices", None) or []
    if not choices:
        return False
    return getattr(choices[0], "finish_reason", None) == "length"


def _complete(client, model, agent_name, system_prompt, user_input, max_tokens):
    """Call the model, retrying with more headroom if the reply is empty or cut off."""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input},
    ]
    best_content = ""
    best_response = None
    for attempt_tokens in (max_tokens, RETRY_MAX_TOKENS):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.2,
                max_tokens=attempt_tokens,
            )
        except Exception as exc:
            raise RuntimeError(f"{agent_name} failed: {exc}") from exc

        content = _extract_content(response)
        if content and not _is_truncated(response):
            return response, _tidy(content)
        if content:
            # Truncated: keep as a fallback, but retry with more room first.
            best_content, best_response = content, response

    if best_content:
        return best_response, _tidy(best_content)
    raise RuntimeError(f"{agent_name} returned an empty response.")


def run_agent(
    client,
    model: str,
    agent_name: str,
    system_prompt: str,
    user_input: str,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> str:
    _, content = _complete(client, model, agent_name, system_prompt, user_input, max_tokens)
    return content


def run_agent_with_usage(
    client,
    model: str,
    agent_name: str,
    system_prompt: str,
    user_input: str,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> tuple[str, dict]:
    response, content = _complete(client, model, agent_name, system_prompt, user_input, max_tokens)
    usage = build_agent_usage(agent_name.replace(" Agent", ""), model, response)
    return content, usage


def run_multi_agent_workflow(
    client,
    model: str,
    resume_text: str,
    job_description: str,
    on_step: Optional[Callable[[str], None]] = None,
) -> dict:
    """Run the seven agents in five stages.

    Independent agents run concurrently (resume + job analysis; resume
    improvement + interview prep), cutting the wall-clock time versus running
    all seven strictly one after another. Agents that depend on earlier output
    still run in the correct order.
    """
    outputs = {}
    usage_by_key = {}

    def notify(agent_name: str) -> None:
        if on_step:
            on_step(agent_name)

    def call(agent_name: str, system_prompt: str, user_input: str):
        max_tokens = AGENT_MAX_TOKENS.get(agent_name, DEFAULT_MAX_TOKENS)
        return run_agent_with_usage(client, model, agent_name, system_prompt, user_input, max_tokens)

    # Stage 1 — resume and job-description analysis are independent: run together.
    notify("Resume Analyzer Agent")
    notify("Job Description Analyzer Agent")
    with ThreadPoolExecutor(max_workers=2) as executor:
        resume_future = executor.submit(
            call, "Resume Analyzer Agent", RESUME_ANALYZER_PROMPT, f"Candidate resume:\n\n{resume_text}"
        )
        job_future = executor.submit(
            call, "Job Description Analyzer Agent", JOB_DESCRIPTION_ANALYZER_PROMPT,
            f"Job description:\n\n{job_description}",
        )
        outputs["resume_analysis"], usage_by_key["resume_analysis"] = resume_future.result()
        outputs["job_analysis"], usage_by_key["job_analysis"] = job_future.result()

    # Stage 2 — skill matching needs both analyses.
    notify("Skill Matching Agent")
    outputs["skill_matching"], usage_by_key["skill_matching"] = call(
        "Skill Matching Agent",
        SKILL_MATCHING_PROMPT,
        _format_context(
            resume_text=resume_text,
            job_description=job_description,
            resume_analysis=outputs["resume_analysis"],
            job_analysis=outputs["job_analysis"],
        ),
    )

    # Stage 3 — gap analysis needs skill matching.
    notify("Gap Analysis Agent")
    outputs["gap_analysis"], usage_by_key["gap_analysis"] = call(
        "Gap Analysis Agent",
        GAP_ANALYSIS_PROMPT,
        _format_context(**outputs, resume_text=resume_text, job_description=job_description),
    )

    # Stage 4 — resume improvement and interview prep both build on the gap
    # analysis but not on each other: run together.
    notify("Resume Improvement Agent")
    notify("Interview Preparation Agent")
    stage4_context = _format_context(**outputs, resume_text=resume_text, job_description=job_description)
    with ThreadPoolExecutor(max_workers=2) as executor:
        improvement_future = executor.submit(
            call, "Resume Improvement Agent", RESUME_IMPROVEMENT_PROMPT, stage4_context
        )
        interview_future = executor.submit(
            call, "Interview Preparation Agent", INTERVIEW_PREPARATION_PROMPT, stage4_context
        )
        outputs["resume_improvement"], usage_by_key["resume_improvement"] = improvement_future.result()
        outputs["interview_preparation"], usage_by_key["interview_preparation"] = interview_future.result()

    # Stage 5 — final report combines everything.
    notify("Final Report Agent")
    outputs["final_report"], usage_by_key["final_report"] = call(
        "Final Report Agent",
        FINAL_REPORT_PROMPT,
        _format_context(**outputs, resume_text=resume_text, job_description=job_description),
    )

    usage_order = [
        "resume_analysis",
        "job_analysis",
        "skill_matching",
        "gap_analysis",
        "resume_improvement",
        "interview_preparation",
        "final_report",
    ]
    usage_items = [usage_by_key[key] for key in usage_order]

    outputs["usage"] = {
        "agents": usage_items,
        "summary": summarize_usage(usage_items),
    }
    return outputs


def _format_context(**sections: str) -> str:
    formatted = []
    for key, value in sections.items():
        formatted.append(f"## {key}\n{value}")
    return "\n\n".join(formatted)
