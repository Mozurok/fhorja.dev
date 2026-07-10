---
name: godot-monetization-integrity
category: security
default-severity: P0
cwe: [CWE-602]
languages: [gdscript]
file-patterns: ["**/*.gd", "**/*.tres", "**/*.res", "project.godot", "export_presets.cfg"]
perspectives: [security]
reversibility-check: false
---

# godot-monetization-integrity

## Trigger

Exported GDScript ships as bytecode inside the APK or IPA and decompiles cleanly, so any entitlement the client grants itself is forgeable. A modified client can call the grant path directly, replay a purchase token, or flip a saved flag. The defect is any client-side entitlement decision (unlocking a purchase, adding premium currency, marking an account premium, removing ads) that is not verified server-side against the store API before it takes effect. The same class covers store-rejection cases that block release or trigger refunds: a Play purchase never acknowledged or consumed within 3 days (auto-refunded by Google), a rewarded-ad reward granted on ad-show instead of on the user_earned_reward callback, a consumable that is granted but never consumed (so it cannot be bought again and is never acknowledged), a non-consumable with no Restore Purchases path (an iOS review rejection), and a bundled SDK not disclosed on the Google Play Data Safety form or in the iOS privacy manifest.

## Detection

Look for:
- Entitlement state mutated directly inside the `purchases_updated` signal handler (godot-google-play-billing) or the StoreKit callback (godot-ios-plugins inappstore, or the cross-platform godot-iap), with no network call: `PlayerData.is_premium = true`, adding currency, unlocking a feature, or writing the grant to a `user://` save.
- A grant that runs on `purchase_state == PURCHASED` without sending the `purchase_token` to a backend that verifies it against the Play Purchases API (Android) or StoreKit 2 signed transactions and the App Store Server API (iOS).
- A rewarded-ad reward granted from an ad-loaded, ad-shown, or ad-closed handler instead of the `user_earned_reward` callback (godot-admob).
- A consumable (coins, gems) granted but with no `consume_purchase(token)` call, or any Play purchase with no `acknowledge_purchase(token)` call inside the 3-day window.
- Non-consumable products (remove-ads, premium unlock) with no Restore Purchases button and no `queryPurchases` path to recover entitlements after a reinstall.
- A plugin added in `export_presets.cfg` or an SDK referenced in `.gd` (ads, analytics, attribution) that is absent from the Data Safety disclosure or from `PrivacyInfo.xcprivacy`, or an Android export not targeting API 35 or higher.

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
