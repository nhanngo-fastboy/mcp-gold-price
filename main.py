"""
Gold Price MCP Server
=====================
A Model Context Protocol (MCP) server that provides real-time gold prices
from Vietnamese and international markets via the vang.today API.

Tools exposed:
  - get_gold_prices(currency?)     : All current gold prices
  - get_gold_price(code)           : Specific gold price by code

Usage:
  python main.py
"""

import asyncio
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

# ─── Server Initialization ────────────────────────────────────────────────────

server = Server("gold-price-server")

API_URL = "https://www.vang.today/api/prices"


# ─── Helper Functions ─────────────────────────────────────────────────────────

async def fetch_prices() -> dict | None:
    """Fetch gold prices from the vang.today API."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(API_URL)
        response.raise_for_status()
        data = response.json()
        if not data.get("success"):
            return None
        return data


def format_price(value: float, currency: str) -> str:
    """Format a price value based on currency."""
    if currency == "USD":
        return f"${value:,.2f}"
    # VND
    return f"{value:,.0f} VND"


def format_change(value: float, currency: str) -> str:
    """Format a price change with arrow indicator."""
    if value == 0:
        return "─ No change"
    arrow = "▲" if value > 0 else "▼"
    if currency == "USD":
        return f"{arrow} ${abs(value):,.2f}"
    return f"{arrow} {abs(value):,.0f} VND"


def format_entry(code: str, entry: dict) -> str:
    """Format a single gold price entry as readable text."""
    name = entry["name"]
    currency = entry["currency"]
    buy = format_price(entry["buy"], currency)
    sell = format_price(entry["sell"], currency) if entry["sell"] else "N/A"
    change_buy = format_change(entry["change_buy"], currency)
    change_sell = format_change(entry["change_sell"], currency) if entry["sell"] else ""

    lines = [
        f"{name} ({code})",
        f"  Buy  : {buy}  ({change_buy})",
    ]
    if entry["sell"]:
        lines.append(f"  Sell : {sell}  ({change_sell})")
    else:
        lines.append(f"  Sell : N/A")
    return "\n".join(lines)


# ─── Tool Definitions ─────────────────────────────────────────────────────────

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """Declare all tools this MCP server provides to Claude."""
    return [
        types.Tool(
            name="get_gold_prices",
            description=(
                "Get current gold prices from Vietnamese and international markets. "
                "Returns buy/sell prices and price changes for all available gold types. "
                "Optionally filter by currency (VND or USD)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "currency": {
                        "type": "string",
                        "description": "Filter by currency: 'VND' or 'USD'. Leave empty for all.",
                        "enum": ["VND", "USD"]
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="get_gold_price",
            description=(
                "Get the current price for a specific gold type by its code. "
                "Common codes: XAUUSD (World Gold), SJL1L10 (SJC 9999), "
                "DOJINHTV (DOJI Jewelry), PQHNVM (PNJ Hanoi), BT9999NTT (Bao Tin 9999)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": (
                            "Gold type code (e.g., 'XAUUSD', 'SJL1L10', 'DOJINHTV', "
                            "'PQHNVM', 'BT9999NTT', 'BTSJC', 'VNGSJC', 'VIETTINMSJC', "
                            "'PQHN24NTT', 'SJ9999', 'DOHNL', 'DOHCML')"
                        )
                    }
                },
                "required": ["code"]
            }
        )
    ]


# ─── Tool Implementation ──────────────────────────────────────────────────────

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Route tool calls from Claude to the appropriate handler."""

    if name == "get_gold_prices":
        return await handle_get_gold_prices(arguments)
    elif name == "get_gold_price":
        return await handle_get_gold_price(arguments)
    else:
        return [types.TextContent(type="text", text=f"Unknown tool: {name}")]


async def handle_get_gold_prices(arguments: dict) -> list[types.TextContent]:
    """Fetch and format all gold prices."""
    currency_filter = arguments.get("currency", "").strip().upper()

    data = await fetch_prices()
    if not data:
        return [types.TextContent(type="text", text="Error: Could not fetch gold prices.")]

    prices = data["prices"]
    date = data.get("date", "")
    time = data.get("time", "")

    lines = [
        f"Gold Prices — {date} {time}",
        "═" * 45
    ]

    for code, entry in prices.items():
        if currency_filter and entry["currency"] != currency_filter:
            continue
        lines.append("")
        lines.append(format_entry(code, entry))

    if len(lines) == 2:
        lines.append(f"\nNo prices found for currency: {currency_filter}")

    return [types.TextContent(type="text", text="\n".join(lines))]


async def handle_get_gold_price(arguments: dict) -> list[types.TextContent]:
    """Fetch and format a specific gold price by code."""
    code = arguments.get("code", "").strip().upper()
    if not code:
        return [types.TextContent(type="text", text="Error: gold type code is required.")]

    data = await fetch_prices()
    if not data:
        return [types.TextContent(type="text", text="Error: Could not fetch gold prices.")]

    prices = data["prices"]
    date = data.get("date", "")
    time = data.get("time", "")

    # Exact match
    if code in prices:
        entry = prices[code]
        header = f"Gold Price — {date} {time}\n{'═' * 45}\n"
        return [types.TextContent(type="text", text=header + format_entry(code, entry))]

    # Fuzzy search by name or partial code
    matches = []
    for c, entry in prices.items():
        if code in c or code.lower() in entry["name"].lower():
            matches.append((c, entry))

    if matches:
        lines = [
            f"Gold Prices — {date} {time}",
            f"No exact match for '{code}'. Similar results:",
            "═" * 45
        ]
        for c, entry in matches:
            lines.append("")
            lines.append(format_entry(c, entry))
        return [types.TextContent(type="text", text="\n".join(lines))]

    available = ", ".join(prices.keys())
    return [types.TextContent(
        type="text",
        text=f"Gold type '{code}' not found.\nAvailable codes: {available}"
    )]


# ─── Entry Point ──────────────────────────────────────────────────────────────

async def main():
    """Start the MCP server using stdio transport."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
