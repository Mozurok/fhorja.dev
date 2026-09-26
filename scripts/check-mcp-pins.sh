#!/usr/bin/env bash
# check-mcp-pins.sh
#
# Guards one invariant: every MCP server declared in .mcp.json has a vetting
# pins entry in .mcp-vet-pins.json. A server that reached the config without a
# vet is the config-entry attack path, which the 2026 CVE record puts ahead of
# the tool-description attacks that ADR-0097 already addresses.
#
# LOCAL-ONLY BY CONSTRUCTION. Both .mcp.json and .mcp-vet-pins.json are
# gitignored (.gitignore:41-42), so this never runs meaningfully in CI and
# never guards the public mirror. It guards the maintainer's working tree.
# That is why a tree with no .mcp.json reports "not measured" and NEVER
# "clean": a checker that measures zero inputs and prints clean is the defect
# this repo already fixed once in check-instruction-budget.sh. Do not wire a
# bare "clean" into lint output for the absent case.
#
# What it does NOT do: it does not verify that the pinned hashes still match
# the live tool surface. That comparison needs the server's tool descriptions
# and schemas, and there is no CLI that dumps them (`claude mcp get` returns
# scope, status, type and URL only). The capture has to come from an MCP
# client, so drift detection stays with mcp-server-vet.
#
# It also does not enforce a re-vet interval. It prints the age of each pins
# record and stops there, because no re-vet policy has been decided.
#
# Exit codes:
#   0  every declared server has a pins entry, or no .mcp.json exists here
#   1  a declared server has no pins entry
#   2  usage error, or a file present but unparseable

set -euo pipefail

ROOT="."
while [ $# -gt 0 ]; do
  case "$1" in
    --root) ROOT="${2:-}"; shift 2 || true ;;
    -h|--help) sed -n '2,30p' "$0"; exit 0 ;;
    *) echo "MCP-pins: skipped (usage error: unknown argument '$1')" >&2; exit 2 ;;
  esac
done

if [ ! -d "$ROOT" ]; then
  echo "MCP-pins: skipped (usage error: --root is not a directory)" >&2
  exit 2
fi

CFG="$ROOT/.mcp.json"
PINS="$ROOT/.mcp-vet-pins.json"

if [ ! -f "$CFG" ]; then
  echo "MCP-pins: not measured (no .mcp.json in this tree; both it and the pins record are gitignored)"
  exit 0
fi

python3 - "$CFG" "$PINS" <<'PY'
import json, os, sys, datetime

cfg_path, pins_path = sys.argv[1], sys.argv[2]

def die(msg):
    print(f"MCP-pins: skipped (unparseable: {msg})", file=sys.stderr)
    sys.exit(2)

try:
    cfg = json.load(open(cfg_path))
except Exception as e:
    die(f".mcp.json: {e}")

servers = cfg.get("mcpServers")
if servers is None or not isinstance(servers, dict):
    die(".mcp.json has no mcpServers object")

declared = sorted(servers)
if not declared:
    print("MCP-pins: not measured (.mcp.json declares 0 servers)")
    sys.exit(0)

pinned = {}
if os.path.isfile(pins_path):
    try:
        doc = json.load(open(pins_path))
    except Exception as e:
        die(f".mcp-vet-pins.json: {e}")
    if isinstance(doc, dict) and "server" in doc:
        pinned[doc["server"]] = doc
    elif isinstance(doc, dict) and isinstance(doc.get("servers"), dict):
        pinned = dict(doc["servers"])
    elif isinstance(doc, list):
        for rec in doc:
            if isinstance(rec, dict) and "server" in rec:
                pinned[rec["server"]] = rec
    else:
        die(".mcp-vet-pins.json shape is neither a single record, a servers map, nor a list")

missing = [s for s in declared if s not in pinned]

for s in declared:
    rec = pinned.get(s)
    if not rec:
        continue
    d = rec.get("vet_date") or "unknown"
    age = ""
    try:
        then = datetime.date.fromisoformat(d)
        age = f", {(datetime.date.today() - then).days}d old"
    except Exception:
        pass
    ntools = len(rec.get("tools") or {})
    print(f"  {s}: pinned {ntools} tool(s), vet_date {d}{age} (age is reported, not enforced)")

if missing:
    print(f"MCP-pins: {len(missing)} of {len(declared)} declared server(s) have NO vetting pins: "
          + ", ".join(missing))
    print("  Run mcp-server-vet on each and record its pins before trusting it.")
    sys.exit(1)

print(f"MCP-pins: clean (measured {len(declared)} of {len(declared)} declared server(s); "
      "coverage only, hash drift not checked)")
sys.exit(0)
PY
