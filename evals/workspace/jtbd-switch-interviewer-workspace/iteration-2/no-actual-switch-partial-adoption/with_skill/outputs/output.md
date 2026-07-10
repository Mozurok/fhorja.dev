# JTBD Switch-Interview Synthesis -- Interview I1

**Team hypothesis under test:** "Users switch from Asana to Linear because of speed."

**Hypothesis restated in user framing (per Step 1):** Team expects OLD solution = Asana being **abandoned**; NEW solution = Linear being **adopted in its place**; motivating force = SPEED.

The interview transcript does not support that framing. Below is the per-interview synthesis, the four-forces framework applicability assessment, and the recommended action.

---

## 1. Per-interview synthesis

### Interview I1
- **Subject:** PM at a 30-person startup; reports "switched to Linear 3 months ago."
- **Adoption type: PARTIAL ADOPTION (also accurately described as ADD-ON / parallel use).**
  - Not SWITCH: Asana was not abandoned. By the subject's own words it still carries marketing campaigns and client requests.
  - Not NO-SWITCH: Linear genuinely replaced Asana for one specific job (engineering / sprint tracking).
  - The accurate label is partial adoption by **job**, not by **org**: Linear was hired for the engineering sprint job; Asana was retained for the cross-functional coordination job.

#### Timeline reconstruction (trigger -> struggle -> switch)
The transcript does **not** reconstruct a clean switch timeline. There is:
- No TRIGGER moment captured ("the day I realized Asana could not keep up was...").
- No STRUGGLE period captured ("for weeks I tried X, Y, Z workarounds...").
- No SWITCH event in the JTBD sense, because the incumbent is still in production use.

What the transcript actually describes is a **tool addition for a newly scoped job**, not a tool replacement for an existing job.

#### Four-forces scoring (verbatim-anchored, per Step 3 / Step 4)

| Force | Evidence | Score |
|---|---|---|
| PUSH (away from Asana) | The only candidate quote is "It is much snappier" -- this is a PULL statement about Linear, not a PUSH statement about Asana. **No verbatim PUSH evidence captured.** The subject explicitly contradicts a strong PUSH: "We never really moved that over" and "They serve different needs now." | NONE (assumption-only) |
| PULL (toward Linear) | "We started using Linear for our roadmap tracking. It is much snappier." -- but scoped narrowly to "sprint stuff" / "the engineering team." | WEAK / job-scoped |
| ANXIETY (about switching) | No quote. The subject never describes hesitation, fear of data loss, training cost, etc. | NONE (gap) |
| HABIT (anchoring them to Asana) | Strongly evidenced: "We still use Asana for marketing campaigns and client requests." "Marketing and client services are still on Asana." "I don't think we will [fully switch]. They serve different needs now." | STRONG |

The dominant signal in this interview is **HABIT/fit-for-job retention of Asana**, not push-away-from-Asana. The "speed" quote is real but is a localized PULL into a new job, not a switch driver.

#### Verbatim quote bank (I1)
- I1-Q1: "We started using Linear for our roadmap tracking. It is much snappier."
- I1-Q2: "We still use Asana for marketing campaigns and client requests. We never really moved that over."
- I1-Q3: "The engineering team is on Linear. Marketing and client services are still on Asana."
- I1-Q4: "Honestly half-half. Linear for sprint stuff, Asana for everything cross-functional."
- I1-Q5: "I don't think we will [fully switch]. They serve different needs now."

---

## 2. Does the four-forces switch framework apply here?

**Short answer: NO -- not to this interview as evidence for the stated hypothesis.**

The Christensen / Moesta four-forces model is explicitly a model of **switching**: a user fires the old solution for a job and hires a new solution for the same job. Push and habit are forces acting on the **incumbent**; pull and anxiety are forces acting on the **candidate**, both with respect to **one job-to-be-done**.

In I1 the job decomposed:
- The engineering sprint job: Linear was hired. Asana was not previously doing this job well enough to count as the incumbent for a four-forces analysis, and the interview never establishes that Asana was the prior solution for this specific job (vs. a generic project-tracker the team also used).
- The marketing / client-services coordination job: Asana remains hired. There is no switch event here at all.

So:
- There is no single job-to-be-done where Asana was fired and Linear was hired. The "switch" the team is hypothesizing did not occur at the job level.
- The four-forces framework was designed to explain a discrete switch decision. It is **not designed for and does not measure**: tool addition, job re-segmentation, or parallel multi-tool stacks.
- Forcing the four forces onto I1 would launder the team's prior hypothesis: the "snappier" quote would get elevated into a PUSH/PULL switch driver even though the subject explicitly denies a switch ("I don't think we will. They serve different needs now.").

The interview is **valid JTBD evidence**, but for a different question -- "which jobs does Linear win against Asana, and which does it not?" -- not for the stated switch hypothesis.

---

## 3. Recommended action -- can the team treat I1 as evidence for "switch because of speed"?

**No. Per Step 4 (verbatim over paraphrase) and Step 5 (pattern strength), this interview must NOT be counted as a confirming case for the "switch from Asana to Linear because of speed" hypothesis.** The reasons are explicit:

1. **No switch occurred.** Treating partial adoption as a switch is the exact failure mode JTBD methodology is built to prevent. The subject volunteered the disconfirmation: "We never really moved that over" and "I don't think we will." Counting I1 as a SWITCH would require ignoring the subject's own framing.
2. **The "speed" signal is real but mis-scoped.** "Snappier" is a verbatim PULL for the engineering sprint job. It is **not** verbatim evidence that speed caused a wholesale Asana -> Linear switch, because no wholesale switch happened.
3. **Cluster strength tag for I1 toward the team's hypothesis: ANECDOTAL at best, and contradicted within the same interview.** Per Step 5, an ANECDOTAL cluster (and especially a self-contradicting one) cannot drive a PROPOSED decision.
4. **The honest finding is a hypothesis reshape, not hypothesis confirmation.** A defensible reshaped hypothesis the team can take into the next interview round:
   - "For the engineering sprint job, teams hire Linear in addition to Asana, citing speed and sprint-fit; Asana is retained for cross-functional coordination jobs. Net market motion is tool-stack expansion, not tool replacement."
   - This reshape changes downstream decisions: pricing (per-seat-against-incumbent vs. per-seat-net-new), positioning (replace Asana vs. complement Asana), and competitive comparisons (speed vs. cross-functional surface area).
5. **Recommended next steps for the team:**
   - Re-run the interview round with explicit job-decomposition probes ("walk me through each job your team coordinates, and which tool owns it") to test whether I1's job-split pattern is STRONG or idiosyncratic.
   - Add an explicit screening question to the recruit: "Have you fully removed Asana from your team's workflow?" -- filter for true switchers separately from partial adopters.
   - Add to "We do not have evidence for X" gap list in `JTBD_INTERVIEWS.md`: "We do not have evidence that any team has fully switched from Asana to Linear citing speed as the primary driver. I1 is partial adoption with explicit no-full-switch statement."
   - Do **not** lock a `D-N` decision on "speed drives Asana -> Linear switch" from this evidence; if drafted at all, mark as ANECDOTAL and self-contradicted, and route promotion blocker to `decision-interview` only after STRONG-cluster evidence accumulates.

### Bottom line
I1 is a high-quality JTBD interview that disconfirms the team's stated switch hypothesis and reveals a more interesting underlying pattern: **job-level partial adoption with persistent parallel use**. The four-forces switch framework does not apply to it as stated. Treating it as a confirming case would be exactly the paraphrase-laundering failure mode this methodology exists to prevent.