"""Pydantic models for the API and for the LLM reply."""

from pydantic import BaseModel, Field


class LabInput(BaseModel):
    """One lab result as it arrives from the frontend."""

    # A test name is required and cannot be blank, otherwise there is nothing
    # to look a reference range up by.
    test_name: str = Field(min_length=1)

    # Numeric tests send a number and strip tests send text like "Negative",
    # so both are accepted here and sorted out by the classifier.
    value: float | str

    unit: str | None = None

    # An uploaded CSV can bring its own reference columns. When they are there
    # they are used instead of the MCP lookup, so a test the dataset does not
    # know about can still be classified.
    reference_range: str | None = None
    min_reference: float | None = None
    max_reference: float | None = None


class AnalyzeRequest(BaseModel):
    """Body of POST /analyze_labs."""

    # An empty list is rejected - there is nothing to analyse.
    labs: list[LabInput] = Field(min_length=1)


class LabResult(BaseModel):
    """One analysed result: the classification plus the LLM's wording."""

    test_name: str
    value: float | str
    unit: str
    reference_range: str
    status: str
    reason: str
    explanation: str
    next_step: str


class Summary(BaseModel):
    """Counts shown above the results."""

    critical: int
    warning: int
    normal: int
    unknown: int


class AnalyzeResponse(BaseModel):
    """What POST /analyze_labs returns, already sorted by severity."""

    results: list[LabResult]
    summary: Summary


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
