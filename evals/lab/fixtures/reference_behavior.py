#!/usr/bin/env python3
"""Calibration fixture, not candidate code or an agent-performance baseline."""
import csv
import io
import json
import re
import sys
from datetime import datetime


def reference(request):
    if request["operation"] == "csv_import":
        existing = set(request.get("existing_keys", []))
        transactions, invalid = [], []
        for n, row in enumerate(csv.DictReader(io.StringIO(request["csv"]), delimiter=";"), 2):
            try:
                date = datetime.strptime(row["date"], "%d/%m/%Y").date().isoformat()
                amount = row["amount"].strip()
                if not re.fullmatch(r"[+-]?\d+(?:,\d{1,2})?", amount):
                    raise ValueError("invalid decimal")
                whole, _, fraction = amount.lstrip("+-").partition(",")
                cents = int(whole) * 100 + int(fraction.ljust(2, "0"))
                if amount.startswith("-"):
                    cents = -cents
                description = row["description"]
                key = f"{date}|{description}|{cents}"
                if key not in existing:
                    transactions.append({"date": date, "description": description,
                                         "amount_cents": cents})
            except (ValueError, KeyError, TypeError):
                invalid.append(n)
        return {"transactions": transactions, "invalid_rows": invalid}
    if request["operation"] == "budget_summary":
        rows = request["transactions"]
        income = sum(r["amount_cents"] for r in rows
                     if r["kind"] == "income" and r["amount_cents"] > 0)
        expenses = -sum(r["amount_cents"] for r in rows
                        if (r["kind"] == "expense" and r["amount_cents"] < 0)
                        or (r["kind"] == "refund" and r["amount_cents"] > 0))
        return {"income_cents": income, "expenses_cents": expenses,
                "net_cents": income - expenses}
    raise ValueError("unknown operation")


if __name__ == "__main__":
    request = json.load(sys.stdin)
    result = reference(request)
    fault = sys.argv[1] if len(sys.argv) > 1 else ""
    if fault == "deduplicate" and request["operation"] == "csv_import":
        unique = {json.dumps(r, sort_keys=True): r for r in result["transactions"]}
        result["transactions"] = list(unique.values())
    if fault == "refund-income" and request["operation"] == "budget_summary":
        refunds = sum(r["amount_cents"] for r in request["transactions"] if r["kind"] == "refund")
        result["income_cents"] += refunds
        result["expenses_cents"] += refunds
    if fault == "all-income" and request["operation"] == "budget_summary":
        result["income_cents"] = sum(r["amount_cents"] for r in request["transactions"]
                                     if r["kind"] == "income")
        result["net_cents"] = result["income_cents"] - result["expenses_cents"]
    if fault == "float" and request["operation"] == "csv_import":
        for row in result["transactions"]:
            row["amount_cents"] = row["amount_cents"] / 100
    print(json.dumps({"result": result}))
