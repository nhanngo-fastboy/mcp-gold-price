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

DEFAULT_CODES = ["SJL1L10", "SJ9999", "PQHNVM", "PQHN24NTT", "VNGSJC"]


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


async def fetch_price_history(code: str, days: int) -> dict | None:
    """Fetch historical gold prices from the vang.today API."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(API_URL, params={"type": code, "days": days})
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
                "Returns buy/sell prices and price changes. "
                "By default returns: SJC 9999, SJC Ring, PNJ Hanoi, PNJ 24K, VN Gold SJC. "
                "Optionally filter by currency (VND or USD) or specific codes."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "currency": {
                        "type": "string",
                        "description": "Filter by currency: 'VND' or 'USD'. Leave empty for all.",
                        "enum": ["VND", "USD"]
                    },
                    "codes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "List of gold type codes to show. "
                            "Defaults to: SJL1L10, SJ9999, PQHNVM, PQHN24NTT, VNGSJC. "
                            "Pass ['ALL'] to show all available types."
                        )
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
        ),
        types.Tool(
            name="get_gold_price_history",
            description=(
                "Get historical gold prices for a specific gold type over a number of days. "
                "Returns daily buy/sell prices and day-over-day changes. "
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
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of days of history to retrieve (e.g., 7, 30, 90). Default: 30.",
                        "default": 30
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
    elif name == "get_gold_price_history":
        return await handle_get_gold_price_history(arguments)
    else:
        return [types.TextContent(type="text", text=f"Unknown tool: {name}")]


async def handle_get_gold_prices(arguments: dict) -> list[types.TextContent]:
    """Fetch and format all gold prices."""
    currency_filter = arguments.get("currency", "").strip().upper()
    codes_filter = arguments.get("codes", None)
    show_all = codes_filter and len(codes_filter) == 1 and codes_filter[0].upper() == "ALL"
    if not show_all:
        allowed_codes = [c.upper() for c in codes_filter] if codes_filter else DEFAULT_CODES

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
        if not show_all and code not in allowed_codes:
            continue
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


async def handle_get_gold_price_history(arguments: dict) -> list[types.TextContent]:
    """Fetch and format historical gold prices."""
    code = arguments.get("code", "").strip().upper()
    if not code:
        return [types.TextContent(type="text", text="Error: gold type code is required.")]

    days = arguments.get("days", 30)

    data = await fetch_price_history(code, days)
    if not data:
        return [types.TextContent(type="text", text="Error: Could not fetch gold price history.")]

    history = data.get("history", [])
    if not history:
        return [types.TextContent(type="text", text=f"No history found for '{code}'.")]

    # Determine currency from first entry
    first_prices = history[0].get("prices", {})
    first_entry = next(iter(first_prices.values()), None)
    currency = "USD" if first_entry and first_entry.get("buy", 0) < 100000 else "VND"

    lines = [
        f"Gold Price History — {code} ({days} days)",
        "═" * 55,
        ""
    ]

    for day in history:
        date = day["date"]
        prices = day.get("prices", {})
        entry = prices.get(code)
        if not entry:
            continue

        buy = format_price(entry["buy"], currency)
        change_buy = format_change(entry.get("day_change_buy", 0), currency)

        if entry.get("sell"):
            sell = format_price(entry["sell"], currency)
            change_sell = format_change(entry.get("day_change_sell", 0), currency)
            lines.append(f"{date}  Buy: {buy} ({change_buy})  |  Sell: {sell} ({change_sell})")
        else:
            lines.append(f"{date}  Buy: {buy} ({change_buy})")

    return [types.TextContent(type="text", text="\n".join(lines))]


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
