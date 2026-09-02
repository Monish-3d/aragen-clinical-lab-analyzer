"""Client side of the MCP connection.

The agent uses this to resolve reference ranges. It starts mcp_server.py as a
subprocess and talks to it over stdio, so the lookup genuinely goes through the
MCP protocol instead of being a direct function call.
"""

import json
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters

from reference_data import ReferenceInfo

SERVER_SCRIPT = Path(__file__).parent / "mcp_server.py"

# Start the server with the same interpreter that is running the API, so it
# picks up the same virtual environment.
SERVER_PARAMS = StdioServerParameters(
    command=sys.executable,
    args=[str(SERVER_SCRIPT)],
)


def read_payload(result):
    """Pull the tool's JSON answer out of an MCP response.

    The tool returns a plain dict, which the SDK sends back as a JSON text
    block. structured_content is checked first in case a future version starts
    filling it in.
    """
    if result.structured_content:
        return result.structured_content

    for block in result.content:
        text = getattr(block, "text", None)
        if text:
            return json.loads(text)

    return None


def build_reference(payload):
    """Turn the tool's JSON answer back into a ReferenceInfo."""
    if not payload or not payload.get("found"):
        return None

    return ReferenceInfo(
        test_name=payload["test_name"],
        unit=payload.get("unit", ""),
        reference_range=payload.get("reference_range", ""),
        is_numeric=payload.get("is_numeric", False),
        min_reference=payload.get("min_reference"),
        max_reference=payload.get("max_reference"),
    )


async def fetch_references(test_names):
    """Look up several tests over one MCP session.

    Returns {test_name: ReferenceInfo or None}. One session is opened for the
    whole batch rather than one per test, so the server subprocess only starts
    once per request.
    """
    references = {}

    async with Client(SERVER_PARAMS) as client:
        for test_name in test_names:
            result = await client.call_tool(
                "reference_range_lookup", {"test_name": test_name}
            )

            # is_error means the tool call itself failed rather than the test
            # simply being missing, so treat it as "no reference available".
            if result.is_error:
                references[test_name] = None
            else:
                references[test_name] = build_reference(read_payload(result))

    return references
