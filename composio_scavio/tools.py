"""Scavio tools for Composio.

Scavio is a single Search API over Google, YouTube, Amazon, Walmart, Reddit,
TikTok, TikTok Shop, Instagram, X and LinkedIn. This toolkit exposes every live
endpoint of all ten platforms as a Composio custom toolkit. Build the toolkit
with ``build_scavio_toolkit()`` and bind it to a session::

    from composio import Composio
    from composio_scavio import build_scavio_toolkit

    composio = Composio()
    scavio = build_scavio_toolkit(api_key="sk_...")  # or set SCAVIO_API_KEY
    session = composio.create(
        user_id="user_1",
        experimental={"custom_toolkits": [scavio]},
    )

Each provider is gated by an ``enable_*`` flag so an agent only sees the tools it
needs. Tools return the raw Scavio JSON response as a dict.
"""

import os
from typing import Any, Callable, Dict, Optional

from pydantic import BaseModel, Field

try:
    from composio import ExperimentalToolkit
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "`composio` not installed. Please install using `pip install composio`"
    ) from exc

try:
    from scavio import ScavioClient
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "`scavio` not installed. Please install using `pip install scavio`"
    ) from exc


# --------------------------------------------------------------------------- #
# Input schemas (one per tool). Field descriptions become the tool arg schema.
# --------------------------------------------------------------------------- #

# Google (all 14 endpoints are /api/v2/google*, 1 credit each)
# v1 (/api/v1/google) was retired on 2026-08-04 and returns 410 Gone. v2 params are
# exposed NATIVELY: `gl`/`hl`/`start`, never v1's country_code/language/page. `start`
# is a 0-based result OFFSET, not a 1-based page - remapping a page number onto it
# silently fetches the wrong page.
_GL_DESC = "Geo country, exactly two letters (ISO 3166-1 alpha-2), e.g. 'us', 'gb'."
_HL_DESC = "UI language (ISO 639-1), e.g. 'en'."
_GOOGLE_DOMAIN_DESC = "Google domain to query, e.g. 'google.co.uk'."
_LOCATION_DESC = "Canonical location name, e.g. 'Austin, Texas, United States'. Converted to a UULE upstream."
_UULE_DESC = "Pre-encoded UULE location string. Takes priority over location."
_CURRENCY_DESC = "Currency code, exactly three letters, e.g. 'USD'."


class GoogleSearchInput(BaseModel):
    query: str = Field(description="The search query.")
    device: Optional[str] = Field(None, description="Device profile: 'desktop' or 'mobile'.")
    start: Optional[int] = Field(
        None,
        description="Result OFFSET, not a page number: 0 = first page, 10 = second page, 20 = third. 0-990.",
    )
    include_html: Optional[bool] = Field(None, description="Include Google's raw HTML in an 'html' key when true.")
    hl: Optional[str] = Field(None, description=_HL_DESC)
    gl: Optional[str] = Field(None, description=_GL_DESC)
    google_domain: Optional[str] = Field(None, description=_GOOGLE_DOMAIN_DESC)
    location: Optional[str] = Field(None, description=_LOCATION_DESC)
    uule: Optional[str] = Field(None, description=_UULE_DESC)
    lr: Optional[str] = Field(None, description="Restrict results to a language, e.g. 'lang_en'.")
    cr: Optional[str] = Field(None, description="Restrict results to a country, e.g. 'countryUS'.")
    safe: Optional[str] = Field(None, description="Safe search. The only accepted value is 'active'.")
    nfpr: Optional[bool] = Field(None, description="Disable auto-correction of the query when true.")
    filter: Optional[str] = Field(
        None,
        description="Similar/omitted-result filtering as a STRING: '1' on (default), '0' off.",
    )
    time_period: Optional[str] = Field(
        None,
        description="Recency filter: 'last_hour', 'last_day', 'last_week', 'last_month', or 'last_year'.",
    )
    resolve_ai_overview: Optional[bool] = Field(
        None,
        description="Resolve a deferred AI Overview with a second call (default true). Set false to skip it and return the stub.",
    )


class GoogleAiModeInput(BaseModel):
    query: str = Field(description="The query to run through Google AI Mode.")
    device: Optional[str] = Field(None, description="Device profile: 'desktop' or 'mobile'.")
    include_html: Optional[bool] = Field(None, description="Include the raw HTML when true.")
    hl: Optional[str] = Field(None, description=_HL_DESC)
    gl: Optional[str] = Field(None, description=_GL_DESC)
    google_domain: Optional[str] = Field(None, description=_GOOGLE_DOMAIN_DESC)
    location: Optional[str] = Field(None, description=_LOCATION_DESC)
    uule: Optional[str] = Field(None, description=_UULE_DESC)
    safe: Optional[str] = Field(None, description="Safe search. The only accepted value is 'active'.")


class GoogleMapsSearchInput(BaseModel):
    query: str = Field(description="What to look for on Google Maps, e.g. 'coffee shops in Austin'.")
    start: Optional[int] = Field(
        None,
        description="Result offset, 0-100, MUST be a multiple of 20 (0, 20, 40, ...). Not a page number.",
    )
    ll: Optional[str] = Field(
        None,
        description="Map center as '@lat,lng,zoomz', e.g. '@40.7128,-74.0060,13z'. Maps localizes by map center; when omitted a centroid is derived from gl.",
    )
    hl: Optional[str] = Field(None, description=_HL_DESC)
    gl: Optional[str] = Field(None, description=_GL_DESC)
    google_domain: Optional[str] = Field(None, description=_GOOGLE_DOMAIN_DESC)


class GoogleMapsPlaceInput(BaseModel):
    place_id: Optional[str] = Field(None, description="Google place id ('ChIJ...'). Provide this or data_cid.")
    data_cid: Optional[str] = Field(None, description="Numeric Google CID. Provide this or place_id.")


class GoogleMapsReviewsInput(BaseModel):
    data_id: Optional[str] = Field(
        None, description="Maps data id in '0xHEX:0xHEX' form. Provide this or place_id."
    )
    place_id: Optional[str] = Field(None, description="Google place id ('ChIJ...'). Provide this or data_id.")
    num: Optional[int] = Field(None, description="Number of reviews to return, 1-20.")
    next_page_token: Optional[str] = Field(None, description="Continuation token from a prior response.")
    sort_by: Optional[str] = Field(
        None,
        description="Sort order: 'relevance', 'newest', 'highest_rating', or 'lowest_rating'.",
    )
    hl: Optional[str] = Field(None, description=_HL_DESC)
    gl: Optional[str] = Field(None, description=_GL_DESC)
    google_domain: Optional[str] = Field(None, description=_GOOGLE_DOMAIN_DESC)


class GoogleShoppingInput(BaseModel):
    query: str = Field(description="The product search query.")
    device: Optional[str] = Field(None, description="Device profile: 'desktop' or 'mobile'.")
    start: Optional[int] = Field(None, description="Result offset, not a page number. Follow pagination.next.")
    min_price: Optional[int] = Field(None, description="Minimum price filter.")
    max_price: Optional[int] = Field(None, description="Maximum price filter.")
    sort_by: Optional[int] = Field(
        None,
        description="Sort as a NUMBER: 0 relevance, 1 price ascending, 2 price descending.",
    )
    free_shipping: Optional[bool] = Field(None, description="Restrict to free-shipping offers when true.")
    on_sale: Optional[bool] = Field(None, description="Restrict to on-sale offers when true.")
    shoprs: Optional[str] = Field(
        None, description="Opaque filter token lifted from filters[] or carousel_filters[] in a prior response."
    )
    hl: Optional[str] = Field(None, description=_HL_DESC)
    gl: Optional[str] = Field(None, description=_GL_DESC)
    google_domain: Optional[str] = Field(None, description=_GOOGLE_DOMAIN_DESC)
    location: Optional[str] = Field(None, description=_LOCATION_DESC)
    uule: Optional[str] = Field(None, description=_UULE_DESC)


class GoogleShoppingProductInput(BaseModel):
    catalog_id: Optional[str] = Field(
        None, description="Durable catalog id. When set, query is also REQUIRED."
    )
    query: Optional[str] = Field(
        None, description="Product query. Mandatory whenever catalog_id is supplied."
    )
    immersive_product_page_token: Optional[str] = Field(None, description="Immersive product page token.")
    page_token: Optional[str] = Field(None, description="Alias of immersive_product_page_token.")
    product_id: Optional[str] = Field(None, description="Google product id.")
    device: Optional[str] = Field(
        None, description="Device profile: 'desktop', 'mobile', or 'tablet' (the only endpoint accepting tablet)."
    )
    google_domain: Optional[str] = Field(None, description=_GOOGLE_DOMAIN_DESC)
    sort_by: Optional[str] = Field(
        None,
        description="Seller sort as a STRING: 'base_price', 'total_price', 'promotion', or 'seller_rating'.",
    )
    load_all_stores: Optional[bool] = Field(None, description="Load every store offer when true.")
    more_stores: Optional[bool] = Field(None, description="Request additional store offers when true.")
    hl: Optional[str] = Field(None, description=_HL_DESC)
    gl: Optional[str] = Field(None, description=_GL_DESC)
    location: Optional[str] = Field(None, description=_LOCATION_DESC)
    uule: Optional[str] = Field(None, description=_UULE_DESC)


class GoogleShoppingStoresInput(BaseModel):
    catalog_id: str = Field(description="The same catalog_id used on the shopping product call.")
    next_page_token: str = Field(description="Continuation token from a prior response.")


class GoogleFlightsInput(BaseModel):
    departure_id: str = Field(description="Origin IATA code, e.g. 'JFK'. Comma-separated multiples allowed.")
    arrival_id: str = Field(description="Destination IATA code, e.g. 'LHR'. Comma-separated multiples allowed.")
    outbound_date: str = Field(description="Outbound date as 'YYYY-MM-DD'.")
    type: Optional[int] = Field(None, description="Trip type: 1 round trip, 2 one way, 3 multi-city.")
    return_date: Optional[str] = Field(
        None, description="Return date as 'YYYY-MM-DD'. Required when type is 1 (round trip)."
    )
    adults: Optional[int] = Field(None, description="Number of adults, 1-9.")
    children: Optional[int] = Field(None, description="Number of children, 0-9.")
    infants_in_seat: Optional[int] = Field(None, description="Infants in their own seat, 0-4.")
    infants_on_lap: Optional[int] = Field(None, description="Infants on a lap, 0-4.")
    travel_class: Optional[int] = Field(
        None, description="Cabin: 1 economy, 2 premium economy, 3 business, 4 first."
    )
    stops: Optional[int] = Field(None, description="Stops: 0 any, 1 nonstop, 2 one stop or fewer, 3 two or fewer.")
    sort_by: Optional[int] = Field(
        None, description="Sort: 1 top, 2 price, 3 departure, 4 arrival, 5 duration, 6 emissions."
    )
    include_airlines: Optional[str] = Field(None, description="Comma-separated airline codes to include.")
    exclude_airlines: Optional[str] = Field(None, description="Comma-separated airline codes to exclude.")
    hl: Optional[str] = Field(None, description=_HL_DESC)
    gl: Optional[str] = Field(None, description=_GL_DESC)
    currency: Optional[str] = Field(None, description=_CURRENCY_DESC)


class GoogleHotelsInput(BaseModel):
    query: str = Field(description="Where to stay, e.g. 'Austin hotels'. Max 200 characters.")
    check_in_date: str = Field(description="Check-in date as 'YYYY-MM-DD'.")
    check_out_date: str = Field(description="Check-out date as 'YYYY-MM-DD'.")
    hl: Optional[str] = Field(None, description=_HL_DESC)
    gl: Optional[str] = Field(None, description=_GL_DESC)
    currency: Optional[str] = Field(None, description=_CURRENCY_DESC)
    sort_by: Optional[int] = Field(
        None, description="Sort: 3 lowest price, 8 highest rating, 13 most reviewed."
    )
    min_price: Optional[int] = Field(None, description="Minimum nightly price.")
    max_price: Optional[int] = Field(None, description="Maximum nightly price.")
    rating: Optional[int] = Field(None, description="Minimum rating: 7 for 3.5+, 8 for 4.0+, 9 for 4.5+.")
    hotel_class: Optional[str] = Field(
        None, description="Comma-separated star classes 2-5 as a STRING, e.g. '4,5'."
    )
    amenities: Optional[str] = Field(None, description="Comma-separated amenity ids.")
    property_types: Optional[str] = Field(None, description="Comma-separated property type ids; '12' is vacation rentals.")
    free_cancellation: Optional[bool] = Field(None, description="Only free-cancellation rates when true.")
    eco_certified: Optional[bool] = Field(None, description="Only eco-certified properties when true.")
    special_offers: Optional[bool] = Field(None, description="Only properties with special offers when true.")
    next_page_token: Optional[str] = Field(None, description="Continuation token from a prior response.")
    limit: Optional[int] = Field(None, description="Maximum properties to return, 1-20.")


class GoogleHotelsDetailInput(BaseModel):
    detail_token: str = Field(description="detail_token taken from a property in a hotels search response.")
    check_in_date: str = Field(description="Check-in date as 'YYYY-MM-DD'. Must be re-sent; the token alone is not enough.")
    check_out_date: str = Field(description="Check-out date as 'YYYY-MM-DD'.")
    currency: Optional[str] = Field(None, description=_CURRENCY_DESC)
    gl: Optional[str] = Field(None, description=_GL_DESC)
    hl: Optional[str] = Field(None, description=_HL_DESC)


class GoogleNewsInput(BaseModel):
    query: Optional[str] = Field(None, description="News search query. Exactly one driver is allowed.")
    topic_token: Optional[str] = Field(None, description="Topic token from a prior response.")
    section_token: Optional[str] = Field(None, description="Section token from a prior response.")
    story_token: Optional[str] = Field(None, description="Story token from a prior response.")
    publication_token: Optional[str] = Field(None, description="Publication token from a prior response.")
    kgmid: Optional[str] = Field(None, description="Knowledge Graph entity id, e.g. '/m/02_286'.")
    hl: Optional[str] = Field(None, description=_HL_DESC)
    gl: Optional[str] = Field(None, description=_GL_DESC)
    google_domain: Optional[str] = Field(None, description=_GOOGLE_DOMAIN_DESC)
    so: Optional[int] = Field(
        None, description="Sort: 0 relevance, 1 date. Only valid alongside query or kgmid."
    )


class GoogleTrendsInput(BaseModel):
    query: str = Field(description="The term to chart. Comma-separated terms compare them.")
    geo: Optional[str] = Field(
        None,
        description="UPPERCASE region, e.g. 'US', 'GB', 'US-CA'. Worldwide when omitted. This endpoint has no gl.",
    )
    hl: Optional[str] = Field(None, description=_HL_DESC)
    date: Optional[str] = Field(
        None, description="Time range, e.g. 'today 12-m' or '2024-01-01 2024-12-31'."
    )
    tz: Optional[str] = Field(None, description="Timezone offset in minutes, sent as a string.")
    data_type: Optional[str] = Field(
        None,
        description="UPPERCASE: 'TIMESERIES', 'GEO_MAP', 'GEO_MAP_0', 'RELATED_QUERIES', or 'RELATED_TOPICS'.",
    )
    cat: Optional[str] = Field(None, description="Category id as a STRING, e.g. '71'.")
    gprop: Optional[str] = Field(
        None, description="Property: 'images', 'news', 'youtube', or 'froogle'. Web search when omitted."
    )
    region: Optional[str] = Field(
        None, description="UPPERCASE breakdown: 'COUNTRY', 'REGION', 'DMA', or 'CITY'."
    )


class GoogleTrendingInput(BaseModel):
    geo: str = Field(description="Country code, e.g. 'US'. Required: this endpoint has no query field.")
    hl: Optional[str] = Field(None, description=_HL_DESC)
    hours: Optional[int] = Field(None, description="Lookback window in hours; 4, 24, 48 or 168 are meaningful.")
    cat: Optional[int] = Field(None, description="Category id as a NUMBER, 0-20; 0 is all categories.")
    sort: Optional[str] = Field(
        None,
        description="Sort: 'relevance', 'search_volume', 'recency', or 'title'. The field is 'sort', not 'sort_by'.",
    )
    status: Optional[str] = Field(None, description="Trend status: 'all' or 'active'.")


# Amazon
# The Amazon API moved upstream in 2026-07: sort_by, pages, category_id,
# merchant_id, language, currency, device, zip_code and autoselect_variant no
# longer exist. Removed rather than kept as no-ops (sort_by was verified to
# return the identical unordered set for every value). `domain` still works on
# the wire as a deprecated alias but is not offered - one spelling per param.
_COUNTRY_DESC = (
    "Marketplace country code (ISO 3166-1 alpha-2), not a domain: 'us' (default), 'gb' (the UK is gb, not uk), 'ca', 'de', 'fr', 'es', 'it', 'jp', 'in', 'au', 'br', 'mx', 'nl', 'pl', 'se', 'sg', 'ae', 'sa', 'eg', 'cn', 'be', 'tr'. An unknown code falls back to us."
)


class AmazonSearchInput(BaseModel):
    query: str = Field(description="The product search query.")
    country: Optional[str] = Field(None, description=_COUNTRY_DESC)
    page: Optional[int] = Field(
        None, description="Result page, 1-based. One page per call, 1 credit each."
    )


class AmazonProductInput(BaseModel):
    asin: str = Field(description="Amazon Standard Identification Number (ASIN) of the product.")
    country: Optional[str] = Field(None, description=_COUNTRY_DESC)


class AmazonOffersInput(BaseModel):
    asin: str = Field(description="Amazon Standard Identification Number (ASIN) of the product.")
    country: Optional[str] = Field(None, description=_COUNTRY_DESC)


# Walmart
class WalmartSearchInput(BaseModel):
    query: str = Field(description="The product search query.")
    domain: Optional[str] = Field(None, description="Walmart domain.")
    device: Optional[str] = Field(None, description="Device profile: 'desktop' or 'mobile'.")
    sort_by: Optional[str] = Field(None, description="Sort order for results.")
    start_page: Optional[int] = Field(None, description="First page to return.")
    min_price: Optional[int] = Field(None, description="Minimum price filter.")
    max_price: Optional[int] = Field(None, description="Maximum price filter.")
    fulfillment_speed: Optional[str] = Field(None, description="Fulfillment speed filter.")
    fulfillment_type: Optional[str] = Field(None, description="Fulfillment type filter.")
    delivery_zip: Optional[str] = Field(None, description="Delivery ZIP/postal code.")
    store_id: Optional[str] = Field(None, description="Restrict to a store id.")


class WalmartProductInput(BaseModel):
    product_id: str = Field(description="Walmart product id.")
    domain: Optional[str] = Field(None, description="Walmart domain.")
    device: Optional[str] = Field(None, description="Device profile: 'desktop' or 'mobile'.")
    delivery_zip: Optional[str] = Field(None, description="Delivery ZIP/postal code.")
    store_id: Optional[str] = Field(None, description="Restrict to a store id.")


# YouTube
class YouTubeSearchInput(BaseModel):
    query: str = Field(description="The video search query.")
    upload_date: Optional[str] = Field(None, description="Upload date filter: 'last_hour', 'today', 'this_week', 'this_month', 'this_year'.")
    type: Optional[str] = Field(None, description="Result type: 'video', 'channel', 'playlist', or 'movie'.")
    duration: Optional[str] = Field(None, description="Duration filter: 'short', 'medium', or 'long'.")
    sort_by: Optional[str] = Field(None, description="Sort order: 'relevance', 'date', 'view_count', or 'rating'.")
    features: Optional[list] = Field(None, description="Feature filters, e.g. ['hd', '4k', 'subtitles', 'creative_commons', 'live', '360', '3d', 'hdr', 'vr180'].")
    cursor: Optional[str] = Field(None, description="Pagination cursor from a prior response.")
    hd: Optional[bool] = Field(None, description="Restrict to HD videos when true.")
    subtitles: Optional[bool] = Field(None, description="Restrict to videos with subtitles when true.")
    creative_commons: Optional[bool] = Field(None, description="Restrict to Creative Commons videos when true.")
    live: Optional[bool] = Field(None, description="Restrict to live videos when true.")


class YouTubeShortsInput(BaseModel):
    query: str = Field(description="The Shorts search query.")
    sort_by: Optional[str] = Field(None, description="Sort order: 'relevance', 'date', 'view_count', or 'rating'.")
    cursor: Optional[str] = Field(None, description="Pagination cursor from a prior response.")


class YouTubeSuggestionsInput(BaseModel):
    query: str = Field(description="The partial query to autocomplete.")
    language: Optional[str] = Field(None, description="Suggestion language (ISO 639-1, default 'en').")
    region: Optional[str] = Field(None, description="Region code (ISO 3166-1 alpha-2, default 'US').")


class YouTubeVideoInput(BaseModel):
    video_id: str = Field(description="YouTube video id or a full watch URL.")


class YouTubeCommentsInput(BaseModel):
    video_id: str = Field(description="YouTube video id or a full watch URL.")
    cursor: Optional[str] = Field(None, description="Pagination cursor from a prior response.")


class YouTubeCommentRepliesInput(BaseModel):
    video_id: str = Field(description="YouTube video id or a full watch URL.")
    reply_cursor: str = Field(description="Reply cursor from a parent comment's 'reply_cursor' field.")
    cursor: Optional[str] = Field(None, description="Pagination cursor from a prior response.")


class YouTubeTranscriptInput(BaseModel):
    video_id: str = Field(description="YouTube video id or a full watch URL.")
    language: Optional[str] = Field(None, description="Caption language code (default 'en').")
    format: Optional[str] = Field(None, description="'text' for a plain transcript or 'srt' for timed subtitles (default 'text').")


class YouTubeRelatedInput(BaseModel):
    video_id: str = Field(description="YouTube video id or a full watch URL.")
    cursor: Optional[str] = Field(None, description="Pagination cursor from a prior response.")


class YouTubeChannelSearchInput(BaseModel):
    query: str = Field(description="The channel search query.")
    cursor: Optional[str] = Field(None, description="Pagination cursor from a prior response.")


class YouTubeChannelInput(BaseModel):
    channel_id: str = Field(description="YouTube channel id, @handle, or channel URL.")


class YouTubeChannelVideosInput(BaseModel):
    channel_id: str = Field(description="YouTube channel id.")
    cursor: Optional[str] = Field(None, description="Pagination cursor from a prior response.")


class YouTubeChannelShortsInput(BaseModel):
    channel_id: str = Field(description="YouTube channel id.")
    cursor: Optional[str] = Field(None, description="Pagination cursor from a prior response.")


class YouTubeChannelCommunityInput(BaseModel):
    channel_id: str = Field(description="YouTube channel id.")
    cursor: Optional[str] = Field(None, description="Pagination cursor from a prior response.")


class YouTubeChannelResolveInput(BaseModel):
    channel: str = Field(description="A channel @handle or channel URL to resolve to a channel id.")


class YouTubeStreamsInput(BaseModel):
    video_id: str = Field(description="YouTube video id or a full watch URL.")


# Reddit
# /reddit/search takes ONLY query + cursor. `type` and `sort` were never real:
# the API strips unknown fields, so they filtered nothing while making the agent
# believe the result set was narrowed. Removed rather than kept as no-ops.
class RedditSearchInput(BaseModel):
    query: str = Field(description="The Reddit search query.")
    cursor: Optional[str] = Field(None, description="Pagination cursor: pass 'next_cursor' from a prior response.")


class RedditSearchSuggestionsInput(BaseModel):
    query: str = Field(description="The partial or full term to get Reddit search suggestions for.")


class RedditPostInput(BaseModel):
    url: Optional[str] = Field(None, description="Full URL of the Reddit post. Provide this or post_id.")
    post_id: Optional[str] = Field(
        None, description="Post fullname ('t3_1v6ngaf') or bare base-36 id. Provide this or url."
    )


# Comment and user-feed sorts are UPPERCASE and passed through verbatim.
_REDDIT_SORT_DESC = "Sort order, UPPERCASE: 'HOT', 'NEW', 'TOP', 'BEST', or 'CONTROVERSIAL'."


class RedditPostCommentsInput(BaseModel):
    post_id: str = Field(description="Post fullname ('t3_1v6ngaf'), bare id, or post URL.")
    sort: Optional[str] = Field(None, description=_REDDIT_SORT_DESC + " Defaults to 'TOP'.")
    cursor: Optional[str] = Field(None, description="Pagination cursor: pass 'next_cursor' from a prior response.")


class RedditCommentRepliesInput(BaseModel):
    post_id: str = Field(description="Post fullname ('t3_1v6ngaf'), bare id, or post URL.")
    cursor: str = Field(
        description="Required here: the 'reply_cursor' of a comment returned by the Reddit post comments tool."
    )
    sort: Optional[str] = Field(None, description=_REDDIT_SORT_DESC + " Defaults to 'TOP'.")


class RedditSubredditInput(BaseModel):
    subreddit: str = Field(description="Bare subreddit name without the 'r/' prefix, e.g. 'AskReddit'.")


class RedditSubredditPostsInput(BaseModel):
    subreddit: str = Field(description="Bare subreddit name without the 'r/' prefix.")
    sort: Optional[str] = Field(
        None,
        description="Feed sort, UPPERCASE: 'BEST', 'HOT', 'NEW', 'TOP', 'CONTROVERSIAL', or 'RISING' (the only endpoint accepting RISING). Defaults to 'HOT'.",
    )
    cursor: Optional[str] = Field(None, description="Pagination cursor: pass 'next_cursor' from a prior response.")


class RedditUserInput(BaseModel):
    username: str = Field(description="Bare Reddit handle without the 'u/' prefix, e.g. 'spez'.")


class RedditUserPostsInput(BaseModel):
    username: str = Field(description="Bare Reddit handle without the 'u/' prefix.")
    sort: Optional[str] = Field(None, description=_REDDIT_SORT_DESC + " Defaults to 'NEW'.")
    cursor: Optional[str] = Field(None, description="Pagination cursor: pass 'next_cursor' from a prior response.")


class RedditUserCommentsInput(BaseModel):
    username: str = Field(description="Bare Reddit handle without the 'u/' prefix.")
    sort: Optional[str] = Field(None, description=_REDDIT_SORT_DESC + " Defaults to 'NEW'.")
    cursor: Optional[str] = Field(None, description="Pagination cursor: pass 'next_cursor' from a prior response.")


class RedditPopularInput(BaseModel):
    cursor: Optional[str] = Field(None, description="Pagination cursor: pass 'next_cursor' from a prior response.")


class RedditTrendingInput(BaseModel):
    """No parameters."""


# TikTok
class TikTokProfileInput(BaseModel):
    username: Optional[str] = Field(None, description="TikTok username (without @). Provide this or sec_user_id.")
    sec_user_id: Optional[str] = Field(None, description="TikTok secUid. Provide this or username.")


class TikTokUserPostsInput(BaseModel):
    sec_user_id: str = Field(description="TikTok secUid of the user.")
    cursor: Optional[str] = Field(None, description="Pagination cursor.")
    count: Optional[int] = Field(None, description="Number of posts to return.")
    sort_type: Optional[str] = Field(None, description="Sort order for posts.")


class TikTokVideoInput(BaseModel):
    video_id: str = Field(description="TikTok video id.")


class TikTokVideoCommentsInput(BaseModel):
    video_id: str = Field(description="TikTok video id.")
    cursor: Optional[str] = Field(None, description="Pagination cursor.")
    count: Optional[int] = Field(None, description="Number of comments to return.")


class TikTokCommentRepliesInput(BaseModel):
    video_id: str = Field(description="TikTok video id.")
    comment_id: str = Field(description="Parent comment id.")
    cursor: Optional[str] = Field(None, description="Pagination cursor.")
    count: Optional[int] = Field(None, description="Number of replies to return.")


class TikTokSearchVideosInput(BaseModel):
    keyword: str = Field(description="Search keyword.")
    cursor: Optional[str] = Field(None, description="Pagination cursor.")
    count: Optional[int] = Field(None, description="Number of videos to return.")
    sort_type: Optional[str] = Field(None, description="Sort order for results.")
    publish_time: Optional[str] = Field(None, description="Publish-time filter.")


class TikTokSearchUsersInput(BaseModel):
    keyword: str = Field(description="Search keyword.")
    cursor: Optional[str] = Field(None, description="Pagination cursor.")
    count: Optional[int] = Field(None, description="Number of users to return.")


class TikTokHashtagInput(BaseModel):
    hashtag_name: Optional[str] = Field(None, description="Hashtag name (without #). Provide this or hashtag_id.")
    hashtag_id: Optional[str] = Field(None, description="Hashtag id. Provide this or hashtag_name.")


class TikTokHashtagVideosInput(BaseModel):
    hashtag_id: str = Field(description="Hashtag id.")
    cursor: Optional[str] = Field(None, description="Pagination cursor.")
    count: Optional[int] = Field(None, description="Number of videos to return.")


class TikTokUserFollowersInput(BaseModel):
    sec_user_id: str = Field(description="TikTok secUid of the user.")
    count: Optional[int] = Field(None, description="Number of followers to return.")
    page_token: Optional[str] = Field(None, description="Pagination token.")
    min_time: Optional[int] = Field(None, description="Minimum timestamp filter.")


class TikTokUserFollowingsInput(BaseModel):
    sec_user_id: str = Field(description="TikTok secUid of the user.")
    count: Optional[int] = Field(None, description="Number of followings to return.")
    page_token: Optional[str] = Field(None, description="Pagination token.")
    min_time: Optional[int] = Field(None, description="Minimum timestamp filter.")


# Instagram
class InstagramProfileInput(BaseModel):
    username: Optional[str] = Field(None, description="Instagram username. Provide this or user_id.")
    user_id: Optional[str] = Field(None, description="Instagram user id. Provide this or username.")


class InstagramUserPostsInput(BaseModel):
    username: Optional[str] = Field(None, description="Instagram username. Provide this or user_id.")
    user_id: Optional[str] = Field(None, description="Instagram user id. Provide this or username.")
    count: Optional[int] = Field(None, description="Number of posts to return.")
    cursor: Optional[str] = Field(None, description="Pagination cursor.")


class InstagramUserReelsInput(BaseModel):
    username: Optional[str] = Field(None, description="Instagram username. Provide this or user_id.")
    user_id: Optional[str] = Field(None, description="Instagram user id. Provide this or username.")
    count: Optional[int] = Field(None, description="Number of reels to return.")
    cursor: Optional[str] = Field(None, description="Pagination cursor.")


class InstagramUserTaggedInput(BaseModel):
    username: Optional[str] = Field(None, description="Instagram username. Provide this or user_id.")
    user_id: Optional[str] = Field(None, description="Instagram user id. Provide this or username.")
    count: Optional[int] = Field(None, description="Number of tagged posts to return.")
    cursor: Optional[str] = Field(None, description="Pagination cursor.")


class InstagramUserStoriesInput(BaseModel):
    username: Optional[str] = Field(None, description="Instagram username. Provide this or user_id.")
    user_id: Optional[str] = Field(None, description="Instagram user id. Provide this or username.")


class InstagramPostInput(BaseModel):
    url: Optional[str] = Field(None, description="Post URL. Provide one of url, media_id, or shortcode.")
    media_id: Optional[str] = Field(None, description="Post media id. Provide one of url, media_id, or shortcode.")
    shortcode: Optional[str] = Field(None, description="Post shortcode. Provide one of url, media_id, or shortcode.")


class InstagramPostCommentsInput(BaseModel):
    shortcode: Optional[str] = Field(None, description="Post shortcode. Provide this or url.")
    url: Optional[str] = Field(None, description="Post URL. Provide this or shortcode.")
    cursor: Optional[str] = Field(None, description="Pagination cursor.")
    sort_order: Optional[str] = Field(None, description="Comment sort order.")


class InstagramCommentRepliesInput(BaseModel):
    media_id: str = Field(description="Post media id.")
    comment_id: str = Field(description="Parent comment id.")
    cursor: Optional[str] = Field(None, description="Pagination cursor.")


class InstagramSearchUsersInput(BaseModel):
    keyword: str = Field(description="Search keyword.")
    cursor: Optional[str] = Field(None, description="Pagination cursor.")


class InstagramSearchHashtagsInput(BaseModel):
    keyword: str = Field(description="Search keyword.")
    cursor: Optional[str] = Field(None, description="Pagination cursor.")


class InstagramUserFollowersInput(BaseModel):
    username: Optional[str] = Field(None, description="Instagram username. Provide this or user_id.")
    user_id: Optional[str] = Field(None, description="Instagram user id. Provide this or username.")
    count: Optional[int] = Field(None, description="Number of followers to return.")
    cursor: Optional[str] = Field(None, description="Pagination cursor.")


class InstagramUserFollowingsInput(BaseModel):
    username: Optional[str] = Field(None, description="Instagram username. Provide this or user_id.")
    user_id: Optional[str] = Field(None, description="Instagram user id. Provide this or username.")
    count: Optional[int] = Field(None, description="Number of followings to return.")
    cursor: Optional[str] = Field(None, description="Pagination cursor.")


# X (Twitter)
_X_SCREEN_NAME_DESC = "X handle WITHOUT the leading '@', e.g. 'elonmusk'."
_X_TWEET_ID_DESC = "Tweet id as a STRING, e.g. '1808168603721650364'."


class XSearchInput(BaseModel):
    search: str = Field(
        description="The search query. The field is named 'search', not 'query'."
    )
    search_type: Optional[str] = Field(
        None,
        description="Capitalized result tab: 'Top' (default), 'Latest', 'People', 'Photos', or 'Videos'.",
    )
    cursor: Optional[str] = Field(None, description="Pagination cursor: pass 'next_cursor' from a prior response.")


class XTweetInput(BaseModel):
    tweet_id: str = Field(description=_X_TWEET_ID_DESC)


class XTweetCommentsInput(BaseModel):
    tweet_id: str = Field(description=_X_TWEET_ID_DESC)
    rank: Optional[str] = Field(
        None, description="Lowercase ranking: 'top' (default, ranked) or 'latest' (chronological)."
    )
    cursor: Optional[str] = Field(None, description="Pagination cursor from a prior response.")


class XTweetRetweetersInput(BaseModel):
    tweet_id: str = Field(description=_X_TWEET_ID_DESC)
    cursor: Optional[str] = Field(None, description="Pagination cursor from a prior response.")


class XUserInput(BaseModel):
    screen_name: str = Field(description=_X_SCREEN_NAME_DESC)


class XUserTweetsInput(BaseModel):
    screen_name: str = Field(description=_X_SCREEN_NAME_DESC)
    cursor: Optional[str] = Field(None, description="Pagination cursor from a prior response.")


class XUserRepliesInput(BaseModel):
    screen_name: str = Field(description=_X_SCREEN_NAME_DESC)
    cursor: Optional[str] = Field(None, description="Pagination cursor from a prior response.")


class XUserMediaInput(BaseModel):
    screen_name: str = Field(description=_X_SCREEN_NAME_DESC)
    cursor: Optional[str] = Field(None, description="Pagination cursor from a prior response.")


class XUserFollowersInput(BaseModel):
    screen_name: str = Field(description=_X_SCREEN_NAME_DESC)
    cursor: Optional[str] = Field(None, description="Pagination cursor from a prior response.")


class XUserFollowingsInput(BaseModel):
    screen_name: str = Field(description=_X_SCREEN_NAME_DESC)
    cursor: Optional[str] = Field(None, description="Pagination cursor from a prior response.")


class XTrendingInput(BaseModel):
    country: Optional[str] = Field(
        None,
        description="Country NAME, not an ISO code, e.g. 'UnitedStates' (the default) or 'Japan'.",
    )


# LinkedIn
# Only the 9 live endpoints are exposed. /linkedin/person/contact, /company/people,
# /company/jobs, /search/people and /search/posts were retired upstream and return
# 410 unbilled, so they are deliberately absent - an agent must not be able to call them.
class LinkedInPersonInput(BaseModel):
    username: Optional[str] = Field(
        None, description="Public profile handle, e.g. 'williamhgates'. Provide this or url."
    )
    url: Optional[str] = Field(None, description="Full LinkedIn profile URL. Provide this or username.")


class LinkedInPersonAboutInput(BaseModel):
    username: Optional[str] = Field(None, description="Public profile handle. Provide this or url.")
    url: Optional[str] = Field(None, description="Full LinkedIn profile URL. Provide this or username.")


class LinkedInPersonPostsInput(BaseModel):
    username: Optional[str] = Field(None, description="Public profile handle. Provide this or url.")
    url: Optional[str] = Field(None, description="Full LinkedIn profile URL. Provide this or username.")
    type: Optional[str] = Field(
        None,
        description="Feed type: 'posts' (default, own posts), 'comments' (posts commented on), or 'reactions' (posts reacted to).",
    )
    cursor: Optional[str] = Field(None, description="Opaque cursor: pass 'next_cursor' from a prior response.")


class LinkedInCompanyInput(BaseModel):
    company: Optional[str] = Field(
        None, description="Company universal name or slug, e.g. 'microsoft'. Provide this or url."
    )
    url: Optional[str] = Field(None, description="Full LinkedIn company URL. Provide this or company.")


class LinkedInCompanyPostsInput(BaseModel):
    company: Optional[str] = Field(None, description="Company universal name or slug. Provide this or url.")
    url: Optional[str] = Field(None, description="Full LinkedIn company URL. Provide this or company.")
    cursor: Optional[str] = Field(None, description="Opaque cursor: pass 'next_cursor' from a prior response.")


class LinkedInSearchJobsInput(BaseModel):
    search: str = Field(
        description="Job keywords, e.g. 'software engineer'. The field is named 'search', not 'query'."
    )
    location: Optional[str] = Field(None, description="Geographic filter; omit to search everywhere.")
    cursor: Optional[str] = Field(None, description="Opaque cursor: pass 'next_cursor' from a prior response.")


class LinkedInJobInput(BaseModel):
    job_id: Optional[str] = Field(None, description="LinkedIn job id, e.g. '4415427228'. Provide this or url.")
    url: Optional[str] = Field(None, description="Full LinkedIn job URL. Provide this or job_id.")


class LinkedInPostInput(BaseModel):
    post_id: Optional[str] = Field(
        None,
        description="Post id or activity urn ('7488618410256523265' or 'urn:li:activity:...'). Provide this or url.",
    )
    url: Optional[str] = Field(None, description="Full LinkedIn post URL. Provide this or post_id.")


class LinkedInPostCommentsInput(BaseModel):
    post_id: Optional[str] = Field(None, description="Post id or activity urn. Provide this or url.")
    url: Optional[str] = Field(None, description="Full LinkedIn post URL. Provide this or post_id.")
    page: Optional[int] = Field(
        None,
        description="1-based PAGE NUMBER, not a cursor: the only LinkedIn endpoint that pages this way. Defaults to 1.",
    )


# TikTok Shop
_TTS_REGION_FULL_DESC = (
    "Marketplace region: 'US' (default), 'GB', 'SG', 'MY', 'PH', 'TH', 'VN', or 'ID'."
)


class TikTokShopSearchInput(BaseModel):
    search: str = Field(
        description="The product keyword. The field is named 'search', not 'query'."
    )
    cursor: Optional[str] = Field(
        None, description="Opaque cursor: pass 'next_cursor' from a prior response. Invalid cursors 400 unbilled."
    )


class TikTokShopSearchSuggestionsInput(BaseModel):
    search: str = Field(description="The partial keyword to autocomplete. Named 'search', not 'query'.")
    region: Optional[str] = Field(None, description=_TTS_REGION_FULL_DESC)


class TikTokShopProductInput(BaseModel):
    product_id: str = Field(description="TikTok Shop product id, 6-25 digits, e.g. '1732293553906094315'.")
    region: Optional[str] = Field(None, description=_TTS_REGION_FULL_DESC)


class TikTokShopProductReviewsInput(BaseModel):
    product_id: str = Field(description="TikTok Shop product id, 6-25 digits.")
    page: Optional[int] = Field(None, description="1-based page number, 1-500. Defaults to 1.")
    page_size: Optional[int] = Field(None, description="Reviews per page, 1-200. Defaults to 20.")
    sort: Optional[str] = Field(
        None,
        description="'relevant' (default, text-complete and image-heavy) or 'recent' (fresher but text-sparse).",
    )
    rating: Optional[int] = Field(None, description="Only reviews with this star rating, 1-5. Omit for no filter.")
    has_media: Optional[bool] = Field(
        None,
        description="Only reviews with a photo or video. Shares one upstream filter slot with verified_only, and wins when both are set.",
    )
    verified_only: Optional[bool] = Field(None, description="Only verified purchases. Ignored when has_media is true.")
    region: Optional[str] = Field(None, description=_TTS_REGION_FULL_DESC)


class TikTokShopCategoriesInput(BaseModel):
    """No parameters."""


class TikTokShopCategoryProductsInput(BaseModel):
    category_id: str = Field(
        description="Category id, 4-20 digits, from the TikTok Shop categories tool. Level 1 or 2 both work."
    )
    cursor: Optional[str] = Field(None, description="Opaque cursor: pass 'next_cursor' from a prior response.")
    region: Optional[str] = Field(
        None, description="Listing region: only 'US' (default) or 'GB' here, not the full 8-region set."
    )


class TikTokShopShopProductsInput(BaseModel):
    shop_id: str = Field(description="TikTok Shop seller id, 6-25 digits, e.g. '7495514739648989419'.")
    cursor: Optional[str] = Field(None, description="Opaque cursor: pass 'next_cursor' from a prior response.")
    region: Optional[str] = Field(None, description=_TTS_REGION_FULL_DESC)


class TikTokShopResolveInput(BaseModel):
    url: str = Field(
        description="A TikTok Shop URL: shop.tiktok.com pdp or store pages, tiktok.com/view/product or /view/shop, affiliate-*.tiktok.com share links, or vt.tiktok.com / tiktok.com/t short links."
    )


def _run(call: Callable[[], Dict[str, Any]]) -> Dict[str, Any]:
    """Run a Scavio SDK call, returning its JSON dict or an ``{"error": ...}`` dict."""
    try:
        return call()
    except Exception as exc:  # noqa: BLE001 - surface any SDK/network error to the agent
        return {"error": str(exc)}


def build_scavio_toolkit(
    api_key: Optional[str] = None,
    *,
    enable_google: bool = True,
    enable_amazon: bool = True,
    enable_walmart: bool = True,
    enable_youtube: bool = True,
    enable_reddit: bool = True,
    enable_tiktok: bool = True,
    enable_tiktok_shop: bool = True,
    enable_instagram: bool = True,
    enable_x: bool = True,
    enable_linkedin: bool = True,
    all: bool = False,
) -> "ExperimentalToolkit":
    """Build a Composio custom toolkit exposing Scavio search tools.

    Scavio is a single Search API over Google, YouTube, Amazon, Walmart, Reddit,
    TikTok, TikTok Shop, Instagram, X and LinkedIn; this toolkit covers every live
    endpoint of all ten. Each provider is gated by an ``enable_*`` flag so you
    expose only the tools your agent needs.

    Args:
        api_key: Scavio API key. Falls back to the ``SCAVIO_API_KEY`` env var.
        enable_google: Register the 14 Google v2 tools (web search, AI Mode, Maps,
            Shopping, Flights, Hotels, News, Trends, Trending). Defaults to True.
        enable_amazon: Register the Amazon search, product and offers tools. Defaults to True.
        enable_walmart: Register the Walmart search and product tools. Defaults to True.
        enable_youtube: Register the 15 YouTube tools (search, shorts, suggestions, video,
            comments, transcript, related, channel, streams, and more). Defaults to True.
        enable_reddit: Register the 12 Reddit tools (1 credit each). Defaults to True.
        enable_tiktok: Register the 11 TikTok tools. Defaults to True.
        enable_tiktok_shop: Register the 8 TikTok Shop tools. Defaults to True.
        enable_instagram: Register the 12 Instagram tools. Defaults to True.
        enable_x: Register the 11 X (Twitter) tools. Defaults to True.
        enable_linkedin: Register the 9 live LinkedIn tools. Defaults to True.
        all: Register every tool, ignoring the individual flags. Defaults to False.

    Returns:
        An ``ExperimentalToolkit`` to pass to
        ``composio.create(..., experimental={"custom_toolkits": [toolkit]})``.
    """
    key = api_key or os.getenv("SCAVIO_API_KEY")
    client = ScavioClient(api_key=key)

    toolkit = ExperimentalToolkit(
        slug="SCAVIO",
        name="Scavio",
        description=(
            "Real-time structured search over Google, YouTube, Amazon, Walmart, "
            "Reddit, TikTok, TikTok Shop, Instagram, X and LinkedIn."
        ),
    )

    def dump(model: BaseModel) -> Dict[str, Any]:
        return model.model_dump(exclude_none=True)

    if all or enable_google:

        @toolkit.tool()
        def scavio_google_search(input: GoogleSearchInput, ctx: Any = None) -> dict:
            """Search Google for real-time web results: organic_results (with link and snippet), ads, top stories, related questions and the AI Overview when present. Response is flat, with no data wrapper. Costs 1 credit."""
            return _run(lambda: client.google.search(**dump(input)))

        @toolkit.tool()
        def scavio_google_ai_mode(input: GoogleAiModeInput, ctx: Any = None) -> dict:
            """Run a query through Google AI Mode and get the generated answer as text_blocks plus its references and shopping_results. Costs 1 credit."""
            return _run(lambda: client.google.ai_mode(**dump(input)))

        @toolkit.tool()
        def scavio_google_maps_search(input: GoogleMapsSearchInput, ctx: Any = None) -> dict:
            """Search Google Maps for local businesses and places, returning local_results with names, ratings, addresses and place ids. Costs 1 credit."""
            return _run(lambda: client.google.maps_search(**dump(input)))

        @toolkit.tool()
        def scavio_google_maps_place(input: GoogleMapsPlaceInput, ctx: Any = None) -> dict:
            """Fetch full Google Maps place details by place_id or data_cid. Costs 1 credit."""
            return _run(lambda: client.google.maps_place(**dump(input)))

        @toolkit.tool()
        def scavio_google_maps_reviews(input: GoogleMapsReviewsInput, ctx: Any = None) -> dict:
            """List Google Maps reviews for a place by data_id or place_id. Reviews cannot be filtered by keyword or topic. Costs 1 credit."""
            return _run(lambda: client.google.maps_reviews(**dump(input)))

        @toolkit.tool()
        def scavio_google_shopping(input: GoogleShoppingInput, ctx: Any = None) -> dict:
            """Search Google Shopping for products and prices, returning shopping_results plus filters you can re-submit as shoprs. Costs 1 credit."""
            return _run(lambda: client.google.shopping(**dump(input)))

        @toolkit.tool()
        def scavio_google_shopping_product(input: GoogleShoppingProductInput, ctx: Any = None) -> dict:
            """Fetch one Google Shopping product with its store offers. Requires one of catalog_id (plus query), immersive_product_page_token, page_token, or product_id. Costs 1 credit."""
            return _run(lambda: client.google.shopping_product(**dump(input)))

        @toolkit.tool()
        def scavio_google_shopping_stores(input: GoogleShoppingStoresInput, ctx: Any = None) -> dict:
            """Page through the remaining store offers for a Google Shopping product, using the catalog_id and a next_page_token. Costs 1 credit."""
            return _run(lambda: client.google.shopping_stores(**dump(input)))

        @toolkit.tool()
        def scavio_google_flights(input: GoogleFlightsInput, ctx: Any = None) -> dict:
            """Search Google Flights between two airports, returning best_flights and other_flights with prices, durations and legs. Costs 1 credit."""
            return _run(lambda: client.google.flights(**dump(input)))

        @toolkit.tool()
        def scavio_google_hotels(input: GoogleHotelsInput, ctx: Any = None) -> dict:
            """Search Google Hotels for a destination and date range, returning properties with rates, ratings and a detail_token for each. Costs 1 credit."""
            return _run(lambda: client.google.hotels(**dump(input)))

        @toolkit.tool()
        def scavio_google_hotels_detail(input: GoogleHotelsDetailInput, ctx: Any = None) -> dict:
            """Fetch one Google Hotels property and its booking_sources using a detail_token from a hotels search. The dates must be re-sent. Costs 1 credit."""
            return _run(lambda: client.google.hotels_detail(**dump(input)))

        @toolkit.tool()
        def scavio_google_news(input: GoogleNewsInput, ctx: Any = None) -> dict:
            """Fetch Google News results. Supply EXACTLY ONE driver: query, topic_token, section_token, story_token, publication_token, or kgmid. Costs 1 credit."""
            return _run(lambda: client.google.news(**dump(input)))

        @toolkit.tool()
        def scavio_google_trends(input: GoogleTrendsInput, ctx: Any = None) -> dict:
            """Fetch Google Trends interest over time and by region for a term. Costs 1 credit."""
            return _run(lambda: client.google.trends(**dump(input)))

        @toolkit.tool()
        def scavio_google_trending(input: GoogleTrendingInput, ctx: Any = None) -> dict:
            """List Google Trending Now searches for a country. This endpoint takes a geo instead of a query. Costs 1 credit."""
            return _run(lambda: client.google.trending(**dump(input)))

    if all or enable_amazon:

        @toolkit.tool()
        def scavio_amazon_search(input: AmazonSearchInput, ctx: Any = None) -> dict:
            """Search Amazon for products matching a query. Results are unsorted and cannot be filtered. Costs 1 credit."""
            return _run(lambda: client.amazon.search(**dump(input)))

        @toolkit.tool()
        def scavio_amazon_product(input: AmazonProductInput, ctx: Any = None) -> dict:
            """Fetch full Amazon product details by ASIN. price is the buy-box price only. Costs 1 credit."""
            return _run(lambda: client.amazon.product(**dump(input)))

        @toolkit.tool()
        def scavio_amazon_offers(input: AmazonOffersInput, ctx: Any = None) -> dict:
            """List every seller offer for an Amazon ASIN: price, seller, condition, shipping, buy box. Page 1 only. Costs 1 credit."""
            return _run(lambda: client.amazon.offers(**dump(input)))

    if all or enable_walmart:

        @toolkit.tool()
        def scavio_walmart_search(input: WalmartSearchInput, ctx: Any = None) -> dict:
            """Search Walmart for products matching a query. Costs 1 credit."""
            return _run(lambda: client.walmart.search(**dump(input)))

        @toolkit.tool()
        def scavio_walmart_product(input: WalmartProductInput, ctx: Any = None) -> dict:
            """Fetch full Walmart product details by product id. Costs 1 credit."""
            return _run(lambda: client.walmart.product(**dump(input)))

    if all or enable_youtube:

        @toolkit.tool()
        def scavio_youtube_search(input: YouTubeSearchInput, ctx: Any = None) -> dict:
            """Search YouTube for videos, channels, or playlists. Costs 2 credits."""
            return _run(lambda: client.youtube.search(**dump(input)))

        @toolkit.tool()
        def scavio_youtube_shorts(input: YouTubeShortsInput, ctx: Any = None) -> dict:
            """Search YouTube Shorts. Costs 2 credits."""
            return _run(lambda: client.youtube.shorts(**dump(input)))

        @toolkit.tool()
        def scavio_youtube_suggestions(input: YouTubeSuggestionsInput, ctx: Any = None) -> dict:
            """Get YouTube search autocomplete suggestions for a partial query. Costs 1 credit."""
            return _run(lambda: client.youtube.suggestions(**dump(input)))

        @toolkit.tool()
        def scavio_youtube_video(input: YouTubeVideoInput, ctx: Any = None) -> dict:
            """Fetch full metadata for a YouTube video by id or watch URL. Costs 1 credit."""
            return _run(lambda: client.youtube.video(**dump(input)))

        @toolkit.tool()
        def scavio_youtube_comments(input: YouTubeCommentsInput, ctx: Any = None) -> dict:
            """List top-level comments on a YouTube video. Costs 1 credit."""
            return _run(lambda: client.youtube.comments(**dump(input)))

        @toolkit.tool()
        def scavio_youtube_comment_replies(input: YouTubeCommentRepliesInput, ctx: Any = None) -> dict:
            """List replies to a YouTube comment using its reply cursor. Costs 1 credit."""
            return _run(lambda: client.youtube.comment_replies(**dump(input)))

        @toolkit.tool()
        def scavio_youtube_transcript(input: YouTubeTranscriptInput, ctx: Any = None) -> dict:
            """Fetch the transcript or timed captions for a YouTube video. Costs 8 credits."""
            return _run(lambda: client.youtube.transcript(**dump(input)))

        @toolkit.tool()
        def scavio_youtube_related(input: YouTubeRelatedInput, ctx: Any = None) -> dict:
            """List videos related to a YouTube video. Costs 1 credit."""
            return _run(lambda: client.youtube.related(**dump(input)))

        @toolkit.tool()
        def scavio_youtube_channel_search(input: YouTubeChannelSearchInput, ctx: Any = None) -> dict:
            """Search YouTube channels by keyword. Costs 1 credit."""
            return _run(lambda: client.youtube.channel_search(**dump(input)))

        @toolkit.tool()
        def scavio_youtube_channel(input: YouTubeChannelInput, ctx: Any = None) -> dict:
            """Fetch YouTube channel details by id, @handle, or URL. Costs 1 credit."""
            return _run(lambda: client.youtube.channel(**dump(input)))

        @toolkit.tool()
        def scavio_youtube_channel_videos(input: YouTubeChannelVideosInput, ctx: Any = None) -> dict:
            """List videos uploaded by a YouTube channel. Costs 1 credit."""
            return _run(lambda: client.youtube.channel_videos(**dump(input)))

        @toolkit.tool()
        def scavio_youtube_channel_shorts(input: YouTubeChannelShortsInput, ctx: Any = None) -> dict:
            """List Shorts posted by a YouTube channel. Costs 1 credit."""
            return _run(lambda: client.youtube.channel_shorts(**dump(input)))

        @toolkit.tool()
        def scavio_youtube_channel_community(input: YouTubeChannelCommunityInput, ctx: Any = None) -> dict:
            """List community posts from a YouTube channel. Costs 1 credit."""
            return _run(lambda: client.youtube.channel_community(**dump(input)))

        @toolkit.tool()
        def scavio_youtube_channel_resolve(input: YouTubeChannelResolveInput, ctx: Any = None) -> dict:
            """Resolve a YouTube @handle or channel URL to a channel id. Costs 1 credit."""
            return _run(lambda: client.youtube.channel_resolve(**dump(input)))

        @toolkit.tool()
        def scavio_youtube_streams(input: YouTubeStreamsInput, ctx: Any = None) -> dict:
            """Fetch playable or downloadable stream formats for a YouTube video. Costs 3 credits."""
            return _run(lambda: client.youtube.streams(**dump(input)))

    if all or enable_reddit:

        @toolkit.tool()
        def scavio_reddit_search(input: RedditSearchInput, ctx: Any = None) -> dict:
            """Search Reddit posts. Returns data.results with next_cursor and has_more; page with cursor. Results cannot be filtered or sorted. Costs 1 credit."""
            return _run(lambda: client.reddit.search(**dump(input)))

        @toolkit.tool()
        def scavio_reddit_search_suggestions(input: RedditSearchSuggestionsInput, ctx: Any = None) -> dict:
            """Get Reddit search autocomplete suggestions for a term. Returns data.suggestions (plain strings) and total_count. Costs 1 credit."""
            return _run(lambda: client.reddit.search_suggestions(**dump(input)))

        @toolkit.tool()
        def scavio_reddit_post(input: RedditPostInput, ctx: Any = None) -> dict:
            """Fetch one Reddit post by URL or post_id. Returns a flat post object under data (post_id, title, text, url, subreddit, author, score, upvote_ratio, num_comments, created_at, is_nsfw, is_video, thumbnail, media); comments are NOT included, use the Reddit post comments tool for those. Costs 1 credit."""
            return _run(lambda: client.reddit.post(**dump(input)))

        @toolkit.tool()
        def scavio_reddit_post_comments(input: RedditPostCommentsInput, ctx: Any = None) -> dict:
            """List top-level comments on a Reddit post. Returns data.comments with next_cursor and has_more; each comment carries a reply_cursor for the Reddit comment replies tool. Costs 1 credit."""
            return _run(lambda: client.reddit.post_comments(**dump(input)))

        @toolkit.tool()
        def scavio_reddit_comment_replies(input: RedditCommentRepliesInput, ctx: Any = None) -> dict:
            """List replies under a Reddit comment. The cursor is REQUIRED and must be a reply_cursor from the Reddit post comments tool. Costs 1 credit."""
            return _run(lambda: client.reddit.comment_replies(**dump(input)))

        @toolkit.tool()
        def scavio_reddit_subreddit(input: RedditSubredditInput, ctx: Any = None) -> dict:
            """Fetch a subreddit's profile: title, description, subscribers, active_count, icon, banner and created_at. Costs 1 credit."""
            return _run(lambda: client.reddit.subreddit(**dump(input)))

        @toolkit.tool()
        def scavio_reddit_subreddit_posts(input: RedditSubredditPostsInput, ctx: Any = None) -> dict:
            """List a subreddit's feed. Returns data.posts with next_cursor and has_more. This feed shape has no text or thumbnail; fetch a post for its body. Costs 1 credit."""
            return _run(lambda: client.reddit.subreddit_posts(**dump(input)))

        @toolkit.tool()
        def scavio_reddit_user(input: RedditUserInput, ctx: Any = None) -> dict:
            """Fetch a Reddit user's profile: karma, post_karma, comment_karma, description, avatar and created_at. Costs 1 credit."""
            return _run(lambda: client.reddit.user(**dump(input)))

        @toolkit.tool()
        def scavio_reddit_user_posts(input: RedditUserPostsInput, ctx: Any = None) -> dict:
            """List posts submitted by a Reddit user. Returns data.posts with next_cursor and has_more. Costs 1 credit."""
            return _run(lambda: client.reddit.user_posts(**dump(input)))

        @toolkit.tool()
        def scavio_reddit_user_comments(input: RedditUserCommentsInput, ctx: Any = None) -> dict:
            """List comments written by a Reddit user. Returns data.comments, each with the parent post id and title. Costs 1 credit."""
            return _run(lambda: client.reddit.user_comments(**dump(input)))

        @toolkit.tool()
        def scavio_reddit_popular(input: RedditPopularInput, ctx: Any = None) -> dict:
            """List posts from Reddit's popular feed. Returns data.posts with next_cursor and has_more. Costs 1 credit."""
            return _run(lambda: client.reddit.popular(**dump(input)))

        @toolkit.tool()
        def scavio_reddit_trending(input: RedditTrendingInput, ctx: Any = None) -> dict:
            """List Reddit's currently trending searches. Takes no parameters. Returns data.trending and total_count. Costs 1 credit."""
            return _run(lambda: client.reddit.trending(**dump(input)))

    if all or enable_tiktok:

        @toolkit.tool()
        def scavio_tiktok_profile(input: TikTokProfileInput, ctx: Any = None) -> dict:
            """Fetch a TikTok user profile by username or secUid. Costs 1 credit."""
            return _run(lambda: client.tiktok.profile(**dump(input)))

        @toolkit.tool()
        def scavio_tiktok_user_posts(input: TikTokUserPostsInput, ctx: Any = None) -> dict:
            """List a TikTok user's posts by secUid. Costs 1 credit."""
            return _run(lambda: client.tiktok.user_posts(**dump(input)))

        @toolkit.tool()
        def scavio_tiktok_video(input: TikTokVideoInput, ctx: Any = None) -> dict:
            """Fetch a TikTok video by id. Costs 1 credit."""
            return _run(lambda: client.tiktok.video(**dump(input)))

        @toolkit.tool()
        def scavio_tiktok_video_comments(input: TikTokVideoCommentsInput, ctx: Any = None) -> dict:
            """List comments on a TikTok video. Costs 1 credit."""
            return _run(lambda: client.tiktok.video_comments(**dump(input)))

        @toolkit.tool()
        def scavio_tiktok_comment_replies(input: TikTokCommentRepliesInput, ctx: Any = None) -> dict:
            """List replies to a TikTok video comment. Costs 1 credit."""
            return _run(lambda: client.tiktok.comment_replies(**dump(input)))

        @toolkit.tool()
        def scavio_tiktok_search_videos(input: TikTokSearchVideosInput, ctx: Any = None) -> dict:
            """Search TikTok videos by keyword. Costs 1 credit."""
            return _run(lambda: client.tiktok.search_videos(**dump(input)))

        @toolkit.tool()
        def scavio_tiktok_search_users(input: TikTokSearchUsersInput, ctx: Any = None) -> dict:
            """Search TikTok users by keyword. Costs 1 credit."""
            return _run(lambda: client.tiktok.search_users(**dump(input)))

        @toolkit.tool()
        def scavio_tiktok_hashtag(input: TikTokHashtagInput, ctx: Any = None) -> dict:
            """Fetch a TikTok hashtag by name or id. Costs 1 credit."""
            return _run(lambda: client.tiktok.hashtag(**dump(input)))

        @toolkit.tool()
        def scavio_tiktok_hashtag_videos(input: TikTokHashtagVideosInput, ctx: Any = None) -> dict:
            """List videos for a TikTok hashtag by id. Costs 1 credit."""
            return _run(lambda: client.tiktok.hashtag_videos(**dump(input)))

        @toolkit.tool()
        def scavio_tiktok_user_followers(input: TikTokUserFollowersInput, ctx: Any = None) -> dict:
            """List a TikTok user's followers by secUid. Costs 1 credit."""
            return _run(lambda: client.tiktok.user_followers(**dump(input)))

        @toolkit.tool()
        def scavio_tiktok_user_followings(input: TikTokUserFollowingsInput, ctx: Any = None) -> dict:
            """List the accounts a TikTok user follows, by secUid. Costs 1 credit."""
            return _run(lambda: client.tiktok.user_followings(**dump(input)))

    if all or enable_instagram:

        @toolkit.tool()
        def scavio_instagram_profile(input: InstagramProfileInput, ctx: Any = None) -> dict:
            """Fetch an Instagram profile by username or user id. Costs 10 credits."""
            return _run(lambda: client.instagram.profile(**dump(input)))

        @toolkit.tool()
        def scavio_instagram_user_posts(input: InstagramUserPostsInput, ctx: Any = None) -> dict:
            """List an Instagram user's posts. Costs 2 credits, the cheapest Instagram endpoint."""
            return _run(lambda: client.instagram.user_posts(**dump(input)))

        @toolkit.tool()
        def scavio_instagram_user_reels(input: InstagramUserReelsInput, ctx: Any = None) -> dict:
            """List an Instagram user's reels. Costs 10 credits."""
            return _run(lambda: client.instagram.user_reels(**dump(input)))

        @toolkit.tool()
        def scavio_instagram_user_tagged(input: InstagramUserTaggedInput, ctx: Any = None) -> dict:
            """List posts an Instagram user is tagged in. Costs 10 credits."""
            return _run(lambda: client.instagram.user_tagged(**dump(input)))

        @toolkit.tool()
        def scavio_instagram_user_stories(input: InstagramUserStoriesInput, ctx: Any = None) -> dict:
            """Fetch an Instagram user's current stories. Costs 10 credits."""
            return _run(lambda: client.instagram.user_stories(**dump(input)))

        @toolkit.tool()
        def scavio_instagram_post(input: InstagramPostInput, ctx: Any = None) -> dict:
            """Fetch an Instagram post by URL, media id, or shortcode. Costs 8 credits."""
            return _run(lambda: client.instagram.post(**dump(input)))

        @toolkit.tool()
        def scavio_instagram_post_comments(input: InstagramPostCommentsInput, ctx: Any = None) -> dict:
            """List comments on an Instagram post by shortcode or URL. Costs 10 credits."""
            return _run(lambda: client.instagram.post_comments(**dump(input)))

        @toolkit.tool()
        def scavio_instagram_comment_replies(input: InstagramCommentRepliesInput, ctx: Any = None) -> dict:
            """List replies to an Instagram post comment. Costs 8 credits."""
            return _run(lambda: client.instagram.comment_replies(**dump(input)))

        @toolkit.tool()
        def scavio_instagram_search_users(input: InstagramSearchUsersInput, ctx: Any = None) -> dict:
            """Search Instagram users by keyword. Costs 10 credits."""
            return _run(lambda: client.instagram.search_users(**dump(input)))

        @toolkit.tool()
        def scavio_instagram_search_hashtags(input: InstagramSearchHashtagsInput, ctx: Any = None) -> dict:
            """Search Instagram hashtags by keyword. Costs 10 credits."""
            return _run(lambda: client.instagram.search_hashtags(**dump(input)))

        @toolkit.tool()
        def scavio_instagram_user_followers(input: InstagramUserFollowersInput, ctx: Any = None) -> dict:
            """List an Instagram user's followers. Costs 10 credits."""
            return _run(lambda: client.instagram.user_followers(**dump(input)))

        @toolkit.tool()
        def scavio_instagram_user_followings(input: InstagramUserFollowingsInput, ctx: Any = None) -> dict:
            """List the accounts an Instagram user follows. Costs 10 credits."""
            return _run(lambda: client.instagram.user_followings(**dump(input)))

    if all or enable_tiktok_shop:

        @toolkit.tool()
        def scavio_tiktok_shop_search(input: TikTokShopSearchInput, ctx: Any = None) -> dict:
            """Search TikTok Shop products by keyword (US catalog only, no region param). Returns data.products with exact prices, plus shops, next_cursor, has_more and degraded. Costs 1 credit."""
            return _run(lambda: client.tiktok_shop.search(**dump(input)))

        @toolkit.tool()
        def scavio_tiktok_shop_search_suggestions(input: TikTokShopSearchSuggestionsInput, ctx: Any = None) -> dict:
            """Get TikTok Shop search autocomplete suggestions. Returns bare strings only: no volume, no score, no CPC. Costs 1 credit."""
            return _run(lambda: client.tiktok_shop.search_suggestions(**dump(input)))

        @toolkit.tool()
        def scavio_tiktok_shop_product(input: TikTokShopProductInput, ctx: Any = None) -> dict:
            """Fetch full TikTok Shop product details: description, images, variants, shipping, shop profile, categories and top reviews. Prices are masked upstream and come back null here, so use the TikTok Shop search or shop products tools for exact prices. Costs 1 credit, billed on a 404 too."""
            return _run(lambda: client.tiktok_shop.product(**dump(input)))

        @toolkit.tool()
        def scavio_tiktok_shop_product_reviews(input: TikTokShopProductReviewsInput, ctx: Any = None) -> dict:
            """List reviews for a TikTok Shop product, up to 200 per call. total_reviews drifts between calls, so page with has_more instead of computing a page count. Costs 1 credit."""
            return _run(lambda: client.tiktok_shop.product_reviews(**dump(input)))

        @toolkit.tool()
        def scavio_tiktok_shop_categories(input: TikTokShopCategoriesInput, ctx: Any = None) -> dict:
            """Fetch the full TikTok Shop category tree (28 top-level, 240 nodes, two levels). Ids are identical in every region and names are always English. Takes no parameters. Costs 1 credit."""
            return _run(lambda: client.tiktok_shop.categories(**dump(input)))

        @toolkit.tool()
        def scavio_tiktok_shop_category_products(input: TikTokShopCategoryProductsInput, ctx: Any = None) -> dict:
            """List products in a TikTok Shop category. Page size varies (15-20), so always follow next_cursor rather than assuming a fixed size. Costs 1 credit, billed on a 404 too."""
            return _run(lambda: client.tiktok_shop.category_products(**dump(input)))

        @toolkit.tool()
        def scavio_tiktok_shop_shop_products(input: TikTokShopShopProductsInput, ctx: Any = None) -> dict:
            """List a TikTok Shop seller's products, 30 per page, with exact prices. Shop follower count, location and rating are not available here; use the TikTok Shop product tool for the full shop profile. Costs 1 credit, billed on a 404 too."""
            return _run(lambda: client.tiktok_shop.shop_products(**dump(input)))

        @toolkit.tool()
        def scavio_tiktok_shop_resolve(input: TikTokShopResolveInput, ctx: Any = None) -> dict:
            """Resolve a TikTok Shop link (including vt.tiktok.com short links) to a product_id or shop_id plus a canonical URL. Costs 1 credit; unsupported URL families 400 unbilled."""
            return _run(lambda: client.tiktok_shop.resolve(**dump(input)))

    if all or enable_x:

        @toolkit.tool()
        def scavio_x_search(input: XSearchInput, ctx: Any = None) -> dict:
            """Search X (Twitter) posts. Returns data.timeline with next_cursor, prev_cursor and has_more. Costs 1 credit."""
            return _run(lambda: client.x.search(**dump(input)))

        @toolkit.tool()
        def scavio_x_tweet(input: XTweetInput, ctx: Any = None) -> dict:
            """Fetch one X post by id, including its reply context and media. Costs 1 credit."""
            return _run(lambda: client.x.tweet(**dump(input)))

        @toolkit.tool()
        def scavio_x_tweet_comments(input: XTweetCommentsInput, ctx: Any = None) -> dict:
            """List replies to an X post. rank='top' is ranked, rank='latest' is chronological. Returns data.timeline with next_cursor. Costs 1 credit."""
            return _run(lambda: client.x.tweet_comments(**dump(input)))

        @toolkit.tool()
        def scavio_x_tweet_retweeters(input: XTweetRetweetersInput, ctx: Any = None) -> dict:
            """List the accounts that reposted an X post. Returns data.retweeters with next_cursor and has_more. Costs 1 credit."""
            return _run(lambda: client.x.tweet_retweeters(**dump(input)))

        @toolkit.tool()
        def scavio_x_user(input: XUserInput, ctx: Any = None) -> dict:
            """Fetch an X user profile by handle: followers_count, friends_count, statuses_count, description, location, website, avatar and pinned posts. Costs 1 credit."""
            return _run(lambda: client.x.user(**dump(input)))

        @toolkit.tool()
        def scavio_x_user_tweets(input: XUserTweetsInput, ctx: Any = None) -> dict:
            """List an X user's posts. Returns data.timeline plus pinned and user; there is no has_more on this endpoint, so page until next_cursor stops changing. Costs 1 credit."""
            return _run(lambda: client.x.user_tweets(**dump(input)))

        @toolkit.tool()
        def scavio_x_user_replies(input: XUserRepliesInput, ctx: Any = None) -> dict:
            """List an X user's replies. Returns data.timeline with next_cursor and prev_cursor. Costs 1 credit."""
            return _run(lambda: client.x.user_replies(**dump(input)))

        @toolkit.tool()
        def scavio_x_user_media(input: XUserMediaInput, ctx: Any = None) -> dict:
            """List an X user's posts that contain photos or videos. Returns data.timeline with next_cursor. Costs 1 credit."""
            return _run(lambda: client.x.user_media(**dump(input)))

        @toolkit.tool()
        def scavio_x_user_followers(input: XUserFollowersInput, ctx: Any = None) -> dict:
            """List an X user's followers. Returns data.followers with followers_count, next_cursor and has_more. Costs 1 credit."""
            return _run(lambda: client.x.user_followers(**dump(input)))

        @toolkit.tool()
        def scavio_x_user_followings(input: XUserFollowingsInput, ctx: Any = None) -> dict:
            """List the accounts an X user follows. The array is data.following (singular), with next_cursor and has_more. Costs 1 credit."""
            return _run(lambda: client.x.user_followings(**dump(input)))

        @toolkit.tool()
        def scavio_x_trending(input: XTrendingInput, ctx: Any = None) -> dict:
            """List trending topics on X for a country. Returns data.trends; no cursor and no has_more. Costs 1 credit."""
            return _run(lambda: client.x.trending(**dump(input)))

    if all or enable_linkedin:

        @toolkit.tool()
        def scavio_linkedin_person(input: LinkedInPersonInput, ctx: Any = None) -> dict:
            """Fetch a LinkedIn profile by handle or URL: headline, about, location, follower_count, connection_count, current_company, experiences and educations. Costs 1 credit."""
            return _run(lambda: client.linkedin.person(**dump(input)))

        @toolkit.tool()
        def scavio_linkedin_person_about(input: LinkedInPersonAboutInput, ctx: Any = None) -> dict:
            """Fetch just the narrative parts of a LinkedIn profile: about, headline, experiences, educations, honors and bio_links. Costs 1 credit."""
            return _run(lambda: client.linkedin.person_about(**dump(input)))

        @toolkit.tool()
        def scavio_linkedin_person_posts(input: LinkedInPersonPostsInput, ctx: Any = None) -> dict:
            """List a LinkedIn member's posts, or the posts they commented on or reacted to, 50 per page. Returns data.data with count, has_more and next_cursor. Costs 10 credits."""
            return _run(lambda: client.linkedin.person_posts(**dump(input)))

        @toolkit.tool()
        def scavio_linkedin_company(input: LinkedInCompanyInput, ctx: Any = None) -> dict:
            """Fetch a LinkedIn company page: description, website, industries, specialties, employee_count, follower_count, headquarters, locations and featured_employees (a 4-6 person sample, the only employee data available). Costs 1 credit."""
            return _run(lambda: client.linkedin.company(**dump(input)))

        @toolkit.tool()
        def scavio_linkedin_company_posts(input: LinkedInCompanyPostsInput, ctx: Any = None) -> dict:
            """List a LinkedIn company's posts, 50 per page. Returns data.data with count, has_more and next_cursor. Costs 10 credits."""
            return _run(lambda: client.linkedin.company_posts(**dump(input)))

        @toolkit.tool()
        def scavio_linkedin_search_jobs(input: LinkedInSearchJobsInput, ctx: Any = None) -> dict:
            """Search LinkedIn job listings, 25 per page. Upstream rotates its result set and pages overlap, so dedupe by job id. Costs 10 credits."""
            return _run(lambda: client.linkedin.search_jobs(**dump(input)))

        @toolkit.tool()
        def scavio_linkedin_job(input: LinkedInJobInput, ctx: Any = None) -> dict:
            """Fetch one LinkedIn job listing in full: description, employment_type, experience_level, skills, benefits, salary, applicant_count and the hiring company. Roughly one in five ids from job search has no detail record and returns 404 unbilled. Costs 30 credits, the most expensive Scavio endpoint."""
            return _run(lambda: client.linkedin.job(**dump(input)))

        @toolkit.tool()
        def scavio_linkedin_post(input: LinkedInPostInput, ctx: Any = None) -> dict:
            """Fetch one LinkedIn post by id, activity urn, or URL: text, media, hashtags, reaction and comment counts, tagged entities, top_comments and the author. Costs 1 credit."""
            return _run(lambda: client.linkedin.post(**dump(input)))

        @toolkit.tool()
        def scavio_linkedin_post_comments(input: LinkedInPostCommentsInput, ctx: Any = None) -> dict:
            """List comments on a LinkedIn post, with their replies. Pages by 1-based page number, not a cursor; page size is not fixed, so keep paging until a page comes back empty. Costs 10 credits."""
            return _run(lambda: client.linkedin.post_comments(**dump(input)))

    return toolkit
