---
name: fixture-padded
purpose: scenario 39 control, a prompt under the threshold whose front matter and fenced example push the raw file over it
note: a detector that counted these front matter words or the fenced example below would flag this file, and that would be a false positive
carrier: native Agent path, so the tail names the fleet inbox destination
---
You are a worker dispatched to check one release of a calendar parsing library for changes to how recurring events are expanded. That is your only objective.

## Context

The library turns a recurrence rule into a list of concrete event instances. A storage service downstream stores those instances and shows them to users. When expansion changes, users can lose an instance, gain a phantom one, or see an exception ignored, and none of that shows up as an error anywhere. The service simply stores what the parser gives it.

The people who read your answer are the on-call engineers for the storage service. They are not maintainers of the library, and they will decide from your answer alone whether to roll the new version out, watch it, or hold it. They need to know which instances change and for which kind of rule, and they do not need the history of the code.

The parts of the code that matter are the rule parser, the handling of exceptions and extra dates, the cap on how many instances are expanded for a rule with no end, and the conversion of each instance to the zone of the calendar that owns it.

## Steps

Read the diff between the previous release and the one you were given. For each hunk that touches one of those four parts, record the file, the function, and one sentence on what changes in the list of instances a rule produces. Say whether the changelog mentions the change, and whether a test in the same release covers it.

A change the changelog does not mention is the most useful thing you can report. A change with no test is the second most useful, because the next release can undo it without anyone noticing.

Do not run the code and do not review the rest of the library. If no hunk touches expansion, return an empty list of changes, which is a valid answer.

Here is the shape of one entry, for reference only. It is an example of the fields, not a finding, and none of its values should appear in your answer unless the diff produces them:

```json
{
  "file": "parser/recurrence.py",
  "function": "expand_rule",
  "description": "the cap on instances for a rule with no end moves from five hundred to one thousand, so a daily rule now expands to almost three years of instances instead of about sixteen months, which doubles the rows the storage service writes on first import for every calendar that holds one",
  "changelog_mentions": false,
  "test_added": true,
  "notes": [
    "the exception list is applied before the cap in the new code and after it in the old code",
    "an exception that falls past the old cap was silently ignored before and is honoured now",
    "the zone conversion still happens per instance, so a rule that crosses a daylight saving change keeps its wall clock time",
    "no other hunk in the release touches the rule parser, the exception handling, or the conversion of instances to the owning calendar zone"
  ],
  "recommendation": "roll out with a watch on duplicates",
  "reason": "the cap change is covered by a test and is described in the pull request, but the changelog is silent about it, so the on-call engineers would not have known to watch the first import after the rollout; the ordering change for exceptions has no test of its own and could be undone by a later refactor of the expansion loop without anyone noticing until users report a missing or extra meeting, which is exactly the failure this check exists to catch before it reaches production"
}
```

## Output

Each change is one entry with the fields shown above. Add one top-level field with your recommendation: roll out, roll out with a watch on duplicates, or hold. Choose hold when you are unsure, and put the reason in the entry that made you unsure.

Write one JSON payload matching `worker_output_schema` to fleet_inbox_artifact and nothing else.
