# composio-scavio

[Scavio](https://scavio.dev) real-time search tools for [Composio](https://composio.dev), in both Python and TypeScript.

Scavio is a single Search API over Google, YouTube, Amazon, Walmart, Reddit, TikTok, and Instagram. This repo exposes those endpoints as a Composio custom toolkit so your agents can pull structured, up-to-date results across any Composio-supported framework.

## Packages

| Language | Package | Directory | Install |
|----------|---------|-----------|---------|
| Python | [`composio-scavio`](https://pypi.org/project/composio-scavio/) (PyPI) | [`python/`](./python) | `pip install composio-scavio` |
| TypeScript | [`@scavio/composio`](https://www.npmjs.com/package/@scavio/composio) (npm) | [`js/`](./js) | `npm install @scavio/composio` |

Both expose the same 32 tools under a `SCAVIO` custom toolkit, gated per provider, wrapping the official Scavio SDK.

## Quick start

Python:

```python
from composio import Composio
from composio_scavio import build_scavio_toolkit

composio = Composio()
scavio = build_scavio_toolkit(api_key="sk_...")  # or SCAVIO_API_KEY
session = composio.create(user_id="u1", experimental={"custom_toolkits": [scavio]})
```

TypeScript:

```ts
import { Composio } from "@composio/core";
import { buildScavioToolkit } from "@scavio/composio";

const composio = new Composio();
const scavio = buildScavioToolkit({ apiKey: process.env.SCAVIO_API_KEY });
```

See each package's README for full usage. Get an API key at the [Scavio Dashboard](https://dashboard.scavio.dev) (50 free credits to start, no credit card).

## Publishing

Pushing to `main` triggers `.github/workflows/publish.yml`, which publishes the Python package to PyPI and the TypeScript package to npm. Each job is a no-op unless its `version` is new, so bump the version in `python/pyproject.toml` and/or `js/package.json` to release.

## Composio catalog

The official catalog listing is tracked in [`SUBMISSION.md`](./SUBMISSION.md). `scavio-openapi.json` is the API spec for that submission (regenerate with `bun run openapi:export` in the backend).

## Links

- Scavio: https://scavio.dev
- Docs: https://scavio.dev/docs
- Dashboard: https://dashboard.scavio.dev
