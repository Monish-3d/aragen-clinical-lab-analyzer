"""The agent flow: classify -> route -> explain.

Reference ranges are resolved through the MCP server, the severity is decided
by classifier.py, and only the wording comes from the LLM.
"""

from classifier import classify_lab_result, route_by_severity, summarize
from llm import explain_results
from mcp_client import fetch_references
from models import AnalyzeResponse, LabResult, Summary


async def resolve_references(test_names):
    """Ask the MCP server for the reference range of each test.

    If the MCP server cannot be reached the analysis still runs - every test
    just comes back without a reference, which the classifier reports as
    UNKNOWN instead of failing the whole request.
    """
    try:
        return await fetch_references(test_names)
    except Exception as error:
        print(f"MCP reference lookup failed: {error}")
        return {}


async def analyze_labs(labs):
    """Run the full flow over a list of validated LabInput objects."""
    references = await resolve_references([lab.test_name for lab in labs])

    # CLASSIFY - deterministic, no LLM involved.
    classifications = [
        classify_lab_result(
            lab.test_name, lab.value, lab.unit, references.get(lab.test_name)
        )
        for lab in labs
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
        )
        for item, explanation in zip(routed, explanations)
    ]

    return AnalyzeResponse(results=results, summary=Summary(**summarize(routed)))
