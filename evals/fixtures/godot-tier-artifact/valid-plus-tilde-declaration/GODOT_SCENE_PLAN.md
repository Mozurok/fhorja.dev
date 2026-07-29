# GODOT_SCENE_PLAN (fixture: valid-plus-tilde-declaration)

AUTHORED fixture, not an observed artifact. See README.md.

## 7. Dimension and platform fit

```wos-godot-declaration
Dimension: 2D
```

A second, tilde-fenced declaration follows later in the same plan:

~~~wos-godot-declaration
Dimension: 3D
Renderer tier: Mobile
~~~

One parseable block plus one marker that produced none is two declarations, one of them broken:
the same ambiguity `double-declaration` blocks on. A scanner that stops at the first good block
grades this `pass` and lets the plan claim whichever target the reader happens to read first.
