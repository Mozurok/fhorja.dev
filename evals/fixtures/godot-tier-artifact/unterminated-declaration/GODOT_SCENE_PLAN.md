# GODOT_SCENE_PLAN (fixture: unterminated-declaration)

AUTHORED fixture, not an observed artifact. See README.md.

## 5. Scene tree

```gdscript
func _ready():
	pass

## 7. Dimension and platform fit

```wos-godot-declaration
Dimension: 3D
Renderer tier: Forward+
```

An earlier gdscript fence is never closed, which Step 2 invites by asking for scene and script samples. The declaration's own closing fence pops the stray one instead, so no body is collected. It carries a waiver in TASK_STATE.md: the marker is present, so this is MALFORMED and the waiver must NOT clear it.
