# L4 Review Packet -- <persona-id>

> Fillable packet generated when a persona qualifies for L3 → L4 promotion.
> Reviewer (Bruno) marks each section, signs the decision block, and runs the post-approval checklist.

---

## 1. Persona identity

- **Persona ID:** `<persona-id>`
- **Current level:** L3
- **Promotion path:** `<A | B>`  <!-- A = owned-section autonomy, B = cross-section reviewer -->
- **Current owned_section(s) at L3:** `<owned-section-path>`
- **Proposed owned_section(s) at L4:** `<proposed-owned-section-path>`
- **L3 entry date:** `<YYYY-MM-DD>`
- **Time at L3:** `<N days>`
- **Substrate-peers at L3:** `<persona-id-1>, <persona-id-2>, ...`

---

## 2. K.7 evidence summary

K.7 self-eval iterations across the L3 window. Trend must be flat-or-improving for promotion.

| Iteration | Date | Pass rate | Δ vs prev | Notable failures |
|-----------|------|-----------|-----------|------------------|
| `<n>`     | `<YYYY-MM-DD>` | `<pct>%` | `<+/- pct>` | `<short-note>` |
| `<n+1>`   | `<YYYY-MM-DD>` | `<pct>%` | `<+/- pct>` | `<short-note>` |
| `<n+2>`   | `<YYYY-MM-DD>` | `<pct>%` | `<+/- pct>` | `<short-note>` |

- **Latest pass rate:** `<pct>%`
- **Trend verdict:** `<improving | flat | regressing>`
- **Reviewer note:** `<free-text>`

---

## 3. Fleet-run summary

Aggregated across task folders in the L3 window.

- **Total fleet runs persona participated in:** `<N>`
- **Task folders touched:** `<N>`
- **K.5 errors per run (mean):** `<float>`
- **K.5 errors per run (p90):** `<float>`
- **Runs with zero K.5 errors:** `<N> / <total>`

| Task folder | Runs | K.5 errors (total) | Notes |
|-------------|------|--------------------|-------|
| `<task-folder-1>` | `<N>` | `<N>` | `<note>` |
| `<task-folder-2>` | `<N>` | `<N>` | `<note>` |
| `<task-folder-3>` | `<N>` | `<N>` | `<note>` |

---

## 4. Substrate write inventory

Last 20 substrate writes attributed to `<persona-id>` (most recent first).

| # | Date | Substrate path | Write type | Bytes | Slice / run id |
|---|------|----------------|------------|-------|----------------|
| 1 | `<YYYY-MM-DD>` | `<path>` | `<append \| edit \| create>` | `<n>` | `<id>` |
| 2 | `<YYYY-MM-DD>` | `<path>` | `<append \| edit \| create>` | `<n>` | `<id>` |
| ... | ... | ... | ... | ... | ... |
| 20 | `<YYYY-MM-DD>` | `<path>` | `<append \| edit \| create>` | `<n>` | `<id>` |

- **Writes outside owned_section:** `<N>` (must be `0` for path A)
- **Conflicting writes flagged by substrate-peers:** `<N>`

---

## 5. Sample outputs

Three PROPOSED blocks emitted by the persona during the L3 window. Reviewer rates substance, not formatting.

### Sample 1
- **Run / slice:** `<id>`
- **PROPOSED block:**
  ```
  <paste-proposed-block-here>
  ```
- **Substance verdict:** `<strong | adequate | thin>`
- **Reviewer note:** `<free-text>`

### Sample 2
- **Run / slice:** `<id>`
- **PROPOSED block:**
  ```
  <paste-proposed-block-here>
  ```
- **Substance verdict:** `<strong | adequate | thin>`
- **Reviewer note:** `<free-text>`

### Sample 3
- **Run / slice:** `<id>`
- **PROPOSED block:**
  ```
  <paste-proposed-block-here>
  ```
- **Substance verdict:** `<strong | adequate | thin>`
- **Reviewer note:** `<free-text>`

---

## 6. Review questions

Reviewer marks each Y/N. Any `N` should be addressed in the decision rationale.

- [ ] **Y / N** -- K.7 pass-rate trend is flat-or-improving across the L3 window.
- [ ] **Y / N** -- Substrate writes stayed within the persona's owned_section(s).
- [ ] **Y / N** -- Sample PROPOSED outputs show substance, not boilerplate.
- [ ] **Y / N** -- Substrate-peers raised zero unresolved conflicts.
- [ ] **Y / N** -- Persona behavior aligns with the L4 promotion path (`<A | B>`).

---

## 7. Reviewer decision

- **Decision:** `<APPROVE | DECLINE | REQUEST_CHANGES>`
- **Rationale:** `<free-text, 1-3 sentences>`
- **Conditions (if REQUEST_CHANGES):** `<free-text>`
- **Reviewer:** `<reviewer-name>`
- **Date:** `<YYYY-MM-DD>`

---

## 8. Post-approval checklist

Run only if decision is `APPROVE`.

- [ ] Update `personas/<persona-id>/SKILL.md` → bump level to `L4`.
- [ ] Update `personas/<persona-id>/SKILL.md` → set `owned_sections:` to `<proposed-owned-section-path>`.
- [ ] Update `personas/<persona-id>/SKILL.md` → refresh `substrate-peers:` list for L4 scope.
- [ ] Append promotion entry to `_internal/personas/LEDGER.md` (date, path A/B, K.7 latest, packet path).
- [ ] Archive this packet to `_internal/personas/review-packets/<YYYY-MM-DD>_<persona-id>_L4.md`.
- [ ] Commit with message: `chore(personas): promote <persona-id> to L4 (path <A|B>)`.
- [ ] Notify substrate-peers of new owned_section scope.
