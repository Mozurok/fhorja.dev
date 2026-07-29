# GODOT_SCENE_PLAN (fixture: unterminated-tilde-sample)

AUTHORED fixture, not an observed artifact. See README.md.

## 5. Scene tree

~~~gdscript
func _ready():
	pass

## 7. Dimension and platform fit

```wos-godot-declaration
Dimension: 3D
Renderer tier: Forward+
```

The tilde twin of `unterminated-declaration`: an earlier `~~~gdscript` fence is never closed, so
the declaration below it is content of that block and no body is collected. The marker is
present, so this is MALFORMED and the waiver in TASK_STATE.md must not clear it.
