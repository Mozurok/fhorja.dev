---
name: dockerfile-security-risk
category: infrastructure
default-severity: P1
cwe: [CWE-250]
languages: []
file-patterns: ["**/Dockerfile", "**/Dockerfile.*", "**/*.dockerfile"]
perspectives: [security, operator]
reversibility-check: false
---

# dockerfile-security-risk

## Trigger

A Dockerfile contains patterns that increase the attack surface of the built container: running as root, including secrets in build args or layers, using a bloated base image without multi-stage build, or pinning to `latest` tag (non-reproducible builds).

## Detection

Look for:
- No `USER` instruction (container runs as root by default)
- `ARG` or `ENV` with secret-like names (`API_KEY`, `PASSWORD`, `TOKEN`, `SECRET`) baked into the image
- `COPY . .` without `.dockerignore` (may include `.env`, `.git`, `node_modules`)
- `FROM node:latest` or `FROM python:latest` (unpinned; non-reproducible)
- No multi-stage build when the final image includes build tools (gcc, make, dev dependencies)
- `RUN apt-get install` without `--no-install-recommends` (bloated image)

## Retrieval

- The Dockerfile
- `.dockerignore` (if present)
- `docker-compose.yml` (if present, for env/secret handling)

## Analysis prompt

Given the Dockerfile:
1. Does the container run as root or a non-root user?
2. Are any secrets baked into build args or environment variables visible in the image layers?
3. Is there a `.dockerignore` preventing `.env`, `.git`, and `node_modules` from being copied?
4. Is the base image pinned to a specific version/digest?
5. Is multi-stage build used to exclude build tools from the final image?

## Severity rubric

- P0: secrets baked into image layers (recoverable via `docker history`)
- P1: running as root; no `.dockerignore` with `.env` likely copied; unpinned base image
- P2: missing multi-stage build or `--no-install-recommends` (image size, not security)

## Confidence factors

- HIGH: `ARG SECRET_KEY` or `ENV API_KEY=sk_live_...` visible in Dockerfile
- MEDIUM: no `USER` instruction and no `.dockerignore` file exists
- LOW: `FROM node:20` (pinned to major but not digest; acceptable for most teams)

## Examples

### Positive (risky)

```dockerfile
FROM node:latest
COPY . .
RUN npm install
CMD ["node", "dist/index.js"]
```

### Negative (hardened)

```dockerfile
FROM node:20-slim AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev
COPY src/ src/
RUN npm run build

FROM node:20-slim
RUN addgroup --system app && adduser --system --ingroup app app
USER app
WORKDIR /app
COPY --from=build /app/dist ./dist
COPY --from=build /app/node_modules ./node_modules
CMD ["node", "dist/index.js"]
```
