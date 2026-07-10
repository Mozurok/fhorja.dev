---
name: xss-via-unescaped-output
category: security
default-severity: P0
cwe: [CWE-79]
languages: [typescript, javascript, python]
file-patterns: ["**/*.tsx", "**/*.jsx", "**/*.html", "**/*.ejs", "**/*.hbs", "controllers/**"]
perspectives: [security]
reversibility-check: false
---

# xss-via-unescaped-output

## Trigger

User-controlled input is rendered into HTML without proper escaping or sanitization, allowing an attacker to inject arbitrary JavaScript that executes in the victim's browser. This includes: server-rendered HTML templates with raw interpolation, React `dangerouslySetInnerHTML`, and inline HTML construction in backend email templates.

## Detection

Look for:
- Template literals or string concatenation that embed user input directly into HTML: `` `<div>${userInput}</div>` ``
- React's `dangerouslySetInnerHTML={{ __html: userControlledValue }}`
- Server-side template engines with raw/unescaped output: `{{{ variable }}}` (Handlebars), `| raw` (Jinja2), `<%- variable %>` (EJS)
- Backend-constructed HTML email bodies that interpolate user input (recipient name, custom messages)

Exclude:
- React JSX expressions `{variable}` (auto-escaped by React)
- Values from trusted internal sources (config, constants, DB-derived IDs)
- Content already sanitized via DOMPurify, sanitize-html, or equivalent

## Retrieval

- The file and function where unescaped rendering occurs
- The source of the variable being rendered (to verify if user-controlled)

## Analysis prompt

Given the unescaped output:
1. Is the rendered value user-controlled (comes from request params, DB field written by users, form input)?
2. If user-controlled: can an attacker inject `<script>`, event handlers (`onerror=`), or other executable HTML?
3. Does the rendering context auto-escape (React JSX does; template literal HTML does not)?
4. Recommended fix: use framework escaping, sanitization library, or `textContent` instead of `innerHTML`.

## Severity rubric

- P0: user-controlled value rendered as raw HTML in a page accessible to other users (stored XSS) or in an email body (email XSS)
- P1: user-controlled value rendered as raw HTML but only visible to the same user (self-XSS, lower impact)
- P2: value is not truly user-controlled but the pattern is unsafe and could become exploitable if the data source changes

## Confidence factors

- HIGH: template literal HTML or `dangerouslySetInnerHTML` with a value traced back to user input (request param, DB user-writable field)
- MEDIUM: value comes from DB but the column is writable by admins only (trusted but not hardened)
- LOW: value is from a trusted source (config, constant) but the rendering pattern is risky if the source ever changes

## Examples

### Positive (XSS)

```typescript
const html = `<p>Hello ${recipientName}</p>`;
// If recipientName = '<script>alert(1)</script>', the script executes
```

### Negative (safe)

```tsx
<p>Hello {recipientName}</p>
// React auto-escapes JSX expressions; script tags render as text
```
