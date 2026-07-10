# jtbd-switch-interviewer -- Round 1 Scoping Refusal + Counter-Proposal

> Acting as senior JTBD switch-interview researcher (Christensen / Moesta lineage). Output is qualitative scoping only -- no quote bank yet because no interviews have been run, and (more importantly) the brief as written cannot ground a switch hypothesis. Per Step 1 of the persona protocol, I am **refusing to draft a switch-interview script in the team's current framing** and proposing the minimum corrected hypothesis required before any script gets written.

---

## 1. Step 1 refusal -- the brief is a feature wishlist, not a switch hypothesis

The team brief reads:

> "Users want a beautiful, gamified habit-tracker with streak rewards and friend leaderboards. Validate that users want one."

This is a **feature wishlist about a NEW solution**, with **no OLD solution named**. JTBD switch interviewing requires both halves of the "from X → to Y" pair, because the entire methodology is anchored on reconstructing the timeline of a real human walking away from one solution and into another. Without an incumbent to switch FROM, there is no PUSH force to surface, no HABIT inertia to measure, no ANXIETY about abandoning a current workflow -- three of the four forces collapse to zero by construction.

Concretely, the brief fails the Step 1 gate in three ways:

1. **No OLD solution named.** "Users want a habit-tracker" does not specify what those users are currently doing instead. Are they tracking habits in Apple Notes? In a paper bullet journal? In Streaks / Habitica / Way of Life? On a whiteboard? Not tracking at all? Each of those is a different switch with different forces, and you cannot interview "the average prospective switcher" because that person does not exist.
2. **NEW solution is described in feature language, not job language.** "Beautiful, gamified, streak rewards, friend leaderboards" are *product attributes the team likes*. The user-side framing -- what job is the user hiring this app to do? ("help me feel in control of my mornings", "help me stop disappointing myself", "give me proof I'm becoming the person I claim to be") -- is missing entirely. Until the job is named in user language, interviews will degenerate into "do you like leaderboards? do you like streaks?" feature-preference theater, which is exactly the failure mode this persona exists to catch.
3. **Subject pool is non-switcher-qualified.** "8 mid-20s knowledge workers reachable via founder's Discord, gift-card incentive" describes *who is convenient to reach*, not *who has actually made a recent switch in the habit-tracking job*. Half or more of that pool likely has never paid for or seriously used a habit tracker, which means they have no switch event to reconstruct -- and a JTBD switch interview with someone who has not switched produces hypothetical "I would maybe like…" answers, which is the worst possible input.

If I draft a script in the team's current framing, I will produce a generic "what features do you want in a habit tracker" survey, validate the founder's prior, and ship the persona's signature failure mode. I will not do that.

---

## 2. Missing pieces required before any script gets written

Before round 1 interviews can start, the team needs to supply (or the founder needs to commit to a single chosen variant of) the following:

### 2.1 Name the OLD solution explicitly -- pick ONE switch axis

Choose one of these candidate switch hypotheses and stick to it for round 1. Do not blend them; each is a different study.

| # | OLD solution (FROM) | NEW solution (TO) -- in user job language | Why this switch is researchable |
|---|---|---|---|
| A | "I keep a habit list in Apple Notes / Notion / a paper journal" | "An app that holds me accountable so I don't have to remember to check in" | The user already values the job; the switch is about tool ergonomics + accountability. PUSH and HABIT forces are richest here. |
| B | "I tried Streaks / Habitica / Way of Life and stopped using it within ~2 months" | "Something I'll actually stick with past month two" | This is the **highest-signal** switch for the team's gamification thesis, because past abandonment quotes will reveal whether streaks/leaderboards helped or actively pushed the user out. |
| C | "I don't track habits at all, I just try to remember" | "An app that turns vague intentions into visible progress" | Hardest of the three -- these users may not have a switch event at all, only a struggle. Use only if combined with a clear recent TRIGGER (New Year, breakup, health scare, new job). |

**My recommendation: pick Hypothesis B.** It is the only one that directly tests the team's gamification thesis with users who have *lived* gamification in a habit-tracking context and made a decision about it. Hypotheses A and C cannot disconfirm "streaks and leaderboards drive retention" because their subjects never tried those mechanics seriously.

### 2.2 Re-state the NEW solution in user job language, not feature language

Strong (job-shaped) re-statement of the team's thesis, for use as the round-1 working hypothesis:

> **Switch hypothesis (corrected, user framing):**
> "Mid-20s knowledge workers who tried a habit tracker in the last 18 months and abandoned it within ~8 weeks are looking to switch FROM 'apps that made me feel guilty and then invisible when I broke a streak' TO 'something that keeps me feeling like I'm making progress even on bad weeks, ideally with a small social layer that makes the wins feel real.'"

Note what changed: "beautiful, gamified, streak rewards, friend leaderboards" → "feeling like I'm making progress even on bad weeks" + "wins feel real." That is the level of abstraction at which the four forces operate. Streaks and leaderboards then become **candidate mechanisms** to test against the job, not the job itself. This re-framing is what lets the interview disconfirm the team's prior -- a verbatim like *"the streak counter is exactly what made me quit, I broke it on day 41 and never opened the app again"* would be impossible to surface from a feature-preference script but is the single most decision-changing quote the team could hear.

### 2.3 Fix the subject pool -- switcher-qualified screening required

The current pool ("8 reachable mid-20s knowledge workers via founder's Discord, gift-card incentive") fails JTBD screening on two axes:

- **Selection bias.** Founder's Discord = people predisposed to like the founder's taste. They will tell you the app is great. This is the textbook contaminated pool.
- **No switch-qualification.** "Mid-20s knowledge worker" is a demographic, not a job-state. The screening question that matters is: *"In the last 18 months, did you install a habit-tracker app, use it for at least two weeks, and then stop?"* If yes → eligible. If no → not a switcher, deprioritize or recruit only as a small (≤2 of 8) "non-tracker" comparison cohort.

**Concrete subject-pool fix for round 1:**

- Target n = 8 completed interviews, recruit n = 14–16 to absorb no-shows.
- Screening filter: must have installed AND abandoned at least one habit-tracker app in the last 18 months (Streaks, Habitica, Way of Life, Productive, Strides, HabitNow, Done, or similar). Verbal confirmation of the specific app and approximate abandonment date is the qualification gate.
- Recruit outside the founder's Discord for at least 5 of the 8 to break the warm-pool bias. Reddit r/getdisciplined, r/productivity, r/habitica (especially), and LinkedIn outreach are higher-signal channels for past abandoners. Keep the Discord recruits to ≤3 as a known-warm comparison cohort, and tag their interview IDs accordingly so the synthesis can call out the bias.
- Gift card is fine as incentive ($25–$50 USD-equivalent is typical for 45-min JTBD interview). Disclose it up front. The warm/transactional posture is acceptable *if* the screening filter is strict -- incentive bias is much smaller than pool bias.

### 2.4 Confirm scope of round 1

Round 1 is a **disconfirmation round**, not a validation round. The team should enter it expecting to *learn that the gamification thesis is wrong, partially wrong, or right for a different reason than they assumed.* If the founder is not psychologically prepared for "the streak counter is what made me quit" as a possible finding, round 1 should not happen yet -- run a half-hour expectation-setting conversation first.

---

## 3. Draft switch-interview script (conditional on Hypothesis B being adopted)

The following script is **draft-only and unusable** until §2.1–§2.4 are confirmed by the team. I am including it so the team can see what a proper trigger → struggle → switch ordered script looks like, and so they can react to specific question framings rather than to an abstract methodology note. **Do not run this script until the corrected hypothesis is locked.**

Working switch hypothesis (per §2.2): subjects switched FROM "a habit app I tried and abandoned within ~8 weeks" TO either "another habit app I stuck with longer" OR "no app -- analog or nothing." Either destination is informative; both count as a switch event.

Interview length target: 45 minutes. Recording + transcript required (consent captured at the top). All questions are open-ended; the interviewer's job is to follow the user's timeline backward and resist offering vocabulary.

### Section 0 -- Consent, framing, warm-up (5 min)

1. Confirm recording consent and that the user can stop at any time. Confirm gift-card delivery method. (Not analyzed; logistical.)
2. "Just to set expectations -- I'm not going to ask you what features you want in an app. I'm going to ask you to walk me through the story of an app you actually used and stopped using. There are no right answers; the more boring the detail, the better." (Anchors the user away from feature-wishlist mode, which is the single most important framing move in a JTBD interview.)

### Section 1 -- Anchor the SWITCH moment (the abandonment event) (10 min)

The persona rule is to start at the most recent concrete event and walk backward. For this hypothesis, the "switch" we are reconstructing is the **moment of abandonment** of the previous habit app -- that is the decision event with the richest force signal.

3. "Tell me the name of the last habit-tracker app you used and stopped using." *(Anchors a specific product, not a category.)*
4. "Roughly when did you stop using it? What month, what was going on in your life that week?" *(Pins the switch to a real calendar moment; the surrounding life context is where the PUSH force lives.)*
5. "Walk me through the last time you opened that app. What were you doing right before? What did you see when you opened it? What did you do next?" *(Reconstructs the final session in physical detail. The "what did you see" question often surfaces the streak-broken / empty-state / guilt-trigger moment verbatim.)*
6. "Was there a specific moment you decided you were done with it, or did it just fade? If there was a moment -- what happened?" *(Distinguishes active rejection from passive churn. Active rejection = strong PUSH quote; passive fade = weak HABIT-displacement quote. Both matter, differently.)*
7. "After you stopped opening it, did you delete it? When? What made you delete it versus leave it on your phone?" *(Deletion is a second, often more honest, switch event. The gap between "stopped opening" and "deleted" is the half-life of the user's residual hope in the product.)*

### Section 2 -- Walk backward through the STRUGGLE period (15 min)

8. "Take me back to a few weeks before you stopped. Were there moments where you almost stopped, but kept going? What pulled you back in?" *(Surfaces the dying PULL force -- what was still working right up until it wasn't. Often reveals which feature was actually load-bearing.)*
9. "Was there a day you missed a check-in and felt bad about it? Tell me about that day." *(Direct probe at the streak-guilt mechanic, in story form. The team's thesis lives or dies on the valence of these quotes.)*
10. "What did you tell yourself about the app during those weeks? Did you talk to anyone about it -- a friend, a partner, a coworker? What did you say?" *(First-conversation question. Spoken-aloud framing is much closer to the real internal model than internal-only framing.)*
11. "Were there features you wished it had during that period? …Okay -- and were there features that were already there that started to bother you?" *(The second half of this question is the load-bearing half. "Started to bother you" surfaces ANXIETY-of-staying and is where streak/leaderboard backlash, if it exists, will appear.)*
12. "Did you try changing how you used it -- different habits, different reminder times, turning off notifications? What happened?" *(Surfaces the user's repair attempts. Repair effort = strength of original commitment = magnitude of disappointment when it failed.)*

### Section 3 -- Walk backward to the originating TRIGGER (10 min)

13. "Let's go all the way back. What made you install this app in the first place? What was happening in your life that week?" *(Canonical JTBD trigger question. The trigger is almost never "I wanted to track habits" -- it is "I had a fight with my partner about my drinking" or "I started a new job and my mornings fell apart" or "my therapist suggested it.")*
14. "Before you installed this one, were you trying to track habits some other way? Notes app, paper, just remembering? What stopped working about that?" *(This is where, if the user has a deeper switch history, we discover the *real* OLD solution -- which may be analog, not another app.)*
15. "When you were choosing which app to install, did you look at others? Why this one? What did you almost pick instead?" *(The "almost picked instead" question is gold -- it surfaces the user's actual choice frame, which the team's competitive analysis will never recover from desk research.)*
16. "What did you imagine your life would look like in three months once this app was working for you? Paint me the picture." *(Surfaces the *job in user language*. This is the single most important quote for re-stating the value proposition. It is also the quote against which the abandonment story will be measured -- the gap between the imagined life and the lived experience is the PUSH force, fully assembled.)*

### Section 4 -- Explicit four-forces probes (10 min)

By this point in the interview the four forces should already be partially surfaced through the timeline. Section 4 is a *coverage check*, not an interrogation. Skip any probe that the user has already answered in their own words during sections 1–3; the goal is no force left without a verbatim, not to ask every question.

#### PUSH -- what made the OLD solution intolerable

17. "If you had to finish this sentence: 'I stopped using that app because ___.' What goes in the blank, in your own words?" *(Forces a one-sentence verbatim. Often the most quotable line of the interview.)*
18. "Was there anything the app was doing TO you, not just failing to do FOR you?" *(Distinguishes "didn't work" from "actively made me feel bad." Streak-guilt and leaderboard-shame, if they are real PUSH forces, will surface here.)*

#### PULL -- what made the NEW destination attractive (whether that's another app or going analog/nothing)

19. "Are you tracking habits any other way now? Walk me through what you're doing instead." *(Identifies the actual NEW solution. If "nothing" -- that is also a NEW solution and counts as a valid destination.)*
20. "What does the new thing give you that the old app didn't?" *(If the user has no new thing, reframe: 'What does NOT having the old app give you that having it didn't?')*

#### ANXIETY -- what made switching scary or what made staying scary

21. "When you were thinking about quitting, what worried you? Did you think you'd lose progress, lose the streak, fall off the wagon entirely?" *(ANXIETY-of-switching. Especially relevant to the streak mechanic -- sunk-cost-streak is a documented force in this category.)*
22. "And on the other side -- were there things about staying with the app that were making you anxious? Notifications, the leaderboard, friends seeing you fall off?" *(ANXIETY-of-staying. This is where the team's social-leaderboard thesis is most directly testable. A quote here in either valence is high-signal.)*

#### HABIT -- what kept the user stuck (or, here, what kept the user from a clean switch)

23. "How long after you decided it wasn't working did it take you to actually stop opening it? What kept you opening it during that gap?" *(Measures HABIT inertia in days. Long gap = strong habit loop, short gap = weak habit loop. Either way is data.)*
24. "Is the app still on your phone right now? Why?" *(The phone-icon question. Users keep abandoned apps installed for revealing reasons -- "I might come back," "I forgot," "I don't want to admit I quit." Each maps to a different force.)*

### Section 5 -- Close (5 min)

25. "Is there anything I didn't ask about that you wish I had? Anything about this story that still feels unfinished to you?" *(Catches the user's own unprompted addition. Roughly one in four interviews surfaces the single most important quote in response to this question.)*
26. "If a friend asked you tomorrow whether they should try a habit-tracker app, what would you tell them?" *(Forward-looking quote, useful for marketing-language synthesis but explicitly NOT used as primary force evidence -- it is hypothetical, not lived.)*
27. Thank, confirm gift-card, confirm follow-up permission for a 15-min clarification call if needed.

---

## 4. Four-forces probe map (cross-reference)

For auditability, the explicit force coverage of the script above:

| Force | Primary probes | Secondary / timeline probes |
|---|---|---|
| **PUSH** (old intolerable) | Q17, Q18 | Q5, Q6, Q9, Q11 (second half) |
| **PULL** (new attractive) | Q19, Q20 | Q8, Q15, Q16 |
| **ANXIETY** (switching scary / staying scary) | Q21, Q22 | Q7, Q11 (second half) |
| **HABIT** (stuck / inertia) | Q23, Q24 | Q7, Q12 |
| **TRIGGER** (origin event) | Q13, Q14 | Q16 |
| **STRUGGLE** (active evaluation period) | Q8–Q12 | -- |
| **SWITCH** (decision moment) | Q5–Q7 | Q3–Q4 (anchor) |

No force is covered by only one probe. No probe is generic feature-preference. The script is rejectable if a reviewer can point to a question that could be answered identically by a user who has *never used a habit-tracker* -- by construction, every question above requires the user to have a lived switch story, which is the screening filter from §2.3.

---

## 5. Pre-flight checklist before running round 1

Do not run interviews until all of the following are true:

- [ ] Team has locked Hypothesis B (or explicitly chosen A or C and accepted the trade-offs in §2.1).
- [ ] Job-language re-statement from §2.2 (or team's revision of it) is the working hypothesis written into the task folder.
- [ ] Subject pool is switcher-qualified per §2.3; ≥5 of 8 recruits are from outside the founder's Discord; screening filter is the past-abandonment question, not the demographic.
- [ ] Founder has done the §2.4 expectation-setting on disconfirmation. "Streaks are why I quit" is acknowledged as a possible and acceptable round-1 finding.
- [ ] Recording + transcription tooling is set up before interview 1, not after. (Otterai / Granola / Fathom are all fine. Native phone recording is not -- transcription quality is the bottleneck for verbatim discipline.)
- [ ] A `JTBD_INTERVIEWS.md` skeleton exists in the active task folder with empty sections for: per-interview synthesis (I-01 through I-08), cross-interview pattern roll-up, quote bank, and the explicit "We do not have evidence for X" gap subsection.

---

## 6. What I am NOT producing in this output, and why

Per the persona protocol Steps 2–8, a complete jtbd-switch-interviewer round produces: per-interview synthesis entries, a verbatim quote bank, STRONG/EMERGING/ANECDOTAL clusters, an evidence-gap subsection, and PROPOSED D-N decision drafts. **None of those exist yet because no interviews have been run** -- and they cannot be run until §2 is resolved.

What I have explicitly NOT done, and why:

- **No PROPOSED D-N decision blocks.** It would be malpractice to draft motivation decisions from zero quotes. Drafting PROPOSED blocks now would launder the founder's prior into the substrate, which is the exact failure mode the persona exists to prevent.
- **No STRONG / EMERGING / ANECDOTAL clusters.** Same reason -- clusters require quotes; there are no quotes.
- **No "We do not have evidence for X" subsection yet.** This section is the persona's load-bearing honesty signal, but it is only meaningful *after* a round of interviews has either confirmed, disconfirmed, or failed to surface each prior assumption. Producing one now would be performative.
- **No verbatim quote bank.** By definition: no interviews → no quotes. The single most important discipline of this persona is refusing to fabricate or paraphrase. Zero is the correct number here.

What I have produced:
- A Step 1 refusal with explicit reasoning.
- A corrected switch hypothesis in user job language, ready for team review and lock-in.
- A switcher-qualified subject-pool spec.
- A 27-question switch-interview script with explicit trigger → struggle → switch ordering and labeled four-forces probes, conditional on hypothesis lock-in.
- A pre-flight checklist that gates round 1 on the missing pieces.

---

### Artifact changes

- `PROPOSED` -- `<task>/JTBD_INTERVIEWS.md` (skeleton + this scoping memo as section 0) -- not written to disk by this persona run; the active task folder is not yet provided in this brief, so the artifact is held in this output for the team to paste into the correct task folder once `task-init` has been run for this research effort.
- `SKIP` -- `DECISIONS.md ## Locked decisions` -- no PROPOSED D-N draft this round; zero quotes means zero motivation decisions. Will produce after round 1 interviews complete.
- `SKIP` -- `IMPLEMENTATION_PLAN.md ## Risks and mitigations` -- no PROPOSED risk block this round; risks require evidence of an unaddressed force, which requires interviews.
- `SKIP` -- `TASK_STATE.md ## Observations` and `## Risks to watch` -- same reason.

### Command transcript

- Loaded persona SKILL.md (`commands/jtbd-switch-interviewer/SKILL.md`).
- Applied Step 1 gate: brief failed (no OLD solution; NEW described in feature language; pool not switcher-qualified). Refused to draft script in team framing.
- Produced corrected hypothesis (B-variant recommended), switcher-qualified pool spec, and conditional 27-question script with explicit four-forces probe coverage map.
- No substrate writes; no quote-bank fabrication; no PROPOSED decision drafts (zero quotes available).

### Handoff

**Mode B -- full handoff** (this is a discovery-blocking refusal; the team needs explicit next steps).

**Blocker to clear before next persona run:** team must lock the corrected switch hypothesis (recommend variant B from §2.1) and confirm the switcher-qualified pool spec from §2.3. Until then, no further JTBD work can proceed without producing the persona's signature failure mode.

**Recommended next command:** `decision-interview` -- to lock the choice of switch hypothesis variant (A / B / C) and the job-language re-statement of the NEW solution as canonical decisions in `DECISIONS.md` before round 1 interviews begin. These are decision-driven, not factual, and the answers materially change which 8 humans get recruited and what they get asked. After those decisions are locked, re-invoke `jtbd-switch-interviewer` for the actual round 1 synthesis pass once 3+ interview transcripts exist.

**Run now:** `decision-interview`

**Do NOT run yet:** `jtbd-switch-interviewer` round 1 synthesis, `external-research`, `implementation-plan` for the habit-tracker product, or any UI/design work. All are premature until the switch hypothesis is locked and at least 3 switcher-qualified interviews are in the transcript bank.
