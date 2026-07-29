# TASK_STATE (fixture)

## Open questions / blockers
tier-declaration waiver: GODOT_SCENE_PLAN.md resumed from before the declaration form landed

An unrelated tilde sample sits in the same file:

~~~gdscript
func _ready():
	pass
~~~

The false-HIDE guard. A fix that treats any tilde fence as swallowing the rest of the file
would silently disable the only escape the floor grants, and no other fixture would catch it.
