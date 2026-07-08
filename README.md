# FAERS Query MCP Server & Agentic Ingestion Workflow

Tools and an agent that connect Claude to FDA FAERS data — both **live OpenFDA
queries** and an **automated quarterly ingestion pipeline** (discover → download →
unzip → merge) — built for the lecture *Claude Model Usage for Healthcare AI Researchers*.

## Contents

| Path | Purpose |
| --- | --- |
| `utils/mcp_faers_server.py` | MCP server exposing 6 FAERS tools |
| `utils/faers_agent.py` | Agentic orchestrator (MCP ↔ Claude tool-use loop) |
| `Claude_Model_Usage_Lecture.ipynb` | Lecture notebook |
| `faers_raw/` | Downloaded/extracted FAERS ASCII releases (created on demand) |
| `<label>.pkl` | Processed merged quarter, e.g. `2026q1.pkl` |

## MCP Tools

The server `faers_query` exposes:

| Tool | Description |
| --- | --- |
| `get_faers_count(drug)` | Total FAERS report count for a drug (OpenFDA) |
| `get_faers_top_events(drug, top_n)` | Top MedDRA PT terms for a drug |
| `get_faers_drug_event_pair(drug, event_pt)` | Co-report count (PRR/ROR numerator) |
| `get_latest_faers_quarter()` | Discover the most recent FAERS quarterly release |
| `download_faers_quarter(year, quarter, dest_dir)` | Download + unzip a quarter's ASCII files |
| `mergeFAERS(path_in, path_out)` | Merge DEMO/DRUG/OUTC/INDI/REAC into one enriched `.pkl` |

`mergeFAERS` enriches each drug with its RxNorm **ingredient** and **ATC4** class
(via `../../RxNorm/name_map_atc4.pkl`) and produces the 13-column schema:

```
fda_dt, rept_cod, primaryid, caseid, age, age_cod, gndr_cod, wt, wt_cod,
treatment, outc_cod, indi_pt, pt
```

where `treatment` is a `"; "`-joined list of per-drug JSON records:
`{"drugname", "ingredient", "atc4", "route", "dose"}`.

## Setup

Requires Python with `mcp`, `anthropic`, `pandas`, `requests`, `python-dotenv`.

1. **API key** — put `ANTHROPIC_API_KEY=sk-ant-...` in `.env` (this folder).
2. **Register the MCP server** so Claude can reach it.

   VS Code extension — project root `.mcp.json`:
   ```json
   {
     "mcpServers": {
       "faers_query": {
         "command": "/home/dada/anaconda3/bin/python",
         "args": ["/<your_path>/utils/mcp_faers_server.py"]
       }
     }
   }
   ```
   Claude Code CLI — same block under `mcpServers` in `~/.claude/settings.json`.

   > Use the **absolute** Python path (the one with `mcp` installed). After editing,
   > reload the VS Code window; confirm with `/mcp` (server should list 6 tools).

## Usage

### 1. Natural language (inside Claude Code)

> "How many FAERS reports link atorvastatin to rhabdomyolysis?"
> "Find the latest FAERS quarter, download it, and merge it into this folder."

Claude calls the tools automatically — no copy-paste.

### 2. Agentic orchestrator (standalone)

```bash
/home/dada/anaconda3/bin/python utils/faers_agent.py
# or target a specific quarter / output dir:
/home/dada/anaconda3/bin/python utils/faers_agent.py \
  "Download and merge FAERS 2025 Q4 into <your_path>"
```

Claude chooses the call order (discover → download → merge) and prints a trace plus a
final summary (quarter label, output `.pkl`, row count). Override the model with
`FAERS_AGENT_MODEL` (default `claude-sonnet-4-6`).

### 3. Direct Python (no LLM)

```python
import sys; sys.path.insert(0, "utils")
import mcp_faers_server as m

q = m.get_latest_faers_quarter()                       # -> {'label': '2026q1', ...}
d = m.download_faers_quarter(q["year"], q["quarter"])  # -> {'ascii_dir': ...}
r = m.mergeFAERS(d["ascii_dir"], ".")                  # -> writes 2026q1.pkl
print(r["rows"], r["output_pkl"])
```

## Notes

- FAERS zips are ~60–200 MB; `download_faers_quarter` streams to disk and skips a valid
  existing zip (idempotent).
- The FDA server mislabels ranged/zip responses as `gzip`; the tools send
  `Accept-Encoding: identity` to fetch raw bytes correctly.
- `mergeFAERS` runs for a few minutes on a full quarter (large DRUG file + RxNorm
  mapping + group-bys); allow generous timeouts in any agent loop.

## Data sources

- FAERS quarterly downloads: <https://fis.fda.gov/extensions/FPD-QDE-FAERS/FPD-QDE-FAERS.html>
- OpenFDA API (no key): <https://api.fda.gov/drug/event.json>
- MedDRA browser: <https://www.meddra.org>
