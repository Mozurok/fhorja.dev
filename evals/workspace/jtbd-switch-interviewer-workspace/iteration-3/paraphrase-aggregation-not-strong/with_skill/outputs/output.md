# JTBD Switch-Interview Synthesis -- Paraphrase Round

**Hypothesis under test:** "Users switch from Microsoft Word (OLD) to Notion (NEW) because they want collaboration."

**Methodology gate (Step 4 + Step 5):** Per persona protocol, verbatim user language is load-bearing evidence. Paraphrase is where the team's prior hypothesis sneaks back in. No paraphrase, no matter how many times repeated, upgrades a cluster to STRONG.

---

## 1. Per-interview synthesis

### I1 -- paraphrase only
- Researcher report: user "switched for the collaboration features" and "mentioned how much easier it was to share docs."
- Verbatim quotes captured: **none**.
- Four-forces scoring: **UNSCORABLE**. Per Step 3, no force may be synthesized without at least one verbatim quote. Researcher framing ("switched for the collaboration features") already encodes the team's hypothesis -- we cannot distinguish what the user said from what the researcher heard through the hypothesis lens.
- Timeline reconstruction (trigger -> struggle -> switch): **missing**. No first thought, first conversation, first action captured.

### I2 -- paraphrase only
- Researcher report: "Collaboration came up several times"; user "emphasized real-time editing with their team as the main reason."
- Verbatim quotes captured: **none**.
- Four-forces scoring: **UNSCORABLE**. "Main reason" is a researcher conclusion, not a user sentence. "Real-time editing" is closer to a concrete feature but is still researcher-rendered.
- Timeline reconstruction: **missing**.

### I3 -- paraphrase only
- Researcher report: user "talked about wanting to work with others on the same document"; "Collaboration was central to their decision."
- Verbatim quotes captured: **none**.
- Four-forces scoring: **UNSCORABLE**. "Central to their decision" is a researcher judgement, not user language.
- Timeline reconstruction: **missing**.

---

## 2. Cluster strength assessment

**Naive count:** 3 interviews mention "collaboration." If we counted paraphrases the way we count verbatim quotes, this would tag STRONG (3+ independent interviews).

**Correct tag per persona Step 5 + Step 4:** **ANECDOTAL-equivalent / UNGRADED.**

Reasoning:
1. **Verbatim threshold not met.** STRONG requires 3+ independent verbatim quotes per force. We have zero verbatim quotes across all three interviews. Aggregating paraphrases does not bridge the gap -- it compounds the bias rather than triangulating against it.
2. **Researcher-bias amplification is systematic, not random.** Three different researchers, all briefed on the same team hypothesis ("users switch because they want collaboration"), are statistically likely to hear "collaboration" in user speech that may actually be about something narrower (avoiding email attachments, version-control panic, "I lost my edits"), broader (modern tool aesthetic), or adjacent (sharing read-only links, async commenting, not real-time co-editing). Paraphrase smooths these into the prior.
3. **Hypothesis-echo risk.** The team brief named "collaboration" as the answer. Three paraphrases that conveniently land on "collaboration" without a single user sentence is the canonical pattern of laundering a prior through the interview round -- exactly the failure mode this persona exists to catch.
4. **"Collaboration" is a researcher word, not typically a user word.** Users say things like "I kept emailing the wrong version" or "my co-founder couldn't see my edits until Monday" or "we were both editing and it overwrote my changes." Absence of that texture in any of three reports is itself a signal that paraphrase compression occurred.

**Cluster tag:** Cannot be promoted above ANECDOTAL. Treated as **UNGRADED -- insufficient evidentiary form** for PROPOSED decision drafting.

---

## 3. "We do not have evidence for X" (Step 8)

This round leaves the following motivation assumptions **unconfirmed and undisconfirmed**:
- Whether the PUSH from Word was collaboration-related at all, vs. document-loss anxiety, formatting fatigue, file-sync friction, or platform/OS friction.
- Whether the PULL toward Notion was real-time co-editing specifically, vs. share-link convenience, block-based structure, database features, or aesthetic/modern-tool signaling.
- Whether ANXIETY forces (data migration cost, team training, lock-in, formatting loss when exporting) were present and how they were overcome.
- Whether HABIT forces (Word muscle memory, .docx as the corporate exchange format, Track Changes workflows with legal/external parties) were resolved or worked around.
- The trigger event that started the switch evaluation in each case.

---

## 4. PROPOSED blocks

**None drafted.** Per persona Definition of Done, no ANECDOTAL cluster may drive a PROPOSED decision. Promoting a D-N draft on paraphrase aggregation would violate Step 5 and Step 6 explicitly. Drafting a PROPOSED block here would be the exact "laundering the team's prior hypothesis through paraphrased 'users seem to want' prose" failure named in the persona's Quality bar.

---

## 5. Recommended next action

**Re-run the interview round under verbatim discipline before any PROPOSED decision lands.**

Concretely:
1. Re-contact I1, I2, I3 (or three fresh subjects matched on the same switch event) with the canonical switch-interview script anchored on **trigger -> struggle -> switch** timeline.
2. Researchers MUST capture exact user sentences inside quote marks, with interview ID and approximate timestamp, per Step 4. No paraphrase substitutes.
3. Brief researchers explicitly **not** to use the word "collaboration" in any probe -- let the user produce the noun. If three users independently produce "collaboration" or a tight semantic neighbor (e.g., "edit together," "see each other's changes"), that is real triangulation; if they produce different nouns ("share," "send," "comment," "version"), the hypothesis was over-compressed.
4. Score the four forces (PUSH / PULL / ANXIETY / HABIT) per interview with at least one verbatim quote per force claim.
5. Only then re-evaluate cluster strength and consider PROPOSED D-N drafts.

**Recommended next command:** `jtbd-switch-interviewer` (re-run with verbatim capture protocol). Do not route to `decision-interview` or `approve-proposed` until verbatim evidence exists.

---

## Command transcript
- Loaded persona SKILL.md; applied Step 4 (verbatim > paraphrase) and Step 5 (cluster strength) as gating rules.
- Refused to upgrade 3 paraphrases to STRONG; refused to draft PROPOSED D-N block on ungraded evidence.
- Logged surviving motivation assumptions under "We do not have evidence for X" per Step 8.

## Handoff
**Run now:** `jtbd-switch-interviewer` -- re-execute the round with verbatim quote capture and timeline anchoring before any decision promotion.