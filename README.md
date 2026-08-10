# composio-scavio

[Scavio](https://scavio.dev) real-time search tools for [Composio](https://composio.dev).

Scavio is a single Search API over 32 platforms -- Google, YouTube, Amazon, Walmart, eBay, Target, Home Depot, Reddit, TikTok, TikTok Shop, Instagram, X, LinkedIn, Threads, Kuaishou, Zillow, Redfin, Booking.com, Airbnb, Tripadvisor, Yelp, Indeed, Glassdoor, the Apple App Store, Google Play, SEC EDGAR, Companies House, G2, Capterra, Google Ads Transparency and the Meta Ad Library -- plus `extract`, which reads any URL as Markdown, plain text or raw HTML. This package exposes **189 tools covering every live Scavio endpoint** as a Composio custom toolkit, so your agents can pull structured, up-to-date results across any Composio-supported framework (OpenAI, Anthropic, LangChain, CrewAI, and more).

> **New in 0.4.0: 21 more platforms, and they are opt-in.** Registering all 189
> tools at once buries the handful an agent actually wants, so the verticals
> added in this release are off by default. The ten original platforms and
> `extract` stay on (104 tools). Turn a vertical on with its flag --
> `build_scavio_toolkit(enable_zillow=True)` -- or pass `all=True` for
> everything. Nothing that worked in 0.3.0 changes, except that Walmart grew
> from 2 tools to 7.

> **Walmart was rebuilt (breaking).** Walmart now runs on a scrape.do rebuild:
> `device`, `delivery_zip` and `store_id` never existed on it and are gone,
> `start_page` is replaced by `page`, and five endpoints beyond search/product
> are exposed for the first time (`REVIEWS`, `CATEGORY`, `OFFERS`, `SELLER`,
> `SELLER_PRODUCTS`). `SCAVIO_WALMART_OFFERS` returns the **buy-box seller
> only** -- there is no way to page the other sellers -- and
> `SCAVIO_WALMART_SELLER_PRODUCTS` returns roughly the first 40 items with no
> pagination at all.

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
    enable_zillow=True,      # opt-in: off unless you ask for it
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

`SCAVIO_EXTRACT` is the agent's "read this page" primitive and is on by default:

```python
page = session.tools.execute(
    "SCAVIO_EXTRACT",
    arguments={"url": "https://example.com/pricing", "format": "markdown"},
)
```

Pass `all=True` to register every tool regardless of the individual flags.

## Tools

189 tools, all namespaced under the `SCAVIO` toolkit. Each provider is gated by an `enable_*` flag. **On by default** are the ten original platforms and `extract` (104 tools); the 21 platforms marked opt-in are off unless you pass their flag or `all=True`.

### On by default

| Provider | Flag | Tools | Names |
|----------|------|-------|-------|
| Google | `enable_google` | 14 | `SCAVIO_GOOGLE_SEARCH`, `SCAVIO_GOOGLE_AI_MODE`, `SCAVIO_GOOGLE_MAPS_SEARCH`, `SCAVIO_GOOGLE_MAPS_PLACE`, `SCAVIO_GOOGLE_MAPS_REVIEWS`, `SCAVIO_GOOGLE_SHOPPING`, `SCAVIO_GOOGLE_SHOPPING_PRODUCT`, `SCAVIO_GOOGLE_SHOPPING_STORES`, `SCAVIO_GOOGLE_FLIGHTS`, `SCAVIO_GOOGLE_HOTELS`, `SCAVIO_GOOGLE_HOTELS_DETAIL`, `SCAVIO_GOOGLE_NEWS`, `SCAVIO_GOOGLE_TRENDS`, `SCAVIO_GOOGLE_TRENDING` |
| YouTube | `enable_youtube` | 15 | `SCAVIO_YOUTUBE_SEARCH`, `SCAVIO_YOUTUBE_SHORTS`, `SCAVIO_YOUTUBE_SUGGESTIONS`, `SCAVIO_YOUTUBE_VIDEO`, `SCAVIO_YOUTUBE_COMMENTS`, `SCAVIO_YOUTUBE_COMMENT_REPLIES`, `SCAVIO_YOUTUBE_TRANSCRIPT`, `SCAVIO_YOUTUBE_RELATED`, `SCAVIO_YOUTUBE_CHANNEL_SEARCH`, `SCAVIO_YOUTUBE_CHANNEL`, `SCAVIO_YOUTUBE_CHANNEL_VIDEOS`, `SCAVIO_YOUTUBE_CHANNEL_SHORTS`, `SCAVIO_YOUTUBE_CHANNEL_COMMUNITY`, `SCAVIO_YOUTUBE_CHANNEL_RESOLVE`, `SCAVIO_YOUTUBE_STREAMS` |
| Amazon | `enable_amazon` | 4 | `SCAVIO_AMAZON_SEARCH`, `SCAVIO_AMAZON_PRODUCT`, `SCAVIO_AMAZON_OFFERS`, `SCAVIO_AMAZON_OPTIONS` |
| Walmart | `enable_walmart` | 7 | `SCAVIO_WALMART_SEARCH`, `SCAVIO_WALMART_PRODUCT`, `SCAVIO_WALMART_REVIEWS`, `SCAVIO_WALMART_CATEGORY`, `SCAVIO_WALMART_OFFERS`, `SCAVIO_WALMART_SELLER`, `SCAVIO_WALMART_SELLER_PRODUCTS` |
| Reddit | `enable_reddit` | 12 | `SCAVIO_REDDIT_SEARCH`, `SCAVIO_REDDIT_SEARCH_SUGGESTIONS`, `SCAVIO_REDDIT_POST`, `SCAVIO_REDDIT_POST_COMMENTS`, `SCAVIO_REDDIT_COMMENT_REPLIES`, `SCAVIO_REDDIT_SUBREDDIT`, `SCAVIO_REDDIT_SUBREDDIT_POSTS`, `SCAVIO_REDDIT_USER`, `SCAVIO_REDDIT_USER_POSTS`, `SCAVIO_REDDIT_USER_COMMENTS`, `SCAVIO_REDDIT_POPULAR`, `SCAVIO_REDDIT_TRENDING` |
| TikTok | `enable_tiktok` | 11 | `SCAVIO_TIKTOK_PROFILE`, `SCAVIO_TIKTOK_USER_POSTS`, `SCAVIO_TIKTOK_VIDEO`, `SCAVIO_TIKTOK_VIDEO_COMMENTS`, `SCAVIO_TIKTOK_COMMENT_REPLIES`, `SCAVIO_TIKTOK_SEARCH_VIDEOS`, `SCAVIO_TIKTOK_SEARCH_USERS`, `SCAVIO_TIKTOK_HASHTAG`, `SCAVIO_TIKTOK_HASHTAG_VIDEOS`, `SCAVIO_TIKTOK_USER_FOLLOWERS`, `SCAVIO_TIKTOK_USER_FOLLOWINGS` |
| TikTok Shop | `enable_tiktok_shop` | 8 | `SCAVIO_TIKTOK_SHOP_SEARCH`, `SCAVIO_TIKTOK_SHOP_SEARCH_SUGGESTIONS`, `SCAVIO_TIKTOK_SHOP_PRODUCT`, `SCAVIO_TIKTOK_SHOP_PRODUCT_REVIEWS`, `SCAVIO_TIKTOK_SHOP_CATEGORIES`, `SCAVIO_TIKTOK_SHOP_CATEGORY_PRODUCTS`, `SCAVIO_TIKTOK_SHOP_SHOP_PRODUCTS`, `SCAVIO_TIKTOK_SHOP_RESOLVE` |
| Instagram | `enable_instagram` | 12 | `SCAVIO_INSTAGRAM_PROFILE`, `SCAVIO_INSTAGRAM_USER_POSTS`, `SCAVIO_INSTAGRAM_USER_REELS`, `SCAVIO_INSTAGRAM_USER_TAGGED`, `SCAVIO_INSTAGRAM_USER_STORIES`, `SCAVIO_INSTAGRAM_POST`, `SCAVIO_INSTAGRAM_POST_COMMENTS`, `SCAVIO_INSTAGRAM_COMMENT_REPLIES`, `SCAVIO_INSTAGRAM_SEARCH_USERS`, `SCAVIO_INSTAGRAM_SEARCH_HASHTAGS`, `SCAVIO_INSTAGRAM_USER_FOLLOWERS`, `SCAVIO_INSTAGRAM_USER_FOLLOWINGS` |
| X | `enable_x` | 11 | `SCAVIO_X_SEARCH`, `SCAVIO_X_TWEET`, `SCAVIO_X_TWEET_COMMENTS`, `SCAVIO_X_TWEET_RETWEETERS`, `SCAVIO_X_USER`, `SCAVIO_X_USER_TWEETS`, `SCAVIO_X_USER_REPLIES`, `SCAVIO_X_USER_MEDIA`, `SCAVIO_X_USER_FOLLOWERS`, `SCAVIO_X_USER_FOLLOWINGS`, `SCAVIO_X_TRENDING` |
| LinkedIn | `enable_linkedin` | 9 | `SCAVIO_LINKEDIN_PERSON`, `SCAVIO_LINKEDIN_PERSON_ABOUT`, `SCAVIO_LINKEDIN_PERSON_POSTS`, `SCAVIO_LINKEDIN_COMPANY`, `SCAVIO_LINKEDIN_COMPANY_POSTS`, `SCAVIO_LINKEDIN_SEARCH_JOBS`, `SCAVIO_LINKEDIN_JOB`, `SCAVIO_LINKEDIN_POST`, `SCAVIO_LINKEDIN_POST_COMMENTS` |
| Extract (any URL) | `enable_extract` | 1 | `SCAVIO_EXTRACT` |

### Opt-in

| Provider | Flag | Tools | Names |
|----------|------|-------|-------|
| Threads | `enable_threads` | 6 | `SCAVIO_THREADS_PROFILE`, `SCAVIO_THREADS_USER_POSTS`, `SCAVIO_THREADS_USER_REPLIES`, `SCAVIO_THREADS_POST`, `SCAVIO_THREADS_POST_COMMENTS`, `SCAVIO_THREADS_SEARCH_USERS` |
| Kuaishou (China) | `enable_kuaishou` | 14 | `SCAVIO_KUAISHOU_PROFILE`, `SCAVIO_KUAISHOU_USER_POSTS`, `SCAVIO_KUAISHOU_USER_LIVE`, `SCAVIO_KUAISHOU_USER_RESOLVE`, `SCAVIO_KUAISHOU_VIDEO`, `SCAVIO_KUAISHOU_VIDEO_COMMENTS`, `SCAVIO_KUAISHOU_COMMENT_REPLIES`, `SCAVIO_KUAISHOU_VIDEOS_BATCH`, `SCAVIO_KUAISHOU_SEARCH`, `SCAVIO_KUAISHOU_SEARCH_VIDEOS`, `SCAVIO_KUAISHOU_SEARCH_USERS`, `SCAVIO_KUAISHOU_SEARCH_LIVE`, `SCAVIO_KUAISHOU_TAG_FEED`, `SCAVIO_KUAISHOU_TRENDING` |
| eBay | `enable_ebay` | 3 | `SCAVIO_EBAY_SEARCH`, `SCAVIO_EBAY_PRODUCT`, `SCAVIO_EBAY_SELLER` |
| Target | `enable_target` | 4 | `SCAVIO_TARGET_SEARCH`, `SCAVIO_TARGET_CATEGORY`, `SCAVIO_TARGET_PRODUCT`, `SCAVIO_TARGET_REVIEWS` |
| Home Depot | `enable_home_depot` | 3 | `SCAVIO_HOME_DEPOT_SEARCH`, `SCAVIO_HOME_DEPOT_PRODUCT`, `SCAVIO_HOME_DEPOT_REVIEWS` |
| Zillow | `enable_zillow` | 3 | `SCAVIO_ZILLOW_SEARCH`, `SCAVIO_ZILLOW_PROPERTY`, `SCAVIO_ZILLOW_AGENT_REVIEWS` |
| Booking.com | `enable_booking` | 3 | `SCAVIO_BOOKING_SEARCH`, `SCAVIO_BOOKING_HOTEL`, `SCAVIO_BOOKING_REVIEWS` |
| Tripadvisor | `enable_tripadvisor` | 4 | `SCAVIO_TRIPADVISOR_LOCATIONS`, `SCAVIO_TRIPADVISOR_SEARCH`, `SCAVIO_TRIPADVISOR_LOCATION`, `SCAVIO_TRIPADVISOR_REVIEWS` |
| Indeed | `enable_indeed` | 4 | `SCAVIO_INDEED_SEARCH`, `SCAVIO_INDEED_JOB`, `SCAVIO_INDEED_COMPANY`, `SCAVIO_INDEED_COMPANY_REVIEWS` |
| Airbnb | `enable_airbnb` | 3 | `SCAVIO_AIRBNB_SEARCH`, `SCAVIO_AIRBNB_LISTING`, `SCAVIO_AIRBNB_REVIEWS` |
| Glassdoor | `enable_glassdoor` | 4 | `SCAVIO_GLASSDOOR_COMPANIES`, `SCAVIO_GLASSDOOR_COMPANY`, `SCAVIO_GLASSDOOR_REVIEWS`, `SCAVIO_GLASSDOOR_SALARIES` |
| Yelp | `enable_yelp` | 3 | `SCAVIO_YELP_SEARCH`, `SCAVIO_YELP_BUSINESS`, `SCAVIO_YELP_REVIEWS` |
| Apple App Store | `enable_app_store` | 3 | `SCAVIO_APP_STORE_SEARCH`, `SCAVIO_APP_STORE_APP`, `SCAVIO_APP_STORE_REVIEWS` |
| Google Play | `enable_google_play` | 3 | `SCAVIO_GOOGLE_PLAY_SEARCH`, `SCAVIO_GOOGLE_PLAY_APP`, `SCAVIO_GOOGLE_PLAY_REVIEWS` |
| SEC EDGAR | `enable_sec` | 6 | `SCAVIO_SEC_LOOKUP`, `SCAVIO_SEC_COMPANY`, `SCAVIO_SEC_FILINGS`, `SCAVIO_SEC_CONCEPT`, `SCAVIO_SEC_FACTS`, `SCAVIO_SEC_SEARCH` |
| Redfin | `enable_redfin` | 3 | `SCAVIO_REDFIN_SEARCH`, `SCAVIO_REDFIN_PROPERTY`, `SCAVIO_REDFIN_MARKET` |
| Companies House | `enable_companies_house` | 4 | `SCAVIO_COMPANIES_HOUSE_SEARCH`, `SCAVIO_COMPANIES_HOUSE_COMPANY`, `SCAVIO_COMPANIES_HOUSE_OFFICERS`, `SCAVIO_COMPANIES_HOUSE_FILING_HISTORY` |
| G2 | `enable_g2` | 3 | `SCAVIO_G2_SEARCH`, `SCAVIO_G2_PRODUCT`, `SCAVIO_G2_REVIEWS` |
| Capterra | `enable_capterra` | 3 | `SCAVIO_CAPTERRA_SEARCH`, `SCAVIO_CAPTERRA_PRODUCT`, `SCAVIO_CAPTERRA_REVIEWS` |
| Google Ads Transparency | `enable_google_ads` | 3 | `SCAVIO_GOOGLE_ADS_ADVERTISERS`, `SCAVIO_GOOGLE_ADS_SEARCH`, `SCAVIO_GOOGLE_ADS_CREATIVE` |
| Meta Ad Library | `enable_meta_ads` | 3 | `SCAVIO_META_ADS_SEARCH`, `SCAVIO_META_ADS_ADVERTISER`, `SCAVIO_META_ADS_AD` |

That is every live Scavio endpoint. Two things are deliberately absent: the deprecated
`/youtube/metadata` alias (identical to `SCAVIO_YOUTUBE_VIDEO`) and the 5 retired
LinkedIn endpoints (always 410, unbilled).

### Resolve first

Six tools exist only to turn a name you have into the id everything else on that
platform is keyed by. Call them first, or the rest of the platform is unreachable:
`SCAVIO_SEC_LOOKUP` (ticker to CIK), `SCAVIO_GLASSDOOR_COMPANIES` (name to
`employer_id`), `SCAVIO_TRIPADVISOR_LOCATIONS` (name to `geo_id` + `location_id`),
`SCAVIO_GOOGLE_ADS_ADVERTISERS` (brand to `advertiser_id`),
`SCAVIO_COMPANIES_HOUSE_SEARCH` (name to `company_number`) and
`SCAVIO_KUAISHOU_USER_RESOLVE` (share link to `user_id`).

## Credits

Every tool states its cost in its own description. Flat-priced platforms:

| Cost | Platforms |
|------|-----------|
| 1 credit | Google (14), Reddit (12), TikTok (11), TikTok Shop (8), X (11), Amazon (3 billable), eBay (3), Target (4), Zillow (3), Booking.com (3), Airbnb (3), Glassdoor (4), App Store (3), SEC EDGAR (6), Redfin (3), Companies House (4), Google Ads (3), Meta Ads (3), and the 11 remaining YouTube tools |
| 2 credits | `SCAVIO_YOUTUBE_SEARCH`, `SCAVIO_YOUTUBE_SHORTS`, `SCAVIO_INSTAGRAM_USER_POSTS`, Home Depot (3), Tripadvisor (4), Indeed (4), Yelp (3), Google Play (3), Capterra (3) |
| 3 credits | `SCAVIO_YOUTUBE_STREAMS` |
| 5 credits | G2 (3) |
| 8 credits | `SCAVIO_YOUTUBE_TRANSCRIPT`, `SCAVIO_INSTAGRAM_POST`, `SCAVIO_INSTAGRAM_COMMENT_REPLIES` |
| 10 credits | The other 9 Instagram tools; LinkedIn `PERSON_POSTS`, `COMPANY_POSTS`, `SEARCH_JOBS`, `POST_COMMENTS` |
| 30 credits | `SCAVIO_LINKEDIN_JOB` (the most expensive Scavio endpoint) |
| Free | `SCAVIO_AMAZON_OPTIONS` (a static marketplace list; no key, no credits) |

LinkedIn `PERSON`, `PERSON_ABOUT`, `COMPANY` and `POST` cost 1 credit.

**Four surfaces are body-priced** -- their cost is a function of the request, not a
constant for the route, so no single number can be quoted:

| Surface | Price |
|---------|-------|
| Walmart | 1 credit on `domain` `com` or `ca`, 2 on `com.mx`. `PRODUCT`, `REVIEWS`, `OFFERS`, `SELLER` and `SELLER_PRODUCTS` take no `domain`, so they are always 1. |
| Threads | 2 credits addressed by `user_id`, 4 by `username` (the handle has to be resolved through people search first). `POST`, `POST_COMMENTS` and `SEARCH_USERS` have no username form and are always 2. |
| Kuaishou | Priced **per endpoint**, never per platform: 1 (`USER_POSTS`, `USER_LIVE`, `USER_RESOLVE`, `VIDEO_COMMENTS`, `COMMENT_REPLIES`, `TAG_FEED`, `TRENDING`), 2 (`VIDEO`), 10 (`PROFILE` and the four searches, per page), 40 (`VIDEOS_BATCH`). |
| Extract | Tier-priced by `mode`: `normal` and `advanced` 1 credit, `ultra` 2. Only a successful extraction is billed -- a dead link, bot wall or timeout costs nothing. |

See [scavio.dev/docs](https://scavio.dev/docs).

## Links

- Scavio: https://scavio.dev
- Docs: https://scavio.dev/docs
- Dashboard: https://dashboard.scavio.dev
