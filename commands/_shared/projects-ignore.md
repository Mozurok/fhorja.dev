WHEN this run creates the `projects/` directory itself in the task repository, it writes `projects/.gitignore` in the same batch, holding the single line `*` (ADR-0223). That line ignores everything under `projects/`, the file included, so task memory stays out of the product repository's history without touching a file the user owns. List it `APPLIED` in `### Artifact changes`.
- Never edit the repository's own `.gitignore`.
- Never write `projects/.gitignore` into a `projects/` that already exists. A user who deleted it chose to track the tree.
- Write it outside a git repository too, so a later `git init` inherits the rule.
