from collections.abc import Callable
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


def create_deepseek_client(api_key: str, base_url: str = DEEPSEEK_BASE_URL):
    return OpenAI(api_key=api_key, base_url=base_url)


def run_agent(
    client,
    model: str,
    agent_name: str,
    system_prompt: str,
    user_input: str,
) -> str:
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ],
            temperature=0.2,
        )
    except Exception as exc:
        raise RuntimeError(f"{agent_name} failed: {exc}") from exc

    content = response.choices[0].message.content
    if not content:
        raise RuntimeError(f"{agent_name} returned an empty response.")
    return content.strip()


def run_agent_with_usage(
    client,
    model: str,
    agent_name: str,
    system_prompt: str,
    user_input: str,
) -> tuple[str, dict]:
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ],
            temperature=0.2,
        )
    except Exception as exc:
        raise RuntimeError(f"{agent_name} failed: {exc}") from exc

    content = response.choices[0].message.content
    if not content:
        raise RuntimeError(f"{agent_name} returned an empty response.")

    usage = build_agent_usage(agent_name.replace(" Agent", ""), model, response)
    return content.strip(), usage


def run_multi_agent_workflow(
    client,
    model: str,
    resume_text: str,
    job_description: str,
    on_step: Optional[Callable[[str], None]] = None,
) -> dict:
    outputs = {}
    usage_items = []

    def notify(agent_name: str) -> None:
        if on_step:
            on_step(agent_name)

    notify("Resume Analyzer Agent")
    outputs["resume_analysis"], usage_item = run_agent_with_usage(
        client,
        model,
        "Resume Analyzer Agent",
        RESUME_ANALYZER_PROMPT,
        f"Candidate resume:\n\n{resume_text}",
    )
    usage_items.append(usage_item)

    notify("Job Description Analyzer Agent")
    outputs["job_analysis"], usage_item = run_agent_with_usage(
        client,
        model,
        "Job Description Analyzer Agent",
        JOB_DESCRIPTION_ANALYZER_PROMPT,
        f"Job description:\n\n{job_description}",
    )
    usage_items.append(usage_item)

    notify("Skill Matching Agent")
    outputs["skill_matching"], usage_item = run_agent_with_usage(
        client,
        model,
        "Skill Matching Agent",
        SKILL_MATCHING_PROMPT,
        _format_context(
            resume_text=resume_text,
            job_description=job_description,
            resume_analysis=outputs["resume_analysis"],
            job_analysis=outputs["job_analysis"],
        ),
    )
    usage_items.append(usage_item)

    notify("Gap Analysis Agent")
    outputs["gap_analysis"], usage_item = run_agent_with_usage(
        client,
        model,
        "Gap Analysis Agent",
        GAP_ANALYSIS_PROMPT,
        _format_context(**outputs, resume_text=resume_text, job_description=job_description),
    )
    usage_items.append(usage_item)

    notify("Resume Improvement Agent")
    outputs["resume_improvement"], usage_item = run_agent_with_usage(
        client,
        model,
        "Resume Improvement Agent",
        RESUME_IMPROVEMENT_PROMPT,
        _format_context(**outputs, resume_text=resume_text, job_description=job_description),
    )
    usage_items.append(usage_item)

    notify("Interview Preparation Agent")
    outputs["interview_preparation"], usage_item = run_agent_with_usage(
        client,
        model,
        "Interview Preparation Agent",
        INTERVIEW_PREPARATION_PROMPT,
        _format_context(**outputs, resume_text=resume_text, job_description=job_description),
    )
    usage_items.append(usage_item)

    notify("Final Report Agent")
    outputs["final_report"], usage_item = run_agent_with_usage(
        client,
        model,
        "Final Report Agent",
        FINAL_REPORT_PROMPT,
        _format_context(**outputs, resume_text=resume_text, job_description=job_description),
    )
    usage_items.append(usage_item)

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
