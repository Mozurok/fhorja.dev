# Review of JTBD Research Brief: "Confirm Mobile Is The Switching Reason"

## 1. Assessment -- Is the brief actionable as written?

**No, not as written.** The brief is operationally clear (5–7 interviews, target = enterprise switchers from Salesforce, output = roadmap input on mobile) but it is methodologically broken. The team has already decided the answer ("we know users switch because of mobile") and is commissioning interviews to *ratify* that answer rather than *discover* the truth. That makes the research a validation theater, not an investigation.

Specific problems:

- **The outcome is pre-committed.** "Prioritize mobile in the roadmap" is the stated downstream action regardless of what the interviews surface. If the data contradicts the hypothesis, there is no defined path for the team to act on the contradiction. That is the textbook signal of a non-actionable research design.
- **Sample is too narrow to support a causal claim.** 5–7 interviews with people who already switched cannot tell you *why people switch*; it can only tell you what *some* switchers say after the fact. There is no comparison to people who evaluated and stayed on Salesforce, or to people who switched for other reasons. Without that, every quote will be coded as "mobile-related" by a team primed to hear it.
- **"Mobile experience" is not yet a Job.** It is a feature category. JTBD interviews are supposed to surface the *progress a person is trying to make* and the *struggling moments* that triggered the switch. "Mobile" might be a surface symptom of an underlying job ("I need to update deal status between meetings without going back to my laptop"), or it might be a rationalization offered after the fact. The brief collapses symptom and cause.
- **No falsification criterion.** A usable research brief states what evidence would *change the team's mind*. This one doesn't. That is the single clearest sign it is not actionable as a learning exercise -- only as a confirmation exercise.

## 2. Confirmation-Bias Risk -- Named Explicitly

This brief has at least four compounding confirmation-bias risks. Naming them plainly:

1. **Hypothesis-confirmation bias in interview design.** The team will (consciously or not) write questions like "Tell me about the mobile experience that frustrated you in Salesforce" instead of "Walk me through the day you decided Salesforce wasn't working anymore." The first prompt plants the answer; the second lets the answer emerge.
2. **Selection bias in recruiting.** If the screener targets "users who switched because of mobile" or even "users who use our mobile app heavily," the sample is rigged. Switchers whose real reason was pricing, admin overhead, integration pain, or a champion changing companies will be excluded before they ever get on a call.
3. **Coding/interpretation bias post-interview.** Even if an interviewee says "the mobile thing was annoying, but honestly we left because Salesforce admin costs were eating a full headcount," the team -- primed for the mobile story -- will likely code that quote as supporting the mobile hypothesis and discount the admin-cost remark as a side comment.
4. **Sunk-commitment bias on the roadmap.** "Prioritize mobile" appears to already be in motion. Research commissioned to justify a decision that's already been made is not research; it's internal political cover. The risk is that the team ships mobile investment, doesn't see the expected retention/expansion lift, and has no diagnostic to understand why.

The net effect: even a perfectly executed 5-interview study will produce a deck that says "users confirmed mobile matters" -- and the team will learn nothing they didn't already believe walking in.

## 3. Reframed Research Question

The original question -- *"Confirm that users switch because of mobile"* -- is not answerable by JTBD interviews because it presumes the answer. Reframed so that the research can actually produce a falsifiable, decision-useful answer:

**Primary research question (reframed):**
> "What progress were recently-switched enterprise customers trying to make that Salesforce was blocking, and what specific event or accumulated friction pushed them to evaluate alternatives? Where does mobile rank among those forces, and what other forces -- if any -- were equally or more decisive?"

**Why this version works:**

- It treats *mobile* as one hypothesis among several, not the conclusion. The interview can confirm, downgrade, or reject it.
- It centers the JTBD frame correctly: the *job* (progress the customer was trying to make), the *struggling moment* (what specifically broke), and the *forces of progress* (push from Salesforce, pull of our product, anxieties, habits) -- not a feature category.
- It is falsifiable. If 5–7 interviews surface mobile as the top force in most accounts, the team has earned the right to prioritize mobile. If mobile shows up as a secondary or post-hoc rationalization while admin cost, reporting flexibility, or AE adoption friction dominate, the team has learned something genuinely new and the roadmap conversation changes.

**Supporting sub-questions the team can actually answer with 5–7 interviews:**

1. What was happening in the customer's business in the 30–90 days *before* they started evaluating alternatives? (Surfaces the trigger event, which is rarely "mobile.")
2. Who inside the customer first said "we need to look at something else" and what were they trying to accomplish that day? (Surfaces the job-holder and the job.)
3. What did they try to do *inside Salesforce* to make it work before giving up? (Surfaces real friction vs. rationalized friction.)
4. When they evaluated us, what did they test first, and what would have made them walk away? (Surfaces the pull forces and the anxieties -- mobile may or may not appear here.)
5. Six months in, what would make them switch *away from us*? (Stress-tests whether the original switching force is durable or situational.)

**Sampling reframe:** Recruit 5–7 switchers *without* screening on the reason for switching. Optionally add 2–3 "evaluated and stayed on Salesforce" interviews as a contrast set -- this is the single highest-leverage change to break confirmation bias, because it forces the team to explain why the *same* mobile pain didn't cause those accounts to switch.

**Decision rule the team should commit to *before* fielding:**
> "If mobile is the dominant force in ≥4 of 6 interviews and shows up as a *trigger* (not just a complaint), we prioritize mobile. If mobile is present but secondary to another force that appears in ≥4 of 6 interviews, we re-open the roadmap conversation before committing engineering capacity."

Without that pre-committed rule, the reframed question won't save the study -- the team will still read the transcripts through the lens they walked in with.

---

**Bottom line:** The brief as written will produce confident-sounding but epistemically empty research. Reframed around the *job*, the *trigger*, and the *forces* -- with an unbiased recruit and a pre-committed decision rule -- the same 5–7 interviews can either validate the mobile bet with real evidence or save the team from investing a quarter of engineering capacity on the wrong cause.