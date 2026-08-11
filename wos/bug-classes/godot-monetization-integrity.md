---
name: godot-monetization-integrity
category: security
default-severity: P0
cwe: [CWE-602]
languages: [gdscript, csharp]
file-patterns: ["**/*.gd", "**/*.tres", "**/*.res", "project.godot", "export_presets.cfg", "**/*.cs", "ProjectSettings/ProjectSettings.asset"]
perspectives: [security]
reversibility-check: false
---

# godot-monetization-integrity

**Scope note (ADR-0130).** Despite the filename, this class is engine-agnostic store-integrity logic and covers Godot and Unity alike. The CWE-602 mechanism (a client-side entitlement decision the server never verified) and every store-rejection case below are store-level, not engine-level. The filename is retained because it is referenced by ADR-0078, by `CHANGELOG.md`, and by `evals/scenarios/89-godot-cluster-deepening.md`, and renaming it would mean rewriting an accepted ADR; the naming debt is recorded in ADR-0130 rather than paid that way. Per ADR-0130 D-3, an engine-agnostic mechanism is widened here, never forked into a per-engine sibling.

## Trigger

Exported GDScript ships as bytecode inside the APK or IPA and decompiles cleanly, so any entitlement the client grants itself is forgeable. The Unity equivalent is the same defect with a different decompiler: Unity's own documentation states that "Local validation is less secure because a malicious user can more easily tamper with code on their own device to bypass the check", and recommends remote validation "for all transactions, and essential for server-delivered content such as granting virtual currency or downloadable items" (https://docs.unity.com/ugs/en-us/manual/iap/manual/receipt-validation). A modified client can call the grant path directly, replay a purchase token, or flip a saved flag. The defect is any client-side entitlement decision (unlocking a purchase, adding premium currency, marking an account premium, removing ads) that is not verified server-side against the store API before it takes effect. The same class covers store-rejection cases that block release or trigger refunds: a Play purchase never acknowledged or consumed within 3 days (auto-refunded by Google), a rewarded-ad reward granted on ad-show instead of on the user_earned_reward callback, a consumable that is granted but never consumed (so it cannot be bought again and is never acknowledged), a non-consumable with no Restore Purchases path (an iOS review rejection), and a bundled SDK not disclosed on the Google Play Data Safety form or in the iOS privacy manifest.

## Detection

Look for:
- Entitlement state mutated directly inside the `purchases_updated` signal handler (godot-google-play-billing) or the StoreKit callback (godot-ios-plugins inappstore, or the cross-platform godot-iap), with no network call: `PlayerData.is_premium = true`, adding currency, unlocking a feature, or writing the grant to a `user://` save.
- A grant that runs on `purchase_state == PURCHASED` without sending the `purchase_token` to a backend that verifies it against the Play Purchases API (Android) or StoreKit 2 signed transactions and the App Store Server API (iOS).
- A rewarded-ad reward granted from an ad-loaded, ad-shown, or ad-closed handler instead of the `user_earned_reward` callback (godot-admob).
- A consumable (coins, gems) granted but with no `consume_purchase(token)` call, or any Play purchase with no `acknowledge_purchase(token)` call inside the 3-day window.
- Non-consumable products (remove-ads, premium unlock) with no Restore Purchases button and no `queryPurchases` path to recover entitlements after a reinstall.
- A plugin added in `export_presets.cfg` or an SDK referenced in `.gd` (ads, analytics, attribution) that is absent from the Data Safety disclosure or from `PrivacyInfo.xcprivacy`, or an Android export not targeting API 35 or higher.

On a Unity target (`**/*.cs`), the same mechanism with Unity call sites:
- Entitlement state mutated directly inside the Unity In-App Purchasing purchase callback, with no network call: a premium flag set, currency added, or a feature unlocked before any backend response. The Unity-specific tell is a grant that runs on local validation alone, which Unity's own docs class as the weaker mode.
- Receipt validation performed on-device only, with the receipt payload never sent to a backend that confirms it against the store's verification service. Unity ships local validation as a supported path, so its presence is not by itself the defect; the defect is a real-money entitlement granted on it with no server confirmation.
- A rewarded-ad reward granted from an ad-loaded, ad-shown, or ad-closed handler rather than the SDK's earned-reward callback, the Unity Ads sibling of the `user_earned_reward` case above.
- A consumable granted with no confirm-pending-purchase step, or a Play purchase left unacknowledged past the 3-day window, which auto-refunds regardless of engine.
- Non-consumable products with no restore path to recover entitlements after a reinstall.
- An SDK present in `Packages/manifest.json` or under `Assets/Plugins/` (ads, analytics, attribution) that is absent from the Google Play Data Safety form or the iOS privacy manifest.

Exclude:
- The grant fires only after a backend verification response returns valid, and the client treats server state as the source of truth.
- Optimistic UI that shows a pending state locally but is reconciled against the server on the next launch (the entitlement itself still comes from the server).
- Cosmetic-only toggles with no real-money value and no store product behind them.

## Retrieval

- The `purchases_updated` handler (or StoreKit callback) and every function it calls up to the state mutation.
- The backend verification call, or its absence, and where the grant waits on its result.
- The `acknowledge_purchase` and `consume_purchase` call sites.
- The rewarded-ad signal wiring and which callback grants the reward.
- The Restore Purchases UI and the `queryPurchases` path.
- `export_presets.cfg` and `project.godot` for the enabled plugin list, plus the Data Safety and `PrivacyInfo.xcprivacy` configuration.

## Analysis prompt

Given the purchase or reward flow:
1. Does the grant (premium flag, currency, feature unlock, save write) run purely client-side inside the billing or ad handler, or does it wait on a backend response?
2. Does a backend verify the `purchase_token` against the store API (Play Purchases API on Android, StoreKit 2 signed transactions or the App Store Server API on iOS) before any entitlement is granted?
3. Is the grant gated on `purchase_state == PURCHASED` and deduped by `purchase_token`, so a replayed or shared token cannot double-grant?
4. Is every Play purchase acknowledged (non-consumables, subscriptions) or consumed (consumables) within 3 days, from the backend right after granting?
5. For rewarded ads, is the reward granted only on the `user_earned_reward` callback, not on ad-load, ad-show, or ad-close?
6. Do non-consumables have a Restore Purchases path, so a reinstall recovers entitlements? (Missing this is an iOS rejection.)
7. Is every bundled SDK disclosed on the Data Safety form and in `PrivacyInfo.xcprivacy`, and is the Android export targeting API 35 or higher?
8. Recommended fix: move the entitlement decision server-side. Send the `purchase_token` to a backend, verify it against the store API, dedupe by token, grant only on `PURCHASED`, and acknowledge or consume within 3 days. Keep the client display-only, and grant ad rewards only on `user_earned_reward`.

## Severity rubric

- P0: an entitlement (premium unlock, currency, remove-ads) is granted client-side with no server-side token verification, so a decompiled or modified client can forge it.
- P1: server verification exists, but a store-rejection defect remains: a purchase never acknowledged or consumed within 3 days, a reward paid on ad-show instead of `user_earned_reward`, a missing Restore Purchases path, or an undisclosed SDK on the Data Safety form or privacy manifest.
- P2: verification and acknowledgement are correct, but a hardening gap remains, such as no Voided Purchases API clawback poll, or dedupe that relies only on a unique constraint with no explicit token check.

## Confidence factors

- HIGH: the grant mutates entitlement state inside `purchases_updated` (or the ad callback) with no network call to a backend.
- MEDIUM: a backend call exists but the grant does not wait on its verified result, or the backend checks only that a receipt is present rather than validating it against the store API.
- LOW: verification is present and the concern is an acknowledge, consume, restore, or disclosure gap rather than the core grant.

## Examples

### Positive (the bug)

```gdscript
func _ready() -> void:
	GodotGooglePlayBilling.purchases_updated.connect(_on_purchases_updated)

func _on_purchases_updated(purchases: Array) -> void:
	for p in purchases:
		# Forgeable: exported GDScript decompiles, so a modified client
		# reaches this path and grants premium with no server proof.
		PlayerData.is_premium = true
		PlayerData.save()  # entitlement written to user:// on the client's word alone
```

### Negative (safe)

```gdscript
func _on_purchases_updated(purchases: Array) -> void:
	for p in purchases:
		if p.purchase_state != 1:  # 1 == PURCHASED in Play Billing
			continue
		# Hand the token to the backend; it verifies against the Play Purchases API.
		Backend.verify_purchase(p.purchase_token, p.products)

func _on_backend_verified(result: Dictionary) -> void:
	# Server verified the token against the store API and deduped by purchase_token.
	if result.valid and result.state == "PURCHASED":
		PlayerData.grant(result.entitlement)
	# Backend acknowledges (non-consumables) or consumes (consumables)
	# within the 3-day window right after granting.
```
