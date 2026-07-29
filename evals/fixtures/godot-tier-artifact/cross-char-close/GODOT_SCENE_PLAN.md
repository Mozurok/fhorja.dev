# GODOT_SCENE_PLAN (fixture: cross-char-close)

AUTHORED fixture, not an observed artifact. See README.md.

## 7. Dimension and platform fit

```wos-godot-declaration
Dimension: 3D
Renderer tier: Forward+
~~~

A backtick declaration fence whose closing line is written in tildes. A fence closes only with
its own character, so this one never closes, no body is collected, and the marker on the page
makes it MALFORMED. A scanner that merely admits tildes without tracking WHICH character opened
the block grades this `pass`, and the whole fixture set still looks green.
