"""
Minimal MCP server exposing two OpenFDA FAERS signal-detection tools.

Self-contained: depends only on `requests` and `mcp` (no pandas / pickle / RxNorm
mapping), so it starts instantly and is easy to demo.

Run standalone:
    python mcp_faers_signal.py

Or register in .mcp.json / Claude Code settings.json:
    {
      "mcpServers": {
        "faers_signal": {
          "command": "python",
          "args": ["./utils/mcp_faers_signal.py"]
        }
      }
    }
"""

import urllib.parse

import requests
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("faers_signal")

OPENFDA_EVENT_URL = "https://api.fda.gov/drug/event.json"


@mcp.tool()
def get_faers_top_events(drug: str, top_n: int = 5) -> dict:
    """Return the top adverse event PT terms reported for a drug in FAERS.

    Args:
        drug: Generic drug name, e.g. 'metformin'
        top_n: Number of top events to return (max 10)
    """
    top_n = min(top_n, 10)
    r = requests.get(
        OPENFDA_EVENT_URL,
        params={
            "search": f'patient.drug.medicinalproduct:"{drug}"',
            "count": "patient.reaction.reactionmeddrapt.exact",
            "limit": top_n,
        },
        timeout=10,
    )
    r.raise_for_status()
    results = r.json().get("results", [])
    return {
        "drug": drug,
        "top_adverse_events": [
            {"meddra_pt": item["term"], "report_count": item["count"]}
            for item in results
        ],
    }


@mcp.tool()
def get_faers_drug_event_pair(drug: str, event_pt: str) -> dict:
    """Return co-report count for a specific drug + MedDRA PT pair (for PRR/ROR signal detection).

    Args:
        drug: Generic drug name, e.g. 'atorvastatin'
        event_pt: MedDRA preferred term, e.g. 'rhabdomyolysis'
    """
    search = (
        f'patient.drug.medicinalproduct:"{drug}"'
        f' AND patient.reaction.reactionmeddrapt:"{event_pt}"'
    )
    url = OPENFDA_EVENT_URL + "?" + urllib.parse.urlencode({"search": search, "limit": 1})
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    total = r.json().get("meta", {}).get("results", {}).get("total", 0)
    return {"drug": drug, "meddra_pt": event_pt, "co_report_count": total}


if __name__ == "__main__":
    mcp.run()
