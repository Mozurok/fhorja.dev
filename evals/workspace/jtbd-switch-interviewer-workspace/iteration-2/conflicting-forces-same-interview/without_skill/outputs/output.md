# JTBD Switch Interview Synthesis -- I1

**Subject:** Freelance consultant, switched QuickBooks Online (QBO) → FreshBooks ~5 weeks ago
**Old solution:** QuickBooks Online
**New solution:** FreshBooks
**Team hypothesis under test:** "Users switch from QBO to FreshBooks because invoicing in QBO is intolerable."

---

## 1. Per-Interview Force Extraction

The four forces of progress (Push, Pull, Anxiety, Habit) are extracted **independently**. Two of them point at the *same* object (QBO) but with *opposite* valence -- these are kept separate by design (see §2).

### Force 1 -- PUSH (from the old solution)
**Definition:** Pain/dissatisfaction with the current situation that creates pressure to leave.
**Target:** QBO invoicing -- specifically tax-engine correctness and time cost.

Verbatim:
- "I had a client tell me they couldn't pay because my QBO invoice had the wrong tax code for the third time. That was the moment."
- "QBO invoicing is genuinely terrible. The tax engine is opaque. I spent two hours every month fixing line items."

Signal strength: HIGH. Includes a **triggering event** ("that was the moment") + recurring frequency ("third time", "two hours every month") + concrete business consequence (client could not pay). This is the textbook anatomy of a switch-causing push.

Tag: ANECDOTAL (n=1).

---

### Force 2 -- PULL (to the new solution)
**Definition:** Attraction of the new situation.
**Target:** FreshBooks -- perceived cleanliness/simplicity.

Verbatim:
- "FreshBooks is cleaner..."

Signal strength: WEAK / IMPLIED. The subject describes FreshBooks positively but only briefly, and the same sentence pivots into a complaint about the learning curve. Pull is **not** the dominant force in this interview -- it is mentioned but not load-bearing.

Tag: ANECDOTAL -- and **thin**. Worth probing in subsequent interviews to determine whether pull is real or whether subjects are mostly *escaping* QBO rather than *choosing* FreshBooks.

---

### Force 3 -- ANXIETY (about the new solution)
**Definition:** Fear/uncertainty about adopting the new situation.
**Target:** Productivity loss during the transition period.

Verbatim:
- "I really hesitated because I knew there'd be a productivity dip."
- "FreshBooks is cleaner but I have to think about every click for the first month. It's slow because it's new, not because it's actually slow."

Signal strength: MEDIUM. The anxiety is **realized**, not just anticipated -- the subject describes the dip as currently happening ("for the first month", "I have to think about every click"). Note the meta-awareness: "It's slow because it's new, not because it's actually slow" -- the subject is correctly attributing friction to unfamiliarity, not to the product. This is important because it means the anxiety is **temporary and self-resolving**, not a structural objection.

Tag: ANECDOTAL (n=1).

---

### Force 4 -- HABIT (loyalty to the old solution)
**Definition:** Inertia, comfort, fluency, or sunk cost binding the user to the current situation.
**Target:** QBO -- muscle memory and operational fluency built over 6 years.

Verbatim:
- "I knew exactly where every button was. After 6 years of using it, my muscle memory was reflexive. I miss that fluency more than I expected."

Signal strength: HIGH. Quantified tenure (6 years), embodied language ("muscle memory was reflexive"), and -- critically -- a **post-switch retrospective emotion** ("I miss that fluency more than I expected"). The subject did not predict how strong this would feel. That surprise is itself data.

Tag: ANECDOTAL (n=1).

---

## 2. The PUSH-vs-HABIT Conflict on the Same Old Solution

> **The trap to avoid:** A naive synthesis would cluster Forces 1 and 4 together as "feelings about QBO" because both quotes are *about* the same product. That cluster would erase the most important finding in this interview.

### Why the conflict is real, not a contradiction
Push and Habit are **different forces operating on different dimensions** of the same product:

| Dimension | Force 1 (PUSH) | Force 4 (HABIT) |
|---|---|---|
| What it's about | **Outcome quality** -- invoices being wrong, clients not paying | **Operational fluency** -- knowing the UI cold |
| Time horizon | Recurring monthly pain culminating in a trigger event | 6 years of accumulated motor learning |
| Valence | Strongly negative | Strongly positive |
| What it does to the switch decision | Pushes user *out* of QBO | Pulls user *back toward* QBO |
| Resolution after switching | Solved -- FreshBooks fixed the tax problem | Unsolved -- the fluency loss is felt as ongoing regret |

A product can be **simultaneously intolerable on outcomes and beloved on ergonomics**. The subject is telling us exactly that. Both quotes are true. Neither cancels the other.

### Why this matters for the team hypothesis
The team hypothesis ("users switch because QBO invoicing is intolerable") is **supported but incomplete**:
- It correctly identifies the push.
- It is silent on the habit force, which the subject says "almost stopped" the switch and which they "miss more than expected" post-switch.

If FreshBooks (or whoever is acting on this research) only addresses the push narrative, they will under-invest in two things this interview suggests matter:
1. **Onboarding that compresses time-to-fluency** -- to shorten the productivity-dip window the subject is currently living through.
2. **Migration-friendly UI conventions** -- so 6 years of QBO muscle memory transfers, rather than being thrown away.

### What this implies for synthesis discipline
- Do **not** average Push and Habit into a net sentiment about QBO. They are vectors, not scalars.
- Do **not** treat Habit as "just a residual feeling." It is a switching-cost force that almost prevented the conversion and continues to shape the post-switch experience.
- Do **not** assume that fixing the Push fully delivers the user. The Habit force tells us the user is partially still attached to the old solution after the switch -- a churn-back risk if FreshBooks stumbles.

---

## 3. Cross-Interview Cluster Tagging Note

This is a single-interview synthesis (n=1). Per JTBD switch-interview discipline, every force surfaced here is classified as **ANECDOTAL** until corroborated.

| Force | Tag | Promotion threshold |
|---|---|---|
| PUSH -- invoicing/tax-engine pain | ANECDOTAL | → EMERGING at n≥3 independent subjects citing tax or invoice correctness as the switch trigger |
| PULL -- FreshBooks "cleaner" | ANECDOTAL (thin) | → EMERGING at n≥3 with *specific* attractors named (not just "cleaner") |
| ANXIETY -- productivity dip | ANECDOTAL | → EMERGING at n≥3 mentioning learning curve / transition cost as a hesitation |
| HABIT -- 6yr muscle memory | ANECDOTAL | → EMERGING at n≥3 referencing fluency loss or UI familiarity as a force pulling them back |

Promotion ladder used (standard switch-interview convention):
- **ANECDOTAL:** 1 subject.
- **EMERGING:** 3+ independent subjects, same force, same shape.
- **VALIDATED:** 5+ independent subjects with at least one disconfirming probe that failed to disconfirm.

Specifically for this interview, the most important cross-interview question to carry forward is:

> *Does the PUSH-vs-HABIT conflict on the same old solution repeat?* If subjects 2, 3, 4 also describe QBO as simultaneously intolerable-on-outcomes and beloved-on-fluency, this is not a quirk of I1 -- it is the structural shape of this switch.

---

## 4. Recommended Next Action for the Round

**Run 4–6 more switch interviews with the same target population (QBO → FreshBooks switchers, switched within last 90 days), with the explicit probes below.**

### Specific probes to add to the guide

1. **Trigger-event probe (confirms PUSH):**
   "Was there a specific moment or event that made you decide it was time to leave QBO? Walk me through that day."

2. **Habit/fluency probe (confirms HABIT -- and tests whether I1 is representative):**
   "How long had you been using QBO before you switched? Is there anything about the old workflow you miss now?"
   -- Listen specifically for ergonomic/fluency language ("muscle memory", "knew where everything was", "faster in the old one").

3. **Pull-specificity probe (stress-tests the thin PULL signal):**
   "When you compared FreshBooks to other options, what specifically pulled you toward it -- not just away from QBO?"
   -- If subjects struggle to answer this, the dominant force in the market is push, not pull. That has different implications for FreshBooks' positioning (defensive against QBO vs. offensive on its own merits).

4. **Anxiety probe (confirms ANXIETY and its self-resolving character):**
   "What almost stopped you from switching? How long did the awkward period last?"

5. **Conflict probe (the I1-specific finding to validate):**
   "Some people we've talked to say QBO's invoicing was unbearable *and* that they miss how familiar it was. Does that resonate, or is one of those much stronger for you?"
   -- This is a leading question used **late** in the interview, only after the subject has given their own unprompted account, to test whether the dual-valence pattern is recognizable.

### What I am explicitly NOT recommending
- **Do not** declare the team hypothesis validated. n=1 supports it directionally but does not validate it, and crucially does not surface the Habit force that the hypothesis ignores.
- **Do not** rewrite the hypothesis yet. Rewrite after n≥3, when the Push/Habit shape is either confirmed as structural or revealed as idiosyncratic to I1.
- **Do not** brief design/PM on "users want a cleaner invoicing UI" based on this interview. The PULL signal is the weakest of the four forces here and the least safe to act on.

### Decision rule for the round
After 4–6 more interviews:
- If PUSH (invoicing/tax pain) appears in ≥3 → promote to EMERGING and the team hypothesis stands.
- If HABIT (fluency loss) also appears in ≥3 → **rewrite** the hypothesis to: *"Users switch from QBO to FreshBooks despite high habit cost, driven by invoicing reliability failures -- meaning onboarding and UI-convention familiarity are leverage points, not afterthoughts."*
- If PULL remains thin across all interviews → flag to the team that FreshBooks' growth is **escape-driven**, not **attraction-driven**, which is a strategically different position than the marketing narrative likely assumes.
