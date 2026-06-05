# DevSecOps Telegram Agent

An AI-powered DevSecOps agent that exposes a full GitLab CI/CD and security workflow through Telegram.

## Features
- Trigger and monitor GitLab pipelines
- Cancel running pipelines and fetch job logs
- Security scan orchestration for SAST, dependency auditing, container vulnerability scanning, and secret detection
- Deploy workflows with confirmation for production
- AI intent parsing via Anthropic Claude

## Setup
1. Copy `.env.example` to `.env` and populate secrets.
2. Build the Docker image:
   ```powershell
   docker-compose build
   ```
3. Start the services:
   ```powershell
   docker-compose up -d
   ```

## Required environment variables
- `TELEGRAM_TOKEN`
- `GITLAB_TOKEN`
- `GITLAB_BASE_URL`
- `GITLAB_PROJECTS`
- `ANTHROPIC_API_KEY`

## Telegram commands
- `/start`
- `/help`
- `/status`
- `/run_pipeline [project] [branch]`
- `/stop_pipeline [pipeline_id]`
- `/logs [pipeline_id] [job_name]`
- `/scan [type] [target]`
- `/deploy [env] [version]`
- `/alerts`
