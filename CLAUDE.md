# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MCP (Model Context Protocol) server that provides real-time gold price data from Vietnamese and international markets via the vang.today API. Single-file Python server (`main.py`) using stdio transport.

## Commands

```bash
uv sync              # Install/sync dependencies
uv run main.py       # Start the MCP server
```

There are no tests or linting configured.

## Architecture

**Single-file MCP server** (`main.py`) with three layers:

1. **API layer** — `fetch_prices()` and `fetch_price_history()` make async HTTP calls to `https://www.vang.today/api/prices` using httpx
2. **Formatting layer** — `format_price()`, `format_change()`, `format_entry()` handle currency-aware display (VND vs USD) with Unicode indicators (▲/▼/─)
3. **Tool handlers** — Three MCP tools registered via `@server.list_tools()` and dispatched in `@server.call_tool()`:
   - `get_gold_prices` — All prices, filterable by currency/codes. Uses `DEFAULT_CODES` when no codes specified, `["ALL"]` for everything
   - `get_gold_price` — Single price lookup with fuzzy search (matches against code and name)
   - `get_gold_price_history` — Historical daily prices with day-over-day changes

**Key constants:** `DEFAULT_CODES = ["SJL1L10", "SJ9999", "PQHNVM", "PQHN24NTT", "VNGSJC"]` — the 5 most popular Vietnamese gold types shown by default.

**Currency detection in history:** Prices < 100,000 are treated as USD, otherwise VND.

## Dependencies

Managed with **uv** (lock file: `uv.lock`). Python >=3.12.

- `httpx` — async HTTP client for API calls
- `mcp` — Anthropic's MCP SDK (server, stdio transport)

## Claude Desktop Integration

```json
{
  "mcpServers": {
    "gold": {
      "command": "uv",
      "args": ["--directory", "/path/to/mcp-gold", "run", "main.py"]
    }
  }
}
```
