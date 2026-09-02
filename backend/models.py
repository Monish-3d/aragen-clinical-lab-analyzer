"""Pydantic models used for validation."""

from pydantic import BaseModel, Field


class LabExplanation(BaseModel):
    """The shape the LLM has to answer in.

    Gemini is given this as a response schema, so the reply comes back as JSON
    with exactly these fields instead of free text the frontend would have to
    pick apart.
    """

    reason: str = Field(description="One sentence on why the result was flagged.")
    explanation: str = Field(
        description="Plain-language note on what the result can indicate."
    )
    next_step: str = Field(description="One reasonable next step to suggest.")
