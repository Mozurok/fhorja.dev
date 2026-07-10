# Style Dictionary Integration Pattern

> How to set up [Style Dictionary](https://amzn.github.io/style-dictionary/) to transform W3C DTCG tokens into platform-specific outputs.

## Overview

```
tokens/*.json (W3C DTCG)
       │
       ▼
  Style Dictionary
  (style-dictionary.config.json)
       │
       ├──► CSS custom properties  (web)
       ├──► Tailwind config        (web)
       ├──► TypeScript constants    (React Native)
       ├──► Swift constants         (iOS native)
       └──► Android XML resources   (Android native)
```

## Setup

### 1. Install

```bash
npm install -D style-dictionary
```

### 2. Config file

Create `style-dictionary.config.json` at the project root (or `packages/design-system/`):

```json
{
  "source": ["tokens/**/*.json"],
  "platforms": {
    "css": {
      "transformGroup": "css",
      "buildPath": "packages/design-system/src/generated/css/",
      "files": [{
        "destination": "tokens.css",
        "format": "css/variables"
      }]
    },
    "tailwind": {
      "transformGroup": "js",
      "buildPath": "packages/design-system/src/generated/tailwind/",
      "files": [{
        "destination": "tokens.js",
        "format": "javascript/module-flat"
      }]
    },
    "rn": {
      "transformGroup": "react-native",
      "buildPath": "packages/design-system/src/generated/rn/",
      "files": [{
        "destination": "tokens.ts",
        "format": "javascript/es6"
      }]
    }
  }
}
```

### 3. Build script

Add to `package.json`:

```json
{
  "scripts": {
    "tokens:build": "style-dictionary build",
    "tokens:clean": "style-dictionary clean"
  }
}
```

### 4. Run

```bash
npm run tokens:build
```

This generates platform-specific token files from the DTCG JSON source.

## CI integration

Add `npm run tokens:build` to your CI pipeline after any change to `tokens/*.json`. The generated files should be committed (so downstream consumers do not need Style Dictionary installed) or generated at build time (if the project prefers).

## Figma sync (optional)

If using Tokens Studio:
1. Export Figma variables as DTCG JSON via Tokens Studio plugin
2. Commit the JSON to `tokens/*.json`
3. Run `npm run tokens:build` to regenerate platform outputs
4. PR review catches any visual regressions via Storybook + Chromatic

## Migration from .ts tokens

If the project currently uses `.ts` token files:
1. Create the DTCG JSON equivalent (use `templates/TOKEN_FILE.json` as starting point)
2. Configure Style Dictionary to generate `.ts` output matching the old format
3. Replace imports project-wide (from hand-written to generated)
4. Delete the old `.ts` token files
5. The `token-format-not-dtcg` bug class will stop flagging once migration is complete
