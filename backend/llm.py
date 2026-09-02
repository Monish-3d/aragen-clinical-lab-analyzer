"""Gemini call for the explanation step.

Only the wording comes from the model. The severity was already decided in
classifier.py and the prompt says not to change it, so the model cannot make a
normal result look critical or the other way round.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

from models import LabExplanation

# .env sits at the project root, one level above backend/, so load it by path
# rather than relying on where the server was started from.
load_dotenv(Path(__file__).parent.parent / ".env")

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

# Give up on a slow reply instead of leaving the whole request hanging. One
# model I tried sat there for over a minute before the server timed it out.
REQUEST_TIMEOUT_MS = 60_000

# Built once. Without a key it stays None and every result gets the fallback.
client = (
    genai.Client(
        api_key=API_KEY,
        http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MS),
    )
    if API_KEY
    else None
)

PROMPT_TEMPLATE = """You are helping explain a laboratory test result.

The application has already classified this result using its reference-range
logic. Do NOT change the classification.

Test name: {test_name}
Value: {value} {unit}
Reference range: {reference_range}
Classification: {status}
Deterministic reason: {reason}

Write three things:
1. reason - one sentence on why this value was flagged, agreeing with the
   deterministic reason above.
2. explanation - what this result can indicate, in plain language.
3. next_step - one reasonable next step.

Use cautious language. A single laboratory result is not enough for a
diagnosis, so describe what it can be associated with rather than stating what
the person has. Do not invent reference ranges or values. If the result is
normal, briefly say it falls within the supplied reference range.

Keep each field to one or two sentences."""


def build_prompt(classification):
    """Fill the prompt with the values the classifier already worked out."""
    return PROMPT_TEMPLATE.format(
        test_name=classification.test_name,
        value=classification.value,
        unit=classification.unit,
        reference_range=classification.reference_range or "not available",
        status=classification.status,
        reason=classification.reason,
    )


def fallback_explanation(classification):
    """Used whenever the model cannot be reached or answers badly.

    The classification is still valid on its own, so a failed explanation must
    not fail the whole result.
    """
    return LabExplanation(
        reason=classification.reason,
        explanation=(
            "AI explanation is temporarily unavailable. This result was "
            "classified from the supplied reference range."
        ),
        next_step="Discuss this result with a healthcare professional.",
    )


def explain_result(classification):
    """Ask Gemini to explain one classified result.

    Always returns a LabExplanation - never raises - so one bad call cannot
    take down the rest of the analysis.
    """
    if client is None:
        return fallback_explanation(classification)

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=build_prompt(classification),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=LabExplanation,
                # Low temperature so the same result is worded much the same
                # way each time it is analysed.
                temperature=0.2,
                # These are short explanations, so the model does not need to
                # think for long. On the default setting the same call took
                # 13 seconds instead of under 3, which adds up when every
                # result gets its own call.
                thinking_config=types.ThinkingConfig(thinking_level="low"),
            ),
        )
    except Exception as error:
        # Printed rather than swallowed silently - a quiet except here hid a
        # 404 for a retired model and made every result look like a fallback.
        print(f"Gemini call failed for {classification.test_name}: {error}")
        return fallback_explanation(classification)

    # .parsed is None if the reply did not fit the schema.
    explanation = response.parsed
    if not isinstance(explanation, LabExplanation):
        return fallback_explanation(classification)

    return explanation
