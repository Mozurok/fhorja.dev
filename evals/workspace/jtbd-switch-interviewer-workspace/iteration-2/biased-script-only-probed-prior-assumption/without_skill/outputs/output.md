# JTBD Switch Interview Review: Notion → Obsidian

## TL;DR -- Interviews are COMPROMISED

The script asked five questions; four of them either name "speed" outright or anchor the subject to it before any open exploration. Only one Force of Progress (Push of the old) was meaningfully probed, and even that was pre-framed as a speed problem. **The captured data cannot be used to confirm or reject the team's hypothesis.** It is confirmatory evidence of the team's prior, not evidence of the subject's actual switching behavior.

---

## 1. Per-Interview Synthesis (verbatim discipline + force tagging)

JTBD switch interviews use four Forces of Progress:

- **Push** -- what made the old situation intolerable
- **Pull** -- what made the new solution attractive
- **Anxiety** -- what worried the subject about switching
- **Habit** -- what tied them to the old solution

Tagging only what the subject actually said (not inferred), and flagging when the quote is contaminated by the interviewer's framing.

### Interview 1
- Verbatim: *"Yeah, Notion was slow. Obsidian is faster. Speed is a big factor."*
- Force tags:
  - PUSH (speed of old) -- **contaminated**: the word "slow" was introduced in Q2 and Q3 before the subject spoke. This is an echo, not an independent push signal.
  - PULL (speed of new) -- **contaminated**: same framing.
- Anxiety: **not probed** (zero data).
- Habit: **not probed** (zero data).
- First-thought / triggering event (Q1 prompt asked but no quote captured): **missing**. We don't know the actual first moment of dissatisfaction.

### Interview 2
- Verbatim: *"Speed definitely. I was tired of waiting for pages to load."*
- Force tags:
  - PUSH -- page-load latency is a concrete, observable pain. This is the strongest single data point in the set, but still elicited only after the interviewer named speed.
  - PULL -- **not probed** in this quote.
- Anxiety: **not probed**.
- Habit: **not probed**.
- Note: "tired of waiting" suggests a struggling moment, but we lack the surrounding story (what were they trying to do? what was the deadline? what made *that* day different?).

### Interview 3
- Verbatim: *"It was speed and also the local-first thing. But mostly speed when you ask."*
- Force tags:
  - PUSH/PULL (speed) -- contaminated by framing.
  - PULL (local-first) -- **uncontaminated and unexplored**. The subject volunteered "local-first" despite the script never asking. The qualifier *"when you ask"* is a tell: it implies the subject is answering the question the interviewer wants answered, not necessarily the most truthful one.
- Anxiety: **not probed**.
- Habit: **not probed**.
- This interview contains the only signal in the entire set that the team's hypothesis may be incomplete.

### Cluster across the three
- Single cluster surfaced: **"speed / latency"** -- but every instance is downstream of an interviewer prompt that named speed first. We cannot distinguish "subject independently cares about speed" from "subject is cooperating with the interviewer."
- Latent cluster (one mention, not followed up): **"local-first / data ownership"** in I3.
- Triggering events, anxieties, and habits: **zero clusters** -- because zero questions probed them.

---

## 2. Script Bias Assessment

### Were all four forces probed?

| Force | Probed? | Evidence |
|---|---|---|
| Push (intolerable old) | Yes, but **framed as speed only** | Q3 names "slowest thing about Notion" -- pre-selects the push dimension |
| Pull (attractive new) | Yes, but **framed as speed only** | Q2 names "in terms of speed" -- pre-selects the pull dimension |
| Anxiety (what worried them about switching) | **No** | No question about hesitation, cost of leaving Notion data behind, learning curve, sync risk, etc. |
| Habit (what tied them to Notion) | **No** | No question about workspaces, templates, team members, shared docs, or sunk investment |

So the answer to the framing question: **only Push and Pull were probed, and both were narrowed to "speed" before the subject spoke.** Two of the four forces are entirely absent from the data.

### Specific script defects

1. **Q2 is a leading question.** Comparing "in terms of speed" before establishing whether speed even mattered to this subject. This is the textbook violation.
2. **Q3 presupposes the conclusion.** "What's the slowest thing about Notion that bothered you?" assumes (a) something was slow and (b) that slowness bothered them. The subject has no graceful way to say "actually, nothing about speed bothered me."
3. **Q4 is leading even though it tries to be balanced.** "Are there other reasons *besides speed*?" still centers speed and signals to the subject what the interviewer cares about. Anything they mention will feel like a side note. I3's "*but mostly speed when you ask*" is exactly this dynamic on display.
4. **Q5 is a closer disguised as a check.** "Would you say speed is the main reason?" invites agreement and gives the subject an easy out from a tiring interview.
5. **Q1 is the only good question** and appears to have been used as warm-up rather than mined. A proper switch interview would spend ~20 minutes on the timeline that Q1 opens -- *when did you first consider an alternative, what happened that day, who was in the room, what did you try first* -- and never have to ask about speed at all, because the subject would surface their real pushes spontaneously.

### Why this matters

JTBD switch interviewing exists specifically to defeat confirmation bias. The technique only works if the interviewer **withholds their hypothesis** and lets the subject reconstruct the timeline. This script does the opposite: it announces the hypothesis in Q2 and asks the subject to validate it three more times. The fact that all three subjects said "speed" is not evidence that speed drives switching -- it is evidence that the script works as a leading instrument.

I3's unprompted "local-first" mention is the single most informative data point in the entire study, and it was not followed up on.

---

## 3. Recommended Next Action

**Discard these three interviews as evidence for or against the hypothesis.** Keep the transcripts as a calibration artifact -- they're a useful internal example of a leading script -- but do not let them influence the roadmap.

Then:

1. **Rewrite the script** to honor the four forces and the timeline structure:
   - Open with the *purchase/adoption moment*: "Take me back to the day you first downloaded Obsidian. What was happening that day?"
   - Walk the timeline backward to the *first thought*: "When did you first think Notion wasn't going to work for you anymore?"
   - Probe push, pull, anxiety, and habit explicitly but **without naming any specific cause** (no "speed", no "local-first", no "price"). Let the subject name the dimensions.
   - Close with anxieties: "What almost stopped you from switching? What did you have to leave behind?"
2. **Run 5–8 new interviews** with people who switched in the last 60 days (recency matters -- memory of the struggling moments fades fast).
3. **Specifically follow up on the "local-first" signal** from I3 by recruiting at least 2 subjects who mention data ownership, sync, or privacy in screening. If the team's hypothesis is right, those subjects will still surface speed as a primary push. If the team is wrong, you'll learn what they're actually buying.
4. **Have a non-team-member transcribe and tag forces blind** before the team reads the results, to break the "we already know it's speed" gravity.
5. **Pre-register the falsification criterion**: e.g., "If fewer than 60% of subjects spontaneously mention latency before the interviewer does, we reject the speed hypothesis as the primary driver." Decide this *before* running the next round.

### What to tell the team

The current interviews tell us the team likes the speed hypothesis. They don't tell us why users switched. That's a meaningful gap, not a small one -- shipping product decisions on this data risks optimizing the wrong dimension (e.g., investing in performance work when the actual switching driver might be local-first storage, plain-text portability, or extension ecosystem).
