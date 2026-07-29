# GODOT_SCENE_PLAN (fixture: crlf-declaration)

AUTHORED fixture, not an observed artifact. See README.md.

## 7. Dimension and platform fit

```wos-godot-declaration
Dimension: 3D
Renderer tier: Compatibility
```

Written with CRLF line endings. The repo has no .gitattributes, so a plan authored on Windows is a real case. This fixture pins that a well-formed CRLF declaration still reads as one; it never reaches the marker reader, because the marker is only consulted when no block parsed. The malformed CRLF cases that do reach it are crlf-malformed-declaration, crlf-unterminated-declaration, crlf-nested-in-outer-fence, and crlf-tab-indented-waived.
