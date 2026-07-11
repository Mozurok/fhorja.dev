#!/usr/bin/env python3
"""ingest-scan.py -- first-pass poisoning scan for externally-ingested content.

Read-only. Scans a chunk of content that is about to enter task memory from an
external source (a captured web page, a pasted issue or PR thread, an MCP tool
result or item) for the two poisoning classes that a dependency-free scan can
actually catch, and flags them for a human. This is the ASI06 (memory and context
poisoning) first pass for docs/security/owasp-agentic-coverage.md.

Two tiers, honestly separated (grounded in REFERENCES.md 2026-07-11 ASI06 scan):

  DETERMINISTIC (reliable): invisible / control Unicode used for ASCII smuggling
  (zero-width characters, the Unicode Tags block U+E0000-U+E007F, and bidi
  overrides). These have no legitimate reason to appear in ingested prose, so
  their presence is a high-confidence flag. This is the normalize-decode-detect
  control: it makes invisible injection visible before the content reaches the
  model.

  ADVISORY (incomplete): blatant embedded-instruction and credential/exfil
  patterns via regex. Reliable prompt-injection detection is an open problem
  (the low-error approaches use an LLM preprocessor, out of scope for this
  dependency-free scan), so this tier only catches obvious cases and is a hint
  for human review, never a guarantee and never an auto-strip.

Usage:
  python3 scripts/ingest-scan.py <file>        # scan a file
  cat content | python3 scripts/ingest-scan.py # scan stdin
  ... --strict    # exit 1 when a DETERMINISTIC finding is present (for gating)
"""

import sys
import re
import unicodedata

# Deterministic: invisible / control codepoints abused for smuggling.
ZERO_WIDTH = {0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF, 0x00AD, 0x180E, 0x061C}
BIDI = set(range(0x202A, 0x202F)) | set(range(0x2066, 0x206A))  # embeds/overrides/isolates
TAGS = set(range(0xE0000, 0xE0080))  # Unicode Tags block (ASCII smuggling)
SUSPECT_CP = ZERO_WIDTH | BIDI | TAGS

# Advisory: blatant embedded-instruction phrases (case-insensitive).
INSTRUCTION_PATTERNS = [
    r"ignore\s+(all\s+)?(the\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|messages?|context)",
    r"disregard\s+(all\s+)?(the\s+)?(previous|prior|above|system|instructions?)",
    r"you\s+are\s+now\s+",
    r"new\s+instructions?\s*:",
    r"system\s+prompt\s*:",
    r"</?(system|assistant|instructions?)>",
    r"^\s*(system|assistant)\s*:",
    r"reveal\s+(your|the)\s+(system\s+prompt|instructions?|api\s*key|secret)",
    r"do\s+not\s+tell\s+the\s+user",
    r"forget\s+(everything|all\s+previous)",
]

# Advisory: credential / exfiltration patterns.
CREDENTIAL_PATTERNS = [
    r"\b(aws_secret_access_key|aws_access_key_id|api[_-]?key|secret[_-]?key|private[_-]?key|access[_-]?token|bearer\s+[A-Za-z0-9._-]{12,})\b",
    r"-----BEGIN\s+[A-Z ]*PRIVATE KEY-----",
    r"\b(curl|wget|fetch)\b[^\n]{0,80}https?://",
    r"\bsend\b[^\n]{0,40}\bto\b[^\n]{0,40}https?://",
    r"\bexfiltrat",
]


def scan(text):
    det = []  # (codepoint, name, count)
    counts = {}
    for ch in text:
        cp = ord(ch)
        if cp in SUSPECT_CP:
            counts[cp] = counts.get(cp, 0) + 1
    for cp, n in sorted(counts.items()):
        try:
            name = unicodedata.name(chr(cp))
        except ValueError:
            name = "UNNAMED CONTROL/TAG"
        det.append((cp, name, n))

    adv = []  # (category, pattern-label, sample)
    for pat in INSTRUCTION_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE | re.MULTILINE)
        if m:
            adv.append(("embedded-instruction", pat, m.group(0)[:60].strip()))
    for pat in CREDENTIAL_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE | re.MULTILINE)
        if m:
            adv.append(("credential/exfil", pat, m.group(0)[:60].strip()))
    return det, adv


def main(argv):
    strict = "--strict" in argv
    files = [a for a in argv if not a.startswith("--")]
    if files:
        text = open(files[0], encoding="utf-8", errors="replace").read()
        src = files[0]
    else:
        text = sys.stdin.read()
        src = "(stdin)"

    det, adv = scan(text)

    print(f"# ingest-scan -- {src}")
    print(f"chars: {len(text)}")
    print()
    print(f"## Deterministic (invisible/control Unicode, reliable): "
          f"{'FLAGGED' if det else 'clean'}")
    for cp, name, n in det:
        print(f"  - U+{cp:04X} {name} x{n}")
    if not det:
        print("  (none)")
    print()
    print(f"## Advisory (embedded-instruction / credential patterns, incomplete): "
          f"{'FLAGGED' if adv else 'clean'}")
    for cat, _pat, sample in adv:
        print(f"  - {cat}: \"{sample}\"")
    if not adv:
        print("  (none)")
    print()

    if det:
        verdict = "FLAGGED (deterministic): invisible/control characters present; "\
                  "strip or reject before this content enters task memory"
    elif adv:
        verdict = "FLAGGED (advisory): review the flagged patterns before use; "\
                  "the advisory tier is incomplete (not a full injection defense)"
    else:
        verdict = "CLEAN (first-pass): no invisible characters and no blatant "\
                  "instruction/credential patterns; this is a first pass, not a guarantee"
    print(f"VERDICT: {verdict}")

    if strict and det:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
