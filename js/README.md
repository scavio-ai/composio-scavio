# @scavio/composio

[Scavio](https://scavio.dev) real-time search tools for [Composio](https://composio.dev) (TypeScript).

Scavio is a single Search API over Google, YouTube, Amazon, Walmart, Reddit, TikTok, and Instagram. This package exposes those endpoints as a Composio custom toolkit so your agents can pull structured, up-to-date results across any Composio-supported framework.

## Install

```bash
npm install @scavio/composio
```

`@composio/core` and `zod` are dependencies. Get a Scavio API key from the [Scavio Dashboard](https://dashboard.scavio.dev) (50 free credits to start, no credit card).

## Usage

```ts
import { Composio } from "@composio/core";
import { buildScavioToolkit } from "@scavio/composio";

const composio = new Composio({ apiKey: process.env.COMPOSIO_API_KEY });

// Build the toolkit; expose only the providers you need.
const scavio = buildScavioToolkit({
  apiKey: process.env.SCAVIO_API_KEY, // or rely on SCAVIO_API_KEY
  enableGoogle: true,
  enableAmazon: true,
  enableTiktok: false,
});

const session = await composio.create("user_1", {
  experimental: { customToolkits: [scavio] },
});

// Hand the agent-ready tools to your framework, or call directly:
const tools = await session.tools();
const out = await session.execute("LOCAL_SCAVIO_GOOGLE_SEARCH", {
  query: "best search API for AI agents",
  light_request: true,
});
console.log(out);
```

Pass `all: true` to register every tool regardless of the individual flags.

## Tools

All tools are grouped under the `SCAVIO` custom toolkit; agent-facing slugs are prefixed `LOCAL_SCAVIO_` (Composio convention for custom tools). Providers: Google, Amazon (search, product), Walmart (search, product), YouTube (search, metadata), Reddit (search, post), TikTok (11 tools), Instagram (12 tools). 32 tools total.

## Credits

Most endpoints cost 1 credit. Reddit and Instagram cost 2 credits each. Google costs 2 credits unless `light_request: true` (1 credit). See [scavio.dev/docs](https://scavio.dev/docs).

## Links

- Scavio: https://scavio.dev
- Docs: https://scavio.dev/docs
- Dashboard: https://dashboard.scavio.dev
