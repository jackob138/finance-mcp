"""
Personal Finance Calculator - MCP Server

This is a small web server that exposes three "tools" Claude can call:
  1. roth_contribution_room - how much Roth IRA room is left this year
  2. project_growth          - compound growth projection
  3. bucket_allocation_check - sanity-check a savings bucket split

WHAT'S ACTUALLY HAPPENING HERE (for the "teach me" part):
- FastMCP is a helper class that handles all the MCP protocol plumbing for you
  (formatting requests/responses, etc.) so you just write normal Python functions.
- Each function below gets turned into a "tool" automatically because of the
  `@mcp.tool()` decorator right above it. The decorator is what makes a plain
  function callable by Claude.
- The docstring (the text in triple-quotes under each function) is not just a
  comment - Claude actually reads it to know what the tool does and how to use it.
"""

from mcp.server.fastmcp import FastMCP

# This name shows up when the server identifies itself - can be anything.
mcp = FastMCP("finance-calculator")


# 2026 IRS Roth IRA contribution limits (update these yearly - they change most years)
ROTH_LIMIT_UNDER_50 = 7000
ROTH_LIMIT_50_PLUS = 8000


@mcp.tool()
def roth_contribution_room(contributed_this_year: float, age: int) -> str:
    """
    Calculate remaining Roth IRA contribution room for the current tax year.

    Args:
        contributed_this_year: Dollar amount already contributed this year.
        age: Your current age (contribution limit is higher at 50+).

    Returns:
        A summary of the annual limit, what's been used, and what's left.
    """
    limit = ROTH_LIMIT_50_PLUS if age >= 50 else ROTH_LIMIT_UNDER_50
    remaining = max(0, limit - contributed_this_year)
    used_pct = min(100, round((contributed_this_year / limit) * 100, 1))

    return (
        f"Annual Roth IRA limit: ${limit:,.2f}\n"
        f"Contributed so far: ${contributed_this_year:,.2f} ({used_pct}% of limit)\n"
        f"Remaining room: ${remaining:,.2f}"
    )


@mcp.tool()
def project_growth(
    starting_balance: float,
    monthly_contribution: float,
    annual_return_pct: float,
    years: int,
) -> str:
    """
    Project compound growth of an investment/savings account over time.

    Args:
        starting_balance: Current balance in the account.
        monthly_contribution: Amount added each month.
        annual_return_pct: Assumed average annual return, as a percent (e.g. 7 for 7%).
        years: Number of years to project forward.

    Returns:
        Year-by-year balance projection plus a total contributions vs. growth breakdown.
    """
    monthly_rate = (annual_return_pct / 100) / 12
    balance = starting_balance
    total_contributed = starting_balance
    yearly_snapshots = []

    for year in range(1, years + 1):
        for _ in range(12):
            balance = balance * (1 + monthly_rate) + monthly_contribution
            total_contributed += monthly_contribution
        yearly_snapshots.append(f"  Year {year}: ${balance:,.2f}")

    total_growth = balance - total_contributed

    result = "Year-by-year projection:\n" + "\n".join(yearly_snapshots)
    result += (
        f"\n\nFinal balance after {years} years: ${balance:,.2f}\n"
        f"Total you contributed: ${total_contributed:,.2f}\n"
        f"Total growth from returns: ${total_growth:,.2f}"
    )
    return result


@mcp.tool()
def bucket_allocation_check(
    monthly_income: float,
    bucket_percentages: dict[str, float],
) -> str:
    """
    Sanity-check a multi-bucket savings allocation against monthly income.

    Args:
        monthly_income: Take-home monthly income.
        bucket_percentages: Dict of bucket name -> percent of income
            (e.g. {"emergency_fund": 10, "roth_ira": 15, "general_savings": 10}).

    Returns:
        Dollar amount for each bucket, total allocated, and how much is left
        for spending/unallocated - flags if the buckets add up to over 100%.
    """
    total_pct = sum(bucket_percentages.values())
    lines = []
    for name, pct in bucket_percentages.items():
        dollar_amount = monthly_income * (pct / 100)
        lines.append(f"  {name}: {pct}% -> ${dollar_amount:,.2f}/month")

    remaining_pct = 100 - total_pct
    remaining_dollars = monthly_income * (remaining_pct / 100)

    result = "Bucket breakdown:\n" + "\n".join(lines)
    result += f"\n\nTotal allocated: {total_pct}% (${monthly_income * total_pct / 100:,.2f})"

    if total_pct > 100:
        result += f"\n\n⚠️ WARNING: Buckets add up to {total_pct}%, which is over 100% of income."
    else:
        result += f"\nRemaining unallocated: {remaining_pct}% (${remaining_dollars:,.2f})"

    return result


# This block only runs when you execute this file directly (python server.py),
# not when it's imported elsewhere. It starts the actual web server.
if __name__ == "__main__":
    mcp.run(transport="streamable-http")
