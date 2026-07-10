# JTBD Switch-Interview Synthesis -- Round 1

**Persona:** jtbd-switch-interviewer
**Prior team assumption under test:** "Users switch from competing tools to us because our product is faster."
**Input material:** Researcher summary notes for I1, I2, I3 (no verbatim transcripts; no direct quotes captured).

---

## 0. Refusal-to-propose-decision-from-paraphrase note (load-bearing)

I will not produce a `PROPOSED` decision block confirming, disconfirming, or refining the team's "faster = the reason they switched" assumption in this round. Per Step 4 of the persona protocol, paraphrase cannot be the load-bearing evidence for a four-forces claim, because paraphrase is exactly where the team's prior assumption sneaks back in. Every line in the provided notes is the junior researcher's restatement of what they thought they heard -- not what the user said. The repeated word "fast" / "faster" / "snappy" / "performance" across I1, I2, I3 cannot be distinguished from the researcher reaching for the team's existing vocabulary. The whole reason the verbatim-quote rule exists is to block this exact failure mode.

Concretely:
- No `D-N` PROPOSED block is drafted for `DECISIONS.md` in this round.
- No `## Risks and mitigations` PROPOSED block is drafted that depends on the "speed" framing.
- The only substrate-touching artifact this round produces is a `TASK_STATE.md ## Observations` PROPOSED entry recording that the round was conducted with paraphrase-only notes and is therefore evidentially void on the prior assumption.

The decision is deferred to Round 2, which must capture verbatim quotes.

---

## 1. Switch hypothesis (restated)

- **Team's hypothesis:** users are switching FROM "a competing/incumbent tool" TO "our product" BECAUSE "our product is faster."
- **OLD solution named:** not specified in the brief beyond "the previous tool" -- already a smell; switch interviews require a concrete named incumbent per subject.
- **NEW solution named:** "our product."
- **Force the hypothesis presupposes:** PULL = speed/performance of the new tool.

Note: the hypothesis is feature-shaped ("faster"), not job-shaped. A clean JTBD restatement would name the job-to-be-done the old tool was failing at and what the user hired the new tool to accomplish. Round 2 script must force the user to articulate the job, not rate the feature.

---

## 2. Per-interview synthesis

Per Step 3 + Step 4: **a force cannot be scored without at least one verbatim quote.** Because none of I1, I2, I3 contain quotes, every force below is marked `UNSCORED -- paraphrase only`.

### Interview I1 -- PM at a startup, switched ~2 months ago

- **Timeline reconstruction (trigger → struggle → switch):** NOT RECONSTRUCTABLE from notes. Researcher captured a feature impression ("faster"), not an event sequence. No first thought, no first conversation, no first action recorded.
- **PUSH (old tool intolerable):** `UNSCORED -- paraphrase only.` No quote. Note says "previous tool" was implicitly worse on speed but the user's own framing of what made it intolerable is missing.
- **PULL (new tool attractive):** `UNSCORED -- paraphrase only.` Researcher wrote "product feels faster than the previous tool" and "liked how snappy it was" -- these are the researcher's words, not I1's. We do not know whether I1 said "fast," "snappy," "responsive," "doesn't hang," "loads instantly," or used a non-speed word the researcher mapped onto "fast."
- **ANXIETY (switching scary):** `UNSCORED -- paraphrase only.` Not probed in notes.
- **HABIT (stuck in old):** `UNSCORED -- paraphrase only.` Not probed in notes.
- **Verbatim quotes captured:** none.

### Interview I2 -- Freelance writer, switched ~4 weeks ago

- **Timeline reconstruction:** NOT RECONSTRUCTABLE. No trigger event captured.
- **PUSH:** `UNSCORED -- paraphrase only.` Note says "previous tool was slow" -- but this is the researcher's compression. We do not know if the user said "slow," "laggy," "took forever to open my drafts," "lost my place," or named a non-speed friction (autosave, formatting, distraction) the researcher then summarized as "slow."
- **PULL:** `UNSCORED -- paraphrase only.` "User seemed to value performance" -- "seemed to" is a tell that the researcher is inferring, not quoting.
- **ANXIETY:** `UNSCORED -- paraphrase only.` Not probed.
- **HABIT:** `UNSCORED -- paraphrase only.` Not probed.
- **Verbatim quotes captured:** none.

### Interview I3 -- Marketing ops lead, switched last week

- **Timeline reconstruction:** NOT RECONSTRUCTABLE. The trigger event for "last week" should be the cleanest of the three (most recent, freshest memory) -- and it is the most thinly captured ("Performance was a theme").
- **PUSH:** `UNSCORED -- paraphrase only.` No quote.
- **PULL:** `UNSCORED -- paraphrase only.` "They liked how fast it was" -- researcher's voice, not I3's.
- **ANXIETY:** `UNSCORED -- paraphrase only.` Not probed. For a marketing ops lead, anxiety forces (data migration, team buy-in, breaking existing reports) are highly likely and entirely missing.
- **HABIT:** `UNSCORED -- paraphrase only.` Not probed.
- **Verbatim quotes captured:** none.

---

## 3. Cross-interview cluster tagging

Per Step 5: clusters require independent verbatim quotes; they cannot be built on paraphrase agreement.

| Candidate cluster | Force | Quotes backing it | Tag |
|---|---|---|---|
| "Speed / fastness / snappiness / performance" surfacing in I1, I2, I3 | PULL (presumed) | 0 verbatim quotes across 3 interviews | **NULL -- not a cluster.** Three notes containing the researcher's word "fast" do not constitute three independent user signals. This is a single signal: the researcher's vocabulary. |
| Trigger events across I1/I2/I3 | (timeline) | 0 | **NULL.** No trigger event was captured in any interview. |
| Old-tool PUSH across I1/I2/I3 | PUSH | 0 | **NULL.** No verbatim PUSH language. |
| ANXIETY about switching | ANXIETY | 0 | **NULL.** Not probed. |
| HABIT keeping users in old tool | HABIT | 0 | **NULL.** Not probed. |

**Strongest defensible cross-interview finding:** the three interviews collectively produce **zero** verbatim-grounded clusters. The round generated process artifacts but not evidence.

A correct STRONG / EMERGING / ANECDOTAL tag requires at minimum 1 verbatim quote per interview in the cluster. The round produces zero. No cluster is eligible to drive a `PROPOSED` block.

---

## 4. Handling the prior assumption -- where it MUST land

The team's prior assumption -- **"users switch to us because our product is faster"** -- entered the round needing either:
(a) confirmation by verbatim quotes from independent users naming speed as the dominant PULL force in their own words, OR
(b) disconfirmation by verbatim quotes naming a different dominant PULL force, OR
(c) an honest gap entry stating we still do not know.

Outcome of Round 1: **(c). The assumption lands in the "We do not have evidence for X" gap subsection.**

It does NOT land:
- in a `D-N` PROPOSED block (would launder paraphrase into a decision)
- in `IMPLEMENTATION_PLAN.md ## Risks and mitigations` as a confirmed force (no quote backing)
- in marketing/positioning copy (the team would be repeating its own vocabulary back to itself via the researcher)

The assumption is **neither confirmed nor disconfirmed by Round 1**. The apparent triple-confirmation across I1, I2, I3 is an artifact of paraphrase, not evidence. Per Step 8 the persona refuses to let absence-of-evidence be treated as evidence-of-absence -- but the symmetric rule also applies: presence-of-paraphrased-agreement is not evidence-of-presence.

---

## 5. We do not have evidence for X (gap subsection -- load-bearing)

The following motivation assumptions survived Round 1 without confirming or disconfirming verbatim quotes and must be carried into Round 2:

1. **"Users switch to our product because it is faster than the incumbent."**
   - Status: UNVERIFIED. Three researcher summaries used speed-adjacent language; zero user quotes captured.
   - Round 2 probe: ask the user "what was the first thing you noticed was different?" -- without offering "speed" as a frame -- and record verbatim.

2. **"Speed/performance is the dominant PULL force."**
   - Status: UNVERIFIED. Cannot be ranked against unmeasured PULL candidates (workflow fit, integrations, pricing, UI clarity, recommendation from peer, mobile access, AI features, reliability).

3. **"The old tool's slowness is the dominant PUSH force."**
   - Status: UNVERIFIED. I2 note says "previous tool was slow" but no user verbatim. PUSH may actually be cost, account changes, a peer recommendation, a failure event, a team mandate, or a feature gap.

4. **The trigger event for each switch.**
   - Status: NOT CAPTURED in any interview. Without the trigger we cannot run the JTBD timeline at all; everything downstream is unanchored.

5. **ANXIETY forces about switching.**
   - Status: NOT PROBED across I1, I2, I3. Likely present (especially I3 -- marketing ops migrations) and entirely invisible to the team.

6. **HABIT forces holding users in the old tool before they switched.**
   - Status: NOT PROBED. We do not know what nearly stopped each user from switching, which is the input the implementation plan needs to design onboarding friction-removal.

7. **Whether "fast" in the team's vocabulary maps to "fast" in the user's vocabulary.**
   - Status: UNVERIFIED. The user may mean "loads instantly," "doesn't crash mid-task," "fewer clicks to get to value," "the AI responds in real time," "doesn't require a meeting to set up." Each of these implies a different roadmap.

---

## 6. PROPOSED blocks for substrate

Per Step 6 and Step 7, PROPOSED blocks must cite the quote bank. Round 1 produced no quote bank. Therefore:

- **`DECISIONS.md ## Locked decisions`:** no `D-N` PROPOSED block this round. Promotion-to-decision is blocked until Round 2 captures verbatim.
- **`IMPLEMENTATION_PLAN.md ## Risks and mitigations`:** no PROPOSED block this round (no verbatim ANXIETY or HABIT to ground a risk on).
- **`TASK_STATE.md ## Observations`:** ONE PROPOSED block (process observation, not a finding):

```
<!-- PROPOSED by jtbd-switch-interviewer: -->
- Round 1 JTBD interviews (I1, I2, I3) were captured as researcher paraphrase, no verbatim quotes. Per Step 4 of the jtbd-switch-interviewer protocol, paraphrase cannot ground four-forces claims because it laundering the team's prior vocabulary back into the evidence. Round 1 produces zero scored forces, zero clusters, and zero D-N drafts. The prior assumption "users switch because our product is faster" is recorded under "We do not have evidence for X" in JTBD_INTERVIEWS.md. Round 2 must re-interview with recording (or near-verbatim notes including quote marks, interview ID, and approximate timestamp) before any decision proposal is unblocked.
```

- **`TASK_STATE.md ## Risks to watch`:** ONE PROPOSED block (methodology risk):

```
<!-- PROPOSED by jtbd-switch-interviewer: -->
- Methodology risk: research process is currently producing paraphrase-only outputs. If Round 2 repeats the same capture pattern, the team will accumulate an interview count without accumulating evidence, and may erroneously treat researcher-vocabulary agreement as user-vocabulary confirmation. Mitigation: require recordings or quote-marked notes for every Round 2 interview; reject any interview write-up with zero verbatim quotes before it enters synthesis.
```

---

## 7. Recommended next action for the round

**Re-run the round.** Specifically:

1. **Do NOT** advance the speed hypothesis to a decision.
2. **Do NOT** add more I4/I5/I6 paraphrase-style notes; that compounds the problem.
3. Re-interview I1, I2, I3 (still within recall window for I2 and I3; I1 at 2 months is on the edge) with:
   - explicit consent to record, OR a typed near-verbatim transcript with quote marks
   - the trigger → struggle → switch timeline script (Step 2)
   - explicit four-forces probes (Step 3), each requiring a quote
   - no leading questions containing the word "fast," "speed," "snappy," or "performance" until the user has used one of those words themselves
4. Only after Round 2 quotes exist, return to this persona for synthesis and PROPOSED decision drafting.

---

### Artifact changes

- `TASK_STATE.md ## Observations`: PROPOSED (Round 1 methodology observation -- see §6).
- `TASK_STATE.md ## Risks to watch`: PROPOSED (paraphrase-laundering methodology risk -- see §6).
- `JTBD_INTERVIEWS.md`: PROPOSED (this synthesis, including the "We do not have evidence for X" gap subsection in §5).
- `DECISIONS.md`: SKIP (no D-N draft this round; refusal-to-propose-from-paraphrase per §0).
- `IMPLEMENTATION_PLAN.md ## Risks and mitigations`: SKIP (no verbatim-grounded risk available this round).

### Command transcript

- Loaded persona SKILL.md; honored Step 4 (verbatim-over-paraphrase) and Step 8 (gap subsection).
- Refused to score four forces or tag clusters from paraphrase-only notes across I1, I2, I3.
- Landed the prior "faster = reason they switched" assumption in the gap subsection, not a decision draft.
- Routed Round 2 re-interview as the only valid next step.

### Handoff

**Next command (Mode A -- compact):** `capture-observation` to promote the PROPOSED `## Observations` and `## Risks to watch` entries in `TASK_STATE.md` once reviewed; then re-run JTBD interviews per §7 before returning to `jtbd-switch-interviewer` for Round 2 synthesis. Do NOT route to `decision-interview` for the speed hypothesis until verbatim quotes exist.

**Run now:** `capture-observation`
