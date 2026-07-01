# Multi-Agent Resume & Job Matching Assistant

## Overview

Multi-Agent Resume & Job Matching Assistant is an MVP web app that compares a candidate resume with a job description and generates a structured, visual job-fit report.

The app uses seven specialized AI agents instead of one large prompt. Each agent focuses on one part of the process: resume analysis, job description analysis, skill matching, gap analysis, resume improvement, interview preparation, and final report generation. The agents run in five stages, with independent agents executing in parallel to reduce waiting time.

**Live app:** deploy on Streamlit Community Cloud (see [Deployment](#deployment)).
**Repository:** https://github.com/JHOng7902/multi-agent-resume-matcher

## Problem Statement

Job seekers often apply for roles without knowing how well their resume matches the job description. This project helps users identify matched skills, missing skills, resume weaknesses, and interview preparation points.

## Key Features

- **Seven specialized agents** run as a five-stage pipeline (independent agents run in parallel).
- **Guided workflow** — a 4-step stepper (Resume → Job Description → Analyze → Report) with sequential gating: the job-description step is locked until a resume is provided, and analysis is disabled until both inputs exist.
- **Loading interceptor** — a full-screen overlay shows the live running agent and blocks interaction during analysis.
- **Visual report** — a job-match score gauge, a matched/partial/missing skills chart, and colored skill chips, plus tabbed detail (Score, Matched, Missing, Resume Suggestions, Interview Prep, Agent Outputs).
- **One-click PDF export** — compiles the full report and all agent outputs into a single downloadable PDF.
- **Usage Dashboard** — per-agent token usage and estimated API cost for the session.
- **Clear All** — resets inputs, uploads, report, and usage in one click.
- **File uploads** — resume as PDF; job description as PDF, DOCX, or TXT.

## Tech Stack

- Python
- Streamlit
- DeepSeek API (OpenAI-compatible Python client)
- pypdf, python-docx (file extraction)
- reportlab (PDF export)
- pandas, altair (report visualizations)
- pytest (tests)

## Setup

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Create a `.env` file:

```text
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_MODEL=deepseek-v4-flash
```

DeepSeek setup is intentionally hidden from the app view. The API key and model are read only from environment variables (`.env` locally, or Secrets when deployed). Editing `.env` requires a full app restart to take effect.

## Run The App

```bash
python -m streamlit run app.py
```

The app opens at http://localhost:8501.

## Multi-Agent Architecture

The seven agents run in five stages. Independent agents run concurrently; dependent agents wait for the data they need. Each agent's output is accumulated into a shared context that later agents receive in full, so no information is dropped between steps.

```text
Resume Input        Job Description Input
     |                       |
     +----------+------------+
                |
   STAGE 1 (parallel)
   Resume Analyzer  ||  Job Description Analyzer
                |
   STAGE 2  Skill Matching
                |
   STAGE 3  Gap Analysis
                |
   STAGE 4 (parallel)
   Resume Improvement  ||  Interview Preparation
                |
   STAGE 5  Final Report
                |
                v
   Report Insights (parse score + skill buckets)
                |
        +-------+-------+
        |               |
   Visual Report    PDF Export
```

## Agent Responsibilities

| Agent | Responsibility |
| --- | --- |
| Resume Analyzer Agent | Extracts education, experience, skills, projects, achievements, strengths, and weaknesses. |
| Job Description Analyzer Agent | Extracts job title, responsibilities, required skills, preferred skills, tools, and hidden expectations. |
| Skill Matching Agent | Compares resume analysis with job requirements (matched, partial, missing). |
| Gap Analysis Agent | Identifies major gaps, minor gaps, risks, and improvement priorities. |
| Resume Improvement Agent | Suggests honest resume improvements without inventing experience. |
| Interview Preparation Agent | Generates likely questions, answer directions, and study topics. |
| Final Report Agent | Combines all outputs into a structured job matching report with a score. |

## Performance

- **Parallel stages:** the two independent agent pairs run concurrently, cutting wall-clock time versus running all seven sequentially.
- **Output caps + concise prompts:** each agent has a `max_tokens` cap and is prompted for concise bullet output, reducing generation time and cost.
- **Resilient calls:** if a reply comes back empty or truncated, the agent falls back to any reasoning content and retries once with a larger token budget before failing.

## Sample Resume Input

```text
Business Analytics graduate with experience in Python, SQL, Power BI, Angular, TypeScript, manual testing, UAT, regression testing, and JIRA defect logging. Worked as Software Engineer II and supported software development, validation, troubleshooting, and system testing activities.
```

## Sample Job Description Input

```text
We are hiring a Software Tester. Responsibilities include preparing test cases, executing manual testing, performing regression testing, supporting UAT, logging defects in JIRA, and working with developers. Knowledge of SQL, Selenium, and API testing will be an advantage.
```

## The Report

The on-screen report includes:

- A job-match **score gauge** with a suitability label
- A **skills overview** chart and colored chips (matched / partial / missing)
- Tabs: Score Overview, Matched Skills, Missing Skills, Resume Suggestions, Interview Prep, Agent Outputs

The final report content covers: job match score, overall suitability, detected role category, matched / partially matched / missing skills, major gaps, resume improvement suggestions, a suggested resume summary, interview preparation, and a final recommendation.

### PDF Export

The **Export Report** button compiles the final report, every agent's output, and a usage summary into a single PDF (rendered with reportlab) and downloads it.

## Usage Dashboard

The app includes a `Usage Dashboard` page for cost transparency. It shows:

- Current model from the environment
- Total input, output, and combined tokens
- Estimated API spend
- Per-agent token and cost breakdown
- Recent run history for the current Streamlit session

Costs are approximate. Defaults use DeepSeek's published USD per 1M token pricing for `deepseek-v4-flash` and `deepseek-v4-pro`, and can be overridden in `.env` if pricing changes.

## Deployment

The app deploys free on **Streamlit Community Cloud**:

1. Push the repository to GitHub.
2. At https://share.streamlit.io, create an app from the repo, branch `main`, main file `app.py`.
3. Under **Advanced settings → Secrets**, add:
   ```toml
   DEEPSEEK_API_KEY = "sk-your-real-key"
   DEEPSEEK_MODEL = "deepseek-v4-flash"
   ```
4. Deploy. Streamlit auto-redeploys on every push to `main`.

Streamlit exposes top-level secrets as environment variables, so no code changes are needed between local and cloud runs. See `DEPLOY_STREAMLIT.md` for the full walkthrough.

## Testing

```bash
python -m pytest -q
```

Unit tests cover the agent workflow, file extraction, prompts, usage/cost accounting, report insights parsing, PDF export, and app helper functions.

## Limitations

- The score is AI-assisted guidance, not a hiring decision.
- Output quality depends on the detail of the resume and job description.
- Resume PDF extraction works best with text-based PDFs, not scanned image resumes.
- Emoji or non-Latin characters in agent output may not render as glyphs in the exported PDF.
- Usage cost is an estimate based on API response token counts and configured token rates.
- The MVP does not include login, user accounts, or database storage.

## Future Enhancements

- DOCX resume upload
- ATS keyword score
- Cover letter generation
- Resume rewrite mode
- Multiple job description comparison
- Saved report history across sessions
