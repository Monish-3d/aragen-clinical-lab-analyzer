"""The agent flow: classify -> route -> explain.

Reference ranges are resolved through the MCP server, the severity is decided
by classifier.py, and only the wording comes from the LLM.
"""

from classifier import (
    classify_lab_result,
    format_number,
    route_by_severity,
    summarize,
)
from llm import explain_results
from mcp_client import fetch_references
from models import AnalyzeResponse, LabResult, Summary
from reference_data import ReferenceInfo, translate_followup, translate_term


async def resolve_references(test_names):
    """Ask the MCP server for the reference range of each test.

    If the MCP server cannot be reached the analysis still runs - every test
    just comes back without a reference, which the classifier reports as
    UNKNOWN instead of failing the whole request.
    """
    # Nothing to ask about if every test brought its own reference range.
    if not test_names:
        return {}

    try:
        return await fetch_references(test_names)
    except Exception as error:
        print(f"MCP reference lookup failed: {error}")
        return {}


def reference_from_input(lab):
    """Build a reference range out of the columns supplied with the upload.

    Returns None when the caller did not supply one, which is the signal to go
    and ask the MCP server instead.
    """
    if lab.min_reference is not None and lab.max_reference is not None:
        return ReferenceInfo(
            test_name=lab.test_name,
            unit=lab.unit or "",
            reference_range=lab.reference_range
            or f"{format_number(lab.min_reference)}-{format_number(lab.max_reference)}",
            is_numeric=True,
            min_reference=lab.min_reference,
            max_reference=lab.max_reference,
            recommended_followup=translate_followup(lab.recommended_followup or ""),
        )

    # Only a text reference, so this is a categorical test like Protein (Strip).
    if lab.reference_range:
        return ReferenceInfo(
            test_name=lab.test_name,
            unit=lab.unit or "",
            reference_range=translate_term(lab.reference_range),
            is_numeric=False,
            recommended_followup=translate_followup(lab.recommended_followup or ""),
        )

    return None


async def analyze_labs(labs):
    """Run the full flow over a list of validated LabInput objects."""
    supplied = [reference_from_input(lab) for lab in labs]

    # Only the tests that did not bring their own reference range need looking
    # up through MCP.
    references = await resolve_references(
        [lab.test_name for lab, given in zip(labs, supplied) if given is None]
    )

    # CLASSIFY - deterministic, no LLM involved.
    classifications = [
        classify_lab_result(
            lab.test_name,
            lab.value,
            lab.unit,
            given or references.get(lab.test_name),
        )
        for lab, given in zip(labs, supplied)
    ]

    # ROUTE - critical first, then warning, then normal.
    routed = route_by_severity(classifications)

    # EXPLAIN - one LLM call per result, overlapped a few at a time. They are
    # not fired all at once because the free tier only allows 5 requests a
    # minute and a burst just gets rejected.
    explanations = await explain_results(routed)

    results = [
        LabResult(
            test_name=item.test_name,
            value=item.value,
            unit=item.unit,
            reference_range=item.reference_range,
            status=item.status,
            # The deterministic reason is what the fallback uses, so the "why"
            # is never lost even when the LLM is unavailable.
            reason=explanation.reason,
            explanation=explanation.explanation,
            next_step=explanation.next_step,
            min_reference=item.min_reference,
            max_reference=item.max_reference,
        )
        for item, explanation in zip(routed, explanations)
    ]

    return AnalyzeResponse(results=results, summary=Summary(**summarize(routed)))
