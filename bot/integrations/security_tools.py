import asyncio
import json
import os
import shlex
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import sys


class SecurityToolError(Exception):
    pass


def _run_subprocess(cmd: List[str], cwd: Optional[str] = None) -> Tuple[int, str, str]:
    try:
        proc = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return proc.returncode, proc.stdout, proc.stderr
    except FileNotFoundError:
        raise SecurityToolError(f"Command not found: {cmd[0]}")


async def run_bandit(target_path: str) -> Dict[str, int]:
    """Run bandit recursively on the target_path and return severity counts."""
    # Prefer running bandit via the current Python interpreter to avoid console-script environment mismatches
    cmd = [sys.executable, "-m", "bandit", "-f", "json", "-r", target_path]
    try:
        returncode, out, err = await asyncio.to_thread(_run_subprocess, cmd)
    except SecurityToolError:
        raise

    if returncode != 0 and not out:
        raise SecurityToolError(f"Bandit failed: {err.strip()}")

    try:
        data = json.loads(out)
    except Exception:
        raise SecurityToolError("Bandit did not return valid JSON")

    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    issues = []
    for issue in data.get("results", []):
        sev = issue.get("issue_severity", "LOW").upper()
        if sev == "HIGH":
            counts["high"] += 1
        elif sev == "MEDIUM":
            counts["medium"] += 1
        elif sev == "LOW":
            counts["low"] += 1
        else:
            counts["low"] += 1
        issues.append({
            "filename": issue.get("filename"),
            "line": issue.get("line_number"),
            "test_name": issue.get("test_name"),
            "severity": issue.get("issue_severity"),
            "message": issue.get("issue_text"),
        })

    return {"counts": counts, "issues": issues}


async def run_dependency_scan(target_path: str) -> Dict[str, int]:
    """Run pip-audit in the given path (if requirements.txt exists) or in env and return counts per severity."""
    # Try to find requirements.txt in target_path
    req = Path(target_path) / "requirements.txt"
    # Prefer running pip-audit via the current Python interpreter to avoid console-script mismatches
    cmd = [sys.executable, "-m", "pip_audit", "-f", "json"]
    if req.exists():
        cmd = [sys.executable, "-m", "pip_audit", "-r", str(req), "-f", "json"]

    try:
        returncode, out, err = await asyncio.to_thread(_run_subprocess, cmd)
    except SecurityToolError:
        # Provide actionable guidance
        raise SecurityToolError(
            "pip-audit not found in this Python environment. Install it in the venv used to run the bot:\n"
            "  . .venv/Scripts/Activate.ps1\n"
            "  python -m pip install pip-audit\n"
            "Or run: python -m pip_audit -f json"
        )

    if returncode != 0 and not out:
        raise SecurityToolError(f"pip-audit failed: {err.strip()}")

    # pip-audit json output is a list of findings; severity mapping may not be provided.
    try:
        data = json.loads(out)
    except Exception:
        raise SecurityToolError("pip-audit did not return valid JSON")

    # We will classify all findings as 'high' as pip-audit doesn't provide severity in simple form.
    counts = {"critical": 0, "high": len(data), "medium": 0, "low": 0}
    vulns = []
    for item in data:
        vulns.append({
            "name": item.get("name"),
            "version": item.get("version"),
            "vulns": item.get("vulns", []),
        })

    return {"counts": counts, "vulns": vulns}


async def run_trivy_scan(image_name: str) -> Dict[str, int]:
    """Run trivy image scan and return a summary of severities.

    Trivy must be installed and available on PATH. We call:
      trivy image --format json <image_name>
    """
    cmd = ["trivy", "image", "--format", "json", image_name]
    try:
        returncode, out, err = await asyncio.to_thread(_run_subprocess, cmd)
    except SecurityToolError:
        # Try Docker-based fallback: run the trivy container if docker is available
        docker_cmd = ["docker", "run", "--rm", "aquasec/trivy", "image", "--format", "json", image_name]
        try:
            returncode, out, err = await asyncio.to_thread(_run_subprocess, docker_cmd)
        except SecurityToolError:
            raise SecurityToolError("trivy CLI not found and docker fallback failed; install Trivy CLI or ensure Docker is available")

    if returncode != 0 and not out:
        raise SecurityToolError(f"trivy failed: {err.strip()}")

    try:
        data = json.loads(out)
    except Exception:
        raise SecurityToolError("trivy did not return valid JSON")

    # trivy JSON has 'Results' containing Vulnerabilities lists
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    vulns = []
    for result in data.get("Results", []):
        for v in result.get("Vulnerabilities", []) or []:
            sev = (v.get("Severity") or "UNKNOWN").upper()
            if sev == "CRITICAL":
                counts["critical"] += 1
            elif sev == "HIGH":
                counts["high"] += 1
            elif sev == "MEDIUM":
                counts["medium"] += 1
            elif sev == "LOW":
                counts["low"] += 1
            vulns.append({
                "vulnerability_id": v.get("VulnerabilityID"),
                "pkg": v.get("PkgName"),
                "installed": v.get("InstalledVersion"),
                "fixed": v.get("FixedVersion"),
                "severity": v.get("Severity"),
                "title": v.get("Title"),
            })

    return {"counts": counts, "vulns": vulns}


async def run_secret_scan(target_path: str) -> Dict[str, int]:
    # Use detect-secrets CLI if available
    cmd = ["detect-secrets", "scan", target_path]
    try:
        returncode, out, err = await asyncio.to_thread(_run_subprocess, cmd)
    except SecurityToolError:
        raise SecurityToolError("detect-secrets CLI not found; install detect-secrets to run secret scans")

    # The CLI prints YAML-like output; for now return raw count of lines with 'Potential secret'
    count = out.count("Potential secret") if out else 0
    return {"counts": {"potential_secrets": count}, "raw": out}


def resolve_target(target: str) -> str:
    if target == ".":
        return str(Path(os.getcwd()).resolve())
    return target
