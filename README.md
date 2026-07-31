# composio-scavio

[Scavio](https://scavio.dev) real-time search tools for [Composio](https://composio.dev).

Scavio is a single Search API over Google, YouTube, Amazon, Walmart, Reddit, TikTok, and Instagram. This package exposes those endpoints as a Composio custom toolkit so your agents can pull structured, up-to-date results across any Composio-supported framework (OpenAI, Anthropic, LangChain, CrewAI, and more).

> **Amazon changed (breaking).** The upstream provider moved in 2026-07:
> `domain` is replaced by `country`, a two-letter marketplace code (`us`, `gb`
> -- the UK is `gb`, not `uk` -- `de`, `jp`, ...), and `sort_by`, `pages`,
> `category_id`, `merchant_id`, `language`, `currency`, `device`, `zip_code`
> and `autoselect_variant` are gone. The marketplace ignores all of them
> (`sort_by` returns the identical unordered set for every value), so they are
> removed rather than kept as silent no-ops. Rank and filter results yourself.

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
    arguments={"query": "best search API for AI agents", "country_code": "us"},
)
print(result)
```

Pass `all=True` to register every tool regardless of the individual flags.

## Tools

All tools are namespaced under the `SCAVIO` toolkit. Each provider is gated by an `enable_*` flag.

| Provider | Tools |
|----------|-------|
| Google | `SCAVIO_GOOGLE_SEARCH` |
| Amazon | `SCAVIO_AMAZON_SEARCH`, `SCAVIO_AMAZON_PRODUCT`, `SCAVIO_AMAZON_OFFERS` |
| Walmart | `SCAVIO_WALMART_SEARCH`, `SCAVIO_WALMART_PRODUCT` |
| YouTube | `SCAVIO_YOUTUBE_SEARCH`, `SCAVIO_YOUTUBE_SHORTS`, `SCAVIO_YOUTUBE_SUGGESTIONS`, `SCAVIO_YOUTUBE_VIDEO`, `SCAVIO_YOUTUBE_METADATA`, `SCAVIO_YOUTUBE_COMMENTS`, `SCAVIO_YOUTUBE_COMMENT_REPLIES`, `SCAVIO_YOUTUBE_TRANSCRIPT`, `SCAVIO_YOUTUBE_RELATED`, `SCAVIO_YOUTUBE_CHANNEL_SEARCH`, `SCAVIO_YOUTUBE_CHANNEL`, `SCAVIO_YOUTUBE_CHANNEL_VIDEOS`, `SCAVIO_YOUTUBE_CHANNEL_SHORTS`, `SCAVIO_YOUTUBE_CHANNEL_COMMUNITY`, `SCAVIO_YOUTUBE_CHANNEL_RESOLVE`, `SCAVIO_YOUTUBE_STREAMS` |
| Reddit | `SCAVIO_REDDIT_SEARCH`, `SCAVIO_REDDIT_POST` |
| TikTok | `SCAVIO_TIKTOK_PROFILE`, `SCAVIO_TIKTOK_USER_POSTS`, `SCAVIO_TIKTOK_VIDEO`, `SCAVIO_TIKTOK_VIDEO_COMMENTS`, `SCAVIO_TIKTOK_COMMENT_REPLIES`, `SCAVIO_TIKTOK_SEARCH_VIDEOS`, `SCAVIO_TIKTOK_SEARCH_USERS`, `SCAVIO_TIKTOK_HASHTAG`, `SCAVIO_TIKTOK_HASHTAG_VIDEOS`, `SCAVIO_TIKTOK_USER_FOLLOWERS`, `SCAVIO_TIKTOK_USER_FOLLOWINGS` |
| Instagram | `SCAVIO_INSTAGRAM_PROFILE`, `SCAVIO_INSTAGRAM_USER_POSTS`, `SCAVIO_INSTAGRAM_USER_REELS`, `SCAVIO_INSTAGRAM_USER_TAGGED`, `SCAVIO_INSTAGRAM_USER_STORIES`, `SCAVIO_INSTAGRAM_POST`, `SCAVIO_INSTAGRAM_POST_COMMENTS`, `SCAVIO_INSTAGRAM_COMMENT_REPLIES`, `SCAVIO_INSTAGRAM_SEARCH_USERS`, `SCAVIO_INSTAGRAM_SEARCH_HASHTAGS`, `SCAVIO_INSTAGRAM_USER_FOLLOWERS`, `SCAVIO_INSTAGRAM_USER_FOLLOWINGS` |

## Credits

Most endpoints cost 1 credit, including Google. Instagram costs 8-10 credits per call per endpoint, except user posts which costs 2. YouTube search and shorts cost 2, YouTube streams 3, and YouTube transcript 8. See [scavio.dev/docs](https://scavio.dev/docs).

## Links

- Scavio: https://scavio.dev
- Docs: https://scavio.dev/docs
- Dashboard: https://dashboard.scavio.dev
