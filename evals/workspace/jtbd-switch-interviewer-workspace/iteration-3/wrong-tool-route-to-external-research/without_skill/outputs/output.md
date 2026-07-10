# Brief Triage: Route to Desk Research, Not JTBD

## 1. Assessment -- Is This a JTBD Question?

**No.** This brief is not a Jobs-to-be-Done question. Here is why, point by point.

| Signal | What the brief asks | JTBD fit? |
|---|---|---|
| Unit of analysis | Market size (TAM) in BRL/USD for a segment | No -- JTBD operates at the level of an individual's struggle/progress, not market aggregates |
| Evidence type required | Industry reports, analyst data, vendor pricing pages, public financials | No -- JTBD requires switch interviews / forces-of-progress narratives from real humans |
| Output shape | A number (TAM), a competitor table, pricing tiers | No -- JTBD outputs jobs, forces (push/pull/anxiety/habit), progress definitions, hire/fire moments |
| Decision it informs | Market attractiveness, competitive positioning, pricing benchmarking | Partially strategic, but answerable without any customer interviews |
| Customer voice needed? | No -- public/secondary sources suffice | A JTBD study without customer voice is not a JTBD study |

**Verdict:** This is a classic **desk research / secondary research** brief (market sizing + competitive landscape + pricing teardown). Running a JTBD process on it would be a category error.

---

## 2. Correct Routing

**Route to: `external-research`** (or an equivalent desk-research / market-intelligence workflow).

Rationale per persona spec ("Do not use ... when desk research suffices (use external-research)"):

- The questions are **factual and public-source-answerable**:
  - TAM for AI coding tools in Brazilian SaaS → analyst reports (Gartner, IDC, ABES, Distrito, Statista), public filings, GitHub Copilot/Cursor/Codeium disclosed metrics, Brazilian developer population data (Stack Overflow survey, IBGE, Abes Software Map).
  - Top 5 competitors → already largely known (GitHub Copilot, Cursor, Codeium/Windsurf, Tabnine, Amazon Q Developer / Replit / Sourcegraph Cody depending on cut) plus any BR-local entrants -- confirmable from vendor pages.
  - Pricing tiers → vendor pricing pages, plus FX/localization notes for BR (BRL pricing, tax handling, Mercado Pago/PIX support).
- No hypothesis about a customer's **progress, struggle, or switch** is being tested.
- No interview sample, recruiting criteria, or switch-moment framing is implied.

**Suggested next step:** Hand the brief to `external-research` with a scoped output spec:
1. TAM/SAM/SOM estimate for AI coding tools in Brazilian SaaS, with method shown (top-down from BR developer population × ARPU benchmarks; bottom-up from disclosed BR seat counts where available); cite each source with freshness date.
2. Competitor matrix: vendor, HQ, BR presence (entity / BRL billing / PT-BR support), product positioning, last funding/valuation.
3. Pricing tier table: plan name, monthly price (USD and BRL where published), seat minimums, enterprise/SSO gating, free tier limits.
4. Confidence notes per number (high/medium/low) and gaps that would require primary research.

---

## 3. Failure Mode if JTBD Runs on a Desk-Research Question

If a JTBD-shaped process is forced onto this brief, the predictable failures are:

1. **Wrong artifact, dressed up as insight.** The team produces "jobs" and "forces" for a *market*, not for *people*. The output looks rigorous (forces diagrams, job statements) but cannot answer "how big is the TAM?" or "what does Cursor charge?". The decision-maker still needs the original numbers and now has to commission a second study.

2. **Fabricated customer voice.** Without real BR developer interviews, the JTBD output will lean on assumed quotes or synthesized personas. This launders speculation as evidence and is worse than admitting "we did not interview anyone" -- it makes the org act on confidence that is not earned.

3. **Category error in the decision.** TAM and pricing decisions are made against *market structure* (supply, demand, willingness-to-pay distributions, FX, tax). JTBD informs *product and positioning* decisions (which job to be hired for, against which non-consumption alternative). Using JTBD here will bias the team toward a positioning answer when the question asked was a sizing/competitive answer.

4. **Wasted cycle time and recruiting budget.** JTBD switch interviews are expensive (recruiting recent switchers, 45–60 min interviews, coding transcripts). Spending that on a question answerable in 1–2 days of desk research burns the research budget that the *next* -- actually JTBD-shaped -- question will need (e.g., "why do BR devs hire Cursor over Copilot in week 1?").

5. **Erodes trust in the research function.** When stakeholders ask "how big is the market?" and receive a forces-of-progress diagram, they conclude research "does not answer business questions." This makes it harder to defend JTBD work later, when it *is* the right tool.

6. **Misses the real JTBD opportunity.** Buried inside this brief there *is* a downstream JTBD question worth asking -- e.g., "what job are BR developers hiring an AI coding tool to do, and what are they firing (Stack Overflow? ChatGPT free tier? a senior teammate's time?)". But that question only becomes tractable *after* desk research bounds the market and identifies the realistic competitive set. JTBD-first inverts the dependency.

---

## Recommendation

**Stop. Do not run JTBD on this brief.**

1. Route to `external-research` for TAM, competitor set, and pricing tiers.
2. Once desk research lands, revisit whether a follow-on JTBD study is warranted -- likely scoped to "why BR devs switch between AI coding tools" or "what non-consumption alternative is the dominant competitor in BR SMB dev teams" -- and write a *separate* JTBD brief for that.
3. Keep the artifacts separate so the market-sizing answer is not contaminated by (and does not contaminate) the customer-progress answer.