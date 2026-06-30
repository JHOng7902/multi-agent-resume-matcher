import prompts


def test_all_agent_prompts_are_available_and_non_empty():
    prompt_names = [
        "RESUME_ANALYZER_PROMPT",
        "JOB_DESCRIPTION_ANALYZER_PROMPT",
        "SKILL_MATCHING_PROMPT",
        "GAP_ANALYSIS_PROMPT",
        "RESUME_IMPROVEMENT_PROMPT",
        "INTERVIEW_PREPARATION_PROMPT",
        "FINAL_REPORT_PROMPT",
    ]

    for name in prompt_names:
        prompt = getattr(prompts, name)
        assert isinstance(prompt, str)
        assert len(prompt.strip()) > 80


def test_final_report_prompt_requires_core_report_sections():
    prompt = prompts.FINAL_REPORT_PROMPT

    required_sections = [
        "Job match score",
        "Overall suitability",
        "Matched skills",
        "Missing skills",
        "Resume improvement suggestions",
        "Interview preparation",
        "Final recommendation",
    ]

    for section in required_sections:
        assert section in prompt
