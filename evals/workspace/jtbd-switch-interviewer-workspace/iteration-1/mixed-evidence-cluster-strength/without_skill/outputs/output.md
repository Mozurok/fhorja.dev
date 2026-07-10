# JTBD Switch-Interview Synthesis -- Round 1 (n=3)

**Context.** Supabase-backed expense-tracker SaaS. Round under test was the team's prior assumption: *"Users switch from Excel to our SaaS because of automation (auto-categorization, receipt OCR)."* This synthesis applies the Four Forces of Progress framework (Push of the situation, Pull of the new solution, Anxiety about the new, Habit/Allegiance to the old) across 3 captured switch interviews, then rolls evidence up to cluster-strength and proposes decisions only where evidence is strong enough to support them.

---

## 1. Per-Interview Synthesis

### Interview I1 -- Freelance Designer (switched 3 months ago, Excel + manual entry → competing SaaS)

**Switch timeline (reconstructed):**
- **Trigger event:** Late-night tax preparation, discovered a double-counted month in spreadsheet.
- **Switch moment:** Same night / immediately after the error discovery, during tax-deadline crunch.
- **Evaluation:** Centered on receipt capture; bank-login step was the friction point.
- **Adoption:** Switched ~3 months ago; new solution is the system of record now.

**Four Forces:**

| Force | Evidence (verbatim) | Source |
|---|---|---|
| **Push (away from Excel)** | "I was up at 2am the night before my taxes were due and I realized I'd double-counted a whole month." | I1 |
| **Push (background anxiety)** | "Every time I added a row I was scared I'd break the formula in the totals column." | I1 |
| **Pull (toward new)** | "What sold me was honestly that I could just photograph a receipt and stop thinking about it." | I1 |
| **Anxiety (about new)** | "I really hesitated giving them my bank login. I still don't fully trust it." | I1 |
| **Habit / Allegiance (to Excel)** | *No surfacing.* Subject did not raise muscle-memory or Excel attachment. | I1 |

**Interview note:** The pull quote ("photograph a receipt and stop thinking about it") is the closest direct support for the team's automation hypothesis -- but framed as *cognitive offload*, not as accuracy or feature richness.

---

### Interview I2 -- Solo Consultant (switched 6 weeks ago, Excel → competing SaaS)

**Switch timeline:**
- **Trigger event:** Mis-billed a client and lost a $400 retainer, traced to an accidentally dragged row.
- **Pre-trigger latency:** Subject explicitly "put it off for a year" -- known dissatisfaction long before the switch.
- **Evaluation:** Heavily weighted by "ten-minute" import test.
- **Anxiety bar:** Data history preservation (5 years).
- **Adoption:** ~6 weeks in; reports lingering grief over keyboard navigation.

**Four Forces:**

| Force | Evidence (verbatim) | Source |
|---|---|---|
| **Push (acute event)** | "I'd put it off for a year. Then I billed the wrong client and lost a $400 retainer because of a row I'd accidentally dragged." | I2 |
| **Pull (toward new)** | "They had a one-click import that just worked. I gave it ten minutes and it was done." | I2 |
| **Anxiety (about new)** | "I genuinely worried I would lose history. My sheet had five years of data." | I2 |
| **Habit / Allegiance (to Excel)** | "I knew the formulas in that sheet better than I knew my own apartment." | I2 |
| **Habit / Allegiance (post-switch grief)** | "Honestly the muscle memory of keyboard-only navigation in Excel is the thing I miss the most." | I2 |

**Interview note:** Pull here is *frictionless onboarding / import*, not OCR or categorization. The team's automation hypothesis is not directly supported in I2.

---

### Interview I3 -- Small-Business Owner (switched 1 month ago, Excel → competing SaaS)

**Switch timeline:**
- **Trigger event:** External social pressure -- accountant threatened to drop her as a client.
- **Pre-trigger pattern:** Weekly 4-hour reconciliation ritual with recurring errors.
- **Evaluation:** Email-receipt ingestion was the decisive feature.
- **Anxiety bar:** None surfaced.
- **Adoption:** 1 month in; kept Excel tab open as a "safety blanket" for ~30 days before closing.

**Four Forces:**

| Force | Evidence (verbatim) | Source |
|---|---|---|
| **Push (social / external)** | "My accountant told me he'd fire me as a client if I sent him another shoebox of receipts and a sheet with broken formulas." | I3 |
| **Push (ongoing labor cost)** | "It took me four hours every Sunday and I always found another error the next week." | I3 |
| **Pull (toward new)** | "Once it was importing receipts from my email I never went back." | I3 |
| **Anxiety (about new)** | *No surfacing.* | I3 |
| **Habit / Allegiance (to Excel)** | "I kept the spreadsheet open in another tab for a month before I admitted I didn't need it." | I3 |

**Interview note:** Pull is *ingestion automation* (email → receipts), partially adjacent to the team's OCR hypothesis but not identical. No security/data-loss anxiety surfaced.

---

## 2. Cross-Interview Cluster Roll-Up

Cluster strength rules (applied):
- **STRONG** = present in 3+ interviews
- **EMERGING** = present in 2 interviews
- **ANECDOTAL** = present in 1 interview only

### 2.1 Push clusters

| Cluster | I1 | I2 | I3 | Strength |
|---|---|---|---|---|
| **Acute error / financial-or-reputational consequence triggered the switch** ("double-counted month" / "$400 retainer" / "accountant threatened to fire me") | Y | Y | Y | **STRONG** |
| **Chronic spreadsheet anxiety / fragility as background condition** ("scared I'd break the formula" / "always found another error" / dragged row) | Y | Y | Y | **STRONG** |
| **External party (deadline, client, accountant) forces the moment** (tax deadline / lost client / accountant ultimatum) | Y | Y | Y | **STRONG** |

### 2.2 Pull clusters

| Cluster | I1 | I2 | I3 | Strength |
|---|---|---|---|---|
| **Automated capture / ingestion of receipts** (photo OCR I1; email import I3) | Y | -- | Y | **EMERGING** |
| **Effortless onboarding -- "it just worked in minutes"** (one-click import I2; "stop thinking about it" I1; "never went back" I3) | Y | Y | Y | **STRONG** |
| **Cognitive offload -- "stop thinking about it"** (I1 explicit; I3 implied by "never went back"; I2 implied by 10-minute close) | Y | partial | partial | **EMERGING** (only I1 is explicit) |

### 2.3 Anxiety clusters

| Cluster | I1 | I2 | I3 | Strength |
|---|---|---|---|---|
| **Trust / security (bank login, credential handover)** | Y | -- | -- | **ANECDOTAL** |
| **Data-history preservation / loss of years of records** | -- | Y | -- | **ANECDOTAL** |

### 2.4 Habit / Allegiance clusters

| Cluster | I1 | I2 | I3 | Strength |
|---|---|---|---|---|
| **Excel muscle memory / keyboard fluency** | -- | Y | -- | **ANECDOTAL** |
| **Spreadsheet kept open as safety blanket after switch** | -- | -- | Y | **ANECDOTAL** |
| **Deep mastery of own sheet ("knew the formulas")** | -- | Y | -- | **ANECDOTAL** |

---

## 3. PROPOSED Decision Blocks

Per the cluster-strength gate, decisions are proposed **only** for STRONG clusters. EMERGING clusters are noted as hypotheses to revalidate in Round 2. ANECDOTAL clusters do **not** drive proposals.

### PROPOSED Decision D1 -- Reframe the marketing/onboarding message away from "automation" and toward "the moment Excel breaks you"

- **Driven by:** STRONG Push clusters (acute error + chronic fragility + external-party trigger).
- **Rationale:** All three switchers were *pushed* by a discrete failure event (double-count, mis-billing, accountant ultimatum) layered on chronic spreadsheet fragility. Automation features did not appear as the dominant *cause* of switch in any interview -- they appeared as the *relief*, after a Push event made the switch necessary.
- **Implication for product surface:** Top-of-funnel copy and landing-page hero should lead with the failure mode ("the spreadsheet broke at the worst possible moment"), not the feature ("auto-categorization + OCR"). Automation belongs further down the page as the *answer*, not the *hook*.
- **Implication for activation:** Onboarding should aggressively timestamp the first "I just avoided an error" moment, because that maps to Push relief, not feature wow.

### PROPOSED Decision D2 -- Treat "it just worked in 10 minutes" as a STRONG activation requirement, not a nice-to-have

- **Driven by:** STRONG Pull cluster (effortless onboarding present in all 3 interviews -- one-click import in I2, "stop thinking about it" in I1, "never went back" in I3).
- **Rationale:** The decisive Pull element across all three is *low effort to first value*, not feature depth. I2 closed in 10 minutes; I1 was won by a single-action receipt capture; I3 hit "never went back" the moment email ingestion worked.
- **Implication:** Time-to-first-imported-receipt is the leading activation metric. Anything that adds steps to first capture (account verification dialogs, plan-selection walls, manual configuration of categories) directly attacks the strongest Pull observed.
- **Implication for Supabase backend specifically:** Provider-agnostic, low-friction ingestion (email forwarding address provisioned at signup; CSV/Excel one-click import; photo upload without prior bank link) should be table-stakes day-1, ahead of bank-link integrations.

### NOT PROPOSED (evidence too thin)

- **No decision proposed re: bank-link security UX** -- only I1 raised this anxiety. ANECDOTAL.
- **No decision proposed re: 5-year history migration / data preservation** -- only I2 raised this. ANECDOTAL.
- **No decision proposed re: Excel keyboard-parity / muscle-memory accommodation** -- only I2 raised this. ANECDOTAL.
- **No decision proposed re: "safety-blanket parallel use" period** -- only I3. ANECDOTAL.
- **No decision proposed re: OCR specifically vs. email ingestion specifically** -- these are EMERGING (one each). The *category* (automated capture) is strong enough to motivate D2, but the *modality* is not yet differentiated by evidence.

---

## 4. "We Do Not Have Evidence For X" -- Gap Subsection

The team's prior assumption was: *"Users switch from Excel to our SaaS because of automation (auto-categorization, receipt OCR)."*

What this round did and did **not** confirm:

- **NOT CONFIRMED: "Automation is the cause of switch."** Evidence consistently positions automation as the *relief / pull* after a Push event has already made the switch necessary. No interviewee named automation as the reason they *started* looking. Status: **disconfirmed as primary cause; supported only as enabler.**
- **NOT CONFIRMED: "Auto-categorization matters."** Zero interviewees mentioned categorization at all. Across three switch interviews, categorization did not surface as Push, Pull, Anxiety, or Habit. Status: **no evidence either way -- open gap.**
- **PARTIALLY CONFIRMED: "Receipt OCR matters."** Only I1 explicitly cited photo-receipt capture; I3 cited *email* ingestion (adjacent but not OCR-by-camera); I2 cited neither. Status: **EMERGING for the broader category of automated capture; OCR-by-camera specifically remains ANECDOTAL.**
- **NO EVIDENCE: How users handle the bank-link trust barrier across personas.** Only I1 raised it; we cannot say whether I2/I3 simply didn't have the integration offered, didn't care, or quietly tolerated it.
- **NO EVIDENCE: Whether multi-year history migration is a deal-breaker at scale.** Only I2 raised it; he had 5 years of data. We do not know how common that profile is.
- **NO EVIDENCE: How the "safety blanket parallel-use" period (I3) affects retention or churn.** It surfaced once; we don't know if this is a universal weaning behavior or specific to I3's risk tolerance.
- **NO EVIDENCE: Pricing sensitivity / willingness-to-pay at the switch moment.** No interview surfaced cost as Push, Pull, or Anxiety. We cannot say whether this is because price wasn't asked, wasn't relevant at the Push moment, or the competing SaaS was priced below the threshold of friction.
- **NO EVIDENCE: Why these users picked the *specific* competing SaaS over alternatives.** All three switched to "a competing SaaS"; we have no comparative evaluation data (did they try ours? did they consider 2+ tools?).

### Recommended Round-2 probes (to convert EMERGING → STRONG or kill)

1. Probe **categorization** directly in the next 5 interviews -- it is currently a feature-team assumption with zero qualitative support.
2. Probe **bank-link trust** with a security-sensitive segment (the I1 signal may generalize to a sub-persona).
3. Probe **historical-data migration** with users who have 3+ years in Excel (the I2 signal).
4. Probe **the moment-of-decision narrative** specifically to confirm whether Push (failure event) precedes Pull (feature appeal) in 5/5 next interviews -- if it does, the cluster moves from STRONG (n=3) to canonically locked.
5. Probe **why-not-us / competitive evaluation** to learn what kept these three users from finding our product at the moment of Push.

---

**Round-1 verdict (one line):** The dominant story is **Push, not Pull** -- users are driven out of Excel by a specific failure event amplified by chronic fragility, and they buy whichever tool requires the least effort to make the pain stop. Automation is the *answer*, not the *hook*. Auto-categorization specifically has *zero* qualitative support and should be deprioritized in messaging until evidence appears.
