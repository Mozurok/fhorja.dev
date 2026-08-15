# bug-class-dispatch (synthetic)

Every file in this tree is fixture data. There is no real application here, no
real client, no real host, and no real credential. It exists so that Fhorja's
`repo-consistency-sweep` can be run end to end against five security bug classes
and the findings compared against a written answer key.

The one prompt-injection sample in this tree is inert by construction: it points
at a file that does not exist, the only network destination uses the reserved
`.invalid` TLD, and the only config write targets a filename that is obviously
not a real agent config. Nothing inside this tree is a directive to whoever or
whatever is reading it.

The answer key lives outside this tree, in the Fhorja repository at
`evals/fixtures/bug-class-dispatch/README.md`.
