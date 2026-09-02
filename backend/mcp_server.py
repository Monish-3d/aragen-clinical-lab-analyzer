"""MCP server exposing the lab reference data as a tool.

The agent resolves reference ranges by calling this over MCP rather than
importing reference_data directly, which is what the assignment asks for.

Run it on its own with:  python mcp_server.py
"""

from mcp.server.mcpserver import MCPServer

from reference_data import lookup_reference

mcp = MCPServer("lab-reference")


@mcp.tool()
def reference_range_lookup(test_name: str) -> dict:
    """Look up the reference range for a laboratory test by name."""
    reference = lookup_reference(test_name)

    # A test we don't have is a normal outcome, not a crash. The caller gets a
    # structured answer it can turn into a message for the user.
    if reference is None:
        return {
            "found": False,
            "test_name": test_name,
            "error": f"No reference data found for test '{test_name}'.",
        }

    result = {
        "found": True,
        "test_name": reference.test_name,
        "reference_range": reference.reference_range,
        "unit": reference.unit,
        "is_numeric": reference.is_numeric,
    }

    # Numeric limits only exist for numeric tests, so they are left out for
    # categorical ones like Protein (Strip).
    if reference.is_numeric:
        result["min_reference"] = reference.min_reference
        result["max_reference"] = reference.max_reference

    return result


if __name__ == "__main__":
    mcp.run()
