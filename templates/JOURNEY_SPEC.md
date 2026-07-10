# Journey: `<journey-name>`

> **Persona(s):** <who takes this journey>
> **Status:** draft | researched | approved
> **Foundation references:** <Foundation sections referenced>
> **Reference benchmarks:** <competitor apps, industry patterns>

---

## 1. Outcome

<What the user achieves at the end of this journey. One sentence.>

## 2. Screens involved

| Order | Screen doc | Route | Purpose in journey |
|---|---|---|---|
| 1 | `screens/<persona>/<NN>-<slug>.md` | `/<route>` | `<what happens here>` |
| 2 | | | |

## 3. Components consumed

<List of design system components used across this journey's screens. Reference by name and tier.>

## 4. Journey map (flow diagram)

```
Start -> Screen 1 -> [Decision?] -> Screen 2a (yes) -> End
                                  -> Screen 2b (no) -> Screen 3 -> End
```

## 5. Critical states

| State | Trigger | UI response | Screen(s) affected | Notes |
|---|---|---|---|---|
| happy path | all inputs valid, network ok | proceed through flow | all | |
| <error state> | <what triggers it> | <what user sees> | <which screen> | |
| <offline state> | no network | <fallback behavior> | <which screen> | |
| <timeout state> | <external dep slow> | <loading / retry UI> | <which screen> | |

## 6. Reference pattern

<What we borrow from (competitor app, design pattern, industry convention) and where we diverge. Why.>

## 7. Accessibility

- **VoiceOver/TalkBack flow:** <focus order across screens, announcements on transitions>
- **Keyboard navigation:** <tab order, enter to submit, escape to dismiss>
- **Reduced Motion:** <animation alternatives for screen transitions>

## 8. Security

<FLAG_SECURE screens, cache purging on logout, screenshot restrictions, idle lock behavior during this journey. "N/A" for non-sensitive journeys.>

## 9. Performance

<Virtualization needs, lazy loading, WebSocket connection management, prefetching strategy.>

## 10. Open questions

<Link to OPEN_QUESTIONS.md entries relevant to this journey.>

## 11. Decisions

| Date | Decision | Rationale | Resolves |
|---|---|---|---|
| `<YYYY-MM-DD>` | `<what>` | `<why>` | `<OPEN_QUESTIONS ID>` |
