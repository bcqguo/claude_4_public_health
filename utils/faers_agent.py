"""
Agentic FAERS ingestion workflow.

Bridges the `faers_query` MCP server's tools into a Claude tool-use loop so that a
single natural-language instruction drives the whole pipeline:

    discover latest quarter -> download + unzip -> mergeFAERS -> processed .pkl

The MCP server is launched over stdio; its tools are converted to the Anthropic
Messages API tool schema, and Claude decides the call order (this is the "agentic"
part — the script only wires tools into the loop, mirroring the lecture's Section 3.7).

Run:
    python utils/faers_agent.py
    python utils/faers_agent.py "Download and merge FAERS 2025 Q4 into ./faers_raw"

Requires ANTHROPIC_API_KEY (loaded from Meetings/Yale_talk/.env).
"""

import os
import sys
import json
import asyncio

from dotenv import load_dotenv
import anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(HERE, "..", ".env"))

# Same interpreter that has `mcp`, `pandas`, etc. installed (see ~/.claude/settings.json)
PYTHON = sys.executable or "/home/dada/anaconda3/bin/python"
SERVER = os.path.join(HERE, "mcp_faers_server.py")
MODEL = os.environ.get("FAERS_AGENT_MODEL", "claude-sonnet-4-6")
DEFAULT_OUTPUT_PATH = "/home/dada/Barn/GQ/ADR/Meetings/Yale_talk"

SYSTEM = (
    "You are a FAERS data-engineering agent. Use the available tools to ingest FDA "
    "FAERS quarterly data. Unless the user specifies a quarter, first discover the "
    "latest available quarter, then download and unzip it, then call mergeFAERS on the "
    "extracted ASCII folder to produce the processed .pkl. Always pass the ascii_dir "
    "returned by the download step into mergeFAERS. When done, report the quarter "
    "label, the output .pkl path, and the row count."
)

DEFAULT_TASK = (
    "Find the latest available FAERS quarterly release, download and unzip it, then "
    f"merge it into '{DEFAULT_OUTPUT_PATH}'. Report the output path and number of rows."
)


def _mcp_tools_to_anthropic(mcp_tools):
    """Convert MCP tool definitions into the Anthropic Messages API `tools` schema."""
    return [
        {
            "name": t.name,
            "description": t.description or "",
            "input_schema": t.inputSchema,
        }
        for t in mcp_tools
    ]


def _tool_result_text(result):
    """Flatten an MCP call_tool result into a string for a tool_result block."""
    parts = []
    for block in result.content:
        text = getattr(block, "text", None)
        parts.append(text if text is not None else str(block))
    return "\n".join(parts) if parts else "(no content)"


async def run_agent(task: str, max_steps: int = 12) -> str:
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
    server_params = StdioServerParameters(command=PYTHON, args=[SERVER])

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            mcp_tools = (await session.list_tools()).tools
            tools = _mcp_tools_to_anthropic(mcp_tools)
            print(f"[agent] MCP tools available: {[t['name'] for t in tools]}\n")

            messages = [{"role": "user", "content": task}]

            for step in range(max_steps):
                resp = client.messages.create(
                    model=MODEL,
                    max_tokens=2048,
                    system=SYSTEM,
                    tools=tools,
                    messages=messages,
                )
                messages.append({"role": "assistant", "content": resp.content})

                if resp.stop_reason != "tool_use":
                    return next(
                        (b.text for b in resp.content if getattr(b, "type", "") == "text"),
                        "(no final text)",
                    )

                tool_results = []
                for block in resp.content:
                    if getattr(block, "type", "") == "tool_use":
                        print(f"[step {step + 1}] calling {block.name}({json.dumps(block.input)})")
                        result = await session.call_tool(block.name, block.input)
                        out = _tool_result_text(result)
                        print(f"          -> {out[:300]}\n")
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": out,
                                "is_error": bool(getattr(result, "isError", False)),
                            }
                        )
                messages.append({"role": "user", "content": tool_results})

            return "Agent reached step limit without finishing."


def main():
    task = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TASK
    print(f"[agent] model={MODEL}\n[agent] task: {task}\n")
    summary = asyncio.run(run_agent(task))
    print("\n=== AGENT SUMMARY ===\n")
    print(summary)


if __name__ == "__main__":
    main()
