"""Scavio tools for Composio.

Scavio is a single Search API over Google, YouTube, Amazon, Walmart, Reddit,
TikTok, TikTok Shop, Instagram, X and LinkedIn. This toolkit exposes the Google,
YouTube, Amazon, Walmart, Reddit, TikTok and Instagram endpoints as a Composio
custom toolkit. Build the toolkit with ``build_scavio_toolkit()`` and bind it to
a session::

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

# Google
class GoogleSearchInput(BaseModel):
    query: str = Field(description="The search query.")
    country_code: Optional[str] = Field(None, description="Two-letter country code, e.g. 'us'.")
    language: Optional[str] = Field(None, description="Two-letter language code, e.g. 'en'.")
    page: Optional[int] = Field(None, description="Result page number (1-based).")
    device: Optional[str] = Field(None, description="Device profile: 'desktop' or 'mobile'.")
    nfpr: Optional[bool] = Field(None, description="Disable auto-correction of the query when true.")


def _google_search_params(input: GoogleSearchInput) -> Dict[str, Any]:
    """Map the public Google args to the v2 SERP wire params the SDK expects."""
    params: Dict[str, Any] = {"query": input.query}
    if input.country_code is not None:
        params["gl"] = input.country_code
    if input.language is not None:
        params["hl"] = input.language
    if input.page is not None and input.page > 1:
        params["start"] = (input.page - 1) * 10
    if input.device is not None:
        params["device"] = input.device
    if input.nfpr is not None:
        params["nfpr"] = input.nfpr
    return params


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


class YouTubeMetadataInput(BaseModel):
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


class RedditPostInput(BaseModel):
    url: str = Field(description="Full URL of the Reddit post.")


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
    enable_instagram: bool = True,
    all: bool = False,
) -> "ExperimentalToolkit":
    """Build a Composio custom toolkit exposing Scavio search tools.

    Scavio is a single Search API over Google, YouTube, Amazon, Walmart, Reddit,
    TikTok, TikTok Shop, Instagram, X and LinkedIn; this toolkit covers the first
    seven. Each provider is gated by an ``enable_*`` flag so you expose only the
    tools your agent needs.

    Args:
        api_key: Scavio API key. Falls back to the ``SCAVIO_API_KEY`` env var.
        enable_google: Register the Google web search tool. Defaults to True.
        enable_amazon: Register the Amazon search, product and offers tools. Defaults to True.
        enable_walmart: Register the Walmart search and product tools. Defaults to True.
        enable_youtube: Register the YouTube tools (search, shorts, suggestions, video,
            comments, transcript, related, channel, streams, and more). Defaults to True.
        enable_reddit: Register the Reddit search and post tools (1 credit each). Defaults to True.
        enable_tiktok: Register the TikTok tools. Defaults to True.
        enable_instagram: Register the Instagram tools. Defaults to True.
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
            "Reddit, TikTok, and Instagram (part of the Scavio API, which also "
            "covers TikTok Shop, X and LinkedIn)."
        ),
    )

    def dump(model: BaseModel) -> Dict[str, Any]:
        return model.model_dump(exclude_none=True)

    if all or enable_google:

        @toolkit.tool()
        def scavio_google_search(input: GoogleSearchInput, ctx: Any = None) -> dict:
            """Search Google for real-time web results (organic_results, ads, and the AI Overview when present). Costs 1 credit."""
            return _run(lambda: client.google.search(**_google_search_params(input)))

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
        def scavio_youtube_metadata(input: YouTubeMetadataInput, ctx: Any = None) -> dict:
            """Fetch metadata for a YouTube video by id. Deprecated alias of scavio_youtube_video."""
            return _run(lambda: client.youtube.metadata(**dump(input)))

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
        def scavio_reddit_post(input: RedditPostInput, ctx: Any = None) -> dict:
            """Fetch one Reddit post by URL. Returns a flat post object under data (post_id, title, text, url, subreddit, author, score, upvote_ratio, num_comments, created_at, is_nsfw, is_video, thumbnail, media); comments are NOT included. Costs 1 credit."""
            return _run(lambda: client.reddit.post(**dump(input)))

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

    return toolkit
