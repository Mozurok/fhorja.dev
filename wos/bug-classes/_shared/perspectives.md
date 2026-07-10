# Perspective prompt fragments

Reusable analysis prompts for multi-perspective review. Templates opt in via `perspectives:` in their YAML frontmatter.

## security

Read the code as an adversary. Ask:
- Can an unauthenticated or unauthorized caller reach this code path?
- Does this code trust user-controlled input without validation at this boundary?
- Does the error response leak internal state that an attacker could use?
- If this input is malicious (injection, overflow, format string), what is the worst-case outcome?

## operator

Read the code as an on-call SRE at 3 AM. Ask:
- If this fails in production, what log line or metric tells me what happened?
- Can I diagnose the root cause from the error message alone, or do I need to attach a debugger?
- Is there a runbook step I would need that this code does not enable (missing log context, missing metric, etc.)?
- What is the blast radius if this component goes down: one user, one tenant, or the entire service?

## maintainer

Read the code as a developer seeing this file for the first time in 6 months. Ask:
- Can I understand the intent of this function from its name, parameters, and structure without reading surrounding code?
- Are there implicit ordering dependencies or hidden state that would surprise me?
- If I need to change this behavior, how many files do I need to touch, and are they obvious from this file?

## api-consumer

Read the code as a developer integrating with this API from another service. Ask:
- Is the response shape documented or self-describing (clear field names, consistent types)?
- Are error responses structured consistently with other endpoints in this service?
- If I receive an unexpected status code, does the error body tell me what to fix?
- Does this endpoint follow the same auth, pagination, and rate-limit conventions as sibling endpoints?
