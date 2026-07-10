# JTBD Switch-Interview Round Design -- Habit-Tracker Mobile App

## 0. Brief diagnosis: the switch hypothesis is NOT groundable as written

A Jobs-To-Be-Done switch interview is structured around a real, observable consumption event -- someone abandoning one solution (the "old") in favor of another (the "new"). Without an incumbent solution that real users have already switched away from (or are visibly preparing to), there is no switch moment to reconstruct, no struggle period to mine, and no originating trigger to chase backward to. You get hypothetical preferences instead of behavior.

The brief as written has three grounding gaps that block a credible switch-interview design:

### Gap 1 -- No incumbent named (the OLD solution is missing)

The brief says "users want a beautiful, gamified habit-tracker." It does not specify:

- What current behavior or product the new app is supposed to replace (Streaks? Notion? Apple Health? a paper journal? a Notes-app checklist? nothing at all?).
- Whether the target user is currently performing the underlying job at all. "Wants a habit-tracker" is a feature wish; "is currently failing to build a meditation habit using Apple Reminders" is a switch candidate.

Without a named incumbent, the four forces collapse: PUSH presupposes dissatisfaction with a specific old thing, PULL presupposes a believable better thing, HABIT presupposes ingrained behavior to be displaced, and ANXIETY presupposes a perceived cost of switching.

### Gap 2 -- No switch event to recruit against

The subject pool (8 mid-20s knowledge-workers in the founder's Discord) is recruited on demographics, not behavior. JTBD interviews require recruiting on a recent, real consumption event -- e.g., "downloaded a habit-tracking app in the last 60 days," "deleted a habit-tracking app in the last 90 days," or "started a new health/productivity routine in the last 30 days and is using SOMETHING to support it." Without behavioral screening you will interview people who have never made a switch, which is interview-as-survey, not JTBD.

### Gap 3 -- Sourcing and incentive bias

A warm Discord pool of the founder's contacts, paid with a gift card, is the highest-bias recruitment posture for validating a founder's thesis. Subjects will (a) be socially motivated to be encouraging, (b) be selected on already liking the founder/space, and (c) treat the conversation as a gifted favor. JTBD aims at reconstructed past behavior, which partially defends against this, but the brief should acknowledge it and add at least one neutral channel.

### Proposed missing piece (before any script is drafted)

Before running the round, the team should commit to a named **switch hypothesis of the form:**

> When a mid-20s knowledge-worker who has recently tried and abandoned [SPECIFIC INCUMBENT -- e.g., the iOS Reminders/Notes checklist they use today, or a previously-installed app like Streaks / Habitica / Notion habit template / Apple Health / Fitbit] in the context of [SPECIFIC LIFE EVENT -- e.g., post-grad routine reset, return-to-office, breakup, new year, therapist recommendation] is looking for a new way to make a desired routine stick, they would switch to [OUR APP] because the old solution failed on [SPECIFIC DIMENSION -- accountability? visibility? motivation decay? friction?].

A defensible recruiting screen then becomes: *"In the last 90 days, have you (a) tried to build or restart a personal routine -- health, learning, sleep, money, whatever -- AND (b) installed, used, or abandoned an app, journal, or other tool to help you stick to it?"* That screen produces subjects with a real switch (or attempted switch) to reconstruct. Eight people from that screen -- even partially sourced from Discord -- is a workable round; eight demographically-matched friends is not.

The team should also explicitly note: **the brief's stated thesis (beautiful + gamified + streaks + leaderboards) is a solution hypothesis, not a switch hypothesis.** A switch interview cannot validate that thesis directly; it can only validate (or kill) the underlying job and the forces around the current incumbent. Confusing these is the single most common JTBD-research failure mode and would waste the round.

---

With those caveats explicit, the deliverables follow. I am drafting them against the **best-available restated hypothesis** the brief implicitly points at, flagged as a working assumption to be confirmed with the team before fielding.

---

## 1. Restated switch hypothesis (user framing, not feature framing)

**Working assumption (must be confirmed before fielding):** The incumbent being displaced is the *ad-hoc personal stack* most mid-20s knowledge-workers actually use to manage personal routines today -- primarily the **native iOS/Android Reminders or Notes app, a paper journal, or a previously-installed-then-abandoned habit app (Streaks, Habitica, Notion template, Apple Health rings)** -- used in isolation, without social visibility.

### Switch hypothesis (user framing)

> When I (mid-20s knowledge-worker) am trying to actually become the kind of person who [exercises / reads / sleeps on time / journals / meditates / drinks less / saves money] **consistently**, and my current way of holding myself to it (private reminders, a Notes checklist, mental promises, or an app I downloaded once and stopped opening) has quietly stopped working -- I drift, I forget, nothing notices when I quit -- I want a way to make the commitment feel *witnessed and alive again*, so that the routine stops depending on willpower I do not reliably have.
>
> I would switch FROM "tracking it alone in my head / in Notes / in an app I no longer open" TO "a place where the streak is visible, where someone (or something) notices when I show up and when I don't, and where doing it feels a little bit like a game I am playing with people I know."

Note the user framing: the job is *"help me become the kind of person who…"*, the failure mode of the incumbent is *"nothing notices when I quit,"* and the pull is *"witnessed and alive."* Streaks, leaderboards and gamification are *candidate mechanisms* for that pull -- they are not the job. The round must test the job and the forces; it must not assume the mechanism.

---

## 2. Interview script -- ordered backward from SWITCH → STRUGGLE → TRIGGER

Standard JTBD timeline order: start where the subject's memory is sharpest (the most recent observable action), then walk backward in time to reconstruct what made them act. Total target: 45–60 minutes. Use silence; do not lead.

### Opening / framing (not numbered -- orientation only)

> *"I'm going to ask you about a very specific recent moment -- when you started using [whatever they use today] / or stopped using [whatever they abandoned]. I'm not interested in what you think you should do or what would be ideal. I'm interested in what actually happened, step by step, and I'll ask a lot of 'and then what' questions. There are no wrong answers; if you don't remember, just say so."*

### Phase A -- The SWITCH moment (the most recent observable event)

1. Tell me about the most recent time you actively tried to build, restart, or hold yourself to a personal routine -- anything: workouts, reading, sleep, meditation, language, money, alcohol, screen time. Which one was it?
2. Walk me through the very first day you used [the current tool / new app / new method] for that routine. Where were you? What time of day? What were you holding -- phone, paper, watch?
3. What did you do *immediately before* you set it up? What were you doing five minutes before you opened the app store / pulled out the notebook / made the calendar block?
4. How did you choose *this* particular way of tracking it? Did you compare alternatives, ask anyone, search anything? Walk me through that.
5. Was anyone else involved in or aware of the decision? Did you tell anyone you were starting? Why or why not?
6. What was the *exact* moment you decided "okay, I am doing this" vs. just thinking about it? What tipped it from idea to action?

### Phase B -- The STRUGGLE period (the days/weeks before the switch)

7. Before you switched to [the new thing], how were you trying to keep this routine? Walk me through a typical day in that earlier setup.
8. What were you using before -- even if it was nothing formal? (Probe gently: phone reminders, Notes, mental notes, a friend, a calendar, a coach, a previous app.)
9. When did you first notice that the old way wasn't working? What was happening -- or not happening -- that told you that?
10. Can you remember a specific day or week when you knew the old approach was failing? What did that day look like?
11. Did you try to *fix* the old approach before abandoning it? What did you try? Why didn't that work?
12. Who, if anyone, said something to you -- or didn't say something -- during this period that mattered? (Probe for partner, friend, doctor, coworker, social-feed comparisons.)
13. How did you feel about *yourself* during that stretch? (Listen for shame, frustration, resignation, quiet ambition -- these are job-energy signals.)
14. Were there moments you almost switched earlier but didn't? What held you back? What made you wait?

### Phase C -- The originating TRIGGER (what made the job become active at all)

15. Step back further. Before any of this -- before you were trying to build this routine at all -- what was going on in your life that made this routine start to matter to you?
16. When did you first start thinking "I should really be doing [X]"? What prompted that thought? (Probe: a doctor's appointment, a photo, a relationship moment, a birthday, a work event, a friend's transformation, a piece of media, a health scare, a vibe shift.)
17. Was there a particular event -- even a small one -- that turned a vague intention into a concrete "I'm starting this now"?
18. How long was the gap between "I should" and "I'm actually doing this"? What filled that gap?
19. Had you tried to build this same routine before, in the past? When? What happened? Why did that attempt end? (Old attempts are *critical* -- most habit switchers are repeat switchers.)
20. If this trigger hadn't happened, do you think you would have started anyway? Why / why not?

### Phase D -- Reconstruction and outcome (closing, behaviorally anchored)

21. Looking at where you are now: is the new approach actually working? Define "working" in your own words.
22. If it's working, what is it doing that the old approach didn't? Be as concrete as you can -- not "it's better," but what specifically.
23. If it isn't working, what's failing? Are you already drifting toward abandoning it? What would the next switch look like?
24. If I took [the new tool] away from you tomorrow, what would you do? Would you go back to [the old thing], find another replacement, or give up on the routine?
25. Is there anyone you've told about [the new tool]? Have you recommended it? Why / why not? (Word-of-mouth is the cleanest pull signal.)

### Do-not-ask list (explicit guardrails)

- Do **not** ask "would you use an app that has streaks and leaderboards?"
- Do **not** ask "what features would you want?"
- Do **not** describe the team's product at any point during the interview.
- Do **not** ask "do you like gamification?" -- it primes and contaminates the trigger reconstruction.
- Do **not** ask hypothetical-future questions until Phase D, and even there only behaviorally ("what would you do," not "would you like").

---

## 3. Four-forces probes -- explicit PUSH / PULL / ANXIETY / HABIT labels

Each force is named, defined for this product context, and given concrete probe questions that can be slotted into Phases A–C as the conversation surfaces material. Forces are *not* asked as a battery -- they are listened for and probed when the subject opens a door.

### PUSH -- dissatisfaction with the current/old situation

*What is making them want to leave the existing way of tracking the routine? What hurts about today?*

- P1. What specifically frustrated you about how you were doing this before?
- P2. Was there a moment of "I can't keep doing it this way"? What happened?
- P3. What was the *cost* of staying with the old approach -- emotional, time, social, health, identity?
- P4. Did anyone or anything reflect that cost back to you (a comment, a photo, a number on a scale, a missed event)?
- P5. When you tried to keep going with the old way, what was the failure mode -- did you forget? get bored? feel alone? lose track? lie to yourself?

### PULL -- attraction of the new solution

*What is drawing them toward the new way? What did the new thing seem to promise?*

- L1. The first time you heard about / saw / considered [the new approach], what stood out? What were the exact words you used in your head?
- L2. What did you imagine your life looking like once you were using it consistently?
- L3. Was there someone using it who you wanted to be more like? Who?
- L4. What was the single thing you were *most* hoping the new thing would do for you that the old one didn't?
- L5. Did you imagine other people would see you using it? Did that matter? (Listen carefully -- this is the leaderboard/social signal probe, asked indirectly.)

### ANXIETY -- fears about adopting the new solution

*What made them hesitate? What could go wrong with switching? What did they not want to admit?*

- A1. Was there anything that made you hesitate before starting? Even briefly?
- A2. Did you worry about looking like the kind of person who needs an app for this? Or about telling friends you were using one?
- A3. Had you tried apps like this before that didn't work? What happened? Were you worried this would be the same?
- A4. Did you worry about cost, privacy, data, ads, getting hooked on another app, screen time?
- A5. Did you worry about the social piece -- being seen failing, being compared, having a streak that everyone watches you break? (Asked only if leaderboards/social arise organically.)

### HABIT -- inertia of the old solution

*What made the old approach sticky even when it wasn't working? What had to be overcome to leave it?*

- H1. Even when the old way wasn't working, why did you stay with it as long as you did?
- H2. Was the old approach woven into anything else -- your morning routine, your phone home screen, your relationship, your sense of yourself as a "person who tries"?
- H3. What did you have to give up or rearrange to switch?
- H4. Are there pieces of the old approach you're still doing alongside the new one? Why those?
- H5. If you tried to picture going back to the old way, what would feel familiar/comfortable about it -- even if you don't want to?

### Force-balance read (post-interview synthesis, not asked)

For each subject, after the interview, score the four forces qualitatively (low / med / high) and write a one-sentence force-balance summary. A switch is plausible when PUSH + PULL > ANXIETY + HABIT, and the round's read-out is the *pattern across the 8 subjects*, not any one story. If PULL is consistently weak or HABIT consistently dominates, the team's thesis is in trouble regardless of how enthusiastically subjects say "yeah I'd use that."

---

## Round-level recommendations (beyond the script)

1. **Re-screen the pool.** Drop subjects who have not made a recent real attempt at a routine + tool. Eight friends-of-founder without that screen is not a JTBD round.
2. **Add ≥2 non-Discord subjects** sourced cold (Respondent, UserInterviews, a Reddit recruit from r/getdisciplined or r/decidingtobebetter) to triangulate against the warm-pool bias.
3. **Confirm the working incumbent hypothesis** with the team in writing before fielding. If the team cannot name what they think users are switching *from*, that is the first finding and the round should be paused.
4. **Pre-register what would kill the thesis.** Specifically: if fewer than ~3/8 subjects surface social visibility or witnessing as a meaningful PULL when probed indirectly, the leaderboard bet is unsupported. If HABIT around private/solo tracking dominates, the social pitch is fighting inertia it cannot win.
5. **Do not show or describe the product** at any point during the round. Demos contaminate every subsequent answer.
6. **Record and transcribe.** Code against the four forces in synthesis, not live.

This design treats the brief honestly: it names the missing piece, refuses to dress a feature-wishlist survey as a JTBD round, and gives the team a script that -- if recruited against properly -- will actually tell them whether anyone is switching, what they're switching from, and whether the team's gamification thesis touches the real job or just decorates it.
