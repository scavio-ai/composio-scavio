# composio-scavio

[Scavio](https://scavio.dev) real-time search tools for [Composio](https://composio.dev).

Scavio is a single Search API over Google, YouTube, Amazon, Walmart, Reddit, TikTok, and Instagram. This package exposes those endpoints as a Composio custom toolkit so your agents can pull structured, up-to-date results across any Composio-supported framework (OpenAI, Anthropic, LangChain, CrewAI, and more).

## Install

```bash
pip install composio-scavio
```

## Setup

Get a Scavio API key from the [Scavio Dashboard](https://dashboard.scavio.dev) (new accounts get 50 free credits to start, no credit card). Set it as an environment variable or pass it directly.

```bash
export SCAVIO_API_KEY=sk_...
export COMPOSIO_API_KEY=...   # from https://app.composio.dev
```

## Usage

```python
from composio import Composio
from composio_scavio import build_scavio_toolkit

composio = Composio()

# Build the toolkit; expose only the providers you need.
scavio = build_scavio_toolkit(
    api_key="sk_...",        # or rely on SCAVIO_API_KEY
    enable_google=True,
    enable_amazon=True,
    enable_tiktok=False,
)

session = composio.create(
    user_id="user_1",
    experimental={"custom_toolkits": [scavio]},
)

result = session.tools.execute(
    "SCAVIO_GOOGLE_SEARCH",
    arguments={"query": "best search API for AI agents", "light_request": True},
)
print(result)
```

Pass `all=True` to register every tool regardless of the individual flags.

## Tools

All tools are namespaced under the `SCAVIO` toolkit. Each provider is gated by an `enable_*` flag.

| Provider | Tools |
|----------|-------|
| Google | `SCAVIO_GOOGLE_SEARCH` |
| Amazon | `SCAVIO_AMAZON_SEARCH`, `SCAVIO_AMAZON_PRODUCT` |
| Walmart | `SCAVIO_WALMART_SEARCH`, `SCAVIO_WALMART_PRODUCT` |
| YouTube | `SCAVIO_YOUTUBE_SEARCH`, `SCAVIO_YOUTUBE_METADATA` |
| Reddit | `SCAVIO_REDDIT_SEARCH`, `SCAVIO_REDDIT_POST` |
| TikTok | `SCAVIO_TIKTOK_PROFILE`, `SCAVIO_TIKTOK_USER_POSTS`, `SCAVIO_TIKTOK_VIDEO`, `SCAVIO_TIKTOK_VIDEO_COMMENTS`, `SCAVIO_TIKTOK_COMMENT_REPLIES`, `SCAVIO_TIKTOK_SEARCH_VIDEOS`, `SCAVIO_TIKTOK_SEARCH_USERS`, `SCAVIO_TIKTOK_HASHTAG`, `SCAVIO_TIKTOK_HASHTAG_VIDEOS`, `SCAVIO_TIKTOK_USER_FOLLOWERS`, `SCAVIO_TIKTOK_USER_FOLLOWINGS` |
| Instagram | `SCAVIO_INSTAGRAM_PROFILE`, `SCAVIO_INSTAGRAM_USER_POSTS`, `SCAVIO_INSTAGRAM_USER_REELS`, `SCAVIO_INSTAGRAM_USER_TAGGED`, `SCAVIO_INSTAGRAM_USER_STORIES`, `SCAVIO_INSTAGRAM_POST`, `SCAVIO_INSTAGRAM_POST_COMMENTS`, `SCAVIO_INSTAGRAM_COMMENT_REPLIES`, `SCAVIO_INSTAGRAM_SEARCH_USERS`, `SCAVIO_INSTAGRAM_SEARCH_HASHTAGS`, `SCAVIO_INSTAGRAM_USER_FOLLOWERS`, `SCAVIO_INSTAGRAM_USER_FOLLOWINGS` |

## Credits

Most endpoints cost 1 credit. Reddit and Instagram cost 2 credits each. Google costs 2 credits unless `light_request=true` (1 credit). See [scavio.dev/docs](https://scavio.dev/docs).

## Links

- Scavio: https://scavio.dev
- Docs: https://scavio.dev/docs
- Dashboard: https://dashboard.scavio.dev
