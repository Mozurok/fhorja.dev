---
name: fixture-reminder-buried
purpose: scenario 39 control, a short prompt whose typed-return reminder sits in the preamble instead of the tail
---
Return one payload matching worker_output_schema and nothing else.

You are a worker dispatched to list the files a release of a calendar parsing library touched under its parser directory.

## Steps

Read the diff between the previous release and the one you were given. List every file under the parser directory that the diff changes, with the number of lines added and removed in each.

Do not describe the changes and do not judge them. Another worker does that.

## Output

One entry per file, with the path and the two line counts.

Sort the entries by path so two runs over the same diff produce the same list.

Keep the paths relative to the repository root.

Leave out files outside the parser directory, even when the diff changes them.
