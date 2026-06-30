# Multi-Agent Resume & Job Matching Assistant

## Overview

Multi-Agent Resume & Job Matching Assistant is a class-assignment MVP that compares a candidate resume with a job description and generates a structured job-fit report.

The app uses seven specialized AI agents instead of one large prompt. Each agent focuses on one part of the process: resume analysis, job description analysis, skill matching, gap analysis, resume improvement, interview preparation, and final report generation.

## Problem Statement

Job seekers often apply for roles without knowing how well their resume matches the job description. This project helps users identify matched skills, missing skills, resume weaknesses, and interview preparation points.

## Tech Stack

- Python
- Streamlit
- DeepSeek API
- OpenAI-compatible Python client
- pypdf
- pytest

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

DeepSeek setup is intentionally hidden from the app view. The API key and model are read only from `.env`.

## Run The App

```bash
python -m streamlit run app.py
```

## Multi-Agent Architecture

```text
Resume Input
    |
    v
Resume Analyzer Agent
    |
    v
Job Description Analyzer Agent
    |
    v
Skill Matching Agent
    |
    v
Gap Analysis Agent
    |
    v
Resume Improvement Agent
    |
    v
Interview Preparation Agent
    |
    v
Final Report Agent
    |
    v
Job Matching Report
```

## Agent Responsibilities

| Agent | Responsibility |
| --- | --- |
| Resume Analyzer Agent | Extracts education, experience, skills, projects, achievements, strengths, and weaknesses. |
| Job Description Analyzer Agent | Extracts job title, responsibilities, required skills, preferred skills, tools, and hidden expectations. |
| Skill Matching Agent | Compares resume analysis with job requirements. |
| Gap Analysis Agent | Identifies major gaps, minor gaps, risks, and improvement priorities. |
| Resume Improvement Agent | Suggests honest resume improvements without inventing experience. |
| Interview Preparation Agent | Generates likely questions, answer directions, and study topics. |
| Final Report Agent | Combines all outputs into a structured job matching report. |

## Sample Resume Input

```text
Business Analytics graduate with experience in Python, SQL, Power BI, Angular, TypeScript, manual testing, UAT, regression testing, and JIRA defect logging. Worked as Software Engineer II and supported software development, validation, troubleshooting, and system testing activities.
```

## Sample Job Description Input

```text
We are hiring a Software Tester. Responsibilities include preparing test cases, executing manual testing, performing regression testing, supporting UAT, logging defects in JIRA, and working with developers. Knowledge of SQL, Selenium, and API testing will be an advantage.
```

## Example Output Summary

The final report includes:

- Job match score
- Overall suitability
- Matched skills
- Partially matched skills
- Missing skills
- Major gaps
- Resume improvement suggestions
- Suggested resume summary
- Interview preparation points
- Final recommendation

## Usage Dashboard

The app includes a `Usage Dashboard` page for class-demo transparency. It shows:

- Current model from `.env`
- Total input, output, and combined tokens
- Estimated API spend
- Per-agent token and cost breakdown
- Recent run history for the current Streamlit session

Costs are approximate. Defaults use DeepSeek's published USD per 1M token pricing for `deepseek-v4-flash` and `deepseek-v4-pro`, and can be overridden in `.env` if pricing changes.

## Limitations

- The score is AI-assisted guidance, not a hiring decision.
- Output quality depends on the detail of the resume and job description.
- Resume PDF extraction works best with text-based PDFs, not scanned image resumes.
- Job description uploads support PDF, DOCX, and TXT files.
- Usage cost is an estimate based on API response token counts and configured token rates.
- The MVP does not include login, history, export, deployment, or database storage.

## Future Enhancements

- PDF report export
- DOCX resume upload
- ATS keyword score
- Cover letter generation
- Resume rewrite mode
- Multiple job description comparison
- Saved report history
- Deployment to a public demo site
