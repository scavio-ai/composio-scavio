"""Scavio tools for Composio.

Scavio is a single Search API over 32 platforms - Google, YouTube, Amazon,
Walmart, eBay, Target, Home Depot, Reddit, TikTok, TikTok Shop, Instagram, X,
LinkedIn, Threads, Kuaishou, Zillow, Redfin, Booking.com, Airbnb, Tripadvisor,
Yelp, Indeed, Glassdoor, the Apple App Store, Google Play, SEC EDGAR, Companies
House, G2, Capterra, Google Ads Transparency and the Meta Ad Library - plus a
top-level ``extract`` that reads any URL as Markdown, text or raw HTML. This
toolkit exposes every live endpoint of all of them. Build the toolkit with
``build_scavio_toolkit()`` and bind it to a session::

    from composio import Composio
    from composio_scavio import build_scavio_toolkit

    composio = Composio()
    scavio = build_scavio_toolkit(api_key="sk_...")  # or set SCAVIO_API_KEY
    session = composio.create(
        user_id="user_1",
        experimental={"custom_toolkits": [scavio]},
    )

Every provider is gated by an ``enable_*`` flag so an agent only sees the tools
it needs. The ten original platforms plus ``extract`` are on by default; the 21
platforms added in 0.4.0 are OPT-IN, because handing an agent all 189 tools at
once buries the ones it actually needs. Turn a vertical on explicitly::

    scavio = build_scavio_toolkit(enable_zillow=True, enable_redfin=True)

or pass ``all=True`` for the complete set. Tools return the raw Scavio JSON
response as a dict.
"""

import os
from typing import Any, Callable, Dict, Optional, Union

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


class AmazonOptionsInput(BaseModel):
    pass


# Walmart
# Rebuilt on the live 0.15.0 surface: device, delivery_zip and store_id never
# existed on the scrape.do rebuild and are gone, `page` replaces start_page, and
# the five endpoints beyond search/product are exposed for the first time.
class WalmartSearchInput(BaseModel):
    query: str = Field(description="Product search query (1-500 characters).")
    domain: Optional[str] = Field(None, description="Marketplace: 'com' (US, default, 1 credit), 'ca' (1 credit), 'com.mx' (2 credits). Sets the currency and product URLs of the response.")
    page: Optional[int] = Field(None, description="Results page, 1-based (integer >= 1). One page per call.")
    start_page: Optional[int] = Field(None, description="Deprecated alias for page; send page instead.")
    sort_by: Optional[str] = Field(None, description="Result sort order. Defaults to 'best_match'. Accepted values: 'best_match', 'price_low', 'price_high', 'best_seller', 'rating_high', 'new'.")
    min_price: Optional[float] = Field(None, description="Minimum price filter in the marketplace's own currency; decimals allowed (e.g. 19.99).")
    max_price: Optional[float] = Field(None, description="Maximum price filter in the marketplace's own currency; decimals allowed (e.g. 199.5).")
    fulfillment_speed: Optional[str] = Field(None, description="Only items deliverable today, or by tomorrow. '2_days' and 'anytime' are not accepted - for anytime, omit this parameter.")
    fulfillment_type: Optional[str] = Field(None, description="Set to 'in_store' to return only items available for in-store pickup.")


class WalmartProductInput(BaseModel):
    product_id: str = Field(description="Walmart item id (usItemId), e.g. '13544111159'.")


class WalmartReviewsInput(BaseModel):
    product_id: str = Field(description="Walmart item id (usItemId), e.g. '13544111159'.")
    page: Optional[int] = Field(None, description="Reviews page, 1-based (integer >= 1). 10 reviews per page.")
    sort: Optional[str] = Field(None, description="Review sort order. Omit for Walmart's own default ordering. Accepted values: 'relevancy', 'submission-desc', 'submission-asc', 'rating-desc', 'rating-asc', 'helpful-desc'.")


class WalmartCategoryInput(BaseModel):
    category_id: str = Field(description="Walmart category id: either a leaf id ('1095191') or the full underscore-joined path ('3944_133251_1095191'). Both are accepted.")
    domain: Optional[str] = Field(None, description="Marketplace: 'com' (US, default, 1 credit), 'ca' (1 credit), 'com.mx' (2 credits). Sets the currency and product URLs of the response.")
    page: Optional[int] = Field(None, description="Results page, 1-based (integer >= 1). One page per call.")
    limit: Optional[int] = Field(None, description="Trim the returned products to at most this many (integer >= 1). Applied after fetching, so it does not reduce the credit cost of the call.")
    sort_by: Optional[str] = Field(None, description="Result sort order. Defaults to 'best_match'. Accepted values: 'best_match', 'price_low', 'price_high', 'best_seller', 'rating_high', 'new'.")
    min_price: Optional[float] = Field(None, description="Minimum price filter in the marketplace's own currency; decimals allowed (e.g. 19.99).")
    max_price: Optional[float] = Field(None, description="Maximum price filter in the marketplace's own currency; decimals allowed (e.g. 199.5).")
    fulfillment_speed: Optional[str] = Field(None, description="Only items deliverable today, or by tomorrow. '2_days' and 'anytime' are not accepted - for anytime, omit this parameter.")


class WalmartOffersInput(BaseModel):
    product_id: str = Field(description="Walmart item id (usItemId), e.g. '2979510112'.")


class WalmartSellerInput(BaseModel):
    seller_id: str = Field(description="Numeric Walmart catalog seller id, as returned in `seller_catalog_id` on a product, search or offers response (e.g. '101480084'). The GUID `seller_id` is not accepted here - it 404s.")


class WalmartSellerProductsInput(BaseModel):
    seller_id: str = Field(description="Numeric Walmart catalog seller id, as returned in `seller_catalog_id` on a product, search or offers response (e.g. '101480084'). The GUID `seller_id` 404s.")


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


# Threads
class ThreadsProfileInput(BaseModel):
    user_id: Optional[str] = Field(None, description="Numeric Threads user id, e.g. '63625256886'. The cheap path: 2 credits.")
    username: Optional[str] = Field(None, description="Threads handle without the @ (1-60 characters). Costs 2 extra credits (4 total): the upstream handle lookup is down, so the handle is resolved through people search first. Pass user_id instead to avoid that.")


class ThreadsUserPostsInput(BaseModel):
    user_id: Optional[str] = Field(None, description="Numeric Threads user id, e.g. '63625256886'. The cheap path: 2 credits.")
    username: Optional[str] = Field(None, description="Threads handle without the @ (1-60 characters). Costs 2 extra credits (4 total) because the handle has to be resolved through people search first.")
    cursor: Optional[str] = Field(None, description="Pagination cursor from a prior response's next_cursor. Omit for the first page.")


class ThreadsUserRepliesInput(BaseModel):
    user_id: Optional[str] = Field(None, description="Numeric Threads user id, e.g. '63625256886'. The cheap path: 2 credits.")
    username: Optional[str] = Field(None, description="Threads handle without the @ (1-60 characters). Costs 2 extra credits (4 total) because the handle has to be resolved through people search first.")
    cursor: Optional[str] = Field(None, description="Pagination cursor from a prior response's next_cursor. Omit for the first page.")


class ThreadsPostInput(BaseModel):
    post_id: Optional[str] = Field(None, description="Threads post id, e.g. '3349029093483693129'.")
    url: Optional[str] = Field(None, description="Full threads.net post URL (e.g. 'https://www.threads.net/@natgeo/post/C8xY'), as an alternative to post_id.")


class ThreadsPostCommentsInput(BaseModel):
    post_id: str = Field(description="Threads post id, e.g. '3349029093483693129'.")
    cursor: Optional[str] = Field(None, description="Pagination cursor from a prior response's next_cursor. Omit for the first page.")


class ThreadsSearchUsersInput(BaseModel):
    query: str = Field(description="Name or handle to search for (1-200 characters).")


# Kuaishou (China)
class KuaishouProfileInput(BaseModel):
    user_id: str = Field(description="Kuaishou user id (non-empty); get one from user_resolve or search_users.")


class KuaishouUserPostsInput(BaseModel):
    user_id: str = Field(description="Kuaishou user id (non-empty); get one from user_resolve or search_users.")
    cursor: Optional[str] = Field(None, description="Opaque next_cursor from a prior response; omit for the first page.")


class KuaishouUserLiveInput(BaseModel):
    user_id: str = Field(description="Kuaishou user id (non-empty); get one from user_resolve or search_users.")


class KuaishouUserResolveInput(BaseModel):
    share_link: str = Field(description="A kuaishou.com or v.kuaishou.com URL; kwai.com links are rejected.")


class KuaishouVideoInput(BaseModel):
    photo_id: Optional[str] = Field(None, description="Kuaishou photo (video) id, non-empty.")
    url: Optional[str] = Field(None, description="Full kuaishou.com video URL, as an alternative to photo_id.")


class KuaishouVideoCommentsInput(BaseModel):
    photo_id: str = Field(description="Kuaishou photo (video) id, non-empty.")
    cursor: Optional[str] = Field(None, description="Opaque next_cursor from a prior response; omit for the first page.")


class KuaishouCommentRepliesInput(BaseModel):
    photo_id: str = Field(description="Kuaishou photo (video) id, non-empty.")
    root_comment_id: str = Field(description="Id of the top-level comment whose replies you want, from video_comments.")
    cursor: Optional[str] = Field(None, description="Opaque next_cursor from a prior response; omit for the first page.")
    count: Optional[int] = Field(None, description="Replies per page, 1-50. Omit to use the upstream default.")


class KuaishouVideosBatchInput(BaseModel):
    photo_ids: list[str] = Field(description="Kuaishou photo (video) ids, 1-20 per call; more than 20 is rejected.")


class KuaishouSearchInput(BaseModel):
    keyword: str = Field(description="Search keyword, 1-200 characters.")
    cursor: Optional[str] = Field(None, description="Opaque next_cursor from a prior response; omit for the first page.")


class KuaishouSearchVideosInput(BaseModel):
    keyword: str = Field(description="Search keyword, 1-200 characters.")
    cursor: Optional[str] = Field(None, description="Opaque next_cursor from a prior response; omit for the first page.")


class KuaishouSearchUsersInput(BaseModel):
    keyword: str = Field(description="Search keyword, 1-200 characters.")
    cursor: Optional[str] = Field(None, description="Opaque next_cursor from a prior response; omit for the first page.")


class KuaishouSearchLiveInput(BaseModel):
    keyword: str = Field(description="Search keyword, 1-200 characters.")
    cursor: Optional[str] = Field(None, description="Opaque next_cursor from a prior response; omit for the first page.")


class KuaishouTagFeedInput(BaseModel):
    tag: str = Field(description="Hashtag text without the leading '#', 1-200 characters.")
    cursor: Optional[str] = Field(None, description="Opaque next_cursor from a prior response; omit for the first page.")


class KuaishouTrendingInput(BaseModel):
    board: Optional[str] = Field(None, description="Leaderboard to return; defaults to 'hot' when omitted. Accepted values: 'hot', 'live', 'shopping', 'brand', 'music'.")


# eBay
class EbaySearchInput(BaseModel):
    query: Optional[str] = Field(None, description="Keyword to search (1-500 characters). Optional: a seller-only search pages that seller's whole catalogue.")
    seller: Optional[str] = Field(None, description="Restrict results to one seller's listings (1-64 characters), as in ebay.com/usr/<name>. Can be sent with no query.")
    page: Optional[int] = Field(None, description="Results page, 1-based.")
    sort_by: Optional[str] = Field(None, description="Result sort order. Defaults to 'best_match'. eBay's 'Distance: nearest first' is deliberately unsupported (it ranks against our proxy exit, not the caller). Accepted values: 'best_match', 'ending_soonest', 'newly_listed', 'price_low', 'price_high'.")
    min_price: Optional[float] = Field(None, description="Minimum price, inclusive. Must be 0 or greater.")
    max_price: Optional[float] = Field(None, description="Maximum price, inclusive. Must be 0 or greater.")
    condition: Optional[str] = Field(None, description="Item condition filter. 'refurbished' is eBay's parent condition, not one of its three graded tiers. Accepted values: 'new', 'open_box', 'refurbished', 'used', 'for_parts'.")
    buying_format: Optional[str] = Field(None, description="Listing format: auction, fixed price (buy_it_now), or fixed price accepting offers (best_offer).")
    free_shipping: Optional[bool] = Field(None, description="Only listings with free shipping.")
    sold: Optional[bool] = Field(None, description="Search completed listings that actually SOLD, for price research. eBay publishes no headline count on this view, so total_results is null.")
    category_id: Optional[str] = Field(None, description="eBay category id; must be numeric (e.g. '112529'). An unrecognised id returns the UNFILTERED set under a 200.")
    per_page: Optional[int] = Field(None, description="Listings per page: 60, 120 or 240 only. Defaults to 60; eBay silently falls back to 60 for anything else.")


class EbayProductInput(BaseModel):
    item_id: str = Field(description="eBay item number (e.g. '168591664725'), or a full ebay.com/itm/... listing URL; tracking parameters on a pasted URL are discarded.")


class EbaySellerInput(BaseModel):
    seller: str = Field(description="eBay username as it appears in ebay.com/usr/<name> (1-64 characters), which is what seller_name on a search or product result returns.")


# Target
class TargetSearchInput(BaseModel):
    keyword: str = Field(description="Search keyword (1-500 characters).")
    page: Optional[int] = Field(None, description="Results page, 1-based.")
    count: Optional[int] = Field(None, description="Results per page, 1-28. Defaults to 24; Target rejects anything above 28 outright.")
    sort: Optional[str] = Field(None, description="Result sort order. Defaults to 'relevance'. Accepted values: 'relevance', 'featured', 'price_low', 'price_high', 'rating_high', 'best_seller', 'newest'.")
    store_id: Optional[str] = Field(None, description="Numeric Target store id whose prices and availability the response reflects. Defaults to '3991', the store target.com uses with no store context.")


class TargetCategoryInput(BaseModel):
    category_id: str = Field(description="Target category id: the segment after 'N-' in a target.com /c/ URL (target.com/c/apple/-/N-5xtg6 -> '5xtg6').")
    page: Optional[int] = Field(None, description="Results page, 1-based.")
    count: Optional[int] = Field(None, description="Results per page, 1-28. Defaults to 24; Target rejects anything above 28 outright.")
    sort: Optional[str] = Field(None, description="Result sort order. Defaults to 'relevance'. Accepted values: 'relevance', 'featured', 'price_low', 'price_high', 'rating_high', 'best_seller', 'newest'.")
    store_id: Optional[str] = Field(None, description="Numeric Target store id whose prices and availability the response reflects. Defaults to '3991'.")


class TargetProductInput(BaseModel):
    tcin: str = Field(description="Target catalog id (tcin, e.g. '1010453160'). A colour/size child tcin is answered by its variation parent, with the child present in 'variants'.")
    store_id: Optional[str] = Field(None, description="Numeric Target store id whose prices and availability the response reflects. Defaults to '3991'.")


class TargetReviewsInput(BaseModel):
    tcin: str = Field(description="Target catalog id (tcin, e.g. '1010453160').")
    limit: Optional[int] = Field(None, description="Trim the returned reviews to at most this many (1 or greater). Target publishes 8 anonymously and offers no paging, so this only trims.")
    store_id: Optional[str] = Field(None, description="Numeric Target store id whose prices and availability the response reflects. Defaults to '3991'.")


# Home Depot
class HomeDepotSearchInput(BaseModel):
    query: str = Field(description="Search keyword (1-500 characters).")
    page: Optional[int] = Field(None, description="Results page, 1-based. Home Depot serves 12 products per page and offers no way to change that, so paging is the only way to read further.")
    sort_by: Optional[str] = Field(None, description="Result sort order. Defaults to 'best_match'. Closed enum: Home Depot answers an unknown sort with an empty page that is still billed. 'Newest' is absent - it is rejected on keyword search. Accepted values: 'best_match', 'top_sellers', 'top_rated', 'price_low', 'price_high'.")
    min_price: Optional[float] = Field(None, description="Minimum price, inclusive. Must be 0 or greater.")
    max_price: Optional[float] = Field(None, description="Maximum price, inclusive. Must be 0 or greater.")


class HomeDepotProductInput(BaseModel):
    item_id: str = Field(description="Home Depot item id (e.g. '325479354'), or a full homedepot.com/p/... product URL; tracking parameters on a pasted URL are discarded.")


class HomeDepotReviewsInput(BaseModel):
    item_id: str = Field(description="Home Depot item id (e.g. '325479354'), or a full homedepot.com/p/... product URL; tracking parameters on a pasted URL are discarded.")
    page: Optional[int] = Field(None, description="Reviews page, 1-based. 30 reviews per page; 'total_pages' in the response is the last one that exists, and asking past it is a 404.")


# Zillow
class ZillowSearchInput(BaseModel):
    location: str = Field(description="Region to search (1-200 characters): a Zillow slug ('austin-tx'), a human form ('Austin, TX'), a ZIP, or a pasted zillow.com search URL. A ZIP works alone but cannot be combined with a filter or sort; an unresolvable region is a 404.")
    listing_status: Optional[str] = Field(None, description="Which listings to return. Defaults to 'for_sale'. Accepted values: 'for_sale', 'for_rent', 'sold'.")
    page: Optional[int] = Field(None, description="Results page, 1-based.")
    sort: Optional[str] = Field(None, description="Result sort order. Sorts that rank against a signed-in profile (saved/featured/personalised) are unsupported - we are never signed in. Accepted values: 'relevance', 'recommended', 'newest', 'price_low', 'price_high', 'payment_low', 'payment_high', 'beds', 'baths', 'sqft', 'lot_size', 'zestimate_low', 'zestimate_high', 'recent_change'.")
    min_price: Optional[float] = Field(None, description="Minimum price, inclusive (0 or greater). On listing_status='for_rent' this is MONTHLY RENT - Zillow files rent under its payment filter.")
    max_price: Optional[float] = Field(None, description="Maximum price, inclusive (0 or greater). On listing_status='for_rent' this is MONTHLY RENT.")
    beds_min: Optional[int] = Field(None, description="Minimum bedrooms; whole number, 0 or greater.")
    beds_max: Optional[int] = Field(None, description="Maximum bedrooms; whole number, 0 or greater.")
    baths_min: Optional[float] = Field(None, description="Minimum bathrooms, 0 or greater. Half-baths are allowed (1.5).")
    baths_max: Optional[float] = Field(None, description="Maximum bathrooms, 0 or greater. Half-baths are allowed (1.5).")
    sqft_min: Optional[int] = Field(None, description="Minimum living area in square feet; whole number, 0 or greater.")
    sqft_max: Optional[int] = Field(None, description="Maximum living area in square feet; whole number, 0 or greater.")
    lot_size_min: Optional[int] = Field(None, description="Minimum lot size in square feet; whole number, 0 or greater.")
    lot_size_max: Optional[int] = Field(None, description="Maximum lot size in square feet; whole number, 0 or greater.")
    year_built_min: Optional[int] = Field(None, description="Earliest year built; whole number, 0 or greater.")
    year_built_max: Optional[int] = Field(None, description="Latest year built; whole number, 0 or greater.")
    max_hoa: Optional[float] = Field(None, description="Maximum monthly HOA fee in dollars, 0 or greater.")
    home_type: Optional[str] = Field(None, description="Property type filter. Accepted values: 'houses', 'townhomes', 'multi_family', 'condos', 'apartments', 'manufactured', 'lots_land'.")
    days_on_zillow: Optional[str] = Field(None, description="Listed - or, with listing_status='sold', sold - within the last N days. Closed enum: an unrecognised value returns the UNFILTERED set under a 200. Accepted values: '1', '7', '14', '30', '90', '6m', '12m', '24m', '36m'.")
    keywords: Optional[str] = Field(None, description="Free-text match against the listing description (1-200 characters).")
    has_pool: Optional[bool] = Field(None, description="Only listings with a pool.")
    has_garage: Optional[bool] = Field(None, description="Only listings with a garage.")
    has_air_conditioning: Optional[bool] = Field(None, description="Only listings with air conditioning.")
    is_waterfront: Optional[bool] = Field(None, description="Only waterfront listings.")
    has_basement: Optional[bool] = Field(None, description="Only listings with a basement.")
    is_new_construction: Optional[bool] = Field(None, description="Only new-construction listings.")
    has_open_house: Optional[bool] = Field(None, description="Only listings with an upcoming open house.")
    price_reduced: Optional[bool] = Field(None, description="Only listings whose price was reduced.")
    is_3d_tour: Optional[bool] = Field(None, description="Only listings with a 3D tour.")


class ZillowPropertyInput(BaseModel):
    zpid: str = Field(description="Zillow property id (e.g. '29414894'), a full /homedetails/ URL, or a rental building URL (zillow.com/apartments/...). The building form is required for buildings: they have no zpid a caller can see.")


class ZillowAgentReviewsInput(BaseModel):
    screen_name: str = Field(description="Zillow agent profile screen name as it appears in zillow.com/profile/<name>/ (1-200 characters, may contain spaces), or a full profile URL.")


# Booking.com
class BookingSearchInput(BaseModel):
    destination: Optional[str] = Field(None, description="Destination to search, e.g. 'Paris' (1-200 characters). Required unless dest_id is given.")
    dest_id: Optional[str] = Field(None, description="Numeric Booking.com destination id, as an alternative to destination.")
    dest_type: Optional[str] = Field(None, description="What dest_id refers to. Requires dest_id and is rejected without it, because Booking silently ignores a lone dest_type. Accepted values: 'city', 'region', 'country', 'district', 'landmark', 'airport', 'hotel'.")
    page: Optional[int] = Field(None, description="Results page, 1-based. 25 properties per page, 1 credit each.")
    sort_by: Optional[str] = Field(None, description="Result sort order (default 'popularity'). Accepted values: 'popularity', 'price_low', 'price_high', 'stars_high', 'stars_low', 'stars_and_price', 'distance', 'review_score'.")
    min_price: Optional[float] = Field(None, description="Minimum price PER NIGHT in `currency`, >= 0. Must not exceed max_price.")
    max_price: Optional[float] = Field(None, description="Maximum price PER NIGHT in `currency`, >= 0.")
    stars: Optional[list[int]] = Field(None, description="Star ratings to include, each 1-5, 1-5 values, OR'd together (e.g. [4, 5]).")
    min_review_score: Optional[str] = Field(None, description="Minimum guest review score. Only '6', '7', '8' and '9' exist upstream; any other threshold is silently dropped.")
    property_type: Optional[Union[str, int]] = Field(None, description="Accommodation type by name, or a raw numeric Booking accommodation-type id (>= 1). Accepted values: 'apartments', 'hostels', 'hotels', 'motels', 'resorts', 'bed_and_breakfasts', 'villas', 'campgrounds', 'vacation_homes', 'lodges', 'homestays'.")
    free_cancellation: Optional[bool] = Field(None, description="Only properties offering free cancellation.")
    no_prepayment: Optional[bool] = Field(None, description="Only properties that take no prepayment.")
    breakfast_included: Optional[bool] = Field(None, description="Only rates that include breakfast.")
    checkin: Optional[str] = Field(None, description="Check-in date, YYYY-MM-DD. Must be sent together with checkout: a lone checkin is ignored and Booking prices a default range of its own.")
    checkout: Optional[str] = Field(None, description="Check-out date, YYYY-MM-DD. Must be later than checkin and sent together with it.")
    adults: Optional[int] = Field(None, description="Adult guests, >= 1 (default 2).")
    children_ages: Optional[list[int]] = Field(None, description="AGES of accompanying children, each 0-17, max 10 entries. Ages, not a count.")
    rooms: Optional[int] = Field(None, description="Rooms required, >= 1 (default 1).")
    currency: Optional[str] = Field(None, description="ISO 4217 currency for prices, 3 letters (default 'USD'). Without it Booking prices off the proxy exit and identical requests disagree.")


class BookingHotelInput(BaseModel):
    hotel: str = Field(description="Booking.com property URL or the bare page slug (1-500 characters); query params are discarded.")
    country_code: Optional[str] = Field(None, description="Two-letter country code for the property page (default 'us'). Only consulted for a bare slug, where a wrong one is a real, BILLED 404.")
    checkin: Optional[str] = Field(None, description="Check-in date, YYYY-MM-DD. Must be sent together with checkout; omitting both prices a two-night range Booking chose, echoed back in the response.")
    checkout: Optional[str] = Field(None, description="Check-out date, YYYY-MM-DD. Must be later than checkin and sent together with it.")
    adults: Optional[int] = Field(None, description="Adult guests, >= 1 (default 2).")
    children_ages: Optional[list[int]] = Field(None, description="AGES of accompanying children, each 0-17, max 10 entries. Ages, not a count.")
    rooms: Optional[int] = Field(None, description="Rooms required, >= 1 (default 1).")
    currency: Optional[str] = Field(None, description="ISO 4217 currency for prices, 3 letters (default 'USD'). Without it Booking prices off the proxy exit and identical requests disagree.")


class BookingReviewsInput(BaseModel):
    hotel: str = Field(description="Booking.com property URL or the bare page slug (1-500 characters); query params are discarded.")
    country_code: Optional[str] = Field(None, description="Two-letter country code for the property page (default 'us'). Only consulted for a bare slug, where a wrong one is a real, BILLED 404.")
    checkin: Optional[str] = Field(None, description="Check-in date, YYYY-MM-DD. Must be sent together with checkout; it prices the stay the review page is rendered for.")
    checkout: Optional[str] = Field(None, description="Check-out date, YYYY-MM-DD. Must be later than checkin and sent together with it.")
    adults: Optional[int] = Field(None, description="Adult guests, >= 1 (default 2).")
    children_ages: Optional[list[int]] = Field(None, description="AGES of accompanying children, each 0-17, max 10 entries. Ages, not a count.")
    rooms: Optional[int] = Field(None, description="Rooms required, >= 1 (default 1).")
    currency: Optional[str] = Field(None, description="ISO 4217 currency for prices, 3 letters (default 'USD').")


# Tripadvisor
class TripadvisorLocationsInput(BaseModel):
    query: str = Field(description="Place or business name to resolve (1-120 characters).")
    limit: Optional[int] = Field(None, description="Rows to return, 1-20 (default 12). Sizes the response only; there is no paging here.")


class TripadvisorSearchInput(BaseModel):
    geo_id: Optional[str] = Field(None, description="TripAdvisor geo id (1-500 characters): 30196, g30196, or a URL carrying one. Required unless url is given.")
    category: Optional[str] = Field(None, description="Listing family to search (default 'restaurants'). Accepted values: 'restaurants', 'hotels', 'attractions'.")
    page: Optional[int] = Field(None, description="Results page, 1-based. 30 locations per page; a page beyond the last is a 404, not an empty result.")
    url: Optional[str] = Field(None, description="Full tripadvisor.com listing URL (1-500 characters), as an alternative to geo_id; country sites are accepted.")


class TripadvisorLocationInput(BaseModel):
    location_id: Optional[str] = Field(None, description="TripAdvisor location id (1-500 characters): 1899234, d1899234, or a full _Review URL. Required unless url is given.")
    geo_id: Optional[str] = Field(None, description="Geo the location sits in; required when location_id is a bare d-id.")
    category: Optional[str] = Field(None, description="Location family (default 'restaurants'); match the location's own type. Accepted values: 'restaurants', 'hotels', 'attractions'.")
    url: Optional[str] = Field(None, description="Full tripadvisor.com _Review URL (1-500 characters), as an alternative to location_id.")


class TripadvisorReviewsInput(BaseModel):
    location_id: Optional[str] = Field(None, description="TripAdvisor location id (1-500 characters): 1899234, d1899234, or a full _Review URL. Required unless url is given.")
    geo_id: Optional[str] = Field(None, description="Geo the location sits in; required when location_id is a bare d-id.")
    category: Optional[str] = Field(None, description="Location family (default 'restaurants'). It sets the page size, so it must match the location's own type on any page past the first. Accepted values: 'restaurants', 'hotels', 'attractions'.")
    url: Optional[str] = Field(None, description="Full tripadvisor.com _Review URL (1-500 characters), as an alternative to location_id.")
    page: Optional[int] = Field(None, description="Reviews page, 1-based. 15 per page for restaurants, 10 for hotels and attractions; past the last page is a 404.")


# Indeed
class IndeedSearchInput(BaseModel):
    query: Optional[str] = Field(None, description="Job title, keywords or employer (1-500 characters). Required unless location is given.")
    location: Optional[str] = Field(None, description="City and state, postal code, state, country, or 'Remote' (1-200 characters). Valid on its own with no query.")
    page: Optional[int] = Field(None, description="Results page, 1-based. 10 postings per page, 1 call each.")
    radius: Optional[int] = Field(None, description="Search radius in miles around location. Closed set: Indeed IGNORES any other value and returns the unfiltered set. Upstream default 50. Accepted values: 0, 5, 10, 15, 25, 35, 50, 100.")
    max_age_days: Optional[int] = Field(None, description="Maximum posting age in days. Closed set: Indeed IGNORES any other value and returns postings of every age. Accepted values: 1, 3, 7, 14.")
    job_type: Optional[str] = Field(None, description="Employment type filter. Accepted values: 'full_time', 'part_time', 'contract', 'temporary', 'internship'.")
    min_salary: Optional[float] = Field(None, description="Minimum annual salary, >= 0. Filters on INDEED'S OWN ESTIMATE for the role, not a posted figure, so postings publishing no salary still match.")
    remote: Optional[bool] = Field(None, description="Remote postings only.")


class IndeedJobInput(BaseModel):
    job_id: str = Field(description="16-hex Indeed job key, or any indeed.com URL carrying jk= (/viewjob, /rc/clk, /pagead/clk).")


class IndeedCompanyInput(BaseModel):
    company: str = Field(description="indeed.com/cmp/<slug> slug or a full profile URL (1-200 characters); slugs are untidy, e.g. 'Tata-Consultancy-Services-(tcs)'.")


class IndeedCompanyReviewsInput(BaseModel):
    company: str = Field(description="indeed.com/cmp/<slug> slug or a full profile URL (1-200 characters).")
    page: Optional[int] = Field(None, description="Reviews page, 1-based. 20 reviews per page.")


# Airbnb
class AirbnbSearchInput(BaseModel):
    location: str = Field(description="City, region, ZIP, or a pasted airbnb.com/s/ URL (1-200 characters). An unresolvable location is a 404.")
    check_in: Optional[str] = Field(None, description="Check-in date, YYYY-MM-DD. Must be sent with check_out; omitting both defaults to +30 days and flags dates_are_defaulted in the response.")
    check_out: Optional[str] = Field(None, description="Check-out date, YYYY-MM-DD. Must be later than check_in; defaults to check_in plus 5 nights when omitted.")
    adults: Optional[int] = Field(None, description="Adult guests, >= 1.")
    children: Optional[int] = Field(None, description="Children aged 2-12, >= 0.")
    infants: Optional[int] = Field(None, description="Infants under 2, >= 0.")
    pets: Optional[int] = Field(None, description="Pets, >= 0.")
    min_price: Optional[float] = Field(None, description="Minimum price for the WHOLE STAY in `currency`, not per night, >= 0. Must not exceed max_price.")
    max_price: Optional[float] = Field(None, description="Maximum price for the WHOLE STAY in `currency`, not per night, >= 0.")
    room_type: Optional[str] = Field(None, description="Room type. Validated before the scrape, because an unrecognised value returns the UNFILTERED set under a 200. Accepted values: 'entire_home', 'private_room', 'shared_room', 'hotel_room'.")
    min_bedrooms: Optional[int] = Field(None, description="Minimum bedrooms, >= 0.")
    min_beds: Optional[int] = Field(None, description="Minimum beds, >= 0.")
    min_bathrooms: Optional[int] = Field(None, description="Minimum bathrooms, >= 0.")
    superhost: Optional[bool] = Field(None, description="Superhost listings only.")
    instant_book: Optional[bool] = Field(None, description="Instant Book listings only.")
    guest_favorite: Optional[bool] = Field(None, description="Guest Favorite listings only.")
    free_cancellation: Optional[bool] = Field(None, description="Listings with free cancellation only.")
    amenities: Optional[str] = Field(None, description="Comma-separated amenities (1-200 characters): wifi, air_conditioning, pool, kitchen, free_parking, washer, self_check_in, tv, or raw numeric Airbnb amenity ids. An unrecognised NAME is rejected before the scrape.")
    currency: Optional[str] = Field(None, description="ISO 4217 currency for prices, 3 letters (default 'USD'). Without it Airbnb prices off the proxy exit and identical requests disagree.")
    page: Optional[int] = Field(None, description="Results page, 1-based. 18 listings per page. Cannot be combined with cursor.")
    cursor: Optional[str] = Field(None, description="next_cursor from a previous response (1-500 characters); wins over page, so sending both is rejected.")


class AirbnbListingInput(BaseModel):
    listing_id: str = Field(description="Airbnb listing id or a full /rooms/ URL (1-500 characters); query params are discarded, since they carry someone else's dates.")
    check_in: Optional[str] = Field(None, description="Check-in date, YYYY-MM-DD. Must be sent with check_out. Does not produce a price: the room page has no nightly rate.")
    check_out: Optional[str] = Field(None, description="Check-out date, YYYY-MM-DD. Must be later than check_in and sent together with it.")
    adults: Optional[int] = Field(None, description="Adult guests, >= 1.")
    children: Optional[int] = Field(None, description="Children aged 2-12, >= 0.")
    infants: Optional[int] = Field(None, description="Infants under 2, >= 0.")
    pets: Optional[int] = Field(None, description="Pets, >= 0.")
    currency: Optional[str] = Field(None, description="ISO 4217 currency, 3 letters (default 'USD').")


class AirbnbReviewsInput(BaseModel):
    listing_id: str = Field(description="Airbnb listing id or a full /rooms/ URL (1-500 characters).")
    currency: Optional[str] = Field(None, description="ISO 4217 currency, 3 letters (default 'USD').")
    limit: Optional[int] = Field(None, description="Reviews to return, 1-50 (default 30). Upstream returns a fixed 7 when no explicit limit is sent.")
    offset: Optional[int] = Field(None, description="Reviews to skip before this page, >= 0 (default 0).")


# Glassdoor
class GlassdoorCompaniesInput(BaseModel):
    query: str = Field(description="Company name to resolve (1-120 characters).")


class GlassdoorCompanyInput(BaseModel):
    employer_id: Optional[str] = Field(None, description="Glassdoor employer id (1-50 characters) in any form Glassdoor writes it: '1699', 'E1699' or 'IE1699'. Must be a STRING - a JSON number is rejected.")
    company: Optional[str] = Field(None, description="Employer name as it appears in a Glassdoor slug (1-200 characters). COSMETIC: the profile resolves on employer_id alone, it is ignored entirely when url is set, and it does not satisfy the employer_id-or-url requirement.")
    url: Optional[str] = Field(None, description="Any glassdoor.com employer URL (1-500 characters): /Overview/, /Reviews/ or /Salary/. A non-glassdoor.com host is rejected.")


class GlassdoorReviewsInput(BaseModel):
    employer_id: Optional[str] = Field(None, description="Glassdoor employer id (1-50 characters): '1699', 'E1699' or 'IE1699'. Must be a STRING - a JSON number is rejected. Addressing by id costs two upstream fetches; the customer price is unchanged.")
    company: Optional[str] = Field(None, description="Employer name as it appears in a Glassdoor slug (1-200 characters). COSMETIC: ignored when url is set, and it does not satisfy the employer_id-or-url requirement.")
    url: Optional[str] = Field(None, description="Any glassdoor.com employer URL (1-500 characters). Pass back reviews_url from company() to skip the resolve fetch. A non-glassdoor.com host is rejected.")
    category: Optional[str] = Field(None, description="Restrict to reviews Glassdoor files under one topic. Closed enum: Glassdoor IGNORES an unknown value and serves the unfiltered set under a 200. Read filtered_review_count on the response to see how many match. Accepted values: 'career_development', 'compensation', 'culture', 'diversity_and_inclusion', 'management', 'work_life_balance'.")
    employment_status: Optional[str] = Field(None, description="Restrict to one kind of employment. Closed enum for the same reason as category; FREELANCE is deliberately absent because it was never confirmed to change the result set. Accepted values: 'full_time', 'part_time', 'contract', 'intern'.")


class GlassdoorSalariesInput(BaseModel):
    employer_id: Optional[str] = Field(None, description="Glassdoor employer id (1-50 characters): '1699', 'E1699' or 'IE1699'. Must be a STRING - a JSON number is rejected. Addressing by id costs two upstream fetches; the customer price is unchanged.")
    company: Optional[str] = Field(None, description="Employer name as it appears in a Glassdoor slug (1-200 characters). COSMETIC: ignored when url is set, and it does not satisfy the employer_id-or-url requirement.")
    url: Optional[str] = Field(None, description="Any glassdoor.com employer URL (1-500 characters). Pass back salaries_url from company() to skip the resolve fetch. A non-glassdoor.com host is rejected.")
    page: Optional[int] = Field(None, description="Results page, 1-based. Ten job titles per page; page_count on the response is how many pages exist.")


# Yelp
class YelpSearchInput(BaseModel):
    term: Optional[str] = Field(None, description="What to look for (1-200 characters): a category ('plumbers'), a dish, or a business name. Required together with location unless url is given.")
    location: Optional[str] = Field(None, description="Where to look (1-200 characters): city and region, a full address, or a postcode. Effectively required - Yelp geolocates a location-less search off the proxy exit, so the same request answers about a different metro run to run.")
    page: Optional[int] = Field(None, description="Results page, 1-based. Yelp fixes the page size at 10.")
    sort: Optional[str] = Field(None, description="Result ordering (upstream default 'recommended'). Closed enum: Yelp IGNORES an unrecognised sortby and serves default ranking under a 200, billing a premium scrape for a sort that never ran. Accepted values: 'recommended', 'rating', 'review_count'.")
    price: Optional[list[int]] = Field(None, description="Price bands to include, 1 ($) to 4 ($$$$); 1-4 values, combined freely - [1, 2] means $ or $$. Accepted values: 1, 2, 3, 4.")
    open_now: Optional[bool] = Field(None, description="Only businesses open at the moment of the request.")
    attributes: Optional[list[str]] = Field(None, description="Raw Yelp filter aliases, max 20, each 1-100 characters ('RestaurantsDelivery', 'GoodForKids', 'WheelchairAccessible'). A deliberate PASSTHROUGH, not an enum - Yelp's vocabulary runs to ~117 values per vertical and an alias it does not know is ignored upstream, returning unfiltered results.")
    url: Optional[str] = Field(None, description="A full yelp.com/search URL (1-1000 characters) as an alternative to term + location; the query, offset and sort are read out of it and the URL is rebuilt.")


class YelpBusinessInput(BaseModel):
    business_id: Optional[str] = Field(None, description="A Yelp business alias ('desnudo-coffee-austin-2'), its opaque encid, or any yelp.com/biz URL carrying one (1-500 characters). Search rows return both id forms.")
    url: Optional[str] = Field(None, description="A full yelp.com/biz URL (1-1000 characters) as an alternative to business_id.")


class YelpReviewsInput(BaseModel):
    business_id: Optional[str] = Field(None, description="A Yelp business alias ('desnudo-coffee-austin-2'), its opaque encid, or any yelp.com/biz URL carrying one (1-500 characters).")
    url: Optional[str] = Field(None, description="A full yelp.com/biz URL (1-1000 characters) as an alternative to business_id.")
    page: Optional[int] = Field(None, description="Reviews page, 1-based, 10 per page. Page 1 duplicates the reviews business() already returned and costs another 2 credits - start at 2. A page past the last review is a 404, not an empty result.")
    sort: Optional[str] = Field(None, description="Review ordering (upstream default 'relevance'). Closed enum: Yelp IGNORES an unrecognised value and serves default ranking under a billed 200. Accepted values: 'relevance', 'newest', 'oldest', 'rating_high', 'rating_low', 'elites'.")
    rating: Optional[int] = Field(None, description="Only reviews at this star rating, 1-5. Changes filtered_review_count on the response, not review_count. Accepted values: 1, 2, 3, 4, 5.")


# Apple App Store
class AppStoreSearchInput(BaseModel):
    term: str = Field(description="What to search for (1-500 characters). Apple matches an app name, a keyword OR a publisher name, so searching a developer returns their catalogue.")
    limit: Optional[int] = Field(None, description="Apps to return, 1-200 (default 25). The ONLY lever on result volume: the search API has no pagination and every offset spelling is silently ignored.")
    country: Optional[str] = Field(None, description="Two-letter ISO storefront code (default 'us'); decides price, currency, localised title and whether the app is sold there at all. Anything that is not exactly two letters is rejected with a free 400.")
    entity: Optional[str] = Field(None, description="Which catalogue to search: iPhone/iPad apps ('software', the default), iPad apps, or Mac App Store apps. These are separate stores, not a filter - Mac rows carry no iPad/Apple TV screenshots, advisories, features, supported devices or Game Center flag, returning them empty rather than absent. Accepted values: 'software', 'ipad_software', 'mac_software'.")
    lang: Optional[str] = Field(None, description="Listing text language as a five-letter code ('en_us', 'ja_jp'); any other shape is rejected. Independent of country: the storefront sets the price, this sets the words.")


class AppStoreAppInput(BaseModel):
    app_id: str = Field(description="App Store id - the digits after 'id' in an apps.apple.com URL - or the app's bundle id ('notion.id', 'com.burbn.instagram'); both resolve to the identical payload. 1-255 characters matching ^[A-Za-z0-9][A-Za-z0-9._-]*$, so a pasted apps.apple.com URL is rejected with a free 400. An id Apple cannot resolve is a billed 404.")
    country: Optional[str] = Field(None, description="Two-letter ISO storefront code (default 'us'); decides price, currency, localised title and whether the app is sold there at all. Anything that is not exactly two letters is rejected with a free 400.")


class AppStoreReviewsInput(BaseModel):
    app_id: str = Field(description="App Store id, NUMERIC ONLY - unlike app(), the reviews feed has no bundle-id form.")
    country: Optional[str] = Field(None, description="Two-letter ISO storefront code (default 'us'). Anything that is not exactly two letters is rejected with a free 400. Ask a different country to reach past the 500-review ceiling.")
    page: Optional[int] = Field(None, description="Reviews page, 1-10, 50 reviews each (default 1). Apple hard-stops at page 10.")
    sort: Optional[str] = Field(None, description="Review ordering (default 'most_recent'). The choice decides whether the vote fields mean anything: under most_recent almost every review is too new to have been voted on and returns zeroes, while most_helpful returns them densely populated.")


# Google Play
class GooglePlaySearchInput(BaseModel):
    query: str = Field(description="What to search the store for (1-200 characters): an app name, a publisher, or a category phrase. Apps only - games are folded into the apps vertical, but books and films use a different card shape and are not covered.")
    hl: Optional[str] = Field(None, description="UI language, 2-20 characters (default 'en'). Changes the STOREFRONT, not only the strings: at hl=pt-BR the title, description, install formatting and content rating all move with it. Play silently falls back to English on a value it does not serve.")
    gl: Optional[str] = Field(None, description="Country code, 2-10 characters (default 'us'), deciding which storefront's price and availability are returned. Play silently falls back to the US storefront on a country it does not serve.")


class GooglePlayAppInput(BaseModel):
    app_id: str = Field(description="Android package name ('com.spotify.music') or any play.google.com URL carrying one in its id param (1-500 characters).")
    hl: Optional[str] = Field(None, description="UI language, 2-20 characters (default 'en'). Changes the STOREFRONT, not only the strings: title, description, install formatting and content rating all move with it. Play silently falls back to English on a value it does not serve.")
    gl: Optional[str] = Field(None, description="Country code, 2-10 characters (default 'us'), deciding which storefront's price and availability are returned. Play silently falls back to the US storefront on a country it does not serve.")


class GooglePlayReviewsInput(BaseModel):
    app_id: str = Field(description="Android package name ('com.spotify.music') or any play.google.com URL carrying one in its id param (1-500 characters).")
    sort: Optional[str] = Field(None, description="Review ordering (default 'newest'). Closed enum. The cursor encodes the sort, so keep this identical when paging. Accepted values: 'relevance', 'newest', 'rating'.")
    count: Optional[int] = Field(None, description="Reviews to return, 1-200 (default 50); 200 is our cap, not Play's. Play honours more, but a single page that large is megabytes for one credit - page with cursor instead.")
    cursor: Optional[str] = Field(None, description="Continuation token from a prior response's next_cursor (1-4000 characters). Opaque and SINGLE-USE, and it encodes the sort as well as the position - send it back with the SAME sort it came from. A cursor past the last review is a 404, not an empty page.")
    hl: Optional[str] = Field(None, description="UI language, 2-20 characters (default 'en'). Changes the STOREFRONT, not only the strings. Play silently falls back to English on a value it does not serve.")
    gl: Optional[str] = Field(None, description="Country code, 2-10 characters (default 'us'), deciding which storefront's price and availability are returned. Play silently falls back to the US storefront on a country it does not serve.")


# SEC EDGAR
class SECLookupInput(BaseModel):
    query: str = Field(description="Ticker ('AAPL', 'BRK.B'), company name, or a fragment of one (1-200 characters); each row carries its match tier as 'match'.")
    limit: Optional[int] = Field(None, description="Rows to return, 1-100. Defaults to 10. Sizes the response; it is not a page param.")
    exchange: Optional[str] = Field(None, description="Restrict to one listing venue; matched case-insensitively, so 'Nasdaq' also works. Filers the SEC lists with no exchange at all are excluded by any value. Accepted values: 'NASDAQ', 'NYSE', 'OTC', 'CBOE'.")


class SECCompanyInput(BaseModel):
    cik: Optional[str] = Field(None, description="Filer CIK in any spelling (1-20 characters): 320193, 0000320193 or CIK0000320193. A ticker is accepted here too.")
    ticker: Optional[str] = Field(None, description="Ticker symbol (1-20 characters), dotted or dashed (BRK.B / BRK-B). Wins over cik when both are given.")


class SECFilingsInput(BaseModel):
    cik: Optional[str] = Field(None, description="Filer CIK, zero-padded or bare (1-20 characters). A ticker is accepted here too.")
    ticker: Optional[str] = Field(None, description="Ticker symbol (1-20 characters), as an alternative to cik.")
    form: Optional[Union[str, list[str]]] = Field(None, description="Form types to keep: '10-K', ['10-K', '10-Q'] or the comma-joined '10-K,8-K'; each value 1-50 characters, at most 25 values. Matched against the form AND its root form, so 10-K also returns 10-K/A amendments; ask for '10-K/A' to get only amendments.")
    date_from: Optional[str] = Field(None, description="Earliest filing date, inclusive (YYYY-MM-DD).")
    date_to: Optional[str] = Field(None, description="Latest filing date, inclusive (YYYY-MM-DD).")
    page: Optional[int] = Field(None, description="Results page, 1-based; page size is whatever limit is set to. No upper bound.")
    limit: Optional[int] = Field(None, description="Filings per page, 1-500. Defaults to 50.")
    include_history: Optional[bool] = Field(None, description="Also fetch the archived filing history beyond EDGAR's 'recent' block, which is not a fixed window (a decade for a quiet filer, about a year for a prolific one). Off by default; at most 10 archived shards are fetched, history_truncated says when a filer had more, and it is still 1 credit.")


class SECConceptInput(BaseModel):
    concept: str = Field(description="XBRL concept tag, CASE-SENSITIVE (1-120 characters, ^[A-Za-z][A-Za-z0-9]*$): 'NetIncomeLoss' matches, 'netincomeloss' is a 404 upstream. Use facts() to list what a filer actually reports.")
    cik: Optional[str] = Field(None, description="Filer CIK, zero-padded or bare (1-20 characters). A ticker is accepted here too.")
    ticker: Optional[str] = Field(None, description="Ticker symbol (1-20 characters), as an alternative to cik.")
    taxonomy: Optional[str] = Field(None, description="Reporting taxonomy (1-40 characters, ^[A-Za-z][A-Za-z0-9-]*$): us-gaap, dei, ifrs-full or srt. Defaults to 'us-gaap'.")
    unit: Optional[str] = Field(None, description="Unit of measure to keep (1-40 characters), e.g. 'USD' vs 'USD/shares'.")
    form: Optional[str] = Field(None, description="Form to keep (1-50 characters). EXACT match here, unlike filings(), so '10-K' excludes 10-K/A.")
    limit: Optional[int] = Field(None, description="Rows to return, 1-2000. Defaults to 250. Sizes the response; it is not a page param.")


class SECFactsInput(BaseModel):
    cik: Optional[str] = Field(None, description="Filer CIK, zero-padded or bare (1-20 characters). A ticker is accepted here too.")
    ticker: Optional[str] = Field(None, description="Ticker symbol (1-20 characters), as an alternative to cik.")
    taxonomy: Optional[str] = Field(None, description="Restrict to one taxonomy (1-40 characters), e.g. 'us-gaap' or 'dei'.")
    query: Optional[str] = Field(None, description="Case-insensitive substring matched against the tag name and label (1-200 characters).")
    limit: Optional[int] = Field(None, description="Rows to return, 1-2000. Defaults to 250. Sizes the response; it is not a page param.")


class SECSearchInput(BaseModel):
    query: Optional[str] = Field(None, description="Full-text query over filing documents (1-500 characters); a quoted phrase is matched exactly, bare words as a bag of terms. Optional - a cik, ticker, form or date filter on its own is a valid search.")
    cik: Optional[Union[str, list[str]]] = Field(None, description="Restrict to one or more filers by CIK: a single value, a list, or a comma-joined string; each 1-20 characters, at most 25 values. Tickers are accepted here too.")
    ticker: Optional[Union[str, list[str]]] = Field(None, description="Restrict to one or more filers by ticker symbol: a single value, a list, or a comma-joined string; each 1-20 characters, at most 25 values.")
    form: Optional[Union[str, list[str]]] = Field(None, description="Form types to keep: '8-K', ['10-K', '10-Q'] or the comma-joined '10-K,10-Q'; each 1-50 characters, at most 25 values.")
    date_from: Optional[str] = Field(None, description="Earliest filing date, inclusive (YYYY-MM-DD). Full-text coverage starts in 2001.")
    date_to: Optional[str] = Field(None, description="Latest filing date, inclusive (YYYY-MM-DD).")
    location: Optional[Union[str, list[str]]] = Field(None, description="Filer business-address locations as EDGAR's own 2-character codes (CA, NY, and its alphanumeric codes for foreign jurisdictions): a single value, a list, or a comma-joined string; at most 25 values.")
    sort: Optional[str] = Field(None, description="Result ordering. Defaults to the index's own relevance ranking. Accepted values: 'relevance', 'newest', 'oldest'.")
    page: Optional[int] = Field(None, description="Results page, 1-based, 1-100, 100 documents per page. The SEC's index refuses a result window past 10,000, so 100 is the last page for any query.")


# Redfin
class RedfinSearchInput(BaseModel):
    location: Optional[str] = Field(None, description="A redfin.com region URL (/city/, /neighborhood/, /county/, /zipcode/) or a bare 5-digit ZIP (1-500 characters). CITY NAMES ARE NOT ACCEPTED - Redfin's own name lookup is blocked to us; use region_id + region_type instead.")
    region_id: Optional[int] = Field(None, description="Redfin internal region id (>= 1), used together with region_type. NOT a ZIP code - the two are different number spaces and a ZIP here resolves to another city rather than failing.")
    region_type: Optional[int] = Field(None, description="Region kind that region_id belongs to: 1 neighborhood, 2 ZIP, 5 county, 6 city. Must be sent together with region_id or both are ignored in favour of location.")
    listing_status: Optional[str] = Field(None, description="Market to search. Defaults to 'for_sale'. Accepted values: 'for_sale', 'sold', 'for_rent'.")
    sold_within_days: Optional[int] = Field(None, description="Sold within the last N days (>= 1). REJECTED unless listing_status='sold', where it defaults to 90.")
    page: Optional[int] = Field(None, description="Results page, 1-based; page size is whatever limit is set to. No upper bound.")
    limit: Optional[int] = Field(None, description="Listings per page, 1-350. Defaults to 100.")
    sort: Optional[str] = Field(None, description="Result sort order. Defaults to 'recommended', Redfin's own ranking. Accepted values: 'recommended', 'price_low', 'price_high', 'newest', 'oldest', 'sqft_low', 'sqft_high', 'price_per_sqft_low', 'price_per_sqft_high'.")
    min_price: Optional[float] = Field(None, description="Minimum price, inclusive (>= 0). Monthly rent when listing_status='for_rent'.")
    max_price: Optional[float] = Field(None, description="Maximum price, inclusive (>= 0). Monthly rent when listing_status='for_rent'.")
    beds_min: Optional[int] = Field(None, description="Minimum bedrooms (whole number >= 0); fractional values are rejected.")
    beds_max: Optional[int] = Field(None, description="Maximum bedrooms (whole number >= 0); fractional values are rejected.")
    baths_min: Optional[int] = Field(None, description="Minimum bathrooms (whole number >= 0). WHOLE BATHS ONLY - 1.5 is rejected rather than silently truncated to 1. There is no baths_max.")
    sqft_min: Optional[int] = Field(None, description="Minimum living area in square feet (whole number >= 0).")
    sqft_max: Optional[int] = Field(None, description="Maximum living area in square feet (whole number >= 0).")
    lot_size_min: Optional[int] = Field(None, description="Minimum lot size in square feet (whole number >= 0). There is no lot_size_max.")
    year_built_min: Optional[int] = Field(None, description="Earliest year built (whole number >= 0).")
    year_built_max: Optional[int] = Field(None, description="Latest year built (whole number >= 0).")
    max_hoa: Optional[float] = Field(None, description="Maximum monthly HOA fee in dollars (>= 0).")
    property_type: Optional[str] = Field(None, description="Restrict to one property type. Accepted values: 'house', 'condo', 'townhouse', 'multi_family', 'land', 'other', 'co_op'.")
    has_pool: Optional[bool] = Field(None, description="Only listings with a pool.")
    max_days_on_market: Optional[int] = Field(None, description="Listed at most N days ago (whole number >= 0). Cannot be combined with min_days_on_market - Redfin expresses both bounds through one param.")
    min_days_on_market: Optional[int] = Field(None, description="Listed at least N days ago (whole number >= 0). Cannot be combined with max_days_on_market.")


class RedfinPropertyInput(BaseModel):
    property_id: str = Field(description="Redfin property id, or any redfin.com listing URL carrying one (1-500 characters).")


class RedfinMarketInput(BaseModel):
    location: Optional[str] = Field(None, description="A redfin.com region URL (/city/, /neighborhood/, /county/, /zipcode/) or a bare 5-digit ZIP (1-500 characters). City names are not accepted.")
    region_id: Optional[int] = Field(None, description="Redfin internal region id (>= 1), used together with region_type. Not a ZIP code.")
    region_type: Optional[int] = Field(None, description="Region kind that region_id belongs to: 1 neighborhood, 2 ZIP, 5 county, 6 city. Must be sent together with region_id or both are ignored in favour of location.")


# Companies House
class CompaniesHouseSearchInput(BaseModel):
    query: str = Field(description="Company name or fragment (1-200 characters, non-blank). Matches CURRENT AND FORMER names.")
    page: Optional[int] = Field(None, description="Results page, 1-based, 1-50, 20 results per page. Defaults to 1. The register serves only a 1000-result window per term whatever hit count it prints, and answers page 51 with HTTP 416.")


class CompaniesHouseCompanyInput(BaseModel):
    company_number: str = Field(description="UK company number (1-20 characters), zero-padded and upper-cased for you, so '445790' and 'sc090312' both work. Registry prefixes supported: SC, NI, OC, SO, NC, FC, BR, CE.")


class CompaniesHouseOfficersInput(BaseModel):
    company_number: str = Field(description="UK company number (1-20 characters), zero-padded and upper-cased for you.")
    page: Optional[int] = Field(None, description="Results page, 1-based, 35 per page. Defaults to 1. No upper bound: past the last page the register answers an ordinary 200 with an empty list, identical to a company with no officers.")


class CompaniesHouseFilingHistoryInput(BaseModel):
    company_number: str = Field(description="UK company number (1-20 characters), zero-padded and upper-cased for you.")
    page: Optional[int] = Field(None, description="Results page, 1-based. Defaults to 1. No upper bound: past the last page the register answers an ordinary 200 with an empty list.")


# G2 Software Reviews
class G2SearchInput(BaseModel):
    query: Optional[str] = Field(None, description="Search term (1-200 characters). Provide this or url.")
    page: Optional[int] = Field(None, description="1-based page number; page size follows limit (server default 20). G2 keeps paginating well past its own widget's page links.")
    limit: Optional[int] = Field(None, description="Results per page (1-100; server default 20). The 100 ceiling is ours, to keep a single request inside the 60s deadline; G2 itself paginates at any size.")
    sort: Optional[str] = Field(None, description="Result sort order (server default 'relevance'). Closed enum: G2 silently accepts an unknown sort and answers 200 with an unstated ordering. Accepted values: 'relevance', 'popular', 'alphabetical', 'rating'.")
    rating: Optional[int] = Field(None, description="Only products at or above this star rating (1-5, sent as an integer). Omit for no rating floor. Accepted values: 1, 2, 3, 4, 5.")
    url: Optional[str] = Field(None, description="Full g2.com/search URL, as an alternative to query (1-1000 characters; the host is checked by the transport).")


class G2ProductInput(BaseModel):
    product_id: Optional[str] = Field(None, description="G2 product slug ('notion') or the numeric G2 id ('82623') as a string (1-200 characters); both resolve on the same upstream path.")
    url: Optional[str] = Field(None, description="Full g2.com product URL, as an alternative to product_id (1-1000 characters).")


class G2ReviewsInput(BaseModel):
    product_id: Optional[str] = Field(None, description="G2 product slug or numeric G2 id as a string (1-200 characters).")
    url: Optional[str] = Field(None, description="Full g2.com reviews URL, as an alternative to product_id (1-1000 characters).")
    page: Optional[int] = Field(None, description="1-based page number; fixed at 10 reviews per page.")
    sort: Optional[str] = Field(None, description="Review sort order (server default 'relevance'). Closed enum: an unknown sort is silently accepted upstream and never runs. Accepted values: 'relevance', 'newest', 'most_helpful', 'rating_high', 'rating_low'.")
    rating: Optional[int] = Field(None, description="Only reviews in this star bucket (1-5, sent as an integer). Buckets are half- star-inclusive: 1 returns 0, 0.5 and 1-star reviews. Accepted values: 1, 2, 3, 4, 5.")
    company_size: Optional[str] = Field(None, description="Reviewer company size: small_business is 50 employees or fewer, mid_market 51-1000, enterprise over 1000. Closed enum -- an unknown value matches nothing and returns a billed 'Reviews (0)'.")
    role: Optional[str] = Field(None, description="Reviewer role. Closed enum -- an unknown value matches nothing rather than erroring. Accepted values: 'user', 'administrator', 'executive_sponsor', 'internal_consultant', 'consultant', 'agency', 'industry_analyst'.")
    region: Optional[str] = Field(None, description="Reviewer region. Closed enum -- an unknown value matches nothing rather than erroring. Accepted values: 'north_america', 'europe', 'asia', 'latin_america', 'anz', 'middle_east', 'africa'.")
    query: Optional[str] = Field(None, description="Full-text search within this product's reviews (1-200 characters); narrows the review list AND every facet count.")


# Capterra Software Reviews
class CapterraSearchInput(BaseModel):
    query: Optional[str] = Field(None, description="Search term (1-200 characters). Required in practice: a term-less Capterra search serves a fixed popular-products list unrelated to the caller.")
    url: Optional[str] = Field(None, description="Full capterra.com search URL, as an alternative to query (1-1000 characters; the transport also accepts capterra.co.uk and capterra.com.br hosts).")


class CapterraProductInput(BaseModel):
    product_id: Optional[str] = Field(None, description="The number in a Capterra product path such as /p/186596/Notion/ (1-50 characters). Must be a STRING -- a JSON number is rejected.")
    slug: Optional[str] = Field(None, description="Product slug (1-200 characters). Cosmetic on this endpoint -- a wrong slug still returns the right profile -- but load-bearing on reviews().")
    url: Optional[str] = Field(None, description="Full Capterra product URL, as an alternative to product_id (1-1000 characters).")


class CapterraReviewsInput(BaseModel):
    product_id: Optional[str] = Field(None, description="Capterra product id as a string (1-50 characters).")
    slug: Optional[str] = Field(None, description="Product slug (1-200 characters). LOAD-BEARING here: it is case-sensitive upstream and a wrong one silently serves page one under a billed 200. Pass back the slug from search() or product().")
    url: Optional[str] = Field(None, description="Full Capterra reviews URL, as an alternative to product_id (1-1000 characters). Passing back reviews_url from product() is the reliable way to page.")
    page: Optional[int] = Field(None, description="1-based page number (1-100); 25 reviews per page. 100 is a hard cap whatever the review count says -- past it Capterra answers 200 with page one.")


# Google Ads Transparency
class GoogleAdsAdvertisersInput(BaseModel):
    query: str = Field(description="Brand name or domain to resolve (1-200 characters).")
    region: Optional[str] = Field(None, description="ISO 3166-1 alpha-2 country ('US', 'GB', 'DE') or a Google geo criteria id as a string (2-12 characters). Default: no region filter.")
    limit: Optional[int] = Field(None, description="Rows per arm (1-20; server default 10). Advertisers and domains are capped separately, so a name query can return up to twice this many rows.")


class GoogleAdsSearchInput(BaseModel):
    domain: Optional[str] = Field(None, description="Advertiser website (1-253 characters): bare host, www host or full URL, reduced to the registrable host. The only way to get `domain` back on each row.")
    advertiser_id: Optional[str] = Field(None, description="Google advertiser id, e.g. 'AR16735076323512287233' (3-40 characters). The shape is checked before any request, so a typo costs no credits. Querying by id drops `domain` from every row.")
    region: Optional[str] = Field(None, description="ISO 3166-1 alpha-2 country ('US', 'GB', 'DE') or a Google geo criteria id as a string (2-12 characters). Scopes the deep links on every row, and the same advertiser can share zero creatives between two countries. Default: worldwide.")
    format: Optional[str] = Field(None, description="Creative format. The three sets are disjoint -- an advertiser's text, image and video ads share no creatives. Default: all formats.")
    platform: Optional[str] = Field(None, description="Google surface the ad ran on. Default: all surfaces. Accepted values: 'play', 'maps', 'search', 'shopping', 'youtube'.")
    topic: Optional[str] = Field(None, description="Ad topic (server default 'all'). Accepted values: 'all', 'political'.")
    limit: Optional[int] = Field(None, description="Ads per page (1-100; server default 40). 100 is a hard upstream ceiling, not our policy: Google answers a larger request with zero rows rather than an error.")
    cursor: Optional[str] = Field(None, description="next_cursor from the previous response (1-4000 characters), 100 ads per page. Re-send the same filters alongside it; next_cursor is null once exhausted.")


class GoogleAdsCreativeInput(BaseModel):
    advertiser_id: str = Field(description="Google advertiser id, e.g. 'AR16735076323512287233' (3-40 characters).")
    creative_id: str = Field(description="Creative id (3-40 characters). It must belong to the advertiser_id sent with it -- the lookup is keyed by the pair and a mismatched pair is a 404.")


# Meta Ad Library
class MetaAdsSearchInput(BaseModel):
    query: str = Field(description="Keyword to search the ad library for (1-200 characters).")
    country: Optional[str] = Field(None, description="Ad library country as an exactly 2-character ISO 3166-1 alpha-2 code (server default 'US').")
    active_status: Optional[str] = Field(None, description="Whether the ad is still running (server default 'all'). Accepted values: 'all', 'active', 'inactive'.")
    ad_type: Optional[str] = Field(None, description="Set 'political_and_issue_ads' to expose spend, reach, impressions and the paid-for-by disclosure; commercial ads leave all four null (server default 'all').")
    media_type: Optional[str] = Field(None, description="Creative media filter. Default: no media filter. Accepted values: 'all', 'image', 'video', 'meme', 'image_and_meme', 'none'.")
    search_type: Optional[str] = Field(None, description="How the query is matched (server default 'keyword_unordered'). Accepted values: 'keyword_unordered', 'keyword_exact_phrase'.")
    cursor: Optional[str] = Field(None, description="next_cursor from the previous response: page 1 is 30 ads, every cursor page is 10. The cursor is a self-contained blob, so ALL other filters are ignored when it is present.")


class MetaAdsAdvertiserInput(BaseModel):
    page_id: str = Field(description="The advertiser's numeric Facebook Page id (3-25 digits, as a string).")
    country: Optional[str] = Field(None, description="Ad library country as an exactly 2-character ISO 3166-1 alpha-2 code (server default 'US').")
    active_status: Optional[str] = Field(None, description="Whether the ad is still running (server default 'all'). Accepted values: 'all', 'active', 'inactive'.")
    ad_type: Optional[str] = Field(None, description="Set 'political_and_issue_ads' to expose spend, reach, impressions and the paid-for-by disclosure; commercial ads leave all four null (server default 'all').")
    media_type: Optional[str] = Field(None, description="Creative media filter. Default: no media filter. Accepted values: 'all', 'image', 'video', 'meme', 'image_and_meme', 'none'.")
    cursor: Optional[str] = Field(None, description="next_cursor from the previous response: page 1 is 30 ads, every cursor page is 10. ALL other filters are ignored when it is present.")


class MetaAdsAdInput(BaseModel):
    ad_archive_id: str = Field(description="Meta ad archive id (3-25 digits, as a string).")


# Extract is a CORE endpoint, not a platform: it is the top-level
# client.extract(url, format=, mode=), never client.extract.extract().
class ExtractInput(BaseModel):
    url: str = Field(description="Page to read (1-2048 characters). http(s) only; a bare host is upgraded to https, and loopback, private, link-local and metadata hosts are rejected with a 400.")
    format: Optional[str] = Field(None, description="Output format: 'html' is the raw page, 'markdown' a readability extraction, 'text' that markdown flattened to plain text (server default 'markdown').")
    mode: Optional[str] = Field(None, description="Fetch tier, and the price-bearing parameter: 'normal' plain datacenter fetch (1 credit), 'advanced' full browser render (1 credit), 'ultra' the hardest-target tier (2 credits). Server default 'normal'.")


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
    enable_extract: bool = True,
    enable_threads: bool = False,
    enable_kuaishou: bool = False,
    enable_ebay: bool = False,
    enable_target: bool = False,
    enable_home_depot: bool = False,
    enable_zillow: bool = False,
    enable_booking: bool = False,
    enable_tripadvisor: bool = False,
    enable_indeed: bool = False,
    enable_airbnb: bool = False,
    enable_glassdoor: bool = False,
    enable_yelp: bool = False,
    enable_app_store: bool = False,
    enable_google_play: bool = False,
    enable_sec: bool = False,
    enable_redfin: bool = False,
    enable_companies_house: bool = False,
    enable_g2: bool = False,
    enable_capterra: bool = False,
    enable_google_ads: bool = False,
    enable_meta_ads: bool = False,
    all: bool = False,
) -> "ExperimentalToolkit":
    """Build a Composio custom toolkit exposing Scavio search tools.

    Scavio is a single Search API over 32 platforms plus a URL reader; this
    toolkit covers every live endpoint of all of them - 189 tools in total.
    Each provider is gated by an ``enable_*`` flag so you expose only the tools
    your agent needs.

    Defaults are deliberately narrow. The ten original platforms and ``extract``
    are on (104 tools); the 21 verticals added in 0.4.0 are opt-in, because
    registering all 189 at once buries the handful an agent actually wants.

    Args:
        api_key: Scavio API key. Falls back to the ``SCAVIO_API_KEY`` env var.
        enable_google: Register the 14 Google v2 tools (web search, AI Mode, Maps,
            Shopping, Flights, Hotels, News, Trends, Trending). Defaults to True.
        enable_amazon: Register the 4 Amazon tools (search, product, offers,
            options). Defaults to True.
        enable_walmart: Register the 7 Walmart tools (search, product, reviews,
            category, offers, seller, seller-products). Defaults to True.
        enable_youtube: Register the 15 YouTube tools (search, shorts, suggestions, video,
            comments, transcript, related, channel, streams, and more). Defaults to True.
        enable_reddit: Register the 12 Reddit tools (1 credit each). Defaults to True.
        enable_tiktok: Register the 11 TikTok tools. Defaults to True.
        enable_tiktok_shop: Register the 8 TikTok Shop tools. Defaults to True.
        enable_instagram: Register the 12 Instagram tools. Defaults to True.
        enable_x: Register the 11 X (Twitter) tools. Defaults to True.
        enable_linkedin: Register the 9 live LinkedIn tools. Defaults to True.
        enable_extract: Register the top-level ``extract`` tool, which reads any
            URL as Markdown, plain text or raw HTML. Defaults to True.
        enable_threads: Register the 6 Threads tools. OPT-IN, defaults to False.
        enable_kuaishou: Register the 14 Kuaishou (China) tools. OPT-IN, defaults to False.
        enable_ebay: Register the 3 eBay tools. OPT-IN, defaults to False.
        enable_target: Register the 4 Target tools. OPT-IN, defaults to False.
        enable_home_depot: Register the 3 Home Depot tools. OPT-IN, defaults to False.
        enable_zillow: Register the 3 Zillow tools. OPT-IN, defaults to False.
        enable_booking: Register the 3 Booking.com tools. OPT-IN, defaults to False.
        enable_tripadvisor: Register the 4 Tripadvisor tools. OPT-IN, defaults to False.
        enable_indeed: Register the 4 Indeed tools. OPT-IN, defaults to False.
        enable_airbnb: Register the 3 Airbnb tools. OPT-IN, defaults to False.
        enable_glassdoor: Register the 4 Glassdoor tools. OPT-IN, defaults to False.
        enable_yelp: Register the 3 Yelp tools. OPT-IN, defaults to False.
        enable_app_store: Register the 3 Apple App Store tools. OPT-IN, defaults to False.
        enable_google_play: Register the 3 Google Play tools. OPT-IN, defaults to False.
        enable_sec: Register the 6 SEC EDGAR tools. OPT-IN, defaults to False.
        enable_redfin: Register the 3 Redfin tools. OPT-IN, defaults to False.
        enable_companies_house: Register the 4 Companies House tools. OPT-IN, defaults to False.
        enable_g2: Register the 3 G2 Software Reviews tools. OPT-IN, defaults to False.
        enable_capterra: Register the 3 Capterra Software Reviews tools. OPT-IN, defaults to False.
        enable_google_ads: Register the 3 Google Ads Transparency tools. OPT-IN, defaults to False.
        enable_meta_ads: Register the 3 Meta Ad Library tools. OPT-IN, defaults to False.
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
            "Real-time structured search over 32 platforms - Google, YouTube, Amazon, "
            "Walmart, eBay, Target, Home Depot, Reddit, TikTok, TikTok Shop, Instagram, "
            "X, LinkedIn, Threads, Kuaishou, Zillow, Redfin, Booking.com, Airbnb, "
            "Tripadvisor, Yelp, Indeed, Glassdoor, the Apple App Store, Google Play, "
            "SEC EDGAR, Companies House, G2, Capterra, Google Ads Transparency and the "
            "Meta Ad Library - plus extract, which reads any URL as Markdown, plain "
            "text or raw HTML."
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

        @toolkit.tool()
        def scavio_amazon_options(input: AmazonOptionsInput, ctx: Any = None) -> dict:
            """Supported Amazon marketplaces, as 'domains' and 'countries'. 'languages' and 'currencies' remain in the payload but are always empty: neither is a request param any more. Needs no API key and costs no credits."""
            return _run(lambda: client.amazon.options())

    if all or enable_walmart:

        @toolkit.tool()
        def scavio_walmart_search(input: WalmartSearchInput, ctx: Any = None) -> dict:
            """Search Walmart and get structured product rows (products, products_count and the store the results were priced against). Costs 1 credit on domain 'com' or 'ca' and 2 credits on 'com.mx' - the price is a function of the request body, not a constant for the route."""
            return _run(lambda: client.walmart.search(**dump(input)))

        @toolkit.tool()
        def scavio_walmart_product(input: WalmartProductInput, ctx: Any = None) -> dict:
            """Full detail for a single Walmart product: price, rating, images, specifications, availability and seller. US marketplace only - walmart.ca product pages could not be fetched at all, so this endpoint takes no domain. Costs 1 credit: Walmart is body-priced through `domain`, but this endpoint takes no domain, so it is always 1."""
            return _run(lambda: client.walmart.product(**dump(input)))

        @toolkit.tool()
        def scavio_walmart_reviews(input: WalmartReviewsInput, ctx: Any = None) -> dict:
            """Customer reviews for a Walmart product with ratings, text, author, date and the rating breakdown. 10 reviews per page; paginate with page. Costs 1 credit: Walmart is body-priced through `domain`, but this endpoint takes no domain, so it is always 1."""
            return _run(lambda: client.walmart.reviews(**dump(input)))

        @toolkit.tool()
        def scavio_walmart_category(input: WalmartCategoryInput, ctx: Any = None) -> dict:
            """Products within a Walmart category, in the same product shape as search. Costs 1 credit on domain 'com' or 'ca' and 2 credits on 'com.mx' - the price is a function of the request body, not a constant for the route."""
            return _run(lambda: client.walmart.category(**dump(input)))

        @toolkit.tool()
        def scavio_walmart_offers(input: WalmartOffersInput, ctx: Any = None) -> dict:
            """The buy-box offer for a Walmart product: price, seller, condition and buy-box flag. BUY-BOX SELLER ONLY - this is not the full offer list, and there is no way to page through the other sellers. Costs 1 credit: Walmart is body-priced through `domain`, but this endpoint takes no domain, so it is always 1."""
            return _run(lambda: client.walmart.offers(**dump(input)))

        @toolkit.tool()
        def scavio_walmart_seller(input: WalmartSellerInput, ctx: Any = None) -> dict:
            """Marketplace seller storefront: name, rating, review count, Pro Seller badge and business details. Costs 1 credit: Walmart is body-priced through `domain`, but this endpoint takes no domain, so it is always 1."""
            return _run(lambda: client.walmart.seller(**dump(input)))

        @toolkit.tool()
        def scavio_walmart_seller_products(input: WalmartSellerProductsInput, ctx: Any = None) -> dict:
            """A marketplace seller's catalog. Roughly the first 40 items are server-rendered and returned; total_count reports the seller's real catalog size. There is no pagination - the rest of the catalog is not reachable. Costs 1 credit: Walmart is body-priced through `domain`, but this endpoint takes no domain, so it is always 1."""
            return _run(lambda: client.walmart.seller_products(**dump(input)))

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
    if all or enable_threads:

        @toolkit.tool()
        def scavio_threads_profile(input: ThreadsProfileInput, ctx: Any = None) -> dict:
            """Profile details for a Threads user. Costs 2 credits addressed by user_id and 4 credits addressed by username - the price is a function of the request body, not a constant for the route; pass user_id whenever you have it."""
            return _run(lambda: client.threads.profile(**dump(input)))

        @toolkit.tool()
        def scavio_threads_user_posts(input: ThreadsUserPostsInput, ctx: Any = None) -> dict:
            """A user's Threads posts, cursor-paginated via next_cursor. Costs 2 credits addressed by user_id and 4 credits addressed by username - the price is a function of the request body, not a constant for the route; pass user_id whenever you have it."""
            return _run(lambda: client.threads.user_posts(**dump(input)))

        @toolkit.tool()
        def scavio_threads_user_replies(input: ThreadsUserRepliesInput, ctx: Any = None) -> dict:
            """A user's Threads replies, cursor-paginated via next_cursor. Costs 2 credits addressed by user_id and 4 credits addressed by username - the price is a function of the request body, not a constant for the route; pass user_id whenever you have it."""
            return _run(lambda: client.threads.user_replies(**dump(input)))

        @toolkit.tool()
        def scavio_threads_post(input: ThreadsPostInput, ctx: Any = None) -> dict:
            """A single Threads post, addressed by post_id or by its threads.net URL. Costs 2 credits: Threads is body-priced by identifier, but this endpoint has no username form, so it is always 2."""
            return _run(lambda: client.threads.post(**dump(input)))

        @toolkit.tool()
        def scavio_threads_post_comments(input: ThreadsPostCommentsInput, ctx: Any = None) -> dict:
            """Replies to a Threads post, cursor-paginated via next_cursor. Costs 2 credits: Threads is body-priced by identifier, but this endpoint has no username form, so it is always 2."""
            return _run(lambda: client.threads.post_comments(**dump(input)))

        @toolkit.tool()
        def scavio_threads_search_users(input: ThreadsSearchUsersInput, ctx: Any = None) -> dict:
            """Search Threads profiles by name or handle. This is the only search Threads exposes - there is no post or content search - and it returns a single unpaginated page. Costs 2 credits: Threads is body-priced by identifier, but this endpoint has no username form, so it is always 2."""
            return _run(lambda: client.threads.search_users(**dump(input)))

    if all or enable_kuaishou:

        @toolkit.tool()
        def scavio_kuaishou_profile(input: KuaishouProfileInput, ctx: Any = None) -> dict:
            """Profile details for a Kuaishou user. Costs 10 credits, the dearest single-object call on the platform: Kuaishou is priced PER ENDPOINT (1, 2, 10 or 40), never per platform."""
            return _run(lambda: client.kuaishou.profile(**dump(input)))

        @toolkit.tool()
        def scavio_kuaishou_user_posts(input: KuaishouUserPostsInput, ctx: Any = None) -> dict:
            """A Kuaishou user's top posts, cursor-paginated via next_cursor. Costs 1 credit: Kuaishou is priced PER ENDPOINT (1, 2, 10 or 40), never per platform."""
            return _run(lambda: client.kuaishou.user_posts(**dump(input)))

        @toolkit.tool()
        def scavio_kuaishou_user_live(input: KuaishouUserLiveInput, ctx: Any = None) -> dict:
            """A Kuaishou user's current live-stream status. Not paginated. Costs 1 credit: Kuaishou is priced PER ENDPOINT (1, 2, 10 or 40), never per platform."""
            return _run(lambda: client.kuaishou.user_live(**dump(input)))

        @toolkit.tool()
        def scavio_kuaishou_user_resolve(input: KuaishouUserResolveInput, ctx: Any = None) -> dict:
            """Turns a Kuaishou share link into a user id. Only kuaishou.com and v.kuaishou.com links are accepted; Kwai international (kwai.com) is not served upstream. Costs 1 credit: Kuaishou is priced PER ENDPOINT (1, 2, 10 or 40), never per platform."""
            return _run(lambda: client.kuaishou.user_resolve(**dump(input)))

        @toolkit.tool()
        def scavio_kuaishou_video(input: KuaishouVideoInput, ctx: Any = None) -> dict:
            """A single Kuaishou video by photo id or URL. Provide photo_id or url. Costs 2 credits: Kuaishou is priced PER ENDPOINT (1, 2, 10 or 40), never per platform."""
            return _run(lambda: client.kuaishou.video(**dump(input)))

        @toolkit.tool()
        def scavio_kuaishou_video_comments(input: KuaishouVideoCommentsInput, ctx: Any = None) -> dict:
            """Comments on a Kuaishou video, cursor-paginated via next_cursor. Costs 1 credit: Kuaishou is priced PER ENDPOINT (1, 2, 10 or 40), never per platform."""
            return _run(lambda: client.kuaishou.video_comments(**dump(input)))

        @toolkit.tool()
        def scavio_kuaishou_comment_replies(input: KuaishouCommentRepliesInput, ctx: Any = None) -> dict:
            """Replies under a root comment on a Kuaishou video, cursor-paginated via next_cursor; count sizes the page (1-50). Costs 1 credit: Kuaishou is priced PER ENDPOINT (1, 2, 10 or 40), never per platform."""
            return _run(lambda: client.kuaishou.comment_replies(**dump(input)))

        @toolkit.tool()
        def scavio_kuaishou_videos_batch(input: KuaishouVideosBatchInput, ctx: Any = None) -> dict:
            """Several Kuaishou videos in one call, hard-capped at 20 photo ids. Costs 40 credits, the dearest call on the platform: Kuaishou is priced PER ENDPOINT (1, 2, 10 or 40), never per platform."""
            return _run(lambda: client.kuaishou.videos_batch(**dump(input)))

        @toolkit.tool()
        def scavio_kuaishou_search(input: KuaishouSearchInput, ctx: Any = None) -> dict:
            """Mixed-result search across Kuaishou, cursor-paginated via next_cursor. Costs 10 credits per page: Kuaishou is priced PER ENDPOINT (1, 2, 10 or 40), never per platform."""
            return _run(lambda: client.kuaishou.search(**dump(input)))

        @toolkit.tool()
        def scavio_kuaishou_search_videos(input: KuaishouSearchVideosInput, ctx: Any = None) -> dict:
            """Kuaishou video search results, cursor-paginated via next_cursor. Costs 10 credits per page: Kuaishou is priced PER ENDPOINT (1, 2, 10 or 40), never per platform."""
            return _run(lambda: client.kuaishou.search_videos(**dump(input)))

        @toolkit.tool()
        def scavio_kuaishou_search_users(input: KuaishouSearchUsersInput, ctx: Any = None) -> dict:
            """Kuaishou user search results, cursor-paginated via next_cursor. Costs 10 credits per page: Kuaishou is priced PER ENDPOINT (1, 2, 10 or 40), never per platform."""
            return _run(lambda: client.kuaishou.search_users(**dump(input)))

        @toolkit.tool()
        def scavio_kuaishou_search_live(input: KuaishouSearchLiveInput, ctx: Any = None) -> dict:
            """Kuaishou live-stream search results, cursor-paginated via next_cursor. Costs 10 credits per page: Kuaishou is priced PER ENDPOINT (1, 2, 10 or 40), never per platform."""
            return _run(lambda: client.kuaishou.search_live(**dump(input)))

        @toolkit.tool()
        def scavio_kuaishou_tag_feed(input: KuaishouTagFeedInput, ctx: Any = None) -> dict:
            """Posts under a Kuaishou hashtag, cursor-paginated via next_cursor. Costs 1 credit: Kuaishou is priced PER ENDPOINT (1, 2, 10 or 40), never per platform."""
            return _run(lambda: client.kuaishou.tag_feed(**dump(input)))

        @toolkit.tool()
        def scavio_kuaishou_trending(input: KuaishouTrendingInput, ctx: Any = None) -> dict:
            """Kuaishou hot / live / shopping / brand / music leaderboards. One board per call, not paginated. Costs 1 credit: Kuaishou is priced PER ENDPOINT (1, 2, 10 or 40), never per platform."""
            return _run(lambda: client.kuaishou.trending(**dump(input)))

    if all or enable_ebay:

        @toolkit.tool()
        def scavio_ebay_search(input: EbaySearchInput, ctx: Any = None) -> dict:
            """Search live or SOLD eBay listings: price, condition, bids, shipping, seller, feedback. Provide query or seller; per_page accepts only 60, 120 or 240. Costs 1 credit."""
            return _run(lambda: client.ebay.search(**dump(input)))

        @toolkit.tool()
        def scavio_ebay_product(input: EbayProductInput, ctx: Any = None) -> dict:
            """One eBay listing in full: price, condition, images, item specifics, shipping, returns, auction state, seller. Costs 1 credit."""
            return _run(lambda: client.ebay.product(**dump(input)))

        @toolkit.tool()
        def scavio_ebay_seller(input: EbaySellerInput, ctx: Any = None) -> dict:
            """eBay seller profile card: store name, feedback score and %, items sold, followers, location, categories. Profile only: page a catalogue with search(seller=...). Costs 1 credit."""
            return _run(lambda: client.ebay.seller(**dump(input)))

    if all or enable_target:

        @toolkit.tool()
        def scavio_target_search(input: TargetSearchInput, ctx: Any = None) -> dict:
            """Search Target.com, the US retailer: prices, ratings, badges and promotions. Up to 28 results per page; rendered upstream, so expect around 9 seconds. Costs 1 credit."""
            return _run(lambda: client.target.search(**dump(input)))

        @toolkit.tool()
        def scavio_target_category(input: TargetCategoryInput, ctx: Any = None) -> dict:
            """Products in a Target category, same shape as search plus the category breadcrumb. Up to 28 per page; the slowest Target endpoint at around 37 seconds. Costs 1 credit."""
            return _run(lambda: client.target.category(**dump(input)))

        @toolkit.tool()
        def scavio_target_product(input: TargetProductInput, ctx: Any = None) -> dict:
            """Target product details by TCIN: price, rating, images, specifications, variants, return policy, fulfillment. seller_id/seller_name are null for stock sold by Target. Costs 1 credit."""
            return _run(lambda: client.target.product(**dump(input)))

        @toolkit.tool()
        def scavio_target_reviews(input: TargetReviewsInput, ctx: Any = None) -> dict:
            """Target reviews with the rating breakdown, per-attribute averages and guest photos. 8 review bodies maximum and no paging; expect around 40 seconds. Costs 1 credit."""
            return _run(lambda: client.target.reviews(**dump(input)))

    if all or enable_home_depot:

        @toolkit.tool()
        def scavio_home_depot_search(input: HomeDepotSearchInput, ctx: Any = None) -> dict:
            """Search Home Depot: price and promotions, brand and model, ratings, badges, per-store pickup/delivery. Page size is fixed at 12 and cannot be changed. Costs 2 credits."""
            return _run(lambda: client.home_depot.search(**dump(input)))

        @toolkit.tool()
        def scavio_home_depot_product(input: HomeDepotProductInput, ctx: Any = None) -> dict:
            """Full Home Depot item detail: pricing, images and videos, spec table, dimensions, bullets, documents, return policy. Carries a 10-review preview only. Costs 2 credits."""
            return _run(lambda: client.home_depot.product(**dump(input)))

        @toolkit.tool()
        def scavio_home_depot_reviews(input: HomeDepotReviewsInput, ctx: Any = None) -> dict:
            """One page of full Home Depot review bodies, the rating distribution, per-attribute ratings, photos and seller responses. 30 reviews per page. Costs 2 credits."""
            return _run(lambda: client.home_depot.reviews(**dump(input)))

    if all or enable_zillow:

        @toolkit.tool()
        def scavio_zillow_search(input: ZillowSearchInput, ctx: Any = None) -> dict:
            """Zillow listings in a region: price, beds, baths, living area, Zestimate, coordinates, images, days on market. A bare ZIP works alone but cannot be combined with a filter or a sort. Costs 1 credit."""
            return _run(lambda: client.zillow.search(**dump(input)))

        @toolkit.tool()
        def scavio_zillow_property(input: ZillowPropertyInput, ctx: Any = None) -> dict:
            """Full Zillow listing: price and price history, Zestimate, tax history, RESO facts, rooms, schools, open houses, photos. Rental buildings return floor plans instead. Costs 1 credit."""
            return _run(lambda: client.zillow.property(**dump(input)))

        @toolkit.tool()
        def scavio_zillow_agent_reviews(input: ZillowAgentReviewsInput, ctx: Any = None) -> dict:
            """A Zillow AGENT's profile and reviews: rating, bodies with sub-ratings, specialties, licenses, service areas, sales counts. Zillow server-renders the first five. Costs 1 credit."""
            return _run(lambda: client.zillow.agent_reviews(**dump(input)))

    if all or enable_booking:

        @toolkit.tool()
        def scavio_booking_search(input: BookingSearchInput, ctx: Any = None) -> dict:
            """Booking.com properties for a destination and stay: live nightly price, review score, star rating, location, room type, deal badges. 25 properties per page. Provide destination or dest_id. Costs 1 credit."""
            return _run(lambda: client.booking.search(**dump(input)))

        @toolkit.tool()
        def scavio_booking_hotel(input: BookingHotelInput, ctx: Any = None) -> dict:
            """One Booking.com property in full: rooms and rate plans, facilities, house rules, check-in windows, policies, images, location and review scores, priced for the stay asked for. Chaining the `url` a search row returns is cheaper than a bare slug. Costs 1 credit."""
            return _run(lambda: client.booking.hotel(**dump(input)))

        @toolkit.tool()
        def scavio_booking_reviews(input: BookingReviewsInput, ctx: Any = None) -> dict:
            """Booking.com guest reviews for a property with the score breakdown by category and Booking's own praise/complaint summary. No page param: total_count is the whole review history, count is what this response holds. Costs 1 credit."""
            return _run(lambda: client.booking.reviews(**dump(input)))

    if all or enable_tripadvisor:

        @toolkit.tool()
        def scavio_tripadvisor_locations(input: TripadvisorLocationsInput, ctx: Any = None) -> dict:
            """START HERE: resolve a place or business NAME to the TripAdvisor geo_id / location_id pair every other TripAdvisor endpoint is keyed by. Up to 20 rows. Costs 2 credits."""
            return _run(lambda: client.tripadvisor.locations(**dump(input)))

        @toolkit.tool()
        def scavio_tripadvisor_search(input: TripadvisorSearchInput, ctx: Any = None) -> dict:
            """Restaurants, hotels or attractions in a TripAdvisor geo, TripAdvisor-ranked: rating, review count, price band, address, coordinates, phone, hours, Travelers' Choice badge; each row carries the location_id + geo_id pair. 30 locations per page. Provide geo_id or url. Costs 2 credits."""
            return _run(lambda: client.tripadvisor.search(**dump(input)))

        @toolkit.tool()
        def scavio_tripadvisor_location(input: TripadvisorLocationInput, ctx: Any = None) -> dict:
            """One TripAdvisor location in full: rating, review histogram and per-aspect sub-ratings, city ranking, price band, cuisines, amenities, address, coordinates, contact, photos, and the FIRST PAGE OF REVIEWS. Provide location_id or url. Costs 2 credits."""
            return _run(lambda: client.tripadvisor.location(**dump(input)))

        @toolkit.tool()
        def scavio_tripadvisor_reviews(input: TripadvisorReviewsInput, ctx: Any = None) -> dict:
            """A page of TripAdvisor reviews: rating, trip date and type, reviewer home town and contribution count, management response. Page 1 already rides along in location(), so use this to page PAST it; consecutive pages can repeat one review at the boundary, so de-duplicate on review_id. Provide location_id or url. Costs 2 credits."""
            return _run(lambda: client.tripadvisor.reviews(**dump(input)))

    if all or enable_indeed:

        @toolkit.tool()
        def scavio_indeed_search(input: IndeedSearchInput, ctx: Any = None) -> dict:
            """Indeed job postings: title, employer, rating, location, salary range, job type, benefits, posting age, apply route. 10 postings per page. Provide query or location - a location-only search (every posting in a metro) is valid. Costs 2 credits."""
            return _run(lambda: client.indeed.search(**dump(input)))

        @toolkit.tool()
        def scavio_indeed_job(input: IndeedJobInput, ctx: Any = None) -> dict:
            """One Indeed posting in full: description text and HTML, structured salary, employment types, benefits, geocoded address, employer rating, applicant count, original ATS link. An unknown job key is a real 404 that is still billed. Costs 2 credits."""
            return _run(lambda: client.indeed.job(**dump(input)))

        @toolkit.tool()
        def scavio_indeed_company(input: IndeedCompanyInput, ctx: Any = None) -> dict:
            """Indeed employer profile: description, industry, HQ, size, revenue, CEO approval, overall and per-category ratings, reported salaries, open roles, locations. An unknown slug is a real 404 that is still billed. Costs 2 credits."""
            return _run(lambda: client.indeed.company(**dump(input)))

        @toolkit.tool()
        def scavio_indeed_company_reviews(input: IndeedCompanyReviewsInput, ctx: Any = None) -> dict:
            """Indeed employee reviews, 20 per page, with per-category ratings, pros/cons, reviewer job title and location, plus aggregated sentiment and topic/location/job-title breakdowns. Costs 2 credits."""
            return _run(lambda: client.indeed.company_reviews(**dump(input)))

    if all or enable_airbnb:

        @toolkit.tool()
        def scavio_airbnb_search(input: AirbnbSearchInput, ctx: Any = None) -> dict:
            """Airbnb stays: stay-total and per-night price with the full discount ledger, rating and review count, bedrooms/beds/baths, coordinates, badges, images, dates_are_defaulted. 18 listings per page; page and cursor are mutually exclusive. Costs 1 credit."""
            return _run(lambda: client.airbnb.search(**dump(input)))

        @toolkit.tool()
        def scavio_airbnb_listing(input: AirbnbListingInput, ctx: Any = None) -> dict:
            """One Airbnb listing in full: description, property/room type, capacity and room counts, the complete grouped amenity list (including what the place does NOT have), host profile and stats, house rules, cancellation policy, sleeping arrangements, photo tour and the RATING BREAKDOWN. Carries NO nightly price - prices are search-only. Costs 1 credit."""
            return _run(lambda: client.airbnb.listing(**dump(input)))

        @toolkit.tool()
        def scavio_airbnb_reviews(input: AirbnbReviewsInput, ctx: Any = None) -> dict:
            """Airbnb review BODIES with per-review rating, date and reviewer name/photo/location, limit/offset paged at up to 50 per call. `count` is the listing's TOTAL review count, `returned` is how many this page holds. The rating breakdown lives on listing(), not here. Costs 1 credit."""
            return _run(lambda: client.airbnb.reviews(**dump(input)))

    if all or enable_glassdoor:

        @toolkit.tool()
        def scavio_glassdoor_companies(input: GlassdoorCompaniesInput, ctx: Any = None) -> dict:
            """START HERE. Resolve a company NAME to the employer_id every other Glassdoor method is keyed by, ranked by Glassdoor and de-duplicated. Costs 1 credit."""
            return _run(lambda: client.glassdoor.companies(**dump(input)))

        @toolkit.tool()
        def scavio_glassdoor_company(input: GlassdoorCompanyInput, ctx: Any = None) -> dict:
            """Glassdoor employer profile: description, mission, industry, sector, HQ, size and revenue bands, stock symbol, year founded, overall and per-category ratings, star distribution, CEO approval, awards, FAQ and the five server-rendered reviews. Also returns reviews_url and salaries_url, which reviews() and salaries() accept as url to save a fetch. Provide employer_id or url. Costs 1 credit."""
            return _run(lambda: client.glassdoor.company(**dump(input)))

        @toolkit.tool()
        def scavio_glassdoor_reviews(input: GlassdoorReviewsInput, ctx: Any = None) -> dict:
            """Up to THREE full Glassdoor reviews - the cap is Glassdoor's login wall - with per-axis scores, pros, cons, advice, job title, location, employment status and employer response, plus complete rating statistics, star distribution, aggregate pro/con highlight terms and per-job-title review counts. There is no page param: move the window with category and employment_status. Provide employer_id or url. Costs 1 credit."""
            return _run(lambda: client.glassdoor.reviews(**dump(input)))

        @toolkit.tool()
        def scavio_glassdoor_salaries(input: GlassdoorSalariesInput, ctx: Any = None) -> dict:
            """Glassdoor salaries by job title, 10 titles per page: base-pay and total-pay percentiles P10-P90 with medians called out, sample counts, currency, pay period and last-reported date. The figures are Glassdoor's ESTIMATES for the title, not individual reported salaries. Provide employer_id or url. Costs 1 credit."""
            return _run(lambda: client.glassdoor.salaries(**dump(input)))

    if all or enable_yelp:

        @toolkit.tool()
        def scavio_yelp_search(input: YelpSearchInput, ctx: Any = None) -> dict:
            """Businesses in Yelp's ranked order: rating, review count, price band, categories, address, contact rails, hours, photos and a review snippet; every row carries both business_id and alias. Yelp fixes the page size at 10. Provide term and location, or url. Costs 2 credits."""
            return _run(lambda: client.yelp.search(**dump(input)))

        @toolkit.tool()
        def scavio_yelp_business(input: YelpBusinessInput, ctx: Any = None) -> dict:
            """One business in full: rating and per-star histogram, review count, price band, categories, address and coordinates, phone, website and menu links, hours and holidays, amenities, photos and videos, popular items, health inspections, Q&A, licences and claim status - plus the first page of reviews at no extra cost. Provide business_id or url. Costs 2 credits."""
            return _run(lambda: client.yelp.business(**dump(input)))

        @toolkit.tool()
        def scavio_yelp_reviews(input: YelpReviewsInput, ctx: Any = None) -> dict:
            """A page of reviews: rating, full text, language, author profile and expertise counts, attached photos, reaction counts and owner response. 10 per page. PAGE 1 IS REDUNDANT - it re-fetches the document business() already returned - so start at page 2. Provide business_id or url. Costs 2 credits."""
            return _run(lambda: client.yelp.reviews(**dump(input)))

    if all or enable_app_store:

        @toolkit.tool()
        def scavio_app_store_search(input: AppStoreSearchInput, ctx: Any = None) -> dict:
            """Search the App Store and get up to 200 fully-shaped app rows - the same 43-field row as app() - so a search doubles as a bulk metadata fetch and as a publisher lookup. NO PAGINATION: raise limit, there is no second page. Costs 1 credit."""
            return _run(lambda: client.app_store.search(**dump(input)))

        @toolkit.tool()
        def scavio_app_store_app(input: AppStoreAppInput, ctx: Any = None) -> dict:
            """Full App Store listing: title, description, developer and seller identity, price and currency, all-time and current-version ratings, version and release notes, genres, content rating and advisories, icons at three sizes, screenshots, download size, minimum OS, languages, supported devices and the Game Center and VPP flags. Costs 1 credit."""
            return _run(lambda: client.app_store.app(**dump(input)))

        @toolkit.tool()
        def scavio_app_store_reviews(input: AppStoreReviewsInput, ctx: Any = None) -> dict:
            """A page of App Store reviews: star rating, title, full text, author and the APP VERSION the review was written against. 50 per page, hard-stopped at page 10 - 500 reviews per storefront is Apple's anonymous ceiling. This endpoint cannot 404: an unknown id and a real app with no reviews return the same empty feed. Costs 1 credit."""
            return _run(lambda: client.app_store.reviews(**dump(input)))

    if all or enable_google_play:

        @toolkit.tool()
        def scavio_google_play_search(input: GooglePlaySearchInput, ctx: Any = None) -> dict:
            """Ranked Google Play apps: package name, title, developer, rating, install count, price and IAP range, content rating, icon and screenshots. A branded query returns the hero card as result 1 in the same row shape, plus Play's related-query rail. NO PAGINATION - one shelf of about 30 apps. Costs 2 credits."""
            return _run(lambda: client.google_play.search(**dump(input)))

        @toolkit.tool()
        def scavio_google_play_app(input: GooglePlayAppInput, ctx: Any = None) -> dict:
            """Full Google Play store listing: installs including the REAL count Play publishes but never renders, rating and star histogram, description, developer identity and legal contact, price and IAPs, categories and gameplay tags, screenshots and trailer, version and Android requirement, release and update dates, changelog, the full permission tree, the Data safety table, the 20 server-rendered reviews and the similar-apps and more-by-developer rails. Costs 2 credits."""
            return _run(lambda: client.google_play.app(**dump(input)))

        @toolkit.tool()
        def scavio_google_play_reviews(input: GooglePlayReviewsInput, ctx: Any = None) -> dict:
            """A page of Google Play reviews: star score, full text, author, thumbs-up count, developer reply and the APP VERSION the reviewer was running. Paged by cursor, up to 200 per call. app() already returns the 20 reviews Play server-renders; use this to page past them or sort differently. Costs 2 credits."""
            return _run(lambda: client.google_play.reviews(**dump(input)))

    if all or enable_sec:

        @toolkit.tool()
        def scavio_sec_lookup(input: SECLookupInput, ctx: Any = None) -> dict:
            """START HERE. Resolve a company name or ticker (AAPL) to the CIK (0000320193) every other SEC EDGAR endpoint is keyed by. Up to 100 rows, tiered by match quality. Costs 1 credit."""
            return _run(lambda: client.sec.lookup(**dump(input)))

        @toolkit.tool()
        def scavio_sec_company(input: SECCompanyInput, ctx: Any = None) -> dict:
            """SEC filer profile: legal and former names, SIC industry, filer category, EIN, LEI, state of incorporation, fiscal year end, addresses, every ticker with its exchange, and a preview of its 10 most recent filings. Provide cik or ticker. Costs 1 credit."""
            return _run(lambda: client.sec.company(**dump(input)))

        @toolkit.tool()
        def scavio_sec_filings(input: SECFilingsInput, ctx: Any = None) -> dict:
            """A page of one filer's filings: accession number, form and root form, filing and period dates, 8-K item codes, direct links to the primary document, filing index and attachment directory. Up to 500 per page. Provide cik or ticker. Costs 1 credit."""
            return _run(lambda: client.sec.filings(**dump(input)))

        @toolkit.tool()
        def scavio_sec_concept(input: SECConceptInput, ctx: Any = None) -> dict:
            """Every value a filer reported for one XBRL concept, newest period first, with the form and filing each number came from. Restatements are kept, not collapsed. Up to 2000 rows. Provide cik or ticker. Costs 1 credit."""
            return _run(lambda: client.sec.concept(**dump(input)))

        @toolkit.tool()
        def scavio_sec_facts(input: SECFactsInput, ctx: Any = None) -> dict:
            """The index of every XBRL concept a filer reports - tag, label, description, units and most recent value - across us-gaap, dei and any other taxonomy it uses. This is how you find what to ask concept() for. Up to 2000 rows. Provide cik or ticker. Costs 1 credit."""
            return _run(lambda: client.sec.facts(**dump(input)))

        @toolkit.tool()
        def scavio_sec_search(input: SECSearchInput, ctx: Any = None) -> dict:
            """EDGAR full-text search, coverage starting 2001: each hit is the matching DOCUMENT with its URL, form, filing date and filer identity, plus facets by company, form, industry and state. 100 documents per page, last page is 100. Costs 1 credit."""
            return _run(lambda: client.sec.search(**dump(input)))

    if all or enable_redfin:

        @toolkit.tool()
        def scavio_redfin_search(input: RedfinSearchInput, ctx: Any = None) -> dict:
            """Redfin listings: price, price per sqft, beds, baths, living area, lot size, year built, coordinates, listing remarks and full photo galleries, for sale, sold or for rent. Up to 350 per page. Provide location, or region_id together with region_type. Costs 1 credit."""
            return _run(lambda: client.redfin.search(**dump(input)))

        @toolkit.tool()
        def scavio_redfin_property(input: RedfinPropertyInput, ctx: Any = None) -> dict:
            """One Redfin listing in full: price, Redfin Estimate and rental estimate, complete MLS fact sheet, price and tax history, listing agents, open houses, schools, climate risk, walkability, sun exposure, monthly weather, permits, zoning, comparable sales and photos. Costs 1 credit."""
            return _run(lambda: client.redfin.property(**dump(input)))

        @toolkit.tool()
        def scavio_redfin_market(input: RedfinMarketInput, ctx: Any = None) -> dict:
            """Redfin housing-market stats for a region: median list and sale price, price per sqft, sale-to-list ratio, average offers and days on market, YoY movement, 0-100 compete score, live inventory by property type and by bedroom count, and Redfin agent presence. Provide location, or region_id together with region_type. Costs 1 credit."""
            return _run(lambda: client.redfin.market(**dump(input)))

    if all or enable_companies_house:

        @toolkit.tool()
        def scavio_companies_house_search(input: CompaniesHouseSearchInput, ctx: Any = None) -> dict:
            """START HERE. Search the UK register by name and get the company_number every other Companies House endpoint is keyed by, plus status, incorporation or dissolution date, registered office and matched former names. 20 per page, last page is 50. Costs 1 credit."""
            return _run(lambda: client.companies_house.search(**dump(input)))

        @toolkit.tool()
        def scavio_companies_house_company(input: CompaniesHouseCompanyInput, ctx: Any = None) -> dict:
            """Full UK register entry: status, type, incorporation and dissolution dates, registered office, SIC codes, previous names, accounts and confirmation-statement due dates with overdue flags, and whether it has charges, insolvency history, officers or UK establishments. Costs 1 credit."""
            return _run(lambda: client.companies_house.company(**dump(input)))

        @toolkit.tool()
        def scavio_companies_house_officers(input: CompaniesHouseOfficersInput, ctx: Any = None) -> dict:
            """UK company officers, current and resigned, 35 per page: name, role, appointment and resignation dates, correspondence address, nationality, country of residence, month-and-year date of birth and identity-verification status. Costs 1 credit."""
            return _run(lambda: client.companies_house.officers(**dump(input)))

        @toolkit.tool()
        def scavio_companies_house_filing_history(input: CompaniesHouseFilingHistoryInput, ctx: Any = None) -> dict:
            """UK filings, most recent first: date, filing type code (AA, CS01, SH03), description, register annotations and child documents, and a link to the filed PDF with its page count. A filing the register has not finished processing carries a processing_note instead of a document. Costs 1 credit."""
            return _run(lambda: client.companies_house.filing_history(**dump(input)))

    if all or enable_g2:

        @toolkit.tool()
        def scavio_g2_search(input: G2SearchInput, ctx: Any = None) -> dict:
            """Search G2, the B2B software review site, for products: star rating, review count, vendor, categories, seller description and logo, with product_id and slug on every row. Up to 100 results per page (server default 20) and page-paginated; total_results is G2's Products-tab headline and caps at 10000, while total_by_type splits the query across products, sellers, categories and discussions. Provide query or url. Costs 5 credits."""
            return _run(lambda: client.g2.search(**dump(input)))

        @toolkit.tool()
        def scavio_g2_product(input: G2ProductInput, ctx: Any = None) -> dict:
            """Full G2 product profile: rating with per-star histogram, review count, vendor, description and seller website, pricing editions with parsed amounts, feature groups, categories and breadcrumbs, supported languages, integrations, alternatives, head-to-head comparisons, media, community discussions and G2's AI-derived pros and cons. Carries NO review text at all -- G2 loads review bodies in a separate frame, so call reviews() for those. Provide product_id or url. Costs 5 credits."""
            return _run(lambda: client.g2.product(**dump(input)))

        @toolkit.tool()
        def scavio_g2_reviews(input: G2ReviewsInput, ctx: Any = None) -> dict:
            """A page of G2 reviews: rating, title, likes and dislikes, problems solved, reviewer job title, industry and company size, validated and incentivized flags -- plus what the profile page has no form of: exact per-star counts, pros and cons with per-theme counts, and company-size, role, industry, region and category facets with counts. Fixed at 10 reviews per page and paginates well past the 10 pages G2's own widget links to. Provide product_id or url. Costs 5 credits."""
            return _run(lambda: client.g2.reviews(**dump(input)))

    if all or enable_capterra:

        @toolkit.tool()
        def scavio_capterra_search(input: CapterraSearchInput, ctx: Any = None) -> dict:
            """Search Capterra, the B2B software review site: 20 ranked products with name, vendor description, rating, review count, logo and paid-placement flag, each row carrying product_id and slug. The result set is fixed at 20 and does NOT paginate -- Capterra serves identical rows for page 2, so there is deliberately no page parameter. Provide query or url. Costs 2 credits."""
            return _run(lambda: client.capterra.search(**dump(input)))

        @toolkit.tool()
        def scavio_capterra_product(input: CapterraProductInput, ctx: Any = None) -> dict:
            """Full Capterra profile: rating with per-star histogram and the four scored criteria, likelihood to recommend, review sentiment and topics, the complete pricing table with every plan and its features, every rated feature and integration, AI-derived pros and cons with the quoted review, FAQs, screenshots, badges and awards, competitor comparisons and alternatives, and the buyer profile by company size, industry and job function -- PLUS the 25 most recent reviews at no extra cost. vendor is always null here: Capterra does not publish it as structured data on the product page. Provide product_id or url. Costs 2 credits."""
            return _run(lambda: client.capterra.product(**dump(input)))

        @toolkit.tool()
        def scavio_capterra_reviews(input: CapterraReviewsInput, ctx: Any = None) -> dict:
            """A page of Capterra reviews: overall score plus five per-criterion scores, title, pros, cons, advice, usage duration, incentivized flag, alternatives considered and what they switched from, reviewer job title, industry and company size, and the vendor response -- plus a competitor list richer than the profile's, each alternative with its own rating histogram and starting price. 25 reviews per page, capped at page 100. Page 1 already rides along inside product(), so use this to page past it. Provide product_id or url. Costs 2 credits."""
            return _run(lambda: client.capterra.reviews(**dump(input)))

    if all or enable_google_ads:

        @toolkit.tool()
        def scavio_google_ads_advertisers(input: GoogleAdsAdvertisersInput, ctx: Any = None) -> dict:
            """Resolve a brand name or domain to the advertiser_id that search() and creative() are keyed by. Returns two row kinds in one list: 'advertiser' rows carrying the id, verified name, verification country and total ad count as a range, and 'domain' rows carrying a website. A name query returns both kinds; a domain-shaped query returns domains only. Autocomplete-backed, roughly 20 rows per arm, and it does not paginate. Costs 1 credit."""
            return _run(lambda: client.google_ads.advertisers(**dump(input)))

        @toolkit.tool()
        def scavio_google_ads_search(input: GoogleAdsSearchInput, ctx: Any = None) -> dict:
            """Every ad Google Ads Transparency holds for one advertiser: the creative (archived image, rich-media bundle, Google's renderer link, dimensions), advertiser id and name, format, first and last seen dates and days actually run, plus total_ads_min and total_ads_max -- Google publishes the advertiser's ad total as a range, never an exact figure. Up to 100 ads per page (server default 40); paginate by sending next_cursor back as cursor alongside the SAME filters. Provide domain or advertiser_id. Costs 1 credit."""
            return _run(lambda: client.google_ads.search(**dump(input)))

        @toolkit.tool()
        def scavio_google_ads_creative(input: GoogleAdsCreativeInput, ctx: Any = None) -> dict:
            """One creative in full, and the only endpoint carrying its history: every size variation of the asset, the impression bucket, the per-region breakdown with first and last shown dates and a per-surface impression split inside each region, the format, Google's category label and the funder disclosure on political ads. Impressions and first_shown are EEA-only (DSA-compelled) and come back null for US creatives, and an impression bucket may carry only a lower or only an upper bound. Costs 1 credit."""
            return _run(lambda: client.google_ads.creative(**dump(input)))

    if all or enable_meta_ads:

        @toolkit.tool()
        def scavio_meta_ads_search(input: MetaAdsSearchInput, ctx: Any = None) -> dict:
            """Search the Meta Ad Library by keyword: 30 ads on page 1 with the full creative -- page name, ad copy, headline, CTA, images and videos, the platforms each ran on and its run dates -- then 10 ads per cursor page, walking has_next_page to the end of the query. total_results caps at 50000 with total_is_capped true, because Meta only reports '>50,000'; never present it as an exact count. Every page costs 1 credit."""
            return _run(lambda: client.meta_ads.search(**dump(input)))

        @toolkit.tool()
        def scavio_meta_ads_advertiser(input: MetaAdsAdvertiserInput, ctx: Any = None) -> dict:
            """Every ad a Facebook Page is running, by numeric page id: 30 ads on page 1 with the same creative detail as search(), then 10 ads per cursor page, walking has_next_page to the end of the advertiser. Every page costs 1 credit."""
            return _run(lambda: client.meta_ads.advertiser(**dump(input)))

        @toolkit.tool()
        def scavio_meta_ads_ad(input: MetaAdsAdInput, ctx: Any = None) -> dict:
            """One Meta ad in full by archive id: creative, advertiser, run dates, the platforms it ran on, and the political disclosure when the ad carries one. Commercial ads leave spend, reach and impressions null. Costs 1 credit."""
            return _run(lambda: client.meta_ads.ad(**dump(input)))

    if all or enable_extract:

        @toolkit.tool()
        def scavio_extract(input: ExtractInput, ctx: Any = None) -> dict:
            """Read any URL and get the page back as raw HTML, readability Markdown or plain text: { url, format, mode, content, content_length }. Tier-priced by mode: 'normal' and 'advanced' cost 1 credit, 'ultra' costs 2. Only a successful extraction is billed - a dead link, bot wall or timeout costs nothing."""
            return _run(lambda: client.extract(**dump(input)))

    return toolkit
