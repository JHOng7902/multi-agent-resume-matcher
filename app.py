from datetime import datetime

import pandas as pd
import streamlit as st

from agents import create_deepseek_client, run_multi_agent_workflow
from pdf_utils import extract_text_from_pdf, extract_text_from_uploaded_file
from utils import clean_text, extract_match_score, resolve_api_key, resolve_model, validate_required_inputs
from usage import format_usd


SAMPLE_JOB_DESCRIPTION = """We are hiring a Software Tester. Responsibilities include preparing test cases, executing manual testing, performing regression testing, supporting UAT, logging defects in JIRA, and working with developers. Knowledge of SQL, Selenium, and API testing will be an advantage."""

AGENT_LABELS = {
    "resume_analysis": "Resume Analyzer",
    "job_analysis": "Job Description Analyzer",
    "skill_matching": "Skill Matching",
    "gap_analysis": "Gap Analysis",
    "resume_improvement": "Resume Improvement",
    "interview_preparation": "Interview Preparation",
    "final_report": "Final Report",
}

WORKFLOW_STEPS = [
    ("1", "Resume", "Provide your resume"),
    ("2", "Job Description", "Provide the job details"),
    ("3", "Analyze", "Our agents analyze the match"),
    ("4", "Report", "View on-screen report"),
]


def main():
    st.set_page_config(
        page_title="Multi-Agent Resume & Job Matching Assistant",
        page_icon=":page_facing_up:",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    inject_styles()

    st.session_state.setdefault("form_nonce", 0)

    api_key = resolve_api_key()
    model = resolve_model()

    render_header()
    selected_page = render_page_navigation()

    if selected_page == "Usage Dashboard":
        render_usage_dashboard(model)
        return

    step_info = compute_step_states()
    render_stepper(step_info)

    resume_text, job_description = render_input_workspace(step_info)
    render_analysis_action(api_key, model, resume_text, job_description)
    render_report_workspace()


def compute_step_states() -> dict:
    """Derive done/active/pending state for each workflow step from session state."""
    nonce = st.session_state.get("form_nonce", 0)
    resume_done = bool(clean_text(st.session_state.get(f"resume_text_{nonce}", ""))) or (
        st.session_state.get(f"resume_pdf_{nonce}") is not None
    )
    job_done = bool(clean_text(st.session_state.get(f"job_description_{nonce}", ""))) or (
        st.session_state.get(f"job_description_file_{nonce}") is not None
    )
    analysis_done = bool(st.session_state.get("agent_outputs"))

    states = []
    states.append("done" if resume_done else "active")  # Step 1: Resume
    if job_done:  # Step 2: Job Description
        states.append("done")
    elif resume_done:
        states.append("active")
    else:
        states.append("pending")
    if analysis_done:  # Step 3: Analyze
        states.append("done")
    elif resume_done and job_done:
        states.append("active")
    else:
        states.append("pending")
    states.append("done" if analysis_done else "pending")  # Step 4: Report

    return {
        "states": states,
        "resume_done": resume_done,
        "job_done": job_done,
        "analysis_done": analysis_done,
    }


def clear_all():
    """Reset Job Matching inputs and report. New nonce forces fresh, empty widgets."""
    st.session_state.form_nonce = st.session_state.get("form_nonce", 0) + 1
    st.session_state.pop("agent_outputs", None)
    st.session_state["active_agent"] = None


def render_header():
    st.markdown(
        '<div class="app-header">'
        '<div class="brand-mark" aria-hidden="true">'
        '<svg viewBox="0 0 48 48" role="img">'
        '<rect x="8" y="5" width="26" height="34" rx="5"></rect>'
        '<path d="M15 15h4m4 0h5M15 23h12M15 31h10"></path>'
        '<circle cx="34" cy="33" r="7"></circle>'
        '<path d="M39 38l5 5"></path>'
        '<path d="M17 10v5m-3-2.5h6"></path>'
        "</svg>"
        "</div>"
        '<div class="brand-copy">'
        "<h1>Multi-Agent Resume & Job Matching Assistant</h1>"
        "<p>Analyze your resume against a job description and get actionable insights.</p>"
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )


def render_stepper(step_info):
    states = step_info["states"]
    reached = [index for index, state in enumerate(states) if state in ("done", "active")]
    fill_pct = int(max(reached, default=0) / (len(WORKFLOW_STEPS) - 1) * 100)

    step_html = "".join(
        f'<div class="step-item step-{state}">'
        f'<div class="step-node">{"✓" if state == "done" else number}</div>'
        f'<div class="step-title">{title}</div>'
        f'<div class="step-caption">{caption}</div>'
        f"</div>"
        for (number, title, caption), state in zip(WORKFLOW_STEPS, states)
    )
    st.markdown(
        f'<div class="stepper"><div class="step-line">'
        f'<div class="step-line-fill" style="width:{fill_pct}%"></div></div>{step_html}</div>',
        unsafe_allow_html=True,
    )


def render_page_navigation():
    return st.radio(
        "Page",
        ["Job Matching", "Usage Dashboard"],
        horizontal=True,
        key="page_nav",
        label_visibility="collapsed",
    )


def render_input_workspace(step_info):
    nonce = st.session_state.get("form_nonce", 0)
    resume_col, job_col, workflow_col = st.columns([1.05, 1.05, 0.8], gap="medium")

    with resume_col:
        resume_text = render_resume_input(nonce)
    with job_col:
        job_description = render_job_description_input(nonce, locked=not step_info["resume_done"])
    with workflow_col:
        render_agent_workflow(st.session_state.get("active_agent"))

    return resume_text, job_description


def render_resume_input(nonce):
    with st.container(border=True):
        st.markdown(
            '<div class="card-heading">'
            '<span class="heading-icon">'
            '<svg viewBox="0 0 24 24"><path d="M7 3h7l4 4v14H7z"></path><path d="M14 3v5h5"></path><path d="M10 13h6M10 17h4"></path><path d="M5 8v13h10"></path></svg>'
            "</span>"
            "<h3>Step 1: Resume Input</h3>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown('<div class="field-label">Paste your resume text below</div>', unsafe_allow_html=True)
        pasted_resume = st.text_area(
            "Paste your resume here",
            height=110,
            max_chars=20000,
            placeholder="Paste your resume content here...",
            label_visibility="collapsed",
            key=f"resume_text_{nonce}",
        )
        st.markdown(
            f'<div class="char-count">{len(pasted_resume or "")} / 20000</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="upload-label">or upload your resume</div>', unsafe_allow_html=True)
        uploaded_pdf = st.file_uploader(
            "Upload Resume PDF",
            type=["pdf"],
            key=f"resume_pdf_{nonce}",
            label_visibility="collapsed",
        )

        pdf_text = ""
        if uploaded_pdf and not clean_text(pasted_resume):
            try:
                pdf_text = extract_text_from_pdf(uploaded_pdf)
                with st.expander("Extracted resume preview", expanded=False):
                    st.write(pdf_text)
            except ValueError as exc:
                st.warning(str(exc))

        return clean_text(pasted_resume) or pdf_text


def render_job_description_input(nonce, locked=False):
    with st.container(border=True):
        st.markdown(
            '<div class="card-heading">'
            '<span class="heading-icon">'
            '<svg viewBox="0 0 24 24"><rect x="4" y="7" width="16" height="12" rx="2"></rect><path d="M8 7V5h8v2M4 12h16M9 12v2m6-2v2"></path></svg>'
            "</span>"
            "<h3>Step 2: Job Description Input</h3>"
            "</div>",
            unsafe_allow_html=True,
        )
        if locked:
            st.markdown(
                '<div class="lock-hint">🔒 Complete Step 1 first — add your resume to unlock this step.</div>',
                unsafe_allow_html=True,
            )

        st.markdown('<div class="field-label">Paste the job description below</div>', unsafe_allow_html=True)
        pasted_job = st.text_area(
            "Paste the job description here",
            key=f"job_description_{nonce}",
            height=110,
            max_chars=20000,
            placeholder="Paste job description content here...",
            label_visibility="collapsed",
            disabled=locked,
        )
        st.markdown(
            f'<div class="char-count">{len(pasted_job or "")} / 20000</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="upload-label">or upload job description file</div>', unsafe_allow_html=True)
        uploaded_job_file = st.file_uploader(
            "Upload Job Description File",
            type=["pdf", "docx", "txt"],
            key=f"job_description_file_{nonce}",
            label_visibility="collapsed",
            disabled=locked,
        )

        file_text = ""
        if uploaded_job_file and not clean_text(pasted_job):
            try:
                file_text = extract_text_from_uploaded_file(uploaded_job_file)
                with st.expander("Extracted job description preview", expanded=False):
                    st.write(file_text)
            except ValueError as exc:
                st.warning(str(exc))

        return clean_text(pasted_job) or file_text


def render_analysis_action(api_key, model, resume_text, job_description):
    ready = not validate_required_inputs(resume_text, job_description)

    st.markdown('<div class="generate-wrap">', unsafe_allow_html=True)
    spacer_l, generate_col, clear_col, spacer_r = st.columns([1, 0.75, 0.4, 1])
    with generate_col:
        clicked = st.button(
            "Generate Job Match Report",
            type="primary",
            use_container_width=True,
            icon=":material/auto_fix_high:",
            disabled=not ready,
        )
    with clear_col:
        st.button(
            "Clear All",
            use_container_width=True,
            on_click=clear_all,
            help="Reset the resume, job description, uploads, and report on this page.",
        )
    st.markdown("</div>", unsafe_allow_html=True)

    if not ready:
        st.caption("Add both your resume and the job description to enable the report.")

    if clicked:
        if not api_key:
            st.error("Missing DeepSeek configuration. Add DEEPSEEK_API_KEY to `.env` and restart the app.")
            return
        run_analysis(api_key, model, resume_text, job_description)


def render_agent_workflow(active_agent=None):
    with st.container(border=True):
        st.markdown(
            '<div class="card-heading workflow-heading">'
            '<span class="heading-icon">'
            '<svg viewBox="0 0 24 24"><circle cx="12" cy="5" r="2.5"></circle><circle cx="5" cy="18" r="2.5"></circle><circle cx="19" cy="18" r="2.5"></circle><path d="M12 8v4M12 12l-5 4M12 12l5 4"></path></svg>'
            "</span>"
            "<h3>Analysis Workflow (7 Agents)</h3>"
            "</div>",
            unsafe_allow_html=True,
        )
        completed = bool(st.session_state.get("agent_outputs"))
        for index, label in enumerate(AGENT_LABELS.values(), start=1):
            state_class = "agent-ready"
            state_text = "Ready"
            icon = str(index)
            if completed:
                state_class = "agent-done"
                state_text = "Completed"
                icon = "✓"
            elif active_agent == label or active_agent == f"{label} Agent":
                state_class = "agent-active"
                state_text = "Running"

            st.markdown(
                f'<div class="agent-row">'
                f'<span class="agent-marker {state_class}">{icon}</span>'
                f"<span>{label}</span>"
                f'<span class="agent-state {state_class}">{state_text}</span>'
                f"</div>",
                unsafe_allow_html=True,
            )


def run_analysis(api_key, model, resume_text, job_description):
    client = create_deepseek_client(api_key)
    total = len(AGENT_LABELS)
    overlay = st.empty()
    counter = {"n": 0}

    overlay.markdown(loading_overlay_html(None, 0, total), unsafe_allow_html=True)

    def on_step(agent_name):
        label = agent_name.replace(" Agent", "")
        counter["n"] += 1
        st.session_state.active_agent = label
        overlay.markdown(loading_overlay_html(label, counter["n"], total), unsafe_allow_html=True)

    try:
        results = run_multi_agent_workflow(
            client=client,
            model=model,
            resume_text=resume_text,
            job_description=job_description,
            on_step=on_step,
        )
        st.session_state.agent_outputs = results
        append_run_history(results["usage"])
        st.session_state.active_agent = None
        overlay.empty()
        st.rerun()
    except RuntimeError as exc:
        st.session_state.active_agent = None
        overlay.empty()
        st.error(str(exc))


def loading_overlay_html(agent_label, current, total) -> str:
    """Full-screen blocking overlay shown while the multi-agent workflow runs."""
    pct = int(min(current, total) / total * 100) if total else 0
    if current == 0 or not agent_label:
        running_line = "Preparing the multi-agent analysis…"
        progress_line = "Initializing"
    else:
        running_line = f"Running: {agent_label} Agent"
        progress_line = f"Agent {min(current, total)} of {total}"

    return (
        '<div class="loading-overlay">'
        '<div class="loading-card">'
        '<div class="spinner"></div>'
        '<div class="loading-title">Loading...</div>'
        f'<div class="loading-agent">{running_line}</div>'
        f'<div class="loading-progress">{progress_line}</div>'
        f'<div class="loading-bar"><div class="loading-bar-fill" style="width:{pct}%"></div></div>'
        '<div class="loading-note">Please wait — do not close or refresh this page.</div>'
        "</div></div>"
    )


def render_report_workspace():
    outputs = st.session_state.get("agent_outputs")
    if not outputs:
        render_empty_report_preview()
        return

    final_report = outputs["final_report"]
    score = extract_match_score(final_report) or "N/A"

    score_col, report_col = st.columns([1, 3], gap="large")
    with score_col:
        with st.container(border=True):
            st.metric("Job Match Score", score)
            st.caption("Estimated from the final report.")

    with report_col:
        tab_score, tab_match, tab_missing, tab_resume, tab_interview, tab_agents = st.tabs(
            [
                "Score Overview",
                "Matched Skills",
                "Missing Skills",
                "Resume Suggestions",
                "Interview Prep",
                "Agent Outputs",
            ]
        )

        with tab_score:
            st.markdown(final_report)
        with tab_match:
            st.markdown(outputs["skill_matching"])
        with tab_missing:
            st.markdown(outputs["gap_analysis"])
        with tab_resume:
            st.markdown(outputs["resume_improvement"])
        with tab_interview:
            st.markdown(outputs["interview_preparation"])
        with tab_agents:
            for key, label in AGENT_LABELS.items():
                with st.expander(label, expanded=key == "resume_analysis"):
                    st.markdown(outputs[key])


def append_run_history(usage_data: dict):
    if "usage_history" not in st.session_state:
        st.session_state.usage_history = []

    summary = usage_data["summary"]
    st.session_state.usage_history.insert(
        0,
        {
            "Date/Time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "Model": summary["model"],
            "Total Tokens": summary["total_tokens"],
            "Estimated Cost": format_usd(summary["estimated_cost_usd"]),
            "Status": "Completed",
        },
    )
    st.session_state.usage_history = st.session_state.usage_history[:10]


def render_usage_dashboard(model: str):
    outputs = st.session_state.get("agent_outputs", {})
    usage_data = outputs.get("usage", default_usage_data(model))
    summary = usage_data["summary"]
    history = st.session_state.get("usage_history", [])

    st.markdown('<div class="section-title">Usage Dashboard</div>', unsafe_allow_html=True)
    st.caption("Track model, token usage, and estimated API spend for this session.")

    metric_cols = st.columns(4, gap="large")
    with metric_cols[0]:
        render_usage_metric("Current Model", summary["model"])
    with metric_cols[1]:
        render_usage_metric("Total Tokens", f'{summary["total_tokens"]:,}')
    with metric_cols[2]:
        render_usage_metric("Estimated Spend", format_usd(summary["estimated_cost_usd"]))
    with metric_cols[3]:
        render_usage_metric("Completed Runs", str(len(history)))

    chart_col, table_col = st.columns([1.2, 1.8], gap="large")
    with chart_col:
        with st.container(border=True):
            st.markdown("#### Token Usage by Agent")
            agent_usage = usage_data["agents"]
            if agent_usage:
                chart_df = pd.DataFrame(
                    {
                        "Agent": [item["agent"] for item in agent_usage],
                        "Input Tokens": [item["input_tokens"] for item in agent_usage],
                        "Output Tokens": [item["output_tokens"] for item in agent_usage],
                    }
                ).set_index("Agent")
                st.bar_chart(chart_df)
            else:
                st.info("Run an analysis to populate token usage by agent.")

    with table_col:
        with st.container(border=True):
            st.markdown("#### Agent Cost Breakdown")
            if usage_data["agents"]:
                st.dataframe(
                    build_agent_cost_table(usage_data["agents"]),
                    hide_index=True,
                    use_container_width=True,
                )
            else:
                st.info("No completed agent usage is available yet.")

    with st.container(border=True):
        note_col, button_col = st.columns([3, 1], gap="large")
        with note_col:
            st.markdown("#### Run History")
            st.caption("Costs are approximate and based on configured token rates.")
        with button_col:
            if st.button("Clear Session Usage", use_container_width=True):
                st.session_state.pop("usage_history", None)
                if "agent_outputs" in st.session_state:
                    st.session_state.agent_outputs.pop("usage", None)
                st.rerun()

        if history:
            st.dataframe(pd.DataFrame(history), hide_index=True, use_container_width=True)
        else:
            st.info("Completed analyses will appear here during this Streamlit session.")

    if st.button("Back to Job Matching"):
        st.session_state.page_nav = "Job Matching"
        st.rerun()


def render_usage_metric(label: str, value: str):
    st.markdown(
        f'<div class="usage-metric"><div class="usage-label">{label}</div><div class="usage-value">{value}</div></div>',
        unsafe_allow_html=True,
    )


def build_agent_cost_table(agent_usage: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Agent": item["agent"],
                "Input Tokens": f'{item["input_tokens"]:,}',
                "Output Tokens": f'{item["output_tokens"]:,}',
                "Total Tokens": f'{item["total_tokens"]:,}',
                "Estimated Cost": format_usd(item["estimated_cost_usd"]),
            }
            for item in agent_usage
        ]
    )


def default_usage_data(model: str) -> dict:
    return {
        "agents": [],
        "summary": {
            "model": model,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_tokens": 0,
            "cache_hit_input_tokens": 0,
            "cache_miss_input_tokens": 0,
            "estimated_cost_usd": 0.0,
        },
    }


def render_empty_report_preview():
    with st.container(border=True):
        st.markdown('<div class="report-heading">Report Preview</div>', unsafe_allow_html=True)
        tab_score, tab_match, tab_missing, tab_resume, tab_interview = st.tabs(
            ["Score Overview", "Matched Skills", "Missing Skills", "Resume Suggestions", "Interview Prep"]
        )
        with tab_score:
            st.info("Run the multi-agent analysis to generate the job match score and final recommendation.")
        with tab_match:
            st.write("- SQL")
            st.write("- Manual testing")
            st.write("- UAT")
            st.write("- JIRA")
        with tab_missing:
            st.write("- Selenium")
            st.write("- API testing")
            st.write("- Automation testing")
        with tab_resume:
            st.write("- Add clearer QA keywords.")
            st.write("- Highlight test case execution and defect logging.")
        with tab_interview:
            st.write("- Prepare examples of manual testing, regression testing, and UAT.")


def inject_styles():
    st.markdown(
        """
        <style>
        :root {
            --page-bg: #ffffff;
            --surface: #ffffff;
            --surface-soft: #f8fbff;
            --border: #cfd9e8;
            --border-strong: #b8c7dc;
            --text: #18243a;
            --muted: #5f6f89;
            --navy: #0e2d63;
            --blue: #1f5edb;
            --blue-light: #eaf2ff;
            --blue-soft: #dbeafe;
            --green: #15934f;
            --amber: #a36a13;
            --shadow: 0 14px 34px rgba(15, 46, 99, .06);
        }
        .stApp {
            background: var(--page-bg);
            color: var(--text);
        }
        .block-container {
            max-width: 1540px;
            padding: 0 1.4rem 2rem !important;
        }
        header[data-testid="stHeader"],
        div[data-testid="stToolbar"],
        #MainMenu,
        footer {
            display: none !important;
            visibility: hidden !important;
        }
        .app-header {
            align-items: center;
            background: var(--surface);
            border-bottom: 1px solid var(--border);
            box-sizing: border-box;
            display: flex;
            gap: 1rem;
            height: 102px;
            margin: 0 -1.4rem 1.25rem;
            min-height: 102px;
            padding: 1rem 1.7rem;
        }
        .brand-mark {
            color: var(--blue);
            flex: 0 0 auto;
            height: 58px;
            width: 58px;
        }
        .brand-mark svg,
        .heading-icon svg {
            display: block;
            height: 100%;
            width: 100%;
        }
        .brand-mark svg *,
        .heading-icon svg * {
            fill: none;
            stroke: currentColor;
            stroke-linecap: round;
            stroke-linejoin: round;
            stroke-width: 2.4;
        }
        .app-header h1 {
            color: var(--navy);
            font-size: 1.8rem;
            font-weight: 850;
            line-height: 1.2;
            letter-spacing: 0;
            margin: 0 0 .4rem;
        }
        .app-header p {
            color: var(--muted);
            margin: 0;
            font-size: 1.05rem;
        }
        .stepper {
            background: var(--surface);
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            margin: -1.7rem auto .9rem;
            max-width: 1220px;
            min-height: 96px;
            position: relative;
            row-gap: 1rem;
        }
        .step-line {
            background: #cfd8e7;
            height: 2px;
            left: 7%;
            position: absolute;
            right: 7%;
            top: 24px;
            z-index: 0;
        }
        .step-line-fill {
            background: var(--blue);
            height: 2px;
            left: 0;
            position: absolute;
            top: 0;
            transition: width .35s ease;
        }
        .step-item {
            align-items: center;
            display: grid;
            justify-items: center;
            position: relative;
            text-align: center;
            z-index: 1;
        }
        .step-node {
            align-items: center;
            background: #f8fbff;
            border: 2px solid #cfd8e7;
            border-radius: 999px;
            color: #52637d;
            display: flex;
            font-size: 1.1rem;
            font-weight: 850;
            height: 44px;
            justify-content: center;
            margin-bottom: .65rem;
            width: 44px;
        }
        .step-active .step-node {
            background: var(--blue);
            border-color: var(--blue);
            color: #fff;
        }
        .step-title {
            color: var(--navy);
            font-size: 1rem;
            font-weight: 800;
            line-height: 1.25;
        }
        .step-active .step-title {
            color: var(--blue);
        }
        .step-done .step-node {
            background: var(--green);
            border-color: var(--green);
            color: #fff;
        }
        .step-done .step-title {
            color: var(--green);
        }
        .step-pending .step-node {
            background: #f1f5fb;
            border-color: #dbe3ef;
            color: #9aa8be;
        }
        .step-pending .step-title,
        .step-pending .step-caption {
            color: #9aa8be;
        }
        .lock-hint {
            background: #fff7e8;
            border: 1px solid #f0d9a8;
            border-radius: 7px;
            color: var(--amber);
            font-size: .86rem;
            font-weight: 700;
            margin-bottom: .7rem;
            padding: .5rem .65rem;
        }
        .step-caption {
            color: var(--muted);
            font-size: .9rem;
            line-height: 1.35;
            margin-top: .25rem;
        }
        .section-title {
            color: var(--navy);
            font-size: 1.2rem;
            font-weight: 850;
            margin: 1.2rem 0 .6rem 0;
        }
        div[data-testid="stElementContainer"]:has(div[data-testid="stRadio"]),
        .element-container:has(div[data-testid="stRadio"]) {
            height: 0 !important;
            margin: 0 !important;
            overflow: visible !important;
            padding: 0 !important;
        }
        div[data-testid="stRadio"] {
            display: flex;
            justify-content: flex-end;
            margin: 0;
            position: fixed;
            right: 1.35rem;
            top: 1.55rem;
            z-index: 50;
        }
        div[role="radiogroup"] {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 999px;
            display: inline-flex;
            gap: .15rem;
            margin-bottom: 0;
            padding: .25rem;
        }
        div[role="radiogroup"] label {
            border-radius: 999px;
            min-height: 32px;
            padding: .05rem .5rem;
        }
        div[role="radiogroup"] label p {
            color: var(--navy);
            font-size: .84rem;
            font-weight: 750;
        }
        .usage-metric {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            min-height: 104px;
            padding: 1rem;
        }
        .usage-label {
            color: var(--muted);
            font-size: .84rem;
            font-weight: 750;
            margin-bottom: .45rem;
        }
        .usage-value {
            color: var(--navy);
            font-size: 1.45rem;
            font-weight: 850;
            line-height: 1.2;
            overflow-wrap: anywhere;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background: var(--surface);
            border: 1px solid var(--border-strong);
            border-radius: 8px;
            box-shadow: none;
            min-height: 100%;
            padding: .9rem 1rem 1rem;
        }
        h1, h2, h3, h4 {
            color: var(--navy);
            letter-spacing: 0;
        }
        .card-heading {
            align-items: center;
            display: flex;
            gap: .78rem;
            margin: .1rem 0 .9rem;
        }
        .workflow-heading {
            margin-bottom: 1.2rem;
        }
        .heading-icon {
            color: var(--blue);
            display: inline-flex;
            height: 34px;
            width: 34px;
        }
        .card-heading h3 {
            color: var(--navy);
            font-size: 1.2rem;
            font-weight: 850;
            line-height: 1.25;
            margin: 0;
        }
        .field-label,
        .upload-label {
            color: var(--text);
            font-size: .93rem;
            font-weight: 750;
            margin-bottom: .45rem;
        }
        .upload-label {
            margin-top: .75rem;
        }
        .char-count {
            color: var(--muted);
            font-size: .9rem;
            font-weight: 650;
            margin-top: .2rem;
            text-align: right;
        }
        .generate-wrap {
            margin: 1.25rem 0 1.05rem;
        }
        div.stButton > button[kind="primary"] {
            background: var(--blue);
            border: 1px solid var(--blue);
            border-radius: 8px;
            box-shadow: var(--shadow);
            color: #fff;
            font-size: 1.04rem;
            font-weight: 800;
            min-height: 48px;
        }
        div.stButton > button:not([kind="primary"]) {
            border-radius: 8px;
            color: var(--blue);
            font-size: .9rem;
            font-weight: 700;
        }
        textarea {
            background: #ffffff !important;
            border: 1px solid var(--border) !important;
            border-radius: 7px !important;
            color: var(--text) !important;
            font-size: .96rem !important;
            line-height: 1.45 !important;
        }
        textarea::placeholder {
            color: #7d8aa2 !important;
        }
        div[data-testid="stFileUploader"] section {
            background: #ffffff;
            border: 1.5px dashed #7bb0ff;
            border-radius: 8px;
            min-height: 96px;
            padding: .65rem 1rem;
        }
        div[data-testid="stFileUploader"] section * {
            color: var(--text);
            font-size: .9rem;
        }
        div[data-testid="stFileUploader"] button {
            background: #ffffff !important;
            border: 1px solid var(--border) !important;
            border-radius: 8px !important;
            color: var(--blue) !important;
            font-weight: 800 !important;
            min-height: 38px !important;
        }
        div[data-testid="stFileUploader"] small {
            color: var(--muted) !important;
        }
        div.stButton > button {
            background: #ffffff;
            border: 1px solid var(--border);
            color: var(--navy);
        }
        .agent-row {
            align-items: center;
            display: grid;
            gap: .75rem;
            grid-template-columns: 34px 1fr auto;
            min-height: 47px;
            padding: .35rem 0;
            position: relative;
        }
        .agent-row:not(:last-child):before {
            border-left: 1.5px dashed #cbd5e1;
            bottom: -12px;
            content: "";
            left: 16px;
            position: absolute;
            top: 32px;
        }
        .agent-marker {
            align-items: center;
            border-radius: 999px;
            display: flex;
            font-size: .9rem;
            font-weight: 850;
            height: 30px;
            justify-content: center;
            width: 30px;
            z-index: 1;
        }
        .agent-row > span:nth-child(2) {
            color: var(--navy);
            font-size: .96rem;
            font-weight: 650;
        }
        .agent-state {
            border-radius: 999px;
            font-size: .82rem;
            font-weight: 800;
            padding: .16rem .25rem;
            text-align: right;
        }
        .agent-ready {
            background: var(--blue-light);
            color: var(--blue);
        }
        .agent-active {
            background: #fef3c7;
            color: var(--amber);
        }
        .agent-done {
            background: #e7f8ef;
            color: var(--green);
        }
        .agent-marker.agent-ready,
        .agent-marker.agent-active {
            border: 1px solid #cfe0fb;
        }
        .agent-marker.agent-done {
            background: var(--green);
            color: #fff;
        }
        div[data-testid="stMetric"] {
            background: #f8fbff;
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1rem;
        }
        .report-heading {
            color: var(--navy);
            font-size: 1.25rem;
            font-weight: 850;
            margin: .2rem 0 1rem;
        }
        .stTabs [data-baseweb="tab-list"] {
            background: #f5f8fc;
            border: 1px solid #dce6f2;
            border-bottom: 0;
            border-radius: 8px 8px 0 0;
            display: inline-flex;
            gap: 0;
            padding: 0;
        }
        .stTabs [data-baseweb="tab"] {
            border-right: 1px solid #dce6f2;
            border-radius: 0;
            color: var(--navy);
            font-size: .95rem;
            font-weight: 750;
            min-width: 150px;
            padding: .75rem 1rem;
        }
        .stTabs [data-baseweb="tab"]:first-child {
            border-radius: 8px 0 0 0;
        }
        .stTabs [data-baseweb="tab"][aria-selected="true"] {
            background: #ffffff;
            color: var(--blue);
        }
        .stTabs [data-baseweb="tab-highlight"] {
            background-color: var(--blue) !important;
        }
        .stAlert {
            border-radius: 8px;
        }
        .loading-overlay {
            align-items: center;
            background: rgba(13, 33, 70, 0.55);
            backdrop-filter: blur(4px);
            display: flex;
            inset: 0;
            justify-content: center;
            position: fixed;
            z-index: 100000;
        }
        .loading-card {
            align-items: center;
            background: #ffffff;
            border-radius: 16px;
            box-shadow: 0 30px 70px rgba(8, 25, 60, .4);
            display: flex;
            flex-direction: column;
            gap: .5rem;
            min-width: 300px;
            padding: 2.2rem 2.8rem;
            text-align: center;
        }
        .spinner {
            animation: spin .9s linear infinite;
            border: 5px solid #dbeafe;
            border-radius: 50%;
            border-top-color: var(--blue);
            height: 56px;
            margin-bottom: .5rem;
            width: 56px;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        .loading-title {
            color: var(--navy);
            font-size: 1.45rem;
            font-weight: 850;
        }
        .loading-agent {
            color: var(--blue);
            font-size: 1.02rem;
            font-weight: 800;
        }
        .loading-progress {
            color: var(--muted);
            font-size: .86rem;
            font-weight: 650;
        }
        .loading-bar {
            background: #e8eef8;
            border-radius: 999px;
            height: 7px;
            margin-top: .55rem;
            overflow: hidden;
            width: 100%;
        }
        .loading-bar-fill {
            background: var(--blue);
            border-radius: 999px;
            height: 100%;
            transition: width .3s ease;
        }
        .loading-note {
            color: var(--muted);
            font-size: .8rem;
            font-weight: 600;
            margin-top: .35rem;
        }
        @media (max-width: 900px) {
            .block-container {
                padding: 0 .9rem 2rem;
            }
            .app-header {
                align-items: center;
                gap: .75rem;
                margin: 0 -.9rem 1.15rem;
                height: auto;
                min-height: 104px;
                padding: 1rem;
            }
            .brand-mark {
                height: 48px;
                width: 48px;
            }
            .app-header h1 {
                font-size: 1.25rem;
            }
            .app-header p {
                font-size: .9rem;
            }
            div[data-testid="stRadio"] {
                justify-content: flex-start;
                margin: 0 0 1rem;
                position: static;
            }
            div[data-testid="stElementContainer"]:has(div[data-testid="stRadio"]),
            .element-container:has(div[data-testid="stRadio"]) {
                height: auto !important;
                overflow: visible !important;
            }
            .stepper {
                grid-template-columns: 1fr;
                margin: 1rem 0 1.1rem;
                min-height: auto;
            }
            .step-line,
            .step-line:before {
                display: none;
            }
            .step-item {
                align-items: center;
                display: grid;
                gap: .35rem .75rem;
                grid-template-columns: 44px 1fr;
                justify-items: start;
                text-align: left;
            }
            .step-node {
                grid-row: span 2;
                margin-bottom: 0;
            }
            .step-caption {
                margin-top: 0;
            }
            .stTabs [data-baseweb="tab-list"] {
                display: flex;
                overflow-x: auto;
                width: 100%;
            }
            .stTabs [data-baseweb="tab"] {
                min-width: max-content;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
