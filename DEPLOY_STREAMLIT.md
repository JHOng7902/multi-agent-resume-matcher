# Deploying to Streamlit Community Cloud (free)

This publishes the app to a public URL like
`https://<your-app>.streamlit.app`. It's free, official, and needs no server config.
The only requirement: your code must be in a **GitHub repository**.

No code changes are needed. You enter `DEEPSEEK_API_KEY` / `DEEPSEEK_MODEL` in the
Streamlit **Secrets** box; Streamlit exposes top-level secrets as environment variables,
so the app's `os.getenv(...)` reads them automatically. Your `.env` is never pushed.

## Step 1 — Put the code on GitHub
You have no commits or remote yet. From the project root:

```bash
git add .
git commit -m "Initial commit: Multi-Agent Resume & Job Matching Assistant"
```

Then create an EMPTY repo on https://github.com/new (no README/.gitignore), and:

```bash
git remote add origin https://github.com/<your-username>/<repo-name>.git
git branch -M main
git push -u origin main
```

Confirm `.env` did NOT get pushed (it's gitignored) — your key must stay private.

## Step 2 — Connect Streamlit Community Cloud
1. Go to https://share.streamlit.io and sign in with GitHub (authorize access to the repo).
2. Click **Create app** -> **Deploy a public app from GitHub**.
3. Fill in:
   - **Repository:** `<your-username>/<repo-name>`
   - **Branch:** `main`
   - **Main file path:** `app.py`
4. Expand **Advanced settings -> Secrets** and paste (see `.streamlit/secrets.toml.example`):
   ```toml
   DEEPSEEK_API_KEY = "sk-your-real-deepseek-key"
   DEEPSEEK_MODEL = "deepseek-v4-flash"
   ```
5. Click **Deploy**. First build takes ~2–3 min (it installs `requirements.txt`).

## Updating the app
Push to the same branch — Streamlit redeploys automatically:
```bash
git add . && git commit -m "Update" && git push
```
Change the key later via **Manage app -> Settings -> Secrets** (the app reboots on save).

## Troubleshooting
- **"Missing DeepSeek configuration":** the Secrets box is empty or has the wrong key name.
  Fix it in Settings -> Secrets and reboot the app.
- **Build fails on a package:** check the build logs in the Streamlit Cloud UI; usually a
  pin in `requirements.txt`.
- **App sleeps after inactivity:** free apps idle out and wake on the next visit (a few seconds).
