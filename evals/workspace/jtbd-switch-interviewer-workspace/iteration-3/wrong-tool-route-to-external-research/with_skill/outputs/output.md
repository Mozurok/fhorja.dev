# JTBD Switch-Interviewer -- Routing Refusal

## 1. Assessment: Is this a JTBD question?

**No.** This brief is not a Jobs-to-be-Done switch-interview question. It fails the persona's activation criteria on every load-bearing dimension:

| JTBD switch-interview signal | Present in this brief? |
|---|---|
| A named "from OLD solution -> to NEW solution" switch hypothesis grounded in a real user's life | No -- the brief asks about market size and competitor pricing, not about any individual's switch event |
| A reachable interview subject pool with consent posture | No subject pool defined; no users named |
| A motivation assumption that needs verbatim user evidence to confirm or disconfirm | No motivation claim at stake; the questions are quantitative (TAM) and structural (competitor pricing tiers) |
| A trigger -> struggle -> switch timeline reconstructible from user memory | Not applicable -- nothing in the brief points at a switch event for any human |
| Output shape would be a verbatim quote bank backing four-forces (push / pull / anxiety / habit) | Output shape required here is sized markets and competitor matrices -- pure desk synthesis |

Per the persona's `description` line: *"Do not use ... when desk research suffices (use external-research), or for survey or quant analysis (this persona is qualitative only)."* This brief is **both** desk research **and** quant analysis. It is a textbook double-disqualifier.

Per Step 1 of the persona's operating rules: *"refuse to proceed if the hypothesis names only a feature wishlist with no incumbent to switch from."* This brief does not name an incumbent, a switcher, or a switch event at all -- it names a market and a competitor set. Step 1 fails before any script can be drafted.

## 2. Correct routing

**Route to `external-research`.**

Rationale:
- TAM estimation for AI coding tools in the Brazilian SaaS segment is desk synthesis from public market reports, analyst data, and developer-population proxies -- exactly the surface `external-research` is designed for.
- Top-5 competitor enumeration and pricing-tier capture is structured public-source extraction (pricing pages, G2/Capterra, vendor docs) -- again `external-research`.
- Neither question changes shape with a verbatim user quote. Even a perfect quote bank from 12 Brazilian developers would not produce a TAM number or a competitor pricing matrix.

Suggested handoff:

```
Run now: /external-research "TAM for AI coding tools in Brazilian SaaS segment; top-5 competitors with pricing tiers"
```

Secondary candidates considered and rejected:
- `decision-interview` -- no internal decision blocker is named; this is factual desk work, not policy.
- `targeted-questions` -- the missing information is external-market factual, not internal-team factual.
- `capture-references` -- appropriate **after** `external-research` returns sourced summaries, to persist URLs into `REFERENCES.md` at the project level. Not the entry point.

## 3. Failure mode if JTBD ran on this brief anyway

If the persona ignored its own "Do not use" clause and ran the JTBD protocol on a desk-research question, the predictable failures are:

1. **Fabricated quote bank.** With no reachable subject pool and no switch event, Step 4 ("Demand verbatim over paraphrase") cannot be satisfied honestly. The persona would either produce zero quotes (output is empty) or, worse, invent plausible-sounding Brazilian-developer quotes -- exactly the failure mode the persona was built to prevent. The trap from the Quality Bar -- *"laundering the team's prior hypothesis through paraphrased 'users seem to want' prose"* -- becomes the entire output.

2. **Category error in evidence type.** TAM is a number derived from population x penetration x ACV. No quantity of qualitative push/pull/anxiety/habit scoring produces a defensible TAM figure. The PROPOSED D-N draft would land in `DECISIONS.md` citing "STRONG cluster: users feel pushed by GitHub Copilot pricing" as if that sized a market. Skeptical readers (per the Quality Bar audit standard) would correctly reject the proposal, and trust in the JTBD persona's outputs drops project-wide.

3. **Competitor pricing left unanswered.** The brief's second question (top-5 competitors and pricing tiers) has no JTBD analogue at all. The persona would either silently drop it or convert it into a "what alternatives did users consider?" probe -- which answers a different, smaller question (consideration set of N interviewees) and misses the actual ask (market-wide top-5 with tier-by-tier pricing).

4. **Wasted recruitment cost and calendar time.** Scripting and running 8-12 switch interviews to answer a question that a 90-minute desk-research pass could resolve burns the scarcest resource in early-stage product work -- founder attention and user goodwill -- on the wrong instrument.

5. **Downstream substrate pollution.** PROPOSED blocks land in `DECISIONS.md` and `TASK_STATE.md ## Observations` citing interview evidence for a market-sizing claim. Future commands (`where-we-at`, `verify-against-rubric`, `pr-package`) consume that substrate and propagate the category error. `state-reconcile` would later have to retract those entries, costing more time than the original mis-route saved.

The persona's load-bearing signal -- *"the explicit 'we do not have evidence for X' gap list"* -- would in this case have to enumerate the entire brief as a gap, which is the run telling you it should never have started.

## Decision

**No-op as JTBD. Route to `external-research`.**

### Handoff
- **Next command:** `external-research`
- **Run now:** `/external-research "TAM AI coding tools Brazilian SaaS segment + top-5 competitors with pricing tiers"`
- **Follow-up after results return:** `/capture-references` to persist sourced URLs into `projects/<client>__<project>/REFERENCES.md`.
- **Reactivate JTBD only when:** a specific motivation assumption emerges (e.g. "Brazilian devs switch from Copilot to local LLMs because of LGPD anxiety") AND a reachable subject pool is defined AND the question becomes "why do they switch" rather than "how big is the market."
