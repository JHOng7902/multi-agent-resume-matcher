from datetime import datetime

from streamlit.testing.v1 import AppTest

from app import build_report_export, compile_report_pdf, report_export_filename, reset_job_matching_state


FAKE_OUTPUTS = {
    "resume_analysis": "Resume analysis",
    "job_analysis": "Job analysis",
    "skill_matching": "Skill matching",
    "gap_analysis": "Gap analysis",
    "resume_improvement": "Resume improvement",
    "interview_preparation": "Interview prep",
    "final_report": "Final report 88%",
    "usage": {
        "agents": [],
        "summary": {
            "model": "deepseek-v4-flash",
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_tokens": 0,
            "estimated_cost_usd": 0.0,
        },
    },
}


def test_build_report_export_includes_final_report_and_agent_sections():
    outputs = {
        "resume_analysis": "Resume analysis content",
        "job_analysis": "Job analysis content",
        "skill_matching": "Skill matching content",
        "gap_analysis": "Gap analysis content",
        "resume_improvement": "Resume improvement content",
        "interview_preparation": "Interview prep content",
        "final_report": "Final recommendation content",
    }

    exported = build_report_export(outputs, generated_at=datetime(2026, 7, 1, 10, 30))

    assert "# Multi-Agent Resume & Job Matching Report" in exported
    assert "Generated: 2026-07-01 10:30" in exported
    assert "## Final Report" in exported
    assert "Final recommendation content" in exported
    assert "## Agent Outputs" in exported
    assert "### Resume Analyzer" in exported
    assert "Resume analysis content" in exported
    assert "### Interview Preparation" in exported


def test_report_export_filename_uses_timestamp():
    filename = report_export_filename(datetime(2026, 7, 1, 10, 30, 15))

    assert filename == "job-match-report-20260701-103015.pdf"


def test_compile_report_pdf_returns_a_pdf_document():
    pdf_bytes = compile_report_pdf(build_report_export(FAKE_OUTPUTS))

    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 500


def test_reset_job_matching_state_clears_inputs_outputs_and_progress():
    state = {
        "form_nonce": 2,
        "resume_text_2": "resume",
        "resume_pdf_2": object(),
        "job_description_2": "job",
        "job_description_file_2": object(),
        "agent_outputs": {"final_report": "report"},
        "active_agent": "Resume Analyzer",
        "focus_report": True,
        "usage_history": [{"Status": "Completed"}],
        "page_nav": "Usage Dashboard",
    }

    reset_job_matching_state(state)

    assert state["form_nonce"] == 3
    assert state["active_agent"] is None
    assert state["page_nav"] == "Job Matching"
    for cleared_key in [
        "resume_text_2",
        "resume_pdf_2",
        "job_description_2",
        "job_description_file_2",
        "agent_outputs",
        "focus_report",
        "usage_history",
    ]:
        assert cleared_key not in state


def test_generated_report_shows_single_export_pdf_button():
    app = AppTest.from_file("app.py")
    app.session_state["agent_outputs"] = FAKE_OUTPUTS
    app.session_state["page_nav"] = "Job Matching"

    app.run(timeout=10)

    assert len(app.exception) == 0

    # Exactly one "Export Report" control, and it is a PDF download button
    # (not a plain button — the old two-step prepare/download flow is gone).
    download_buttons = app.get("download_button")
    export_labels = [b.label for b in download_buttons if b.label == "Export Report"]
    assert export_labels == ["Export Report"]
    assert all(b.label != "Export Report" for b in app.button)
    assert all(b.label != "Download Report (.md)" for b in download_buttons)


def test_clear_all_button_appears_once_and_clears_state():
    app = AppTest.from_file("app.py")
    app.session_state["agent_outputs"] = FAKE_OUTPUTS
    app.session_state["page_nav"] = "Job Matching"

    app.run(timeout=10)

    assert len(app.exception) == 0
    clear_buttons = [b for b in app.button if b.label == "Clear All"]
    assert len(clear_buttons) == 1

    clear_buttons[0].click().run(timeout=10)

    assert len(app.exception) == 0
    assert "agent_outputs" not in app.session_state
    assert app.session_state["page_nav"] == "Job Matching"
