---
name: unity-destroyed-object-null-check
category: type-safety
default-severity: P1
cwe: [CWE-480, CWE-476]
languages: [csharp]
file-patterns: ["**/*.cs"]
perspectives: [maintainer]
reversibility-check: false
---

# unity-destroyed-object-null-check

Unity-scoped by mechanism: the defect exists because `UnityEngine.Object` overloads `==`, so single-stack for the same reason as its two siblings (ADR-0130 D-3 carve-out).

## Trigger

`UnityEngine.Object` overloads the equality operator: "In addition to checking if the managed object reference is `null`, the custom `==` operator in `UnityEngine.Object` also checks if the underlying native object pointer is null", and "If either is true, `== null` evaluates to `true`" (https://docs.unity3d.com/ScriptReference/Object-operator_eq.html).

A destroyed Unity object therefore lives on in a detached state: the native counterpart is gone, the managed reference persists, and only the overloaded `==` reports it as null. `Object.ReferenceEquals`, C#'s `is null` pattern, and the null-propagating `?.` and `??` operators all bypass the overload and see a live reference.

The defect is any null check on a `UnityEngine.Object` (a `GameObject`, `Component`, `MonoBehaviour`, `Transform`, `Renderer`, `ScriptableObject`, and so on) that uses `is null`, `is not null`, `?.`, `??`, `??=`, or `ReferenceEquals` instead of `==` or `!=`.

This class is worth carrying specifically because idiomatic modern C# pushes toward the wrong answer. Analyzers, style guides, and habit all favour `?.` and `is null`; every one of them is incorrect on a Unity object. The symptom is a `MissingReferenceException` or a silently skipped branch, appearing far from the `Destroy` call that caused it.

## Detection

Look for:
- `is null` or `is not null` applied to a variable whose type derives from `UnityEngine.Object`.
- `?.`, `?[`, `??`, or `??=` on such a variable, especially in `Update`, `LateUpdate`, `FixedUpdate`, a coroutine body, or an event or signal handler, where the target can be destroyed between frames.
- `ReferenceEquals(x, null)` on a Unity object.
- A cached reference (a field assigned in `Awake` or `Start`) used later with no `==` guard, in a class whose targets are destroyed at runtime (pooled enemies, spawned projectiles, UI torn down on scene change).
- A null-coalescing default such as `_target ??= FindTarget()`, which never re-resolves after `_target` is destroyed because the managed reference is still non-null to `??=`.

Exclude:
- Plain C# types that do not derive from `UnityEngine.Object` (a POCO, a `struct`, a `string`, a plain interface implementation), where `is null` and `?.` are correct and preferable.
- An interface-typed variable whose implementations are all non-Unity types.
- A deliberate `ReferenceEquals` used to detect the detached state on purpose, with a comment saying so.

## Retrieval

- Every null check in the changed files, with the declared type of each checked variable.
- The declaration site of each checked variable, to resolve whether its type derives from `UnityEngine.Object`.
- The `Destroy` and `DestroyImmediate` call sites in the same feature, and the lifetime between assignment and use.
- Any object-pooling or scene-unload path that destroys the referenced objects.

## Analysis prompt

Given the changed C#:
1. For each null check, does the checked variable's type derive from `UnityEngine.Object`?
2. If so, does the check use `==` or `!=`, or does it use `is null`, `?.`, `??`, `??=`, or `ReferenceEquals`?
3. Can the referenced object be destroyed between the moment the reference is stored and the moment it is used (pooling, scene unload, an explicit `Destroy`)?
4. Would the wrong operator here fail loudly with a `MissingReferenceException`, or silently by taking a branch that assumes the object is alive?
5. Recommended fix: use `== null` and `!= null` for anything deriving from `UnityEngine.Object`, and reserve `is null` and `?.` for plain C# types. Where a codebase wants the modern syntax uniformly, the deliberate alternative is an explicit helper whose name says which semantics it applies.

## Severity rubric

- P0: the wrong operator guards a destroyed object on a per-frame path, so the failure is a runtime exception every frame or a gameplay branch that silently never runs.
- P1: the wrong operator is used on a Unity object whose destruction is possible but not per-frame (scene change, pooling return).
- P2: the wrong operator is used on a Unity object that is never destroyed during its lifetime, so the defect is latent rather than active.

## Confidence factors

- HIGH: `is null` or `?.` on a variable whose declared type is a known `UnityEngine.Object` subclass, on a path that also calls `Destroy`.
- MEDIUM: the operator is wrong but the declared type is an interface or generic whose Unity derivation cannot be confirmed from the diff.
- LOW: the checked type is ambiguous and no destruction path is visible in the retrieved code.

## Examples

### Positive (the bug)

```csharp
private Enemy _target;

void Update()
{
    // Wrong twice. `?.` bypasses the overloaded operator, so a destroyed
    // _target is still non-null here and Follow() throws
    // MissingReferenceException. `??=` never re-resolves for the same reason.
    _target ??= FindClosestEnemy();
    _target?.Follow(transform.position);
}

void OnEnemyKilled(Enemy e)
{
    // `is null` sees the detached managed reference as alive, so the
    // re-acquire branch silently never runs.
    if (_target is null) _target = FindClosestEnemy();
}
```

### Negative (not the bug)

```csharp
private Enemy _target;

void Update()
{
    // `==` consults the native pointer, so a destroyed _target reads as
    // null and the reference is re-acquired.
    if (_target == null) _target = FindClosestEnemy();
    if (_target != null) _target.Follow(transform.position);
}

// Plain C# type: `is null` and `?.` are correct here and stay.
private IScoreFormatter _formatter;
string Format(int n) => _formatter?.Format(n) ?? n.ToString();
```
