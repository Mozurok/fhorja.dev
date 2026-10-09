**Digest fallback when the canonical helper is unreachable.** `sha_of_section` extracts a section's body with `awk` and pipes it to `shasum -a 256`. A run inside a permission boundary that admits `shasum` but refuses `awk` and `sed` cannot invoke that helper, and MUST NOT reimplement it. Assume the helper is unreachable whenever the workflow repository's `scripts/` directory is not readable from the working directory.

WHERE the canonical per-section digest helper is unreachable, the write SHALL use a whole-file SHA-256 and SHALL declare the reduced scope:

```bash
# One call per file. Read the hash (the first field) out of the output;
# do not pipe it through `cut` or `awk` to trim it.
shasum -a 256 TASK_STATE.md
```

Then add `"sha_scope":"file"` to that JSONL line, so a validator distinguishes a file digest from a section digest. The rest of the protocol is unchanged: the transaction header still goes above the section heading, and there is exactly one JSONL line per section write.

Do NOT rebuild the helper by writing each section out as its own file to hash it separately.

At file scope two sections written in the same run share a digest, so the `sha_scope` field is mandatory, not optional.
