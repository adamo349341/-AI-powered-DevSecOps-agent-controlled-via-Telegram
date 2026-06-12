# DevSecOps Telegram Agent

An AI-assisted DevSecOps agent that exposes GitLab CI/CD controls and security workflows through Telegram.

## What changed (recent)
- New commands: `/myid` (returns your numeric chat id) and `/detect` (download a GitLab project archive and run local SAST + dependency scans).
- Scanners now run via the running Python interpreter (e.g. `python -m bandit`) so CLI tools must be installed into the same virtual environment that runs the bot.
- Trivy-based container scanning has a Docker-container fallback when the native `trivy` binary is not present; Docker daemon must be running for that fallback.
- The pipeline poller runs in a resilient background task (no optional PTB job-queue extras required) and uses retry/backoff for Telegram notifications.
- Generated scan artifacts are ignored by `.gitignore` (they were removed from the repo).

## Features
- Trigger and monitor GitLab pipelines
- Cancel running pipelines and fetch job logs
- Security scan orchestration: SAST (Bandit), dependency auditing (pip-audit), container scanning (Trivy), secret detection (detect-secrets)
- Project-level detection via `/detect` (downloads archive and runs scans)
- Notifications in Telegram for pipeline status changes
- Small AI agent stub for intent parsing (Anthropic Claude integration is scaffolded but remediation suggestions are a work in progress)

## Quick local run (recommended for development)
1. Copy `.env.example` to `.env` and populate the values (see Required environment variables below).
2. Create and activate a Python virtual environment and install requirements:

   ```powershell
   python -m venv .venv
   . .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

3. Install optional scanner tools into the same environment if you plan to use them there:

   ```powershell
   pip install bandit pip-audit detect-secrets
   # Either install trivy on the host, or ensure Docker Desktop is running for the Trivy Docker fallback
   ```

4. Start the bot in polling mode:

   ```powershell
   # with the virtualenv activated
   python -m bot.main
   ```

Notes:
- If you see a Bandit "pbr" or similar ModuleNotFoundError when running scans, install the scanner into the same venv or run via `python -m bandit` as shown above.
- For Trivy container scans the Docker daemon must be running (Docker Desktop on Windows). If you prefer not to use Docker, install the `trivy` binary on the host and make it available in PATH.

## Required / recommended environment variables
- `TELEGRAM_TOKEN` — bot token from BotFather
- `BOT_ADMIN_IDS` — comma-separated numeric Telegram chat ids for administrator notifications (use `/myid` to get your id)
- `GITLAB_TOKEN` — personal access token with API/read_repo and pipeline access
- `GITLAB_BASE_URL` — e.g. `https://gitlab.com` (defaults to public GitLab when not set)
- `GITLAB_PROJECTS` — comma-separated project IDs or paths the poller should watch
- `ANTHROPIC_API_KEY` — optional, for AI intent parsing (agent stub)
- `LOG_LEVEL` — optional, e.g. `INFO` or `DEBUG`

## Telegram commands (current)
- `/start`
- `/help`
- `/status`
- `/myid` — returns your numeric Telegram chat id (useful to populate `BOT_ADMIN_IDS`)
- `/run_pipeline [project] [branch]`
- `/stop_pipeline [pipeline_id]`
- `/logs [pipeline_id] [job_name]`
- `/scan [type] [target]` — supported types: `sast`, `deps`, `docker`, `secrets`
- `/detect [project_id_or_path] [ref]` — download the project archive and run Bandit + pip-audit on it
- `/deploy [env] [version]`
- `/alerts`

## Scanners & behavior notes
- Bandit and pip-audit are executed using the bot's Python interpreter (module form). Make sure those packages are installed into the same `.venv` used to run the bot.
- Trivy runs the native `trivy` binary when available; otherwise the bot will try to run the official Trivy Docker container. Running via Docker requires a working Docker daemon.
- Secret scanning uses `detect-secrets` and runs similarly from the active interpreter.

## Files and utilities
- `bot/` — main bot code, handlers, integrations
- `bot/integrations/security_tools.py` — runner wrappers for Bandit, pip-audit, Trivy, detect-secrets
- `bot/integrations/gitlab.py` — async GitLab REST client (archive download, pipelines, jobs)
- `bot/notifications/poller.py` — background poller that notifies admins of pipeline status changes
- `tools/generate_report.py` — generates a demo PDF report (`rapport_devsecops.pdf`)

## Troubleshooting
- Use `/myid` to get your chat id and add it to `BOT_ADMIN_IDS` in `.env`. Restart the bot if you change `.env`.
- If pipeline jobs return 404 during poller checks it can indicate incorrect project IDs or token scope; verify `GITLAB_PROJECTS` and `GITLAB_TOKEN` scopes.
- If Trivy via Docker fails, ensure Docker Desktop is started and the daemon is running.

## Roadmap / TODO
- Wire AI remediation suggestions to scan results (currently an agent stub exists)
- Add `/report` command to upload aggregated scan artifacts and the generated PDF to Telegram for evidence/demos
- Optional: support webhook mode for production deployment (currently runs in polling mode for development)
