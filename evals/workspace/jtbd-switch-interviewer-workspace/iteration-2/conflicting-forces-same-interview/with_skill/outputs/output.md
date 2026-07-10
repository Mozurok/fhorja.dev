# JTBD Switch-Interview Synthesis -- I1

**Switch hypothesis (team):** Users switch from QuickBooks Online (QBO) to FreshBooks because invoicing in QBO is intolerable.

**Restated in user framing (OLD -> NEW):** A freelance consultant abandons a 6-year QBO invoicing workflow (the OLD solution) and adopts FreshBooks invoicing (the NEW solution) after a client-facing tax-code failure on a live invoice.

---

## 1. Per-interview synthesis

### Interview I1
- **Subject:** Freelance consultant
- **Recency:** Switched ~5 weeks ago
- **OLD solution:** QuickBooks Online (invoicing module), 6 years of daily use
- **NEW solution:** FreshBooks (invoicing module), ~5 weeks in
- **Timeline reconstruction:**
  - **TRIGGER (concrete moment):** A client told the consultant they could not pay because the QBO-generated invoice had the wrong tax code -- for the **third** time.
  - **STRUGGLE (active evaluation):** Recurring monthly cleanup of QBO line items (~2 hours/month) and opaque tax-engine behavior accumulated over months, but the third client-facing failure converted background frustration into an active search.
  - **SWITCH:** Adopted FreshBooks; ~5 weeks of acclimation; productivity dip acknowledged and accepted.

#### Four-forces extraction (each force scored separately, verbatim-anchored)

**PUSH -- what made the OLD solution intolerable** *(present, strong)*
- Quote [I1-Q1, trigger moment]: *"I had a client tell me they couldn't pay because my QBO invoice had the wrong tax code for the third time. That was the moment."*
- Quote [I1-Q2, sustained pain]: *"QBO invoicing is genuinely terrible. The tax engine is opaque. I spent two hours every month fixing line items."*
- **Subject of PUSH:** QBO invoicing module specifically (tax engine + line-item correctness).

**PULL -- what made the NEW solution attractive** *(present, weak / partial)*
- Quote [I1-Q3]: *"FreshBooks is cleaner..."* (only fragment available; "cleaner" is the entire pull signal in this interview).
- **Note:** PULL evidence in I1 is thin. The subject did not articulate a specific FreshBooks capability that pulled them in; "cleaner" is aesthetic/UX shorthand. Logged as weak signal, not strong pull.

**ANXIETY -- what made switching scary** *(present, explicit)*
- Quote [I1-Q4]: *"I really hesitated because I knew there'd be a productivity dip."*
- Quote [I1-Q5, post-switch confirmation of anxiety being founded]: *"FreshBooks is cleaner but I have to think about every click for the first month. It's slow because it's new, not because it's actually slow."*
- **Subject of ANXIETY:** Productivity loss during re-learning, not feature-parity or data-migration risk.

**HABIT -- what kept them stuck in the OLD solution** *(present, strong)*
- Quote [I1-Q6]: *"I knew exactly where every button was. After 6 years of using it, my muscle memory was reflexive. I miss that fluency more than I expected."*
- **Subject of HABIT:** 6-year reflexive muscle memory in QBO's UI. Notable: the HABIT is **about the same QBO product the PUSH is about**, and is reported *after* the switch as ongoing loss ("I miss that fluency more than I expected").

---

## 2. Explicit handling of the PUSH-vs-HABIT conflict on the SAME old solution

This is the load-bearing observation of I1, and the persona must NOT collapse it into a single "feelings about QBO" cluster.

**The conflict:** Within one interview, the subject reports both:
- **PUSH against QBO** -- the invoicing/tax engine is "genuinely terrible," intolerable enough to drive the switch.
- **HABIT toward QBO** -- the same product's UI fluency is missed enough, post-switch, that the subject volunteers the regret unprompted ("more than I expected").

**Why these are NOT the same force:**
- PUSH is about the **functional output** of QBO invoicing (wrong tax codes, monthly cleanup, client-facing failure). It operates on the **job dimension** (get a correct invoice paid).
- HABIT is about the **interaction surface** of QBO (button locations, motor-memory shortcuts). It operates on the **operator-fluency dimension** (execute any action without cognitive load).
- A user can hate the engine while loving the cockpit. Clustering both as "QBO sentiment" would erase the actionable distinction: the PUSH validates the team's switch hypothesis, but the HABIT predicts a real adoption-risk surface for FreshBooks (the first-month "think about every click" period) that the team's brief did not anticipate.

**Anti-pattern explicitly avoided:** Reporting "user has mixed feelings about QBO" would be a paraphrase that laundries both forces into a vague affect. The persona keeps them as two scored forces with two different subjects (functional correctness vs. interaction fluency) so each one can drive a different downstream proposal.

**Implication for the team hypothesis:** The hypothesis ("invoicing in QBO is intolerable") is **partially confirmed** by I1's PUSH quotes, but I1 also reveals a **co-existing retention force (HABIT)** the hypothesis ignores. A version of the hypothesis that survives I1 is closer to: *"Users switch from QBO to FreshBooks when a client-facing invoicing failure overrides 6-year UI muscle memory -- the muscle memory does not disappear; it gets outweighed."*

---

## 3. Cross-interview cluster tagging

Single interview in the round (n=1). Per the persona's cluster-strength rules:

| Force | Subject | Cluster strength | Note |
|---|---|---|---|
| PUSH | QBO invoicing tax engine + line-item correctness | **ANECDOTAL** | 1 interview; cannot drive a PROPOSED decision yet |
| PULL | "Cleaner" UX of FreshBooks | **ANECDOTAL (weak)** | Single fragmentary quote; PULL evidence is thinnest in this round |
| ANXIETY | Productivity dip during re-learning | **ANECDOTAL** | 1 interview |
| HABIT | 6-year QBO UI muscle memory | **ANECDOTAL** | 1 interview |

**Cluster-driving rule applied:** No ANECDOTAL cluster may drive a PROPOSED `D-N` decision block. This round produces **no decision proposals**. It produces only an **observation entry** and a **risk-to-watch entry**, both flagged as evidence-gated by future interviews.

**We do not have evidence for X (surviving motivation assumptions):**
- Whether the PUSH (tax-engine pain) generalizes beyond consultants with multi-jurisdiction tax exposure -- no evidence.
- Whether PULL toward FreshBooks is functional (specific capability) or aesthetic (UX polish) at population level -- no evidence; I1's "cleaner" is insufficient.
- Whether the HABIT/fluency loss is a temporary acclimation cost (resolves in weeks) or a permanent retention risk that drives churn back to QBO -- no evidence; I1 is only 5 weeks in.
- Whether the "third tax-code failure" pattern (3 strikes) is the typical trigger or idiosyncratic to I1 -- no evidence.

---

## 4. Recommended next action for the round

**Run 4–6 more switch interviews with QBO -> FreshBooks switchers within the last 90 days, oversampling for HABIT signal.**

Specifically:
1. **Schedule 4–6 additional interviews** to move PUSH and HABIT clusters from ANECDOTAL to at least EMERGING (2) or STRONG (3+). Sampling target: recent switchers (under 90 days), mix of solo freelancers and small-firm operators, mix of single- and multi-jurisdiction tax contexts.
2. **Add two explicit probes to the script for every subsequent interview**, derived from I1's conflict:
   - *"What about QBO do you miss now that you've switched?"* -- surfaces HABIT directly rather than letting it emerge by accident.
   - *"Walk me through the moment you decided. Was it one event or an accumulation?"* -- tests whether the "third-strike trigger" pattern repeats.
3. **Do NOT promote a `D-N` decision draft yet.** The PUSH cluster is ANECDOTAL; promoting it now would launder I1's single quote into a team-wide motivation claim, which is the exact failure mode this persona exists to catch.
4. **Open one PROPOSED risk-to-watch entry** (anchored to I1-Q4/Q5/Q6) flagging "first-month productivity dip and muscle-memory loss" as an adoption-risk surface FreshBooks onboarding must address, contingent on the HABIT cluster reaching EMERGING in the next round. Owner command for promotion: `capture-observation` (for the observation) and `implementation-plan` (for the risk block) once cluster strength rises.

**Routing for promotion (when clusters strengthen):**
- PUSH/PULL motivation claims → `decision-interview` (drafts a `D-N` in `DECISIONS.md ## Locked decisions`).
- HABIT/ANXIETY risk surfaces → `implementation-plan` (drafts under `## Risks and mitigations`) and `sync-task-state` (mirrors under `## Risks to watch`).
- Observation entries linking back to the I1 quote bank → `capture-observation`.

**Handoff (Mode A):** Run now → schedule and conduct interviews I2–I6 with the augmented script, then re-run `jtbd-switch-interviewer` to re-cluster.
