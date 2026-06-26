"""
Compiler Service — safe GCC wrapper
  - Writes code to temp file
  - Compiles with GCC
  - Executes with stdin, timeout, and output size limits
  - Returns structured result dict
"""

import os
import re
import uuid
import subprocess
import tempfile
import time
from flask import current_app


SUPPORTED_LANGUAGES = {
    "c": {"ext": ".c", "compiler": "gcc", "flags": ["-o", "{binary}", "{source}", "-lm"], "run": "{binary}"},
    "cpp": {"ext": ".cpp", "compiler": "g++", "flags": ["-o", "{binary}", "{source}", "-lm"], "run": "{binary}"},
}


def _sanitize_output(text: str, max_size: int) -> str:
    """Trim and sanitize program output."""
    if not text:
        return ""
    if len(text) > max_size:
        text = text[:max_size] + "\n... [output truncated]"
    return text


def compile_and_run(code: str, language: str = "c", stdin_data: str = "") -> dict:
    """
    Compile and optionally run student code.

    Returns:
        {
            "compilation_success": bool,
            "compiler_output": str,
            "run_output": str,
            "execution_time_ms": float,
            "memory_kb": float,
            "error": str | None,
            "status": "ok" | "compile_error" | "runtime_error" | "timeout" | "unsupported"
        }
    """
    language = language.lower()
    if language not in SUPPORTED_LANGUAGES:
        return {"status": "unsupported", "error": f"Language '{language}' is not supported.", "compilation_success": False}

    lang_cfg = SUPPORTED_LANGUAGES[language]
    gcc_path = current_app.config.get("GCC_PATH", lang_cfg["compiler"])
    timeout = current_app.config.get("EXECUTION_TIMEOUT", 10)
    max_out = current_app.config.get("MAX_OUTPUT_SIZE", 65536)

    # Create temp directory for this run
    with tempfile.TemporaryDirectory(prefix="labmind_") as tmpdir:
        run_id = uuid.uuid4().hex[:8]
        source_path = os.path.join(tmpdir, f"prog_{run_id}{lang_cfg['ext']}")
        binary_path = os.path.join(tmpdir, f"prog_{run_id}")

        # Write source file
        with open(source_path, "w", encoding="utf-8") as f:
            f.write(code)

        # Build compile command
        compile_cmd = [gcc_path] + [
            arg.replace("{binary}", binary_path).replace("{source}", source_path)
            for arg in lang_cfg["flags"]
        ]

        # ── COMPILE ──
        try:
            compile_result = subprocess.run(
                compile_cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            return {"status": "compile_error", "compilation_success": False,
                    "compiler_output": "Compilation timed out.", "run_output": "", "error": "Compilation timeout"}
        except FileNotFoundError:
            return {"status": "compile_error", "compilation_success": False,
                    "compiler_output": f"Compiler not found: {gcc_path}. Ensure GCC is installed.",
                    "run_output": "", "error": "Compiler not found"}

        compiler_stderr = compile_result.stderr.strip()
        compiler_stdout = compile_result.stdout.strip()
        compiler_output = (compiler_stderr or compiler_stdout).strip()

        if compile_result.returncode != 0:
            return {
                "status": "compile_error",
                "compilation_success": False,
                "compiler_output": _sanitize_output(compiler_output, max_out),
                "run_output": "",
                "execution_time_ms": None,
                "memory_kb": None,
                "error": "Compilation failed",
            }

        # ── RUN ──
        run_cmd = [binary_path]
        start_time = time.perf_counter()
        try:
            run_result = subprocess.run(
                run_cmd,
                input=stdin_data,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            elapsed_ms = (time.perf_counter() - start_time) * 1000
        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "compilation_success": True,
                "compiler_output": "",
                "run_output": "",
                "execution_time_ms": timeout * 1000,
                "memory_kb": None,
                "error": f"Program exceeded time limit of {timeout} seconds (possible infinite loop).",
            }
        except Exception as exc:
            return {
                "status": "runtime_error",
                "compilation_success": True,
                "compiler_output": "",
                "run_output": "",
                "execution_time_ms": None,
                "memory_kb": None,
                "error": str(exc),
            }

        run_output = _sanitize_output(run_result.stdout, max_out)
        run_stderr  = _sanitize_output(run_result.stderr, max_out)

        if run_result.returncode != 0 and run_stderr:
            return {
                "status": "runtime_error",
                "compilation_success": True,
                "compiler_output": "",
                "run_output": run_stderr,
                "execution_time_ms": round(elapsed_ms, 2),
                "memory_kb": None,
                "error": f"Runtime error (exit code {run_result.returncode})",
            }

        return {
            "status": "ok",
            "compilation_success": True,
            "compiler_output": compiler_output or "Compilation successful.",
            "run_output": run_output,
            "execution_time_ms": round(elapsed_ms, 2),
            "memory_kb": None,
            "error": None,
        }


def compile_only(code: str, language: str = "c") -> dict:
    """
    Compile without executing. Used for quick error checking.
    Returns: {"compilation_success": bool, "compiler_output": str, "errors": list}
    """
    result = compile_and_run(code, language, stdin_data="")
    errors = parse_compiler_errors(result.get("compiler_output", ""))
    return {
        "compilation_success": result["compilation_success"],
        "compiler_output": result.get("compiler_output", ""),
        "errors": errors,
        "status": result["status"],
    }


def parse_compiler_errors(compiler_output: str) -> list:
    """
    Parse GCC error output into structured error objects.
    Each error: {"file": str, "line": int, "col": int, "type": str, "message": str, "raw": str}
    """
    errors = []
    # GCC format: filename:line:col: error|warning|note: message
    pattern = re.compile(
        r"^(?P<file>[^:]+):(?P<line>\d+):(?P<col>\d+):\s+(?P<type>error|warning|note):\s+(?P<message>.+)$",
        re.MULTILINE,
    )
    for match in pattern.finditer(compiler_output):
        errors.append({
            "file": match.group("file"),
            "line": int(match.group("line")),
            "col": int(match.group("col")),
            "type": match.group("type"),
            "message": match.group("message").strip(),
            "raw": match.group(0),
        })
    # If structured parsing found nothing, return raw lines as a single error
    if not errors and compiler_output.strip():
        errors.append({
            "file": None, "line": None, "col": None,
            "type": "error", "message": compiler_output.strip(), "raw": compiler_output.strip(),
        })
    return errors


def run_test_case(code: str, test_input: str, expected_output: str, language: str = "c") -> dict:
    """
    Run code against a single test case and compare output.
    Returns: {"passed": bool, "actual_output": str, "expected_output": str, "execution_time_ms": float}
    """
    result = compile_and_run(code, language, stdin_data=test_input or "")

    if not result["compilation_success"]:
        return {
            "passed": False,
            "actual_output": "",
            "expected_output": expected_output,
            "execution_time_ms": None,
            "status": result["status"],
            "error": result.get("error"),
        }

    if result["status"] != "ok":
        return {
            "passed": False,
            "actual_output": result.get("run_output", ""),
            "expected_output": expected_output,
            "execution_time_ms": result.get("execution_time_ms"),
            "status": result["status"],
            "error": result.get("error"),
        }

    actual = (result["run_output"] or "").strip()
    expected = (expected_output or "").strip()
    passed = actual == expected

    return {
        "passed": passed,
        "actual_output": actual,
        "expected_output": expected,
        "execution_time_ms": result.get("execution_time_ms"),
        "status": "ok",
        "error": None,
    }
