# composio-scavio

[Scavio](https://scavio.dev) real-time search tools for [Composio](https://composio.dev).

Scavio is a single Search API over Google, YouTube, Amazon, Walmart, Reddit, TikTok, TikTok Shop, Instagram, X and LinkedIn. This package exposes **97 tools covering every live endpoint of all ten platforms** as a Composio custom toolkit, so your agents can pull structured, up-to-date results across any Composio-supported framework (OpenAI, Anthropic, LangChain, CrewAI, and more).

> **Google v1 is gone.** `/api/v1/google` was retired on 2026-08-04 and now
> returns 410. Every Google tool here runs on `/api/v2/google*` and takes v2
> params natively: `gl` (two-letter country), `hl` (language), `google_domain`,
> `device`, and `start`. **`start` is a 0-based result OFFSET, not a page
> number** -- 0 is the first page, 10 the second, 20 the third. The old
> `country_code` / `language` / `page` arguments are removed rather than
> silently remapped, because mapping a page number onto `start` fetches the
> wrong page. Google responses are also FLAT: there is no `data` wrapper, and
> results are `organic_results[]` with `link` and `snippet`.

> **Amazon changed (breaking).** The upstream provider moved in 2026-07:
> `domain` is replaced by `country`, a two-letter marketplace code (`us`, `gb`
> -- the UK is `gb`, not `uk` -- `de`, `jp`, ...), and `sort_by`, `pages`,
> `category_id`, `merchant_id`, `language`, `currency`, `device`, `zip_code`
> and `autoselect_variant` are gone. The marketplace ignores all of them
> (`sort_by` returns the identical unordered set for every value), so they are
> removed rather than kept as silent no-ops. Rank and filter results yourself.

> **Reddit search has no filters.** `/reddit/search` accepts only `query` and
> `cursor`; the API strips anything else, so the old `type` and `sort` args
> narrowed nothing and are removed. It returns `data.results` with `next_cursor`
> and `has_more`. `SCAVIO_REDDIT_POST` returns the post itself only -- comments
> are not included, use `SCAVIO_REDDIT_POST_COMMENTS` for those. The subreddit
> and user feeds do return `data.posts`.

> **Five LinkedIn endpoints are retired.** `person/contact`, `company/people`,
> `company/jobs`, `search/people` and `search/posts` were retired upstream and
> always answer 410 unbilled, so they are deliberately not registered as tools.
> Use `SCAVIO_LINKEDIN_COMPANY` (its `featured_employees` is a 4-6 person
> sample) instead of company/people, and `SCAVIO_LINKEDIN_SEARCH_JOBS` with the
> company name instead of company/jobs.

## Install

```bash
pip install composio-scavio
```

## Setup

Get a Scavio API key from the [Scavio Dashboard](https://dashboard.scavio.dev) (new accounts get 50 one-time signup credits, no credit card; the free plan does not refill monthly). Set it as an environment variable or pass it directly.

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
    arguments={"query": "best search API for AI agents", "gl": "us", "hl": "en"},
)
print(result)
```

Pass `all=True` to register every tool regardless of the individual flags.

## Tools

97 tools, all namespaced under the `SCAVIO` toolkit. Each provider is gated by an `enable_*` flag.

| Provider | Flag | Tools | Names |
|----------|------|-------|-------|
| Google | `enable_google` | 14 | `SCAVIO_GOOGLE_SEARCH`, `SCAVIO_GOOGLE_AI_MODE`, `SCAVIO_GOOGLE_MAPS_SEARCH`, `SCAVIO_GOOGLE_MAPS_PLACE`, `SCAVIO_GOOGLE_MAPS_REVIEWS`, `SCAVIO_GOOGLE_SHOPPING`, `SCAVIO_GOOGLE_SHOPPING_PRODUCT`, `SCAVIO_GOOGLE_SHOPPING_STORES`, `SCAVIO_GOOGLE_FLIGHTS`, `SCAVIO_GOOGLE_HOTELS`, `SCAVIO_GOOGLE_HOTELS_DETAIL`, `SCAVIO_GOOGLE_NEWS`, `SCAVIO_GOOGLE_TRENDS`, `SCAVIO_GOOGLE_TRENDING` |
| YouTube | `enable_youtube` | 15 | `SCAVIO_YOUTUBE_SEARCH`, `SCAVIO_YOUTUBE_SHORTS`, `SCAVIO_YOUTUBE_SUGGESTIONS`, `SCAVIO_YOUTUBE_VIDEO`, `SCAVIO_YOUTUBE_COMMENTS`, `SCAVIO_YOUTUBE_COMMENT_REPLIES`, `SCAVIO_YOUTUBE_TRANSCRIPT`, `SCAVIO_YOUTUBE_RELATED`, `SCAVIO_YOUTUBE_CHANNEL_SEARCH`, `SCAVIO_YOUTUBE_CHANNEL`, `SCAVIO_YOUTUBE_CHANNEL_VIDEOS`, `SCAVIO_YOUTUBE_CHANNEL_SHORTS`, `SCAVIO_YOUTUBE_CHANNEL_COMMUNITY`, `SCAVIO_YOUTUBE_CHANNEL_RESOLVE`, `SCAVIO_YOUTUBE_STREAMS` |
| Amazon | `enable_amazon` | 3 | `SCAVIO_AMAZON_SEARCH`, `SCAVIO_AMAZON_PRODUCT`, `SCAVIO_AMAZON_OFFERS` |
| Walmart | `enable_walmart` | 2 | `SCAVIO_WALMART_SEARCH`, `SCAVIO_WALMART_PRODUCT` |
| Reddit | `enable_reddit` | 12 | `SCAVIO_REDDIT_SEARCH`, `SCAVIO_REDDIT_SEARCH_SUGGESTIONS`, `SCAVIO_REDDIT_POST`, `SCAVIO_REDDIT_POST_COMMENTS`, `SCAVIO_REDDIT_COMMENT_REPLIES`, `SCAVIO_REDDIT_SUBREDDIT`, `SCAVIO_REDDIT_SUBREDDIT_POSTS`, `SCAVIO_REDDIT_USER`, `SCAVIO_REDDIT_USER_POSTS`, `SCAVIO_REDDIT_USER_COMMENTS`, `SCAVIO_REDDIT_POPULAR`, `SCAVIO_REDDIT_TRENDING` |
| TikTok | `enable_tiktok` | 11 | `SCAVIO_TIKTOK_PROFILE`, `SCAVIO_TIKTOK_USER_POSTS`, `SCAVIO_TIKTOK_VIDEO`, `SCAVIO_TIKTOK_VIDEO_COMMENTS`, `SCAVIO_TIKTOK_COMMENT_REPLIES`, `SCAVIO_TIKTOK_SEARCH_VIDEOS`, `SCAVIO_TIKTOK_SEARCH_USERS`, `SCAVIO_TIKTOK_HASHTAG`, `SCAVIO_TIKTOK_HASHTAG_VIDEOS`, `SCAVIO_TIKTOK_USER_FOLLOWERS`, `SCAVIO_TIKTOK_USER_FOLLOWINGS` |
| TikTok Shop | `enable_tiktok_shop` | 8 | `SCAVIO_TIKTOK_SHOP_SEARCH`, `SCAVIO_TIKTOK_SHOP_SEARCH_SUGGESTIONS`, `SCAVIO_TIKTOK_SHOP_PRODUCT`, `SCAVIO_TIKTOK_SHOP_PRODUCT_REVIEWS`, `SCAVIO_TIKTOK_SHOP_CATEGORIES`, `SCAVIO_TIKTOK_SHOP_CATEGORY_PRODUCTS`, `SCAVIO_TIKTOK_SHOP_SHOP_PRODUCTS`, `SCAVIO_TIKTOK_SHOP_RESOLVE` |
| Instagram | `enable_instagram` | 12 | `SCAVIO_INSTAGRAM_PROFILE`, `SCAVIO_INSTAGRAM_USER_POSTS`, `SCAVIO_INSTAGRAM_USER_REELS`, `SCAVIO_INSTAGRAM_USER_TAGGED`, `SCAVIO_INSTAGRAM_USER_STORIES`, `SCAVIO_INSTAGRAM_POST`, `SCAVIO_INSTAGRAM_POST_COMMENTS`, `SCAVIO_INSTAGRAM_COMMENT_REPLIES`, `SCAVIO_INSTAGRAM_SEARCH_USERS`, `SCAVIO_INSTAGRAM_SEARCH_HASHTAGS`, `SCAVIO_INSTAGRAM_USER_FOLLOWERS`, `SCAVIO_INSTAGRAM_USER_FOLLOWINGS` |
| X | `enable_x` | 11 | `SCAVIO_X_SEARCH`, `SCAVIO_X_TWEET`, `SCAVIO_X_TWEET_COMMENTS`, `SCAVIO_X_TWEET_RETWEETERS`, `SCAVIO_X_USER`, `SCAVIO_X_USER_TWEETS`, `SCAVIO_X_USER_REPLIES`, `SCAVIO_X_USER_MEDIA`, `SCAVIO_X_USER_FOLLOWERS`, `SCAVIO_X_USER_FOLLOWINGS`, `SCAVIO_X_TRENDING` |
| LinkedIn | `enable_linkedin` | 9 | `SCAVIO_LINKEDIN_PERSON`, `SCAVIO_LINKEDIN_PERSON_ABOUT`, `SCAVIO_LINKEDIN_PERSON_POSTS`, `SCAVIO_LINKEDIN_COMPANY`, `SCAVIO_LINKEDIN_COMPANY_POSTS`, `SCAVIO_LINKEDIN_SEARCH_JOBS`, `SCAVIO_LINKEDIN_JOB`, `SCAVIO_LINKEDIN_POST`, `SCAVIO_LINKEDIN_POST_COMMENTS` |

That is every live Scavio endpoint. Two things are deliberately absent: the deprecated
`/youtube/metadata` alias (identical to `SCAVIO_YOUTUBE_VIDEO`) and the 5 retired
LinkedIn endpoints (always 410, unbilled).

## Credits

Every tool states its cost in its own description. The full table:

| Cost | Endpoints |
|------|-----------|
| 1 credit | All 14 Google v2 tools, all 12 Reddit, all 11 TikTok, all 8 TikTok Shop, all 11 X, Amazon (3), Walmart (2), and the 11 remaining YouTube tools |
| 2 credits | `SCAVIO_YOUTUBE_SEARCH`, `SCAVIO_YOUTUBE_SHORTS`, `SCAVIO_INSTAGRAM_USER_POSTS` |
| 3 credits | `SCAVIO_YOUTUBE_STREAMS` |
| 8 credits | `SCAVIO_YOUTUBE_TRANSCRIPT`, `SCAVIO_INSTAGRAM_POST`, `SCAVIO_INSTAGRAM_COMMENT_REPLIES` |
| 10 credits | The other 9 Instagram tools; LinkedIn `PERSON_POSTS`, `COMPANY_POSTS`, `SEARCH_JOBS`, `POST_COMMENTS` |
| 30 credits | `SCAVIO_LINKEDIN_JOB` (the most expensive Scavio endpoint) |

LinkedIn `PERSON`, `PERSON_ABOUT`, `COMPANY` and `POST` cost 1 credit. See
[scavio.dev/docs](https://scavio.dev/docs).

## Links

- Scavio: https://scavio.dev
- Docs: https://scavio.dev/docs
- Dashboard: https://dashboard.scavio.dev
