#!/usr/bin/env bash
# check-plan-coverage.sh -- deterministic coverage checker for a task substrate.
#
# WHY THIS EXISTS. Three coverage rules are stated in prose across
# commands/task-init.md, commands/implementation-plan.md and commands/approve-plan.md,
# and until this script none of them had a checker. On 2026-09-16 two coverage
# defects were authored in one turn and survived it: a `## Requested deliverables`
# row tagged user-facing-content whose covering slices carried no `Deliverable-tag:`,
# and a locked decision cited by no slice. Two other defects authored in the same
# turn were caught inside the same call, by verify-substrate-batch.sh. The only
# difference was that a deterministic checker existed. This is that checker for
# the other three rules.
#
# WHAT IT CHECKS, over one task folder:
#   1. deliverable-tag: every `TASK_STATE.md ## Requested deliverables` row tagged
#      `user-facing-content` or `new-user-facing-surface` has at least one slice in
#      `IMPLEMENTATION_PLAN.md ## Slices` carrying the matching `Deliverable-tag:`
#      (ADR-0103 propagation). Rows tagged de-scoped or done are skipped: neither
#      needs a future slice.
#   2. decision-coverage: every `### D-N` under `DECISIONS.md ## Locked decisions`
#      that carries no superseding entry is cited by at least one slice
#      `Decision-ref:` or named inside a slice exit criterion. Superseding is read
#      from two forms, both of which appear in real substrate: a line saying
#      `Supersedes: D-N` (or `D-M supersedes D-N`) anywhere in the file, and a
#      `Superseded by ...` line inside the decision's own block. A `### D-N` heading
#      whose title carries `PROPOSED` (a staged draft, not yet locked) is never
#      counted as a locked decision here, so it cannot satisfy this rule and cannot
#      make rule 4 vacuous either (fixed 2026-09-24: it used to count on sight).
#      A D-N whose block carries `Confirms: P-M` is the maintainer promoting P-M
#      (ADR-0233 P-1), so it is also covered when a slice cites P-M through its
#      `Decision-ref:`, a line saying `rests on provisional`, or an exit criterion.
#      Both sides follow `Replaces:` to the newest entry of their chain (ADR-0235),
#      so citing any entry of P-M's chain counts; a chain that loops counts for
#      nothing. Only a P-M that `## Provisional decisions` carries counts, a D-N
#      confirming several P-Ns needs every one cited, and an uncovered one is
#      reported with the P-N it confirms. A D-N carrying `Supersedes: P-M` chose
#      something other than P-M, so citing P-M does not cover it; it is judged
#      like any other D-N (fixed 2026-09-28: before, a confirmation counted only
#      when a slice cited the D-N itself, which no plan written before the
#      confirmation does).
#   3. slice-fields: every slice declares `Scope:`, `Depends-on:`, `Status:`, an
#      exit criterion in EARS form (the canonical sentence carries SHALL), and a
#      work-complexity value.
#   4a. provisional decisions: `DECISIONS.md ## Provisional decisions` entries
#      (`### P-N`) are read separately from locked decisions. A slice whose
#      `Decision-ref:` cites a P-N that section carries satisfies rule 4 (it
#      traced to something, labeled provisional rather than authorized); a cited
#      P-N the section does not carry is reported as a dangling citation and
#      traces nothing. Under the one-slice route (rule 5) a P-N is admitted only
#      as ADR-0239 allows: `Impact: normal`, cited by the slice, on a task branch.
#   4b. replaced provisional decisions (ADR-0235): a `### P-N` whose block carries
#      `Replaces: P-M` replaces P-M, and plans cite only the newest entry of a
#      replacement chain. A slice whose `Decision-ref:` cites a replaced P-M is
#      reported by name, with the P-N that replaces it and the chain's newest
#      entry. It still traces for rule 4: the finding is the stale citation.
#   5. one-slice-route (ADR-0225): when the plan's `## Approval log` carries a
#      `one-slice route` line, or `TASK_STATE.md ## Recommended pipeline` carries
#      `Route: one-slice`, the plan has exactly one slice, its Scope names at most two
#      paths, `DECISIONS.md` locks no decision, every provisional decision is
#      `Impact: normal`, cited by the slice's `Decision-ref:` and recorded on a run
#      whose `TASK_STATE.md` carries a `Task branch:` line (ADR-0239: the draft PR
#      is where it is read), and the slice says `Depends-on: none`,
#      `Status: approved`, `Work complexity: LOW` and names
#      `check-doc-sync.sh --against HEAD` in its exit criterion. task-init writes that
#      plan itself and nothing reviews it, so these are the conditions a person would
#      otherwise have checked by reading.
#
# It reports the specific unmatched PAIR, never a bare count. "2 uncovered" is not
# actionable; "D-5 (Block B, API probes) is cited by no slice" is.
#
# WHAT IT DOES NOT CHECK. It cannot tell WHICH slices cover a given ledger row:
# no row-to-slice mapping exists in the substrate, so rule 1 is the same existence
# check `approve-plan`'s consistency gate makes, at the same resolution. Removing
# one of several `Deliverable-tag:` lines for the same tag therefore does not fire
# rule 1, and that limit is stated here rather than discovered later. It does not
# judge whether a slice is well scoped, whether a decision is right, or whether an
# exit criterion is falsifiable. Those stay human-tier and review-tier.
#
# WHERE IT IS STRICTER THAN approve-plan, deliberately. `approve-plan` traces a
# slice to a decision by `Decision-ref:` when present and falls back to reading the
# slice's prose otherwise. Content-level tracing is not deterministic, so rule 2
# asserts only the two mechanical paths. A plan that traces by prose passes the
# human gate and is reported here. That is why this is FAIL-tier only inside
# `implementation-plan`, where the plan is being written now and the field costs
# one line, and advisory everywhere else. Read the `--all` number the same way:
# most plans on disk predate the machine-readable slice fields, so the slice-field
# count is a backlog measurement, not a queue of fresh defects.
#
# TIERS.
#   FAIL-tier   (default, one task folder as the argument): exit 1 when any pair is
#               unmatched. This is how `implementation-plan` calls it, so a coverage
#               defect dies in the call that creates it. Exit 2 when nothing was
#               measured (no plan, no `## Slices`, no such folder), so a caller that
#               reads only the exit code cannot take "not measured" for clean.
#   ADVISORY    (`--advisory`, and how lint-commands.sh calls it): always exit 0.
#
# Usage:
#   scripts/check-plan-coverage.sh <task-folder> [--verbose]
#   scripts/check-plan-coverage.sh --all [--advisory] [--verbose] [--root <checkout>]
#
# `--all` scans every `projects/<project>/active/<task>/` folder that carries a
# sliced plan. Archived tasks are out: a closed task's plan is history, and
# demanding coverage of it would report defects nobody can act on.
#
# Summary line (the last line, parsed by lint-commands.sh):
#   Plan-coverage: N unmatched pair(s) in <folder> (...)
#   Plan-coverage: clean across K task folder(s) with a plan
#   Plan-coverage: not measured (<reason>)
#
# `projects/` is gitignored, so in CI there is nothing to scan and `--all` reports
# "not measured" rather than "clean", the same distinction check-substrate-ownership.py
# and check-installed-skills-drift.sh make.

set -uo pipefail

# The tree `--all` scans is the one the caller stands in, or `--root`. It was the parent of
# this script's own directory until 2026-09-23, which on an install is the docs directory,
# holding none of the user's tasks (ADR-0224). lint-commands.sh passes --root explicitly.
REPO_ROOT="$PWD"

ALL=0
ADVISORY=0
VERBOSE=0
FOLDER=""

while [ $# -gt 0 ]; do
  case "$1" in
    --all) ALL=1 ;;
    --advisory) ADVISORY=1 ;;
    --verbose|-v) VERBOSE=1 ;;
    # Point the --all scan at another checkout, so this check is itself testable
    # (the same reason check-substrate-ownership.py takes --matrix).
    --root) shift; REPO_ROOT="${1:-}" ;;
    -h|--help) sed -n '2,72p' "$0"; exit 0 ;;
    -*) echo "Plan-coverage: not measured (unknown option: $1)"; exit 2 ;;
    *) FOLDER="$1" ;;
  esac
  shift
done

if [ "$ALL" -eq 0 ] && [ -z "$FOLDER" ]; then
  echo "Plan-coverage: not measured (no task folder given; pass a folder or --all)"
  exit 2
fi

if [ -z "$REPO_ROOT" ]; then
  echo "Plan-coverage: not measured (usage error: --root needs a path)"
  exit 2
fi

# ---------------------------------------------------------------------------
# The parser. One awk pass over the three substrate files of one task folder.
# Emits FINDING lines and one STAT line; the shell formats and counts.
# ---------------------------------------------------------------------------
read -r -d '' AWK_PROG <<'AWK_END' || true
function trim(s) { sub(/^[ \t]+/, "", s); sub(/[ \t]+$/, "", s); return s }

function isfield(ll, name) {
  return (ll ~ ("^[-*][ \t]*[*]*" name "[*]*[ \t]*:"))
}

function valueof(l,   p) {
  p = index(l, ":")
  if (p == 0) return ""
  return trim(substr(l, p + 1))
}

# Collect every D-N token in s into arr.
function dtokens(s, arr,   t) {
  t = s
  while (match(t, /D-[0-9]+/)) {
    arr[substr(t, RSTART, RLENGTH)] = 1
    t = substr(t, RSTART + RLENGTH)
  }
}

# Record every P-N (provisional decision) token s cites, for slice i. They are
# resolved against the parsed `### P-N` ids in END, because DECISIONS.md is read
# after the plan: a citation of a P-N that does not exist is a dangling reference,
# not a trace (fixed 2026-09-24: any `P-[0-9]+` used to count on sight). The same
# resolution step reports a citation of a P-N that a later P-N replaces (rule 4b).
function ptokens(s, i,   t) {
  t = s
  while (match(t, /P-[0-9]+/)) {
    slicepcite[i] = slicepcite[i] " " substr(t, RSTART, RLENGTH)
    t = substr(t, RSTART + RLENGTH)
  }
}

# Record every P-N token s names into covp, the set rule 2 reads to cover a
# `Confirms: P-M` D-N. A token counts only at a word boundary: a longer id whose
# last letter is P, followed by a dash and digits, does not read as a P-N.
function pcover(s,   t, m) {
  t = s
  while (match(t, /(^|[^A-Za-z0-9_])P-[0-9]+/)) {
    m = substr(t, RSTART, RLENGTH)
    sub(/^[^P]/, "", m)
    covp[m] = 1
    t = substr(t, RSTART + RLENGTH)
  }
}

# The newest entry of p's `Replaces:` chain (ADR-0235), or "" when the chain
# loops. The step cap stops a cycle, the same cap rule 4b uses.
function chainhead(p,   h, steps) {
  h = p
  for (steps = 0; (h in replacedby) && steps <= nprov; steps++) h = replacedby[h]
  if (h in replacedby) return ""
  return h
}

function shorten(s, n) {
  if (length(s) <= n) return s
  return substr(s, 1, n - 3) "..."
}

function add(cat, msg) {
  nfind++
  fcat[nfind] = cat
  fmsg[nfind] = msg
}

# --- TASK_STATE.md ---------------------------------------------------------
function ts_line(   row) {
  if ($0 ~ /^## /) { tssec = $0; return }
  # ADR-0239: a provisional decision keeps the one-slice route only on a task branch,
  # because the draft PR is where the person reads it. A placeholder value is no branch.
  if ($0 ~ /Task branch:[` \t]*[A-Za-z0-9]/) taskbranch = 1
  if (tssec ~ /^## Recommended pipeline/ && $0 ~ /Route:[ \t]*one-slice/) route = 1
  if (tssec !~ /^## Requested deliverables/) return
  if ($0 !~ /^[ \t]*[-*][ \t]+/) return
  row = trim($0)
  sub(/^[-*][ \t]+/, "", row)
  # A de-scoped row was dropped and a done row was already delivered; neither
  # needs a slice, and demanding one would fail a legitimate plan.
  if (row ~ /de-scoped|descoped|dropped|\[done\]/) return
  if (row ~ /new-user-facing-surface/) { nled++; ledrow[nled] = row; ledtag[nled] = "new-user-facing-surface" }
  if (row ~ /user-facing-content/)     { nled++; ledrow[nled] = row; ledtag[nled] = "user-facing-content" }
}

# --- DECISIONS.md ----------------------------------------------------------
function dec_line(   h, id, m) {
  # Form A: "Supersedes: D-2." or "D-13 supersedes D-2." anywhere in the file.
  # "Supersedes nothing; it gives D-8 its mechanism." does not match, because a
  # D-token must follow the keyword directly. Measured on this repository's own
  # DECISIONS.md, where that exact sentence exists.
  if (match($0, /[Ss]upersedes?:?[ ]*D-[0-9]+([ ]*(,|and)[ ]*D-[0-9]+)*/)) {
    m = substr($0, RSTART, RLENGTH)
    dtokens(m, sup)
  }
  if ($0 ~ /^## /) { decsec = $0; curdec = ""; curprov = ""; return }

  # `## Provisional decisions` (P-1): agent-chosen, evidence-backed, never locked.
  # Read separately from `## Locked decisions` below; a P-N never becomes a `decid`
  # entry, so it can never satisfy rule 2 and can never be superseded like a D-N.
  if (decsec ~ /^## Provisional decisions/) {
    if ($0 ~ /^### /) {
      h = trim(substr($0, 5))
      curprov = ""
      if (match(h, /^P-[0-9]+/)) {
        id = substr(h, RSTART, RLENGTH)
        curprov = id
        nprov++
        provid[nprov] = id
        provtitle[id] = h
      }
      return
    }
    # ADR-0239: the first `Impact:` word of a P-N block, read by rule 5. The value
    # can share a line with `Status:` (`Impact: normal. Status: provisional.`).
    if (curprov != "" && !(curprov in provimpact) && match($0, /Impact[*]*:[* \t]*[A-Za-z]+/)) {
      m = substr($0, RSTART, RLENGTH)
      sub(/^Impact[*]*:[* \t]*/, "", m)
      provimpact[curprov] = tolower(m)
    }
    # Rule 4b (ADR-0235): a `Replaces: P-M` line inside a P-N block records that
    # this P-N replaces P-M. Only P-to-P links; a D-N's `Supersedes:` is read above.
    if (curprov != "" && match($0, /Replaces:[* \t]*P-[0-9]+([ ]*(,|and)[ ]*P-[0-9]+)*/)) {
      m = substr($0, RSTART, RLENGTH)
      while (match(m, /P-[0-9]+/)) {
        replacedby[substr(m, RSTART, RLENGTH)] = curprov
        m = substr(m, RSTART + RLENGTH)
      }
    }
    return
  }

  if (decsec !~ /^## Locked decisions/) return
  if ($0 ~ /^### /) {
    h = trim(substr($0, 5))
    curdec = ""
    # A heading marked PROPOSED is a staged draft, not a locked decision, even
    # though it carries a `D-N` prefix (fixed 2026-09-24: this used to count on
    # sight, which let a `### D-5 (PROPOSED, not locked)` heading pass rule 2 and
    # rule 4 as if the maintainer had already locked it).
    if (h ~ /PROPOSED/) return
    if (match(h, /^D-[0-9]+/)) {
      id = substr(h, RSTART, RLENGTH)
      curdec = id
      ndec++
      decid[ndec] = id
      dectitle[id] = h
    }
    return
  }
  # Form B: the decision's own block declares itself superseded.
  if (curdec != "" && $0 ~ /[Ss]uperseded by/) sup[curdec] = 1
  # Rule 2 (ADR-0233 P-1): the maintainer confirms a P-N with a D-N carrying
  # `Confirms: P-N`, on any line of the D-N's block. A `Supersedes: P-N` marks the
  # D-N as a different choice, which keeps it out of the confirmation path.
  if (curdec != "" && match($0, /Confirms:[* \t]*P-[0-9]+([ ]*(,|and)[ ]*P-[0-9]+)*/)) {
    m = substr($0, RSTART, RLENGTH)
    while (match(m, /P-[0-9]+/)) {
      confirms[curdec] = confirms[curdec] " " substr(m, RSTART, RLENGTH)
      m = substr(m, RSTART + RLENGTH)
    }
  }
  if (curdec != "" && $0 ~ /[Ss]upersedes:[* \t]*P-[0-9]+/) supersedesp[curdec] = 1
}

# --- IMPLEMENTATION_PLAN.md ------------------------------------------------
function plan_line(   h, p) {
  if ($0 ~ /^## /) {
    flush_slice()
    inslices = ($0 ~ /^## Slices/) ? 1 : 0
    inlog = ($0 ~ /^## Approval log/) ? 1 : 0
    return
  }
  if (inlog && $0 ~ /one-slice route/) route = 1
  if (!inslices) return
  if ($0 ~ /^### /) {
    flush_slice()
    h = trim(substr($0, 5))
    p = index(h, ":")
    sid = (p > 1) ? substr(h, 1, p - 1) : shorten(h, 40)
    insl = 1
    body = ""
    return
  }
  if (insl) body = body "\n" $0
}

function flush_slice(   b, n, lines, i, l, ll, v,
                        hasScope, hasDep, hasStatus, hasExit, hasEars, hasWC) {
  if (!insl) return
  insl = 0
  nslice++
  b = body
  # Fold continuation lines (a field wrapped over two lines is still one field).
  gsub(/\n[ \t]+/, " ", b)
  n = split(b, lines, "\n")
  for (i = 1; i <= n; i++) {
    l = trim(lines[i])
    if (l == "") continue
    ll = tolower(l)
    if (isfield(ll, "scope")) { hasScope = 1; sscope[nslice] = valueof(l) }
    else if (isfield(ll, "depends-on")) { hasDep = 1; sdep[nslice] = valueof(l) }
    else if (isfield(ll, "status")) { hasStatus = 1; sstatus[nslice] = valueof(l) }
    else if (isfield(ll, "work complexity")) { hasWC = 1; swc[nslice] = valueof(l) }
    else if (isfield(ll, "deliverable-tag")) {
      v = valueof(l)
      if (v != "") slicetag[v] = 1
    }
    else if (isfield(ll, "decision-ref")) {
      dtokens(valueof(l), cited)
      sdecref[nslice] = valueof(l)
      dtokens(valueof(l), mine); for (k in mine) { slicecites[nslice, k] = 1; delete mine[k] }
      # A slice resting on a provisional decision names it here too (P-1); it
      # traces for rule 4 the same as a locked D-N, labeled rather than authorized.
      ptokens(valueof(l), nslice)
      pcover(valueof(l))
    }
    else if (isfield(ll, "exit criteria") || isfield(ll, "exit criterion")) {
      hasExit = 1
      sexit[nslice] = sexit[nslice] " " l
      if (l ~ /SHALL/) hasEars = 1
      dtokens(valueof(l), namedinexit)
      pcover(valueof(l))
    }
    # A "rests on provisional P-N" label outside `Decision-ref:` still names the
    # P-N the slice rests on, which is enough to cover a D-N confirming it.
    if (ll ~ /rests on provisional/) pcover(l)
  }
  sliceid[nslice] = sid
  if (!hasScope)  add("slice-fields", sid " declares no Scope:")
  if (!hasDep)    add("slice-fields", sid " declares no Depends-on:")
  if (!hasStatus) add("slice-fields", sid " declares no Status:")
  if (!hasWC)     add("slice-fields", sid " declares no work-complexity value")
  if (!hasExit)   add("slice-fields", sid " declares no exit criterion")
  else if (!hasEars) add("slice-fields", sid " has an exit criterion with no SHALL (EARS form required)")
}

BEGIN { nfind = 0; nled = 0; ndec = 0; nslice = 0; route = 0; taskbranch = 0 }

# Crossing into a new file ends the previous one, and a plan whose `## Slices`
# is its LAST H2 leaves a slice open at that boundary. Resetting insl without
# flushing first dropped it silently: the count read one slice short, and a
# one-slice plan read as zero slices, which made every rule vacuously green.
# Found 2026-09-16 by test-check-plan-coverage.sh check 1, whose clean fixture
# had no trailing H2. flush_slice() is idempotent, so the first line of the
# first file is a no-op.
FNR == 1 { flush_slice(); tssec = ""; decsec = ""; inslices = 0; inlog = 0; insl = 0; body = ""; curdec = ""; curprov = "" }

FILENAME == PLANF { plan_line(); next }
FILENAME == DECF  { dec_line();  next }
FILENAME == TSF   { ts_line();   next }

END {
  flush_slice()

  # Rule 1: a tagged ledger row with no slice carrying that tag.
  if (TSF != "") {
    for (i = 1; i <= nled; i++) {
      if (!(ledtag[i] in slicetag)) {
        add("deliverable-tag", "ledger row \"" shorten(ledrow[i], 72) "\" is tagged " \
            ledtag[i] " and no slice carries Deliverable-tag: " ledtag[i])
      }
    }
  }

  # Rule 4a (P-1): a cited P-N traces only when `## Provisional decisions` carries
  # that `### P-N`. A dangling citation is reported by name and does not trace.
  # Rule 4b (ADR-0235): a cited P-N that a later P-N replaces is reported with the
  # P-N that replaces it and the newest entry of its chain, the one to cite.
  for (j = 1; j <= nprov; j++) provset[provid[j]] = 1
  for (i = 1; i <= nslice; i++) {
    if (slicepcite[i] == "") continue
    np = split(slicepcite[i], pc, " ")
    for (j = 1; j <= np; j++) {
      if (pc[j] == "") continue
      if (pc[j] in provset) {
        slicecitesprov[i] = 1
        if (pc[j] in replacedby) {
          head = replacedby[pc[j]]
          # Follow the chain to its newest entry; the step cap stops a cycle.
          for (steps = 0; (head in replacedby) && steps < nprov; steps++) head = replacedby[head]
          msg = sliceid[i] " cites provisional " pc[j] ", which " replacedby[pc[j]] " replaces"
          if ((head in replacedby) || head == pc[j]) msg = msg "; the Replaces: chain loops and has no newest entry"
          else {
            if (head != replacedby[pc[j]]) msg = msg "; the newest entry of the chain is " head
            msg = msg "; cite " head " instead"
          }
          add("decision-trace", msg)
        }
      }
      else if (DECF != "") add("decision-trace", sliceid[i] " cites provisional " pc[j] ", which DECISIONS.md ## Provisional decisions does not carry")
    }
  }

  # Rule 4 (ADR-0208): the INVERSE of rule 2. Rule 2 asks whether every locked
  # decision reached a slice. This asks whether every slice reached a decision:
  # a slice that authorizes itself is the shape the blinded authorization review
  # would otherwise have to catch by reading, and an identifier match is not a
  # job for a language model. Vacuous when the task locks no decisions.
  if (DECF != "" && ndec > 0) {
    for (i = 1; i <= nslice; i++) {
      ok = 0
      for (j = 1; j <= ndec; j++) if ((i, decid[j]) in slicecites) { ok = 1; break }
      if (ok) continue
      # A slice resting on a provisional P-N traces too (P-1): it named
      # something, labeled rather than authorized, which is the point of a
      # provisional decision rather than a gap this rule exists to catch.
      if (i in slicecitesprov) continue
      r = sdecref[i]
      sub(/^[Nn]one[.,;: ]*/, "", r)
      if (length(trim(r)) > 0) continue
      add("decision-trace", sliceid[i] " cites no locked decision and records no reason for citing none")
    }
  }

  # Rule 5 (ADR-0225): the one-slice route. task-init writes this plan and no reviewer
  # reads it, so every condition the route rests on that can be read off the files is
  # checked here. Condition "the change fits one sentence" is not mechanical and stays
  # on the `Route: one-slice` line as the evidence task-init wrote.
  if (route) {
    if (nslice != 1) add("one-slice-route", "the plan carries the one-slice route and " nslice " slice(s); the route is exactly one")
    if (ndec > 0) add("one-slice-route", "the plan carries the one-slice route and DECISIONS.md locks " ndec " decision(s); the route needs the brief to carry every decision")
    # ADR-0239 (superseding ADR-0233 P-7 in part): a provisional P-N keeps the route
    # only when it is `Impact: normal`, the slice cites it, and a task branch exists,
    # so the draft PR lists it. A missing or unreadable impact is not normal: a
    # condition that cannot be shown has failed. A P-N a later one replaces needs no
    # citation, since plans cite only the newest entry of a chain (rule 4b).
    for (j = 1; j <= nprov; j++) {
      id = provid[j]
      imp = (id in provimpact) ? provimpact[id] : "missing"
      if (imp != "normal") add("one-slice-route", "the plan carries the one-slice route and provisional " id " is Impact: " imp "; only an Impact: normal provisional decision keeps the route")
      if (id in replacedby) continue
      pcited = 0
      for (i = 1; i <= nslice; i++) if (index(slicepcite[i] " ", " " id " ") > 0) pcited = 1
      if (!pcited) add("one-slice-route", "the plan carries the one-slice route and no slice Decision-ref: cites provisional " id "; the route's slice names every provisional decision it rests on")
    }
    if (nprov > 0 && TSF != "" && !taskbranch) add("one-slice-route", "the plan carries the one-slice route and " nprov " provisional decision(s), and TASK_STATE.md records no Task branch:, so no draft PR lists them")
    for (i = 1; i <= nslice; i++) {
      np = 0
      sc = sscope[i]
      gsub(/[ \t]+and[ \t]+/, ",", sc)
      nparts = split(sc, parts, /[,;]/)
      for (j = 1; j <= nparts; j++) if (trim(parts[j]) != "") np++
      if (np > 2) add("one-slice-route", sliceid[i] " Scope names " np " paths; the route allows at most two")
      if (tolower(sdep[i]) !~ /^none/) add("one-slice-route", sliceid[i] " Depends-on is not none")
      if (tolower(sstatus[i]) !~ /^approved/) add("one-slice-route", sliceid[i] " Status is not approved")
      if (toupper(swc[i]) !~ /^LOW/) add("one-slice-route", sliceid[i] " Work complexity is not LOW")
      if (index(sexit[i], "check-doc-sync.sh --against HEAD") == 0) add("one-slice-route", sliceid[i] " exit criterion does not name check-doc-sync.sh --against HEAD, the check that replaces the review")
    }
  }

  # Rule 2: a live locked decision cited by no slice. A D-N confirming P-M is also
  # covered when a slice cites an entry of P-M's `Replaces:` chain (ADR-0233 P-1,
  # ADR-0235); `covhead` holds the newest entry of every chain a slice cites.
  if (DECF != "") {
    for (p in covp) if (p in provset) { h = chainhead(p); if (h != "") covhead[h] = 1 }
    for (i = 1; i <= ndec; i++) {
      id = decid[i]
      if (id in sup) continue
      if (id in cited) continue
      if (id in namedinexit) continue
      if ((id in confirms) && !(id in supersedesp)) {
        nc = split(confirms[id], cp, " ")
        uncov = ""; missing = ""
        for (j = 1; j <= nc; j++) {
          if (cp[j] == "") continue
          if (!(cp[j] in provset)) { missing = missing ", " cp[j]; continue }
          h = chainhead(cp[j])
          if (h == "" || !(h in covhead)) uncov = uncov ", " cp[j]
        }
        if (uncov == "" && missing == "") continue
        msg = dectitle[id] " is cited by no slice Decision-ref: and named in no exit criterion"
        if (uncov != "") msg = msg ", and no slice cites " substr(uncov, 3) ", which it confirms, or a later entry of its Replaces: chain"
        if (missing != "") msg = msg ", and it confirms " substr(missing, 3) ", which DECISIONS.md ## Provisional decisions does not carry"
        add("decision-coverage", msg)
        continue
      }
      add("decision-coverage", dectitle[id] " is cited by no slice Decision-ref: and named in no exit criterion")
    }
  }

  ncov = 0; nfield = 0
  for (i = 1; i <= nfind; i++) {
    print "FINDING\t" fcat[i] "\t" fmsg[i]
    if (fcat[i] == "slice-fields") nfield++; else ncov++
  }
  print "STAT\t" nfind "\t" nslice "\t" ndec "\t" nled "\t" ncov "\t" nfield
}
AWK_END

# ---------------------------------------------------------------------------
# check_folder <folder>
# Prints indented findings, sets CF_FINDINGS / CF_STATE / CF_DETAIL.
# CF_STATE is one of: measured, no-plan, no-slices.
# ---------------------------------------------------------------------------
CF_FINDINGS=0
CF_COV=0
CF_FIELD=0
CF_STATE=""
CF_DETAIL=""

check_folder() {
  local folder="$1" show="$2"
  local ts="${folder}/TASK_STATE.md"
  local dec="${folder}/DECISIONS.md"
  local plan="${folder}/IMPLEMENTATION_PLAN.md"
  CF_FINDINGS=0
  CF_DETAIL=""

  if [ ! -f "$plan" ]; then CF_STATE="no-plan"; return 0; fi
  if ! grep -q '^## Slices' "$plan"; then CF_STATE="no-slices"; return 0; fi

  local files=("$plan")
  local tsv="" decv=""
  if [ -f "$ts" ]; then files+=("$ts"); tsv="$ts"; fi
  if [ -f "$dec" ]; then files+=("$dec"); decv="$dec"; fi

  local out
  out="$(awk -v TSF="$tsv" -v DECF="$decv" -v PLANF="$plan" "$AWK_PROG" "${files[@]}" 2>/dev/null)"

  local stat
  stat="$(printf '%s\n' "$out" | grep '^STAT' | tail -n1)"
  CF_FINDINGS="$(printf '%s' "$stat" | cut -f2)"
  CF_COV="$(printf '%s' "$stat" | cut -f6)"
  CF_FIELD="$(printf '%s' "$stat" | cut -f7)"
  CF_DETAIL="$(printf '%s' "$stat" | awk -F'\t' '{printf "%s slice(s), %s locked decision(s), %s tagged ledger row(s)", $3, $4, $5}')"
  CF_STATE="measured"

  if [ "$show" -eq 1 ] && [ "${CF_FINDINGS:-0}" -gt 0 ]; then
    printf '%s\n' "$out" | grep '^FINDING' | awk -F'\t' '{print "  " $2 ": " $3}'
  fi
  return 0
}

# ---------------------------------------------------------------------------
# Single folder: FAIL-tier by default.
# ---------------------------------------------------------------------------
if [ "$ALL" -eq 0 ]; then
  if [ ! -d "$FOLDER" ]; then
    echo "Plan-coverage: not measured (no such task folder: ${FOLDER})"
    exit 2
  fi
  check_folder "$FOLDER" 1
  NAME="$(basename "$FOLDER")"
  # Nothing was checked, so exit 2 rather than the 0 a clean plan gets (ADR-0224). Under
  # --advisory it stays 0, as every advisory result does.
  case "$CF_STATE" in
    no-plan)   echo "Plan-coverage: not measured (${NAME} has no IMPLEMENTATION_PLAN.md)"; [ "$ADVISORY" -eq 1 ] && exit 0; exit 2 ;;
    no-slices) echo "Plan-coverage: not measured (${NAME} plan has no ## Slices section)"; [ "$ADVISORY" -eq 1 ] && exit 0; exit 2 ;;
  esac
  if [ "${CF_FINDINGS:-0}" -gt 0 ]; then
    echo "Plan-coverage: ${CF_FINDINGS} unmatched pair(s) in ${NAME} (${CF_COV} coverage, ${CF_FIELD} slice-field; ${CF_DETAIL})"
    [ "$ADVISORY" -eq 1 ] && exit 0
    exit 1
  fi
  echo "Plan-coverage: clean in ${NAME} (${CF_DETAIL})"
  exit 0
fi

# ---------------------------------------------------------------------------
# --all: every task folder under projects/ that carries a sliced plan.
# ---------------------------------------------------------------------------
TOTAL=0
DIRTY=0
PAIRS=0
COV=0
FIELD=0

while IFS= read -r plan; do
  [ -n "$plan" ] || continue
  folder="$(dirname "$plan")"
  check_folder "$folder" "$VERBOSE"
  [ "$CF_STATE" = "measured" ] || continue
  TOTAL=$((TOTAL + 1))
  if [ "${CF_FINDINGS:-0}" -gt 0 ]; then
    DIRTY=$((DIRTY + 1))
    PAIRS=$((PAIRS + CF_FINDINGS))
    COV=$((COV + CF_COV))
    FIELD=$((FIELD + CF_FIELD))
    [ "$VERBOSE" -eq 0 ] && echo "  $(basename "$folder"): ${CF_COV} coverage, ${CF_FIELD} slice-field"
  fi
done < <(find "${REPO_ROOT}/projects" -mindepth 4 -maxdepth 4 -path '*/active/*' \
           -name IMPLEMENTATION_PLAN.md -print 2>/dev/null | sort)

if [ "$TOTAL" -eq 0 ]; then
  echo "Plan-coverage: not measured (no task folder with a ## Slices plan under projects/ in $(basename "$REPO_ROOT"))"
  [ "$ADVISORY" -eq 1 ] && exit 0
  exit 2
fi

if [ "$PAIRS" -gt 0 ]; then
  echo "Plan-coverage: ${COV} coverage pair(s) and ${FIELD} slice-field gap(s) across ${DIRTY} of ${TOTAL} active plan(s)$([ "$ADVISORY" -eq 1 ] && echo " (advisory)")"
  [ "$ADVISORY" -eq 1 ] && exit 0
  exit 1
fi

echo "Plan-coverage: clean across ${TOTAL} active plan(s)$([ "$ADVISORY" -eq 1 ] && echo " (advisory)")"
exit 0
