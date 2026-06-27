"""
AI Service — wraps LLM providers for:
  - Compiler error explanation
  - Runtime error explanation
  - Guided debugging hints
  - AI chat assistant
  - Personalized learning recommendations
  - Program difficulty warnings
"""

import re
import os
from flask import current_app


# ─────────────────────────────────────────────
#  SYSTEM PROMPTS
# ─────────────────────────────────────────────
ERROR_ANALYSIS_SYSTEM = """You are an intelligent programming tutor for beginner C programming students.
When given a compiler or runtime error message and the student's code, you must:
1. Explain the error in simple, beginner-friendly language (avoid jargon).
2. Tell the student exactly what went wrong and on which line.
3. Provide a short, actionable hint to fix it WITHOUT giving the complete corrected code.
4. Give a brief educational tip about the underlying concept.

Respond ONLY as valid JSON with this exact structure:
{
  "error_type": "<syntax|runtime|linker|logic>",
  "error_line": <line number as integer or null>,
  "title": "<short error title>",
  "explanation": "<beginner-friendly explanation in 2-3 sentences>",
  "hint": "<specific actionable hint — do not give complete solution>",
  "tip": "<educational tip about the concept behind this error>"
}"""

DEBUGGING_SYSTEM = """You are a patient debugging mentor for beginner programmers.
Your role is to guide students through the debugging process step by step.
NEVER provide complete corrected code. Instead:
- Ask clarifying questions to help the student think.
- Point to the area of concern.
- Give hints that lead the student to discover the solution themselves.
- Explain the concept behind the bug.
Keep responses concise and encouraging."""

CHAT_SYSTEM = """You are an AI programming lab assistant for computer science students.
Your role is to:
- Explain programming concepts clearly.
- Help students understand errors and bugs.
- Guide debugging without giving direct solutions.
- Recommend learning strategies.
- Answer theory questions.

You MUST NOT:
- Write complete solutions to programming assignments.
- Do homework for students.
- Provide code that directly solves the current assignment.

Always encourage independent thinking. Be friendly, patient, and supportive."""

RECOMMENDATION_SYSTEM = """You are a learning analytics expert for programming education.
Given a student's performance data, generate personalized learning recommendations.
Respond as valid JSON with this structure:
{
  "risk_level": "<low|medium|high>",
  "summary": "<2-sentence performance summary>",
  "weak_areas": ["<area1>", "<area2>"],
  "recommendations": [
    {"type": "<concept|practice|resource>", "title": "<title>", "description": "<description>"}
  ],
  "encouragement": "<motivational message>"
}"""


def _get_client():
    """Return the configured LLM client."""
    provider = current_app.config.get("AI_PROVIDER", "openai")

    if provider == "openai":
        try:
            from openai import OpenAI
            return "openai", OpenAI(api_key=current_app.config["OPENAI_API_KEY"])
        except ImportError:
            raise RuntimeError("openai package not installed. Run: pip install openai")

    if provider == "anthropic":
        try:
            import anthropic
            return "anthropic", anthropic.Anthropic(api_key=current_app.config["ANTHROPIC_API_KEY"])
        except ImportError:
            raise RuntimeError("anthropic package not installed. Run: pip install anthropic")

    raise ValueError(f"Unknown AI_PROVIDER: {provider}")


def _call_llm(system_prompt: str, user_message: str, max_tokens: int = 800) -> str:
    """Unified LLM call returning the assistant's text response."""
    provider, client = _get_client()

    if provider == "openai":
        response = client.completions.create(
            model="gpt-4o-mini",
            messages=[ # type: ignore
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=max_tokens,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip() if response.choices and response.choices[0].message.content else ""

    if provider == "anthropic":
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text.strip() if response.content and response.content[0].text else ""

    return ""


def _parse_json_response(text: str) -> dict:
    """Extract JSON from LLM response, handling markdown code fences."""
    import json
    # Strip markdown fences if present
    text = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("```").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw": text}


# ─────────────────────────────────────────────
#  PUBLIC SERVICE FUNCTIONS
# ─────────────────────────────────────────────

def analyze_compiler_error(raw_error: str, code: str, language: str = "c", is_runtime: bool = False) -> dict:
    """
    Convert a raw compiler or runtime error message into a beginner-friendly explanation.
    Returns a dict with: error_type, error_line, title, explanation, hint, tip
    """
    error_type_str = "Runtime Error" if is_runtime else "Compiler Error"
    user_msg = (
        f"Language: {language.upper()}\n\n"
        f"Student's Code:\n```{language}\n{code}\n```\n\n"
        f"{error_type_str}:\n```\n{raw_error}\n```\n\n"
        f"Analyze this {error_type_str.lower()} and respond with the JSON structure specified."
    )
    try:
        raw = _call_llm(ERROR_ANALYSIS_SYSTEM, user_msg, max_tokens=600)
        return _parse_json_response(raw)
    except Exception as exc:
        current_app.logger.error("AI error analysis failed: %s", exc)
        return _fallback_error_analysis(raw_error)


def get_debugging_hint(code: str, error_description: str, language: str = "c") -> str:
    """
    Provide a guided debugging hint without giving the full solution.
    """
    user_msg = (
        f"Language: {language.upper()}\n\n"
        f"Student's Code:\n```{language}\n{code}\n```\n\n"
        f"Problem the student is facing: {error_description}\n\n"
        "Guide this student through the debugging process step by step."
    )
    try:
        return _call_llm(DEBUGGING_SYSTEM, user_msg, max_tokens=400)
    except Exception as exc:
        current_app.logger.error("Debugging hint failed: %s", exc)
        return "Try reading through your code line by line and check that every statement ends correctly."


def chat_with_assistant(
    message: str,
    conversation_history: list[dict[str, str]],
    context: dict | None = None,
) -> str:
    """
    AI chat assistant for student programming questions.
    conversation_history: list of {"role": "user"|"assistant", "content": str}
    context: optional dict with current program info, recent error, etc.
    """
    provider, client = _get_client()

    system = CHAT_SYSTEM
    if context:
        ctx_parts = []
        if context.get("program_title"):
            ctx_parts.append(f"Current program: {context['program_title']}")
        if context.get("recent_error"):
            ctx_parts.append(f"Recent compiler error: {context['recent_error']}")
        if context.get("language"):
            ctx_parts.append(f"Language: {context['language'].upper()}")
        if ctx_parts:
            system += "\n\nContext:\n" + "\n".join(ctx_parts)

    messages = conversation_history[-10:] + [{"role": "user", "content": message}]

    try:
        if provider == "openai":
            response = client.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": system}] + messages,
                max_tokens=500,
                temperature=0.5,
            )
            return response.choices[0].message.content.strip() if response.choices and response.choices[0].message.content else ""

        if provider == "anthropic":
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=500,
                system=system,
                messages=messages,
            )
            return response.content[0].text.strip() if response.content and response.content[0].text else ""

    except Exception as exc:
        current_app.logger.error("Chat assistant failed: %s", exc)
        return "I'm having trouble responding right now. Please try again in a moment."

    return ""


def generate_recommendations(performance_data: dict) -> dict:
    """
    Generate personalized learning recommendations from a student's performance data.
    performance_data keys: avg_score, error_history, weak_programs, completed_count, etc.
    """
    user_msg = (
        f"Student performance data:\n{performance_data}\n\n"
        "Generate personalized recommendations for this student."
    )
    try:
        raw = _call_llm(RECOMMENDATION_SYSTEM, user_msg, max_tokens=700)
        return _parse_json_response(raw)
    except Exception as exc:
        current_app.logger.error("Recommendations failed: %s", exc)
        return {
            "risk_level": "low",
            "summary": "Keep practising regularly to improve your skills.",
            "weak_areas": [],
            "recommendations": [],
            "encouragement": "You're doing well! Keep going.",
        }


def evaluate_code_logic(student_code: str, reference_code: str, language: str = "c") -> dict:
    """
    Compare student code logic against reference solution.
    Returns: {"logic_score": float 0-1, "feedback": str, "approach": str}
    """
    system = """You are an automated programming assessment engine.
Compare the student's code logic to the reference solution.
DO NOT penalise for different variable names, formatting, or valid alternative approaches.
Respond as valid JSON:
{
  "logic_score": <float 0.0-1.0>,
  "approach": "<brief description of student's approach>",
  "feedback": "<constructive feedback on the logic>",
  "is_correct_approach": <true|false>
}"""

    user_msg = (
        f"Language: {language.upper()}\n\n"
        f"Reference Solution:\n```{language}\n{reference_code}\n```\n\n"
        f"Student's Code:\n```{language}\n{student_code}\n```\n\n"
        "Evaluate the logical correctness of the student's approach."
    )
    try:
        raw = _call_llm(system, user_msg, max_tokens=400)
        return _parse_json_response(raw)
    except Exception as exc:
        current_app.logger.error("Logic evaluation failed: %s", exc)
        return {"logic_score": 0.5, "feedback": "Manual review required.", "approach": "unknown", "is_correct_approach": False}


# ─────────────────────────────────────────────
#  FALLBACK (no API key / network failure)
# ─────────────────────────────────────────────

_ERROR_PATTERNS = [
    (r"expected\s+'?;'?",          "syntax",  "Missing Semicolon",
     "A semicolon (;) is missing at the end of a statement.",
     "Check the line mentioned in the error and the line before it. Add a semicolon at the end of the statement.",
     "Every C statement must end with a semicolon — like a full stop at the end of a sentence."),
    (r"undeclared",                 "syntax",  "Undeclared Variable",
     "You are using a variable that has not been declared.",
     "Declare the variable with its data type (e.g., int x;) before using it.",
     "In C, every variable must be declared before it can be used."),
    (r"implicit declaration",       "linker",  "Missing Function Declaration",
     "You are calling a function that the compiler does not know about yet.",
     "Add the appropriate #include header at the top of your file (e.g., #include <stdio.h>).",
     "Standard library functions like printf and scanf require their headers to be included."),
    (r"conflicting types",          "syntax",  "Type Conflict",
     "The same function or variable is declared with different types in two places.",
     "Check that your function declaration and definition have identical parameter types and return types.",
     "Function declarations must exactly match their definitions in C."),
    (r"return type",                "syntax",  "Return Type Mismatch",
     "The value you are returning does not match the declared return type of the function.",
     "Check what type your function declares it returns, then make sure your return statement returns that type.",
     "The return type in a function definition must match what is actually returned."),
]


def _fallback_error_analysis(raw_error: str) -> dict:
    """Rule-based fallback when AI API is unavailable."""
    for pattern, etype, title, explanation, hint, tip in _ERROR_PATTERNS:
        if re.search(pattern, raw_error, re.IGNORECASE):
            line_match = re.search(r":(\d+):", raw_error)
            return {
                "error_type": etype,
                "error_line": int(line_match.group(1)) if line_match else None,
                "title": title,
                "explanation": explanation,
                "hint": hint,
                "tip": tip,
            }
    return {
        "error_type": "syntax",
        "error_line": None,
        "title": "Compilation Error",
        "explanation": "Your code has a compilation error. Read the error message carefully.",
        "hint": "Look at the line number in the error message and check that line and the line before it.",
        "tip": "Compiler errors always include the file name, line number, and a description. Start from the first error listed.",
    }
