# Claude Model Usage for Healthcare AI Researchers

A hands-on guide to accessing and prompting Claude models for public-health and pharmacovigilance research workflows. Companion material to `Claude_Model_Usage.ipynb`.

## Agenda
1. How to access Claude models
2. Prompting Claude: Simple to Complex — system prompts, pre/postfix, model context protocol (MCP)

## Setup: Claude Code Environment
1. Install VS Code
2. Install the Claude Code extension
3. Link your Claude subscription to Claude Code

> No Anthropic API key is required to use Claude through the Claude Code subscription.

---

## Part 1: Prompting Claude — Simple to Complex

### Claude Model Family (2026) — Choose the Right Model

| Model | ID | Context | Input $/1M | Output $/1M | Best For |
|---|---|---|---|---|---|
| Fable 5 | `claude-fable-5` | 1M | $10 | $50 | Frontier reasoning |
| **Opus 4.8** | `claude-opus-4-8` | 1M | $5 | $25 | **Default: complex research** |
| Sonnet 4.6 | `claude-sonnet-4-6` | 1M | $3 | $15 | Balanced speed/quality |
| Haiku 4.5 | `claude-haiku-4-5` | 200K | $1 | $5 | High-throughput classification |

> **Rule of thumb:** Start with Opus 4.8 for research. Use Haiku for batch classification tasks.

### 1.1 — The Simplest Possible Request
- You do **not** need an Anthropic API key to use Claude.
- Select a model: `/model` → switch model → choose Opus.
- Type your instruction directly in the Claude Code chat, e.g. *"What is pharmacovigilance?"*

### 1.2 — System Prompts: Setting Persona & Context
The `system` parameter sets persistent instructions Claude follows throughout the conversation.

Good system prompts:
- Define the AI's role and expertise
- Specify output format preferences
- Set domain constraints
- Establish tone and vocabulary

Example: `"You are an expert pharmacovigilance scientist. Always cite MedDRA terminology."`

### 1.3 — Prefixes & Postfixes
Modify a request by wrapping it with a keyword:
- **`artifact`** (postfix) — generate an interactive app or dashboard, e.g. `"describe the transformer algorithm artifact"` produces a webpage.
- **`L99`** (prefix) — deep reasoning / level-99 expert mode, e.g. `"L99 describe the transformer algorithm"`.
- **`godmode`** (prefix) — decisive mode, e.g. `"godmode describe the transformer algorithm"`.

### 1.3 — Slash Commands Reference

| Command | What it does |
|---|---|
| `/help` | Show all available commands |
| `/clear` | Reset conversation context |
| `/compact` | Summarize and compress conversation |
| `/cost` | Show token usage and cost |
| `/model` | Switch models mid-session |
| `/fast` | Toggle Fast mode (Opus with faster output) |
| `/plan` | Enter planning mode — Claude presents a plan first |
| `/review` | Review code changes |
| `/mcp` | Manage MCP server connections |
| `/add-dir` | Add a directory to Claude's context |

For Jupyter research workflows:
- `/plan` — review the plan before Claude touches any code
- `/cost` — track API spending per session
- `/compact` — keep long research sessions alive without losing context

### 1.4 — MCP: Model Context Protocol
MCP lets Claude connect to **external data sources and tools** via a standard protocol.

Configure `.mcp.json` in the project path:
```json
{
  "mcpServers": {
    "faers_query": {
      "command": "<your_python_path>",
      "args": ["./utils/mcp_faers_server.py"]
    }
  }
}
```

Once connected, Claude can query FAERS directly in a conversation — without any copy-paste.

#### `utils/mcp_faers_server.py` — MCP server tools

| Tool | OpenFDA call | Use case |
|---|---|---|
| `get_faers_top_events(drug, top_n)` | Top MedDRA PTs for a drug | Adverse event profiling |
| `get_faers_drug_event_pair(drug, event_pt)` | Co-report count | PRR/ROR numerator |

**Reloading the server:** press `Ctrl+Shift+P` → "Developer: Reload Window" to refresh the notebook and pick up changes.

**Testing:** run `/mcp` in the Claude chat to list connected servers, then invoke a tool to confirm it works.

Example result:
```
4,215 FAERS reports link atorvastatin to rhabdomyolysis (co-reporting both the
drug and the MedDRA preferred term "rhabdomyolysis").

Note: this raw co-report count is useful for disproportionality signal detection
(PRR/ROR) but isn't proof of causation, since FAERS is a spontaneous, voluntary
reporting system.
```

---

## Resources & References

| Resource | URL |
|---|---|
| Anthropic API Docs | https://docs.anthropic.com |
| Python SDK | https://github.com/anthropic-ai/anthropic-sdk-python |
| Claude Code CLI | https://claude.ai/code |
| Model Pricing | https://anthropic.com/api/pricing |
| MedDRA Browser | https://www.meddra.org |
| FAERS Data | https://fis.fda.gov/extensions/FPD-QDE-FAERS |

---

## Appendix — Install Claude CLI on Windows
1. Open PowerShell and run:
   ```powershell
   irm https://claude.ai/install.ps1 | iex
   ```
2. Update your system PATH to include:
   ```
   C:\Users\<you>\.local\bin\
   ```
3. Test the install by running:
   ```powershell
   claude
   ```

**Done!** You have successfully installed the Claude CLI.
