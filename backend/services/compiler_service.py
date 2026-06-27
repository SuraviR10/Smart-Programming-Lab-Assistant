"""
Compiler Service — handles the compilation and execution of code.
Uses subprocess to securely run compilers and capture output.
"""

import subprocess
import os
import tempfile
import time
from flask import current_app


def _get_compiler_path(language: str) -> str:
    """Gets the path to the compiler for a given language."""
    if language == "c":
        # Assumes 'gcc' is in the system's PATH.
        # For Windows, this requires adding MinGW's bin to PATH.
        return "gcc"
    # Add other languages like 'g++' for C++ here
    raise ValueError(f"Unsupported language: {language}")


def compile_only(code: str, language: str = "c") -> dict:
    """
    Compiles the given code without running it.
    Returns a dictionary with compilation status and output.
    """
    compiler = _get_compiler_path(language)
    ext = {"c": "c", "cpp": "cpp"}.get(language, "tmp")

    with tempfile.TemporaryDirectory() as temp_dir:
        source_path = os.path.join(temp_dir, f"source.{ext}")
        output_path = os.path.join(temp_dir, "program.exe")

        with open(source_path, "w", encoding="utf-8") as f:
            f.write(code)

        command = [compiler, source_path, "-o", output_path, "-Wall", "-Wextra"]

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=10,  # 10-second timeout for compilation
                encoding="utf-8",
                errors="replace"
            )

            if result.returncode != 0:
                # Compilation failed
                return {
                    "compilation_success": False,
                    "compiler_output": result.stderr,
                    "status": "Compilation Error",
                }

            # Compilation succeeded
            return {
                "compilation_success": True,
                "compiler_output": result.stderr,  # May contain warnings
                "status": "Compilation Successful",
            }

        except subprocess.TimeoutExpired:
            return {"compilation_success": False, "error": "Compilation timed out."}
        except FileNotFoundError:
            current_app.logger.error(f"Compiler '{compiler}' not found. Ensure it's in the system's PATH.")
            return {"compilation_success": False, "error": f"Compiler '{compiler}' not found."}
        except Exception as e:
            current_app.logger.error(f"An unexpected error occurred during compilation: {e}")
            return {"compilation_success": False, "error": "An unexpected server error occurred."}


def compile_and_run(code: str, language: str = "c", stdin_data: str = "") -> dict:
    """
    Compiles and then runs the code with provided stdin.
    Returns a dictionary with full results.
    """
    compile_result = compile_only(code, language)
    if not compile_result["compilation_success"]:
        return compile_result

    # Since compile_only runs in a temp dir, we must re-compile here to get the executable.
    with tempfile.TemporaryDirectory() as temp_dir:
        source_path = os.path.join(temp_dir, f"source.{language}")
        output_path = os.path.join(temp_dir, "program.exe")

        with open(source_path, "w", encoding="utf-8") as f:
            f.write(code)

        compile_command = [_get_compiler_path(language), source_path, "-o", output_path]
        subprocess.run(compile_command, check=True) # We know it compiles

        start_time = time.perf_counter()
        try:
            run_result = subprocess.run(
                [output_path],
                input=stdin_data,
                capture_output=True,
                text=True,
                timeout=5,  # 5-second timeout for execution
                encoding="utf-8",
                errors="replace"
            )
            execution_time = (time.perf_counter() - start_time) * 1000

            return {
                "compilation_success": True,
                "compiler_output": compile_result.get("compiler_output", ""),
                "run_output": run_result.stdout,
                "execution_time_ms": round(execution_time),
                "status": "Execution Successful" if run_result.returncode == 0 else "Runtime Error",
                "error": run_result.stderr if run_result.returncode != 0 else None,
            }
        except subprocess.TimeoutExpired:
            return {"compilation_success": True, "status": "Runtime Error", "error": "Execution timed out (> 5 seconds)."}
        except Exception as e:
            current_app.logger.error(f"An unexpected error occurred during execution: {e}")
            return {"compilation_success": True, "status": "Runtime Error", "error": "An unexpected server error occurred during execution."}