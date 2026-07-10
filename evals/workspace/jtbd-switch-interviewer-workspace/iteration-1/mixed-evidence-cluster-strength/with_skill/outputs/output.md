# JTBD Switch-Interview Synthesis -- Round 1

**Active task:** Supabase-backed expense-tracker SaaS -- motivation evidence round
**Switch hypothesis (team-stated):** "Users switch from Excel to our SaaS because of automation (auto-categorization, receipt OCR)."
**Switch hypothesis restated in user framing (OLD -> NEW):** From "I keep my expenses in a spreadsheet I maintain by hand" -> to "I let a dedicated expense app capture and organize my expenses for me."
**Interview pool:** n=3 (I1 freelance designer, I2 solo consultant, I3 small-business owner). All three switched within the last 3 months from Excel to a competing SaaS. Sample size note: at n=3 the strongest possible cluster tag is STRONG (3/3); no cluster can be more than tentatively generalized to the broader market.

---

## Per-interview synthesis

### I1 -- Freelance designer (switched 3 months ago; Excel + manual entry -> competing SaaS)

**Timeline reconstruction:**
- **TRIGGER:** Year-end tax preparation under deadline pressure. The discovery that her spreadsheet had double-counted a month was the originating event. > "I was up at 2am the night before my taxes were due and I realized I'd double-counted a whole month." (I1)
- **STRUGGLE:** Ongoing low-grade dread around the integrity of her own sheet -- formula fragility was the active pain during the evaluation window. > "Every time I added a row I was scared I'd break the formula in the totals column." (I1)
- **SWITCH:** Adopted a competing SaaS whose receipt-photo capture removed the cognitive load of manual entry. > "What sold me was honestly that I could just photograph a receipt and stop thinking about it." (I1)

**Four-forces scoring:**

| Force | Score | Verbatim evidence |
|---|---|---|
| PUSH (old intolerable) | STRONG | > "I was up at 2am the night before my taxes were due and I realized I'd double-counted a whole month." (I1) + > "Every time I added a row I was scared I'd break the formula in the totals column." (I1) |
| PULL (new attractive) | STRONG | > "What sold me was honestly that I could just photograph a receipt and stop thinking about it." (I1) -- specifically the offload-the-thinking framing, not the OCR feature in isolation |
| ANXIETY (switching scary) | STRONG | > "I really hesitated giving them my bank login. I still don't fully trust it." (I1) -- bank-credential trust, residual post-switch |
| HABIT (kept stuck) | NOT SURFACED | No quote captured. Recorded as evidence-absent, not evidence-of-no-habit-force. |

---

### I2 -- Solo consultant (switched 6 weeks ago; Excel -> competing SaaS)

**Timeline reconstruction:**
- **TRIGGER:** A concrete revenue loss caused by a spreadsheet manipulation error. A year of procrastination collapsed under a single billable incident. > "I'd put it off for a year. Then I billed the wrong client and lost a $400 retainer because of a row I'd accidentally dragged." (I2)
- **STRUGGLE:** Deep familiarity with the old tool was itself part of the bind -- the sheet had become load-bearing identity, not just a tool. > "I knew the formulas in that sheet better than I knew my own apartment." (I2)
- **SWITCH:** Frictionless onboarding (one-click import) cleared the activation barrier in minutes. > "They had a one-click import that just worked. I gave it ten minutes and it was done." (I2)

**Four-forces scoring:**

| Force | Score | Verbatim evidence |
|---|---|---|
| PUSH (old intolerable) | STRONG | > "I billed the wrong client and lost a $400 retainer because of a row I'd accidentally dragged." (I2) -- a concrete, measurable cost event, not generalized frustration |
| PULL (new attractive) | STRONG | > "They had a one-click import that just worked. I gave it ten minutes and it was done." (I2) -- import-from-spreadsheet, not OCR or auto-categorization |
| ANXIETY (switching scary) | STRONG | > "I genuinely worried I would lose history. My sheet had five years of data." (I2) -- data-portability anxiety, distinct from I1's credential anxiety |
| HABIT (kept stuck) | STRONG | > "Honestly the muscle memory of keyboard-only navigation in Excel is the thing I miss the most." (I2) -- explicitly named muscle memory, post-switch grief |

---

### I3 -- Small-business owner (switched 1 month ago; Excel -> competing SaaS)

**Timeline reconstruction:**
- **TRIGGER:** External social pressure from a trusted professional. The accountant's ultimatum was the originating event, not an internal realization. > "My accountant told me he'd fire me as a client if I sent him another shoebox of receipts and a sheet with broken formulas." (I3)
- **STRUGGLE:** Weekly four-hour ritual of reconciliation with compounding error discovery -- structural unwinnable maintenance. > "It took me four hours every Sunday and I always found another error the next week." (I3)
- **SWITCH:** Email-receipt ingestion was the lock-in feature that ended return-to-Excel behavior. > "Once it was importing receipts from my email I never went back." (I3)

**Four-forces scoring:**

| Force | Score | Verbatim evidence |
|---|---|---|
| PUSH (old intolerable) | STRONG | > "My accountant told me he'd fire me as a client if I sent him another shoebox of receipts and a sheet with broken formulas." (I3) + > "It took me four hours every Sunday and I always found another error the next week." (I3) |
| PULL (new attractive) | STRONG | > "Once it was importing receipts from my email I never went back." (I3) -- automated ingestion of inbox receipts |
| ANXIETY (switching scary) | NOT SURFACED | No quote captured. Recorded as evidence-absent, not evidence-of-no-anxiety. |
| HABIT (kept stuck) | EMERGING | > "I kept the spreadsheet open in another tab for a month before I admitted I didn't need it." (I3) -- behavioral residue rather than explicit muscle-memory naming |

---

## Cross-interview cluster roll-up

> **Strength tagging legend:** STRONG = 3+ interviews; EMERGING = 2 interviews; ANECDOTAL = 1 interview. Per persona rule, ANECDOTAL clusters MUST NOT drive PROPOSED decision blocks.

### PUSH clusters

| Cluster | Strength | Backing interviews | Anchor quotes |
|---|---|---|---|
| **Spreadsheet-integrity-failure-with-real-cost** -- the moment the sheet was caught producing a wrong, costly answer | **STRONG (3/3)** | I1, I2, I3 | I1: "I'd double-counted a whole month." / I2: "I billed the wrong client and lost a $400 retainer." / I3: "I always found another error the next week." |
| **Manual-maintenance-time-burden** -- the unpaid recurring labor of keeping the sheet alive | **EMERGING (2/3)** | I1, I3 | I1: "scared I'd break the formula" / I3: "four hours every Sunday" |
| **External-pressure-from-trusted-professional** -- a third party forcing the switch | **ANECDOTAL (1/3)** | I3 only | I3: "My accountant told me he'd fire me as a client." |

### PULL clusters

| Cluster | Strength | Backing interviews | Anchor quotes |
|---|---|---|---|
| **Offload-the-thinking / receipt-ingestion-as-cognitive-relief** -- the new tool absorbs the work the user used to carry | **STRONG (3/3)** | I1, I2, I3 | I1: "photograph a receipt and stop thinking about it." / I2: "I gave it ten minutes and it was done." / I3: "importing receipts from my email I never went back." |
| **Auto-categorization specifically** (the team's stated motivator) | **NO EVIDENCE** | none | Not a single subject named categorization as the pull. See evidence-gap subsection. |
| **OCR specifically** (the team's stated motivator) | **ANECDOTAL (1/3)** | I1 only ("photograph a receipt" -- adjacent to OCR but the framing is "stop thinking," not OCR accuracy) | I1: "photograph a receipt and stop thinking about it." |
| **Frictionless-onboarding / data-import** -- the activation moment that cleared the switch | **EMERGING (2/3)** | I2 (one-click import), I3 (email ingestion) | I2: "one-click import that just worked." / I3: "importing receipts from my email." |

### ANXIETY clusters

| Cluster | Strength | Backing interviews | Anchor quotes |
|---|---|---|---|
| **Data-and-credential trust toward the new vendor** -- generalized "what am I handing over?" anxiety | **EMERGING (2/3)** | I1 (bank-login trust), I2 (history loss) | I1: "I really hesitated giving them my bank login." / I2: "I genuinely worried I would lose history." |
| **Bank-credential trust specifically** | **ANECDOTAL (1/3)** | I1 only | I1: "I still don't fully trust it." |
| **History / data-portability loss specifically** | **ANECDOTAL (1/3)** | I2 only | I2: "My sheet had five years of data." |

### HABIT clusters

| Cluster | Strength | Backing interviews | Anchor quotes |
|---|---|---|---|
| **Spreadsheet muscle-memory and lingering attachment** -- the old tool persists in body and behavior after rational switch | **EMERGING (2/3)** | I2 (explicit muscle memory), I3 (kept it open in another tab) | I2: "muscle memory of keyboard-only navigation... is the thing I miss the most." / I3: "I kept the spreadsheet open in another tab for a month." |
| **Keyboard-only navigation specifically** | **ANECDOTAL (1/3)** | I2 only | I2: "keyboard-only navigation in Excel." |

---

## Confrontation with the team's prior assumption

The team's pre-interview assumption was: **"users switch from Excel to our SaaS because of automation (auto-categorization, receipt OCR)."**

Tested against this round:

- **Auto-categorization:** **DISCONFIRMED by absence.** 0/3 subjects named categorization as the pull. This is a meaningful negative across a small sample because the question "what sold you" was asked directly and three different subjects volunteered three different non-categorization answers (photo capture, one-click import, email ingestion). Not proof, but a strong directional signal.
- **Receipt OCR:** **WEAKLY SUPPORTED, but reframed.** Only I1 mentioned receipt photography, and even she framed it as "stop thinking about it" -- the value was cognitive offload, not OCR accuracy. The deeper PULL cluster is **receipt-ingestion-as-cognitive-relief** (STRONG), which includes OCR as one of three substitutable ingestion paths (photo, spreadsheet import, email).
- **The real STRONG PULL cluster** is broader than the team's framing: users are not buying OCR; they are buying **"the tool does the thinking I used to do."** Receipt ingestion is one of several interchangeable mechanisms that deliver that job.

---

## PROPOSED blocks (only for STRONG or EMERGING clusters)

> Per persona Step 5: no ANECDOTAL cluster drives a PROPOSED block. The clusters that qualify are: PUSH-integrity-failure (STRONG), PULL-cognitive-relief (STRONG), PUSH-maintenance-burden (EMERGING), PULL-frictionless-onboarding (EMERGING), ANXIETY-vendor-trust (EMERGING), HABIT-muscle-memory (EMERGING).

### PROPOSED for `DECISIONS.md ## Locked decisions`

```markdown
<!-- PROPOSED by jtbd-switch-interviewer: -->
### D-N (draft) -- Primary switch motivation reframed from "automation" to "cognitive-offload-from-spreadsheet-integrity-failure"

**Context:** Pre-interview assumption was "users switch because of automation (auto-categorization, OCR)." JTBD round 1 (I1, I2, I3) disconfirms auto-categorization by absence (0/3 named it) and reframes OCR as one substitutable ingestion path inside a broader job.

**Decision:** Position the product around the job **"the tool does the integrity work I keep failing at, so I can stop thinking about my expenses"** rather than around any specific automation feature. Receipt ingestion (photo / import / email) is a mechanism, not the message.

**Evidence (STRONG, 3/3):**
- PUSH -- spreadsheet-integrity-failure-with-real-cost: I1 ("double-counted a whole month"), I2 ("billed the wrong client and lost a $400 retainer"), I3 ("always found another error the next week").
- PULL -- offload-the-thinking / receipt-ingestion-as-cognitive-relief: I1 ("stop thinking about it"), I2 ("ten minutes and it was done"), I3 ("never went back").

**Cross-link:** `JTBD_INTERVIEWS.md` cluster roll-up, PUSH-integrity-failure and PULL-cognitive-relief rows.

**Caveat:** n=3, single round. Treat as directional, not market-validated.
```

```markdown
<!-- PROPOSED by jtbd-switch-interviewer: -->
### D-N+1 (draft) -- Onboarding-friction is a load-bearing PULL, not a polish item

**Context:** Two of three subjects (I2 one-click import, I3 email ingestion) named the activation moment itself as why the switch stuck. This is EMERGING, not STRONG, but it directly informs go-to-market and first-run UX.

**Decision (draft):** Treat the first-ten-minutes experience -- specifically Excel/CSV import and inbox receipt ingestion -- as P0 acquisition surface, not as later-stage convenience. Defer dedicated auto-categorization investment behind these.

**Evidence (EMERGING, 2/3):**
- I2: "They had a one-click import that just worked. I gave it ten minutes and it was done."
- I3: "Once it was importing receipts from my email I never went back."

**Cross-link:** `JTBD_INTERVIEWS.md` PULL-frictionless-onboarding cluster.

**Caveat:** EMERGING strength. One more confirming interview would promote this to STRONG.
```

### PROPOSED for `IMPLEMENTATION_PLAN.md ## Risks and mitigations` (Step 7 -- STRONG/EMERGING adoption risks)

```markdown
<!-- PROPOSED by jtbd-switch-interviewer: -->
**Risk R-N: Vendor-trust ANXIETY at sign-up blocks conversion** (EMERGING, 2/3)
- **Force:** ANXIETY -- generalized vendor-trust anxiety at the handover moment.
- **Evidence:** I1 -- "I really hesitated giving them my bank login. I still don't fully trust it." / I2 -- "I genuinely worried I would lose history. My sheet had five years of data."
- **Implication:** Two distinct anxiety vectors -- bank-credential trust (I1) and data-portability/history-loss (I2). A single "trust" mitigation is unlikely to address both.
- **Mitigation candidates:** (a) defer bank-link until after first value moment; allow manual / CSV / email-only path; (b) explicit, visible "export everything" affordance from day one as anti-lock-in signal; (c) on-import preview that shows historical data intact before commit.
- **Cross-link:** `JTBD_INTERVIEWS.md` ANXIETY-vendor-trust cluster.
```

```markdown
<!-- PROPOSED by jtbd-switch-interviewer: -->
**Risk R-N+1: Excel muscle-memory HABIT causes silent churn-back during first month** (EMERGING, 2/3)
- **Force:** HABIT -- the old tool persists physically and behaviorally past the rational switch.
- **Evidence:** I2 -- "muscle memory of keyboard-only navigation in Excel is the thing I miss the most." / I3 -- "I kept the spreadsheet open in another tab for a month before I admitted I didn't need it."
- **Implication:** Users may appear converted (paid, onboarded) yet still operate dual-tool for weeks; if the SaaS doesn't earn its place in that first month, the user reverts when the spreadsheet tab is closer to hand.
- **Mitigation candidates:** (a) ship a strong keyboard-shortcut surface and document it on first-run; (b) instrument "spreadsheet still open" signals (e.g., low session frequency) as early-churn precursor; (c) first-month onboarding loop that explicitly retires the user's old sheet (one-time data audit + archive prompt).
- **Cross-link:** `JTBD_INTERVIEWS.md` HABIT-muscle-memory cluster.
```

### PROPOSED for `TASK_STATE.md ## Observations`

```markdown
<!-- PROPOSED by jtbd-switch-interviewer: -->
- 2026-06-05 -- JTBD round 1 (n=3) disconfirms auto-categorization as the primary pull (0/3 mentions) and reframes OCR (1/3, and only as substitutable ingestion path) under a broader STRONG cluster: "the tool does the thinking I used to do." See `JTBD_INTERVIEWS.md` PULL-cognitive-relief cluster.
- 2026-06-05 -- STRONG PUSH cluster (3/3) is spreadsheet-integrity-failure-with-real-cost, not generic spreadsheet inconvenience. The switch trigger in every interview was a moment of being caught wrong by the sheet, not chronic frustration. See `JTBD_INTERVIEWS.md` PUSH-integrity-failure cluster.
- 2026-06-05 -- Sample is n=3; STRONG = 3/3. No claim here generalizes safely to market without round 2.
```

### PROPOSED for `TASK_STATE.md ## Risks to watch`

```markdown
<!-- PROPOSED by jtbd-switch-interviewer: -->
- Vendor-trust ANXIETY at sign-up (EMERGING, I1+I2): bank-credential handover and history-loss fear are distinct vectors; single trust message will under-serve one of them.
- Excel muscle-memory HABIT in first month (EMERGING, I2+I3): risk of silent dual-tool churn-back; needs early-churn instrumentation and an explicit retire-the-sheet onboarding step.
```

---

## We do not have evidence for X

> Persona Step 8. This list is load-bearing: a motivation assumption sitting here is NOT disproven -- it is unconfirmed and at risk of sneaking back in via paraphrase. The team MUST treat every line as a research debt, not a settled question.

1. **We do not have evidence for: "auto-categorization is a primary purchase driver."** Zero of three subjects named categorization. Round 1 did not actively probe it either; a follow-up question is required before declaring it disconfirmed rather than untested.
2. **We do not have evidence for: "OCR accuracy is a primary purchase driver."** I1's "photograph a receipt" mention was framed as cognitive offload, not OCR-quality satisfaction. We have no data on whether OCR failure rates would have killed the switch.
3. **We do not have evidence for: "users will pay more for automation than for ingestion-of-existing-data."** Pricing / WTP was not probed in any of the three interviews. The team's "automation justifies premium pricing" assumption survives untouched.
4. **We do not have evidence for: "Excel muscle-memory is a STRONG force across the broader market."** It is EMERGING here (I2+I3). I1 did not surface it -- which could mean she lacked it, or could mean it simply wasn't asked. We do not know which.
5. **We do not have evidence for: "vendor-trust anxiety blocks conversion at scale."** EMERGING here, but post-switch (all three subjects already crossed the line). We have not interviewed any non-switcher who stalled at the trust step. The negative case is unrepresented.
6. **We do not have evidence for: "mobile vs desktop primary surface preference."** Not probed in any interview.
7. **We do not have evidence for: "small-team / shared-access use cases."** All three subjects were solo operators (designer, consultant, owner-operator). Multi-user / collaboration motivation is untested.
8. **We do not have evidence for: "willingness to grant bank-link access ever, vs only after the first value moment."** I1's hesitation is captured, but we never asked her what would have unblocked her, or whether she would have accepted a deferred bank-link onboarding.
9. **We do not have evidence for: "the role of accountant-as-buyer-influencer at scale."** I3's accountant ultimatum is striking but ANECDOTAL (1/3). We do not know whether accountants are a systematic distribution channel or an I3 idiosyncrasy.
10. **We do not have evidence for: "non-switchers and never-switchers."** The entire sample is successful switchers. We are blind to the population that struggled and stayed on Excel, and that is the population most likely to expose the team's untested assumptions.

---

## Recommended next command

`decision-interview` -- to promote the two PROPOSED `D-N` draft blocks into locked decisions, and to make an explicit team call on whether to defer auto-categorization investment behind ingestion + integrity-relief messaging. Round 2 of `jtbd-switch-interviewer` should follow, targeting non-switchers and the evidence-gap list above (especially items 1, 2, 5, 10) before pricing or feature-prioritization decisions are locked.
