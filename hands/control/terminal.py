"""
MIO System Agent - Terminal, CLI & Shell Command Execution Engine (hands.control.terminal)

Provides safe, high-performance command execution, environment variable management,
and PowerShell script dispatch with timeout guards and process isolation.
"""

import os
import subprocess
import time
from typing import Any

# Forbidden commands for safety guardrails
FORBIDDEN_COMMANDS = [
    "format ",
    "rmdir /s /q c:\\windows",
    "del /f /s /q c:\\windows",
    "diskpart",
    ":(){ :|:& };:",
    "drop database",
]


def _is_command_safe(cmd: str) -> tuple[bool, str]:
    """Inspects command line for catastrophic system destruction patterns."""
    lower = cmd.lower().strip()
    for forbidden in FORBIDDEN_COMMANDS:
        if forbidden in lower:
            return False, f"Command contains blocked destructive pattern: '{forbidden.strip()}'."
    return True, "Safe"


def run_command(
    command: str,
    timeout: int = 30,
    cwd: str | None = None,
    shell: str = "powershell",
) -> dict[str, Any]:
    """
    Executes a shell command (PowerShell or cmd) with timeout protection and stdout/stderr capture.

    Args:
        command: Command string to execute.
        timeout: Maximum execution time in seconds (default 30s).
        cwd: Working directory (defaults to current working directory).
        shell: 'powershell' or 'cmd' (default 'powershell').
    """
    if not command or not isinstance(command, str):
        return {"success": False, "message": "Command must be a non-empty string."}

    is_safe, reason = _is_command_safe(command)
    if not is_safe:
        return {"success": False, "command": command, "message": f"Execution blocked: {reason}"}

    working_dir = os.path.abspath(cwd) if cwd and os.path.isdir(cwd) else os.getcwd()
    clean_shell = shell.lower().strip()

    if clean_shell == "cmd":
        args = ["cmd.exe", "/c", command]
    else:
        args = ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", command]

    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            args,
            cwd=working_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        duration_ms = round((time.perf_counter() - t0) * 1000, 1)

        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()
        exit_code = proc.returncode

        return {
            "success": exit_code == 0,
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "duration_ms": duration_ms,
            "command": command,
            "cwd": working_dir,
            "message": stdout if exit_code == 0 and stdout else (stderr if stderr else f"Process exited with code {exit_code} ({duration_ms}ms).")
        }

    except subprocess.TimeoutExpired:
        duration_ms = round((time.perf_counter() - t0) * 1000, 1)
        return {
            "success": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Command timed out after {timeout} seconds.",
            "duration_ms": duration_ms,
            "command": command,
            "cwd": working_dir,
            "message": f"Command execution timed out after {timeout}s."
        }
    except Exception as err:
        duration_ms = round((time.perf_counter() - t0) * 1000, 1)
        return {
            "success": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": str(err),
            "duration_ms": duration_ms,
            "command": command,
            "cwd": working_dir,
            "message": f"Failed to execute command: {err}"
        }


def run_powershell_script(script_text: str, timeout: int = 45) -> dict[str, Any]:
    """
    Executes a multi-line PowerShell script block.
    """
    if not script_text or not isinstance(script_text, str):
        return {"success": False, "message": "Script text is required."}

    return run_command(script_text, timeout=timeout, shell="powershell")


def get_environment_variable(name: str) -> dict[str, Any]:
    """
    Retrieves the value of a system or user environment variable.
    """
    if not name or not isinstance(name, str):
        return {"success": False, "message": "Variable name is required."}

    val = os.environ.get(name.strip())
    if val is not None:
        return {
            "success": True,
            "name": name.strip(),
            "value": val,
            "message": f"{name.strip()}={val}"
        }
    return {
        "success": False,
        "name": name.strip(),
        "value": None,
        "message": f"Environment variable '{name.strip()}' is not set."
    }


def set_environment_variable(name: str, value: str, permanent: bool = False) -> dict[str, Any]:
    """
    Sets an environment variable in the current process, and optionally in Windows user environment.
    """
    if not name or not isinstance(name, str):
        return {"success": False, "message": "Variable name is required."}

    clean_name = name.strip()
    clean_val = str(value)

    os.environ[clean_name] = clean_val

    if permanent:
        res = run_command(f"[Environment]::SetEnvironmentVariable('{clean_name}', '{clean_val}', 'User')")
        if not res.get("success"):
            return {
                "success": True,
                "name": clean_name,
                "value": clean_val,
                "permanent": False,
                "message": f"Set {clean_name} for current session, but failed to persist to Windows registry: {res.get('message')}"
            }
        return {
            "success": True,
            "name": clean_name,
            "value": clean_val,
            "permanent": True,
            "message": f"Permanently set environment variable {clean_name}={clean_val} for current user."
        }

    return {
        "success": True,
        "name": clean_name,
        "value": clean_val,
        "permanent": False,
        "message": f"Set environment variable {clean_name}={clean_val} for active session."
    }
