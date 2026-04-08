# MCP Gold Price Server

A Model Context Protocol (MCP) server that provides real-time gold prices from Vietnamese and international markets via the [vang.today](https://www.vang.today) API.

## Tools

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_gold_prices` | `currency` (optional: VND/USD) | Get all current gold prices |
| `get_gold_price` | `code` (required) | Get a specific gold price by code |

### Available Gold Codes

| Code | Name |
|------|------|
| XAUUSD | World Gold (XAU/USD) |
| SJL1L10 | SJC 9999 |
| BT9999NTT | Bao Tin 9999 |
| BTSJC | Bao Tin SJC |
| VNGSJC | VN Gold SJC |
| VIETTINMSJC | Viettin SJC |
| PQHNVM | PNJ Hanoi |
| PQHN24NTT | PNJ 24K |
| SJ9999 | SJC Ring |
| DOJINHTV | DOJI Jewelry |
| DOHNL | DOJI Hanoi |
| DOHCML | DOJI HCM |

## Setup

```bash
uv sync
python main.py
```

## Claude Desktop Config

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
