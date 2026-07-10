# JTBD Switch-Interview Brief Review

**Persona:** jtbd-switch-interviewer (Christensen / Moesta lineage)
**Brief under review:**
> "We already know that our enterprise users switch from Salesforce to our product because they want a better mobile experience. We want to run 5-7 JTBD interviews to CONFIRM this is the reason so we can prioritize mobile in the roadmap."

---

## 1. Assessment -- Is the brief actionable as written?

**No. I refuse to run this engagement as scoped.** Three load-bearing failures make the brief unusable for JTBD switch-interview research:

### 1a. The conclusion is pre-locked
The brief opens with *"We already know..."* and explicitly names the goal as **"CONFIRM this is the reason."** A switch interview whose stated objective is to confirm a pre-existing hypothesis is not a switch interview -- it is a testimonial-collection exercise. Per Step 4 of the persona protocol (*demand verbatim over paraphrase*), the failure mode this persona is designed to catch is exactly this: *"the team locking a motivation decision on a paraphrased hypothesis nobody ever heard a user say."* The brief is that failure mode in its purest form.

### 1b. "Better mobile experience" is a feature wishlist, not a switch hypothesis
Per Step 1 of the protocol, I must restate the team's hypothesis as **"from OLD solution → to NEW solution"** in the user's own framing language, naming the incumbent being abandoned. "They want a better mobile experience" describes a *feature preference*, not a *switching force*. It tells me nothing about:
- What event in the user's week made the Salesforce mobile experience suddenly *intolerable* (PUSH).
- What specifically pulled them toward our product over the other 8 competitors with mobile apps (PULL).
- What made them anxious about ripping out Salesforce -- a system their company has integrated, customized, and trained on for years (ANXIETY).
- What kept them on Salesforce for as long as they stayed (HABIT).

"Mobile" is almost certainly a *symptom* a user named when asked a leading question, not the *job* they hired our product to do.

### 1c. The roadmap decision is downstream of a finding the research has not earned
The brief states the purpose of confirmation is "so we can prioritize mobile in the roadmap." This means the team has already drafted the implementation consequence and is reverse-engineering interview evidence to authorize it. Per persona Step 6, JTBD findings flow *into* PROPOSED `D-N` decision drafts; they do not *certify* decisions the team has already made. The proper sequence is inverted.

**Verdict:** Brief is **not actionable**. Reframe required before scripting.

---

## 2. Confirmation-bias risks -- explicitly named

I am naming these so the team can see them, push back on them, or accept them -- not so I can sneak them past in synthesis later.

| # | Bias | How it would manifest in *this* engagement |
|---|------|-------------------------------------------|
| **B1** | **Hypothesis-locking / Confirmation bias** | Interview script will be built around "tell us about your mobile pain" prompts; users will oblige (most users will agree with anything plausible an interviewer suggests, especially enterprise buyers who want to be helpful to a vendor relationship). Verbatim quotes about mobile *will* be captured. They will be real. They will also be **artifacts of the question**, not evidence of the job. |
| **B2** | **Leading-question contamination** | A script asking "what made you want a better mobile experience?" presupposes the conclusion and converts the interview into a guided narrative. Users reconstruct memory to match the framing offered (well-documented in Christensen/Moesta methodology and broader cognitive interviewing literature). |
| **B3** | **Selection bias on subject pool** | If recruiting filters on "users who switched because of mobile" (explicitly or implicitly via the sales team handing over their favorite references), the sample is rigged. Need a switch-event-based recruit, not a reason-based recruit. |
| **B4** | **Survivorship bias -- only the switched are interviewed** | The brief only mentions users who *did* switch to our product. The strongest learning in JTBD lives in users who **evaluated and did not switch**, and users who **switched and churned back**. ANXIETY and HABIT forces are nearly invisible without them. |
| **B5** | **Single-force tunnel vision** | The brief privileges PULL ("better mobile") and is silent on PUSH, ANXIETY, HABIT. Even if mobile is part of the story, locking the roadmap on PULL alone is the classic JTBD failure (build the feature, users still don't switch, because the real blocker was anxiety about CRM data migration). |
| **B6** | **"Absence of evidence" laundering** | If we run a confirmation-shaped script and mobile quotes show up, the team will treat that as confirmation. If non-mobile quotes show up, the team will treat them as anecdotes. The script's framing predetermines the synthesis. |
| **B7** | **Sunk-cost / roadmap-momentum bias** | The brief already names the roadmap consequence. If interviews produce disconfirming evidence, the team has a strong incentive to discount it. Pre-commit to a disconfirmation criterion before running interviews. |

The persona-specific risk worth naming most loudly: **per the protocol's quality bar, "if the report contains no direct quotes, the persona missed its job"** -- and the matched failure is *if the report contains only quotes that match the team's prior hypothesis, the persona was used to launder bias.* I will not produce that report.

---

## 3. Reframed research question

The team's brief, deconstructed, contains three separate things glued together:
- A **motivation claim** ("users switch because of mobile") -- unproven.
- A **switch-event** (Salesforce → us, enterprise segment) -- real and researchable.
- A **roadmap intent** (prioritize mobile) -- premature, downstream of research not yet done.

Only the middle one is a legitimate JTBD switch-interview anchor. I am dropping the motivation claim and the roadmap intent from the research question and rebuilding around the event.

### Reframed question (proposed)

> **"For enterprise users who switched from Salesforce to our product in the last 6 months, what was the trigger event, what was the struggling moment that pushed them to evaluate alternatives, what specifically pulled them toward our product over other options they considered, what anxieties did they have to overcome to commit, and what habits or sunk costs kept them on Salesforce for as long as they stayed?"**

This question:
- Anchors on the **switch event** (Step 1 satisfied: OLD = Salesforce, NEW = our product, both named).
- Walks the **trigger → struggle → switch timeline backward** from the moment of purchase (Step 2 satisfied).
- Forces **all four forces** into scope -- not just PULL (Step 3 satisfied).
- Holds open the possibility that mobile is a force, a surface symptom of a deeper force, an after-the-fact rationalization, or unrelated to the switch -- and lets verbatim quotes decide (Steps 4–5 satisfied).
- Produces a finding that can either **support** "prioritize mobile," **redirect** to a different priority (e.g., "actually it's pipeline-velocity reporting; mobile is just where they noticed it"), or **complicate** it (e.g., "they want mobile but ANXIETY about offline data sync would block adoption -- fix sync first") -- Step 6 and Step 7 satisfied.

### Sub-questions the script will probe (not leading)

1. **The trigger.** What specifically happened the week or month before you started looking for an alternative to Salesforce? What was the first conversation you had about leaving? Whose idea was it? *(Surfaces PUSH without naming a feature.)*
2. **The evaluation.** Once you decided to look around, what other products did you put on the list? What ruled them out? What made our product survive the cut? *(Surfaces PULL relatively against competitors, not absolutely in a vacuum.)*
3. **The hesitation.** What almost stopped you from switching? Who internally pushed back? What did you have to promise to get the budget or the approval? *(Surfaces ANXIETY -- the force the brief is silent on and the one most likely to block adoption.)*
4. **The stickiness.** Why didn't you switch sooner? What had you tolerated about Salesforce for as long as you did? *(Surfaces HABIT -- the force that explains why the trigger had to be as strong as it was.)*
5. **The role of mobile (asked last, neutrally).** When you think about a typical day using our product vs Salesforce, where do you actually use each one -- desk, phone, between meetings, at customer sites? *(Asked only after the four forces are mapped, so mobile is positioned as a finding to be discovered or not, not a hypothesis to be confirmed.)*

### Pre-committed disconfirmation criteria (Step 8 honesty)

Before running interviews, the team commits in writing to what would *disconfirm* the mobile hypothesis. Examples:
- If fewer than 3 of 5–7 interviews cite a mobile-specific moment in the trigger or evaluation phase, the hypothesis drops from STRONG to EMERGING/ANECDOTAL and **does not justify roadmap reprioritization on its own**.
- If a non-mobile force (e.g., reporting speed, admin overhead, pricing model) shows up as STRONG (3+ interviews) and was not in the brief, that finding gets a PROPOSED `D-N` block of equal weight to the mobile hypothesis.
- Any motivation in the original brief that survives the round with zero confirming AND zero disconfirming quotes lands explicitly under **"We do not have evidence for X"** in `JTBD_INTERVIEWS.md` and is **not silently treated as confirmed**.

### Subject pool reframe

Recruit on the **switch event** ("enterprise users who moved off Salesforce to us in the last 6 months"), not the **suspected reason** ("users who switched because of mobile"). Additionally:
- 1–2 interviews with users who **evaluated us and stayed on Salesforce** (controls for ANXIETY/HABIT -- addresses B4).
- 1 interview, if reachable, with a user who **switched to us and churned back** (the highest-signal interview the team is currently not planning to run).

---

## Recommended next step

Take this reframe back to the team. If they accept it, I can proceed to draft the full switch-interview script (Step 2 of the protocol) anchored on the reframed question and the subject-pool changes. If they reject the reframe and insist on the confirmation-shaped script, I decline the engagement -- running a biased script and producing a quote-bank that launders the team's prior hypothesis is the specific failure this persona exists to refuse.

**Recommended next command:** `decision-interview` -- the team needs to lock the reframed research question, the disconfirmation criteria, and the subject-pool definition as a `D-N` decision **before** the script is drafted. That decision is upstream of the JTBD interview script and is currently the real blocker.

---

### Command transcript
- Loaded persona SKILL.md and applied Steps 1, 4, 8, and quality-bar guardrails to a pre-interview brief.
- Refused to script confirmation-shaped interviews; reframed research question around switch event, not prior conclusion.
- Routed next action to `decision-interview` to lock the reframe before any interview script is written.