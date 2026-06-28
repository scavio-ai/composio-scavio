"""Scavio tools for Composio.

Exposes the Scavio search API (Google, YouTube, Amazon, Walmart, Reddit, TikTok,
Instagram) as a Composio custom toolkit. Build the toolkit with
``build_scavio_toolkit()`` and bind it to a session::

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
    search_type: Optional[str] = Field(None, description="Search vertical, e.g. 'search', 'news', 'images'.")
    device: Optional[str] = Field(None, description="Device profile: 'desktop' or 'mobile'.")
    nfpr: Optional[bool] = Field(None, description="Disable auto-correction of the query when true.")
    light_request: Optional[bool] = Field(None, description="Cheaper, lighter response (1 credit instead of 2) when true.")


# Amazon
class AmazonSearchInput(BaseModel):
    query: str = Field(description="The product search query.")
    domain: Optional[str] = Field(None, description="Amazon domain, e.g. 'amazon.com'.")
    country: Optional[str] = Field(None, description="Two-letter country code.")
    language: Optional[str] = Field(None, description="Two-letter language code.")
    currency: Optional[str] = Field(None, description="Currency code, e.g. 'USD'.")
    device: Optional[str] = Field(None, description="Device profile: 'desktop' or 'mobile'.")
    sort_by: Optional[str] = Field(None, description="Sort order for results.")
    start_page: Optional[int] = Field(None, description="First page to return.")
    pages: Optional[int] = Field(None, description="Number of pages to return.")
    category_id: Optional[str] = Field(None, description="Restrict to an Amazon category id.")
    merchant_id: Optional[str] = Field(None, description="Restrict to a merchant id.")
    zip_code: Optional[str] = Field(None, description="Delivery ZIP/postal code.")
    autoselect_variant: Optional[bool] = Field(None, description="Auto-select the best product variant when true.")


class AmazonProductInput(BaseModel):
    asin: str = Field(description="Amazon Standard Identification Number (ASIN) of the product.")
    domain: Optional[str] = Field(None, description="Amazon domain, e.g. 'amazon.com'.")
    country: Optional[str] = Field(None, description="Two-letter country code.")
    language: Optional[str] = Field(None, description="Two-letter language code.")
    currency: Optional[str] = Field(None, description="Currency code, e.g. 'USD'.")
    device: Optional[str] = Field(None, description="Device profile: 'desktop' or 'mobile'.")
    zip_code: Optional[str] = Field(None, description="Delivery ZIP/postal code.")
    autoselect_variant: Optional[bool] = Field(None, description="Auto-select the best product variant when true.")


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
    upload_date: Optional[str] = Field(None, description="Upload date filter, e.g. 'today', 'week', 'month'.")
    type: Optional[str] = Field(None, description="Result type, e.g. 'video', 'channel', 'playlist'.")
    duration: Optional[str] = Field(None, description="Duration filter, e.g. 'short', 'long'.")
    sort_by: Optional[str] = Field(None, description="Sort order for results.")
    hd: Optional[bool] = Field(None, description="Restrict to HD videos when true.")
    subtitles: Optional[bool] = Field(None, description="Restrict to videos with subtitles when true.")
    creative_commons: Optional[bool] = Field(None, description="Restrict to Creative Commons videos when true.")
    live: Optional[bool] = Field(None, description="Restrict to live videos when true.")


class YouTubeMetadataInput(BaseModel):
    video_id: str = Field(description="YouTube video id.")


# Reddit
class RedditSearchInput(BaseModel):
    query: str = Field(description="The Reddit search query.")
    type: Optional[str] = Field(None, description="Search type, e.g. 'posts', 'subreddits', 'users'.")
    sort: Optional[str] = Field(None, description="Sort order, e.g. 'relevance', 'new', 'top'.")
    cursor: Optional[str] = Field(None, description="Pagination cursor.")


class RedditPostInput(BaseModel):
    url: str = Field(description="Full URL of the Reddit post to fetch with its comments.")


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
    TikTok, and Instagram. Each provider is gated by an ``enable_*`` flag so you
    expose only the tools your agent needs.

    Args:
        api_key: Scavio API key. Falls back to the ``SCAVIO_API_KEY`` env var.
        enable_google: Register the Google web search tool. Defaults to True.
        enable_amazon: Register the Amazon search and product tools. Defaults to True.
        enable_walmart: Register the Walmart search and product tools. Defaults to True.
        enable_youtube: Register the YouTube search and metadata tools. Defaults to True.
        enable_reddit: Register the Reddit search and post tools. Defaults to True.
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
            "Reddit, TikTok, and Instagram."
        ),
    )

    def dump(model: BaseModel) -> Dict[str, Any]:
        return model.model_dump(exclude_none=True)

    if all or enable_google:

        @toolkit.tool()
        def scavio_google_search(input: GoogleSearchInput, ctx: Any = None) -> dict:
            """Search Google for real-time web results (organic, knowledge graph, news, and more)."""
            return _run(lambda: client.google.search(**dump(input)))

    if all or enable_amazon:

        @toolkit.tool()
        def scavio_amazon_search(input: AmazonSearchInput, ctx: Any = None) -> dict:
            """Search Amazon for products matching a query."""
            return _run(lambda: client.amazon.search(**dump(input)))

        @toolkit.tool()
        def scavio_amazon_product(input: AmazonProductInput, ctx: Any = None) -> dict:
            """Fetch full Amazon product details by ASIN."""
            return _run(lambda: client.amazon.product(**dump(input)))

    if all or enable_walmart:

        @toolkit.tool()
        def scavio_walmart_search(input: WalmartSearchInput, ctx: Any = None) -> dict:
            """Search Walmart for products matching a query."""
            return _run(lambda: client.walmart.search(**dump(input)))

        @toolkit.tool()
        def scavio_walmart_product(input: WalmartProductInput, ctx: Any = None) -> dict:
            """Fetch full Walmart product details by product id."""
            return _run(lambda: client.walmart.product(**dump(input)))

    if all or enable_youtube:

        @toolkit.tool()
        def scavio_youtube_search(input: YouTubeSearchInput, ctx: Any = None) -> dict:
            """Search YouTube for videos, channels, or playlists."""
            return _run(lambda: client.youtube.search(**dump(input)))

        @toolkit.tool()
        def scavio_youtube_metadata(input: YouTubeMetadataInput, ctx: Any = None) -> dict:
            """Fetch metadata for a YouTube video by id."""
            return _run(lambda: client.youtube.metadata(**dump(input)))

    if all or enable_reddit:

        @toolkit.tool()
        def scavio_reddit_search(input: RedditSearchInput, ctx: Any = None) -> dict:
            """Search Reddit posts, subreddits, or users."""
            return _run(lambda: client.reddit.search(**dump(input)))

        @toolkit.tool()
        def scavio_reddit_post(input: RedditPostInput, ctx: Any = None) -> dict:
            """Fetch a Reddit post and its comment thread by URL."""
            return _run(lambda: client.reddit.post(**dump(input)))

    if all or enable_tiktok:

        @toolkit.tool()
        def scavio_tiktok_profile(input: TikTokProfileInput, ctx: Any = None) -> dict:
            """Fetch a TikTok user profile by username or secUid."""
            return _run(lambda: client.tiktok.profile(**dump(input)))

        @toolkit.tool()
        def scavio_tiktok_user_posts(input: TikTokUserPostsInput, ctx: Any = None) -> dict:
            """List a TikTok user's posts by secUid."""
            return _run(lambda: client.tiktok.user_posts(**dump(input)))

        @toolkit.tool()
        def scavio_tiktok_video(input: TikTokVideoInput, ctx: Any = None) -> dict:
            """Fetch a TikTok video by id."""
            return _run(lambda: client.tiktok.video(**dump(input)))

        @toolkit.tool()
        def scavio_tiktok_video_comments(input: TikTokVideoCommentsInput, ctx: Any = None) -> dict:
            """List comments on a TikTok video."""
            return _run(lambda: client.tiktok.video_comments(**dump(input)))

        @toolkit.tool()
        def scavio_tiktok_comment_replies(input: TikTokCommentRepliesInput, ctx: Any = None) -> dict:
            """List replies to a TikTok video comment."""
            return _run(lambda: client.tiktok.comment_replies(**dump(input)))

        @toolkit.tool()
        def scavio_tiktok_search_videos(input: TikTokSearchVideosInput, ctx: Any = None) -> dict:
            """Search TikTok videos by keyword."""
            return _run(lambda: client.tiktok.search_videos(**dump(input)))

        @toolkit.tool()
        def scavio_tiktok_search_users(input: TikTokSearchUsersInput, ctx: Any = None) -> dict:
            """Search TikTok users by keyword."""
            return _run(lambda: client.tiktok.search_users(**dump(input)))

        @toolkit.tool()
        def scavio_tiktok_hashtag(input: TikTokHashtagInput, ctx: Any = None) -> dict:
            """Fetch a TikTok hashtag by name or id."""
            return _run(lambda: client.tiktok.hashtag(**dump(input)))

        @toolkit.tool()
        def scavio_tiktok_hashtag_videos(input: TikTokHashtagVideosInput, ctx: Any = None) -> dict:
            """List videos for a TikTok hashtag by id."""
            return _run(lambda: client.tiktok.hashtag_videos(**dump(input)))

        @toolkit.tool()
        def scavio_tiktok_user_followers(input: TikTokUserFollowersInput, ctx: Any = None) -> dict:
            """List a TikTok user's followers by secUid."""
            return _run(lambda: client.tiktok.user_followers(**dump(input)))

        @toolkit.tool()
        def scavio_tiktok_user_followings(input: TikTokUserFollowingsInput, ctx: Any = None) -> dict:
            """List the accounts a TikTok user follows, by secUid."""
            return _run(lambda: client.tiktok.user_followings(**dump(input)))

    if all or enable_instagram:

        @toolkit.tool()
        def scavio_instagram_profile(input: InstagramProfileInput, ctx: Any = None) -> dict:
            """Fetch an Instagram profile by username or user id."""
            return _run(lambda: client.instagram.profile(**dump(input)))

        @toolkit.tool()
        def scavio_instagram_user_posts(input: InstagramUserPostsInput, ctx: Any = None) -> dict:
            """List an Instagram user's posts."""
            return _run(lambda: client.instagram.user_posts(**dump(input)))

        @toolkit.tool()
        def scavio_instagram_user_reels(input: InstagramUserReelsInput, ctx: Any = None) -> dict:
            """List an Instagram user's reels."""
            return _run(lambda: client.instagram.user_reels(**dump(input)))

        @toolkit.tool()
        def scavio_instagram_user_tagged(input: InstagramUserTaggedInput, ctx: Any = None) -> dict:
            """List posts an Instagram user is tagged in."""
            return _run(lambda: client.instagram.user_tagged(**dump(input)))

        @toolkit.tool()
        def scavio_instagram_user_stories(input: InstagramUserStoriesInput, ctx: Any = None) -> dict:
            """Fetch an Instagram user's current stories."""
            return _run(lambda: client.instagram.user_stories(**dump(input)))

        @toolkit.tool()
        def scavio_instagram_post(input: InstagramPostInput, ctx: Any = None) -> dict:
            """Fetch an Instagram post by URL, media id, or shortcode."""
            return _run(lambda: client.instagram.post(**dump(input)))

        @toolkit.tool()
        def scavio_instagram_post_comments(input: InstagramPostCommentsInput, ctx: Any = None) -> dict:
            """List comments on an Instagram post by shortcode or URL."""
            return _run(lambda: client.instagram.post_comments(**dump(input)))

        @toolkit.tool()
        def scavio_instagram_comment_replies(input: InstagramCommentRepliesInput, ctx: Any = None) -> dict:
            """List replies to an Instagram post comment."""
            return _run(lambda: client.instagram.comment_replies(**dump(input)))

        @toolkit.tool()
        def scavio_instagram_search_users(input: InstagramSearchUsersInput, ctx: Any = None) -> dict:
            """Search Instagram users by keyword."""
            return _run(lambda: client.instagram.search_users(**dump(input)))

        @toolkit.tool()
        def scavio_instagram_search_hashtags(input: InstagramSearchHashtagsInput, ctx: Any = None) -> dict:
            """Search Instagram hashtags by keyword."""
            return _run(lambda: client.instagram.search_hashtags(**dump(input)))

        @toolkit.tool()
        def scavio_instagram_user_followers(input: InstagramUserFollowersInput, ctx: Any = None) -> dict:
            """List an Instagram user's followers."""
            return _run(lambda: client.instagram.user_followers(**dump(input)))

        @toolkit.tool()
        def scavio_instagram_user_followings(input: InstagramUserFollowingsInput, ctx: Any = None) -> dict:
            """List the accounts an Instagram user follows."""
            return _run(lambda: client.instagram.user_followings(**dump(input)))

    return toolkit
