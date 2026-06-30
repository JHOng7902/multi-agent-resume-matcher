# Screenshots Guide

Use these screenshots for the class submission or presentation.

## Screenshot Order

1. **Home and Workflow**
   - Show the app title, subtitle, and four-step workflow.
   - Do not show DeepSeek setup in the app. Configuration is read from `.env`.

2. **Resume Input**
   - Show the resume text area and PDF upload area.
   - If using PDF upload, show the extracted resume preview expander.

3. **Job Description Input**
   - Show the job description text area.
   - Show the PDF, DOCX, and TXT upload control.
   - Use the sample Software Tester job description button for a quick demo.

4. **Running Agent Status**
   - Capture the status panel while it shows one of the agents running.
   - Explain that each agent is a separate DeepSeek API call.

5. **Final Report**
   - Show the job match score and final report tab.

6. **Agent Outputs**
   - Show the expandable outputs for each specialized agent.

7. **Resume Suggestions and Interview Prep**
   - Show role-specific resume improvement suggestions and interview questions.

8. **Usage Dashboard**
   - Show the current model, total tokens, estimated spend, token usage by agent, and run history.
   - Explain that token costs are approximate and based on configured rates.

## Presentation Script

This project is a Multi-Agent Resume & Job Matching Assistant. The user provides a resume and a job description. The system then runs seven specialized AI agents. One agent analyzes the resume, one analyzes the job description, one compares skills, one identifies gaps, one suggests resume improvements, one prepares interview guidance, and the final agent creates a structured job-fit report.

The purpose is to help job seekers understand whether their resume fits a role, what skills are missing, how to improve their resume honestly, and what interview topics they should prepare.

## Demo Tips

- Prepare a short resume sample before presenting.
- Use the sample job description button if time is limited.
- Keep the DeepSeek API key ready before starting the demo.
- Add the DeepSeek API key to `.env` before starting the demo.
- Mention that the MVP stores outputs only in the current Streamlit session.
- Explain that the match score is guidance, not an official hiring decision.
