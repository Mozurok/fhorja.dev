---
name: missing-graceful-degradation
category: resilience
default-severity: P1
cwe: [CWE-755]
languages: [typescript, javascript, python, go]
file-patterns: ["controllers/**", "services/**", "consumers/**", "handlers/**", "api/**"]
perspectives: [operator]
reversibility-check: false
---

# missing-graceful-degradation

## Trigger

A feature depends on an external service (email provider, maps API, analytics, feature flags, CDN) and has no fallback behavior when that service is unavailable. The entire feature or page crashes, shows a blank screen, or returns a 500 error instead of gracefully degrading to a partial or cached state.

## Detection

Look for:
- External API calls whose failure causes the entire request to fail (throw/re-throw in catch without fallback)
- FE components that crash if a data fetch fails (no error boundary, no fallback UI)
- Features where the external dependency is non-essential to the core value (e.g., maps are nice-to-have; driver name + CDL are essential)
- `try/catch` blocks where the catch re-throws or returns 500 instead of returning a degraded response

## Retrieval

- The function calling the external service
- The error handling path (catch block)
- The consumer of this function (to see if it handles the error gracefully)

## Analysis prompt

Given the external dependency:
1. What happens if this service is down for 5 minutes? (crash, blank page, 500, or graceful fallback?)
2. Is this dependency essential to the core value of the feature, or is it enhancement (maps, analytics, rich preview)?
3. If non-essential: what is a reasonable fallback? (cached data, placeholder, partial response, skip silently)
4. If essential: is there a circuit breaker or queued retry that prevents cascading failure?

## Severity rubric

- P0: essential dependency (auth provider, payment gateway) with no fallback and no retry; total feature outage
- P1: enhancement dependency (email, maps, analytics) with no fallback; feature degrades poorly
- P2: dependency with a fallback but the fallback quality is low (empty state instead of cached data)

## Confidence factors

- HIGH: catch block re-throws or returns 500; no fallback value; external service is non-essential
- MEDIUM: catch block logs but the caller does not handle the error (implicit 500 from Express error handler)
- LOW: catch block has a fallback but it may not cover all failure modes

## Examples

### Positive (no degradation)

```typescript
const mapData = await fetch("https://api.mapbox.com/geocoding/...");
if (!mapData.ok) throw new Error("Geocoding failed"); // entire endpoint fails
res.json({ driver, location: await mapData.json() });
```

### Negative (graceful)

```typescript
let locationDisplay = null;
try {
  const mapData = await fetch("https://api.mapbox.com/geocoding/...");
  if (mapData.ok) locationDisplay = await mapData.json();
} catch {
  // Geocoding is non-essential; proceed with lat/lng only
}
res.json({ driver, location: locationDisplay ?? { lat, lng, geocoded: false } });
```
