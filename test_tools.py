"""Tests for composio-scavio. The Scavio SDK client is mocked, so no key or network is used."""

import re
import typing

import composio_scavio.tools as tools_mod
from composio_scavio import build_scavio_toolkit


class _Recorder:
    """Stands in for a Scavio SDK namespace; records calls and returns a canned dict."""

    def __init__(self, namespace, calls):
        self._namespace = namespace
        self._calls = calls

    def __getattr__(self, method):
        def _call(**kwargs):
            self._calls.append((self._namespace, method, kwargs))
            return {"ok": True, "namespace": self._namespace, "method": method, "kwargs": kwargs}

        return _call


# The 31 SDK namespaces, plus the pseudo-provider "extract" for the top-level
# client.extract() method, which is a CORE endpoint and never a namespace.
_NAMESPACES = (
    "google", "amazon", "walmart", "youtube", "reddit", "tiktok",
    "tiktok_shop", "instagram", "x", "linkedin", "threads", "kuaishou",
    "ebay", "target", "home_depot", "zillow", "booking", "tripadvisor",
    "indeed", "airbnb", "glassdoor", "yelp", "app_store", "google_play",
    "sec", "redfin", "companies_house", "g2", "capterra", "google_ads",
    "meta_ads",
)
_PROVIDERS = _NAMESPACES + ("extract",)

# Tool count per provider, and therefore the coverage contract of this package.
# Total = 189 = every live Scavio endpoint (195 in the SDK, minus the deprecated
# /youtube/metadata alias, which is not exposed, minus the 5 retired LinkedIn
# endpoints, which are never registered).
EXPECTED_COUNTS = {
    "google": 14,
    "amazon": 4,
    "walmart": 7,
    "youtube": 15,
    "reddit": 12,
    "tiktok": 11,
    "tiktok_shop": 8,
    "instagram": 12,
    "x": 11,
    "linkedin": 9,
    "threads": 6,
    "kuaishou": 14,
    "ebay": 3,
    "target": 4,
    "home_depot": 3,
    "zillow": 3,
    "booking": 3,
    "tripadvisor": 4,
    "indeed": 4,
    "airbnb": 3,
    "glassdoor": 4,
    "yelp": 3,
    "app_store": 3,
    "google_play": 3,
    "sec": 6,
    "redfin": 3,
    "companies_house": 4,
    "g2": 3,
    "capterra": 3,
    "google_ads": 3,
    "meta_ads": 3,
    "extract": 1,
}

# The verticals added in 0.4.0 are opt-in: registering all 189 tools at once
# buries the handful an agent actually wants.
OPT_IN = (
    "threads", "kuaishou", "ebay", "target", "home_depot", "zillow", "booking",
    "tripadvisor", "indeed", "airbnb", "glassdoor", "yelp", "app_store",
    "google_play", "sec", "redfin", "companies_house", "g2", "capterra",
    "google_ads", "meta_ads",
)
DEFAULT_ON = tuple(p for p in _PROVIDERS if p not in OPT_IN)


class _FakeClient:
    def __init__(self, *args, **kwargs):
        self.calls = []
        for ns in _NAMESPACES:
            setattr(self, ns, _Recorder(ns, self.calls))

    def extract(self, **kwargs):
        """extract is a top-level method on the client, not a namespace."""
        self.calls.append((None, "extract", kwargs))
        return {"ok": True, "namespace": None, "method": "extract", "kwargs": kwargs}


def _build(monkeypatch, **kwargs):
    monkeypatch.setattr(tools_mod, "ScavioClient", _FakeClient)
    return build_scavio_toolkit(api_key="test", **kwargs)


def _only(monkeypatch, provider):
    """Build a toolkit with exactly one provider enabled."""
    flags = {f"enable_{p}": (p == provider) for p in _PROVIDERS}
    return _build(monkeypatch, **flags)


def _sample(annotation):
    """A schema-valid value for a pydantic field, whatever its annotation."""
    origin = typing.get_origin(annotation)
    if origin is typing.Union:
        args = [a for a in typing.get_args(annotation) if a is not type(None)]
        return _sample(args[0])
    if origin is list:
        return [_sample(typing.get_args(annotation)[0])]
    if annotation is list:  # bare `list`, as on YouTubeSearchInput.features
        return ["x"]
    if annotation is bool:
        return True
    if annotation is int:
        return 1
    if annotation is float:
        return 1.0
    return "x"


def test_all_tools_register(monkeypatch):
    toolkit = _build(monkeypatch, all=True)
    slugs = [t.slug for t in toolkit.tools]
    assert len(slugs) == 189, len(slugs)
    assert len(set(slugs)) == len(slugs), "slugs must be unique"
    assert all(s.startswith("SCAVIO_") for s in slugs)


def test_per_provider_coverage(monkeypatch):
    """Every provider registers exactly the number of tools it has live endpoints."""
    actual = {p: len(_only(monkeypatch, p).tools) for p in _PROVIDERS}
    assert actual == EXPECTED_COUNTS
    assert sum(actual.values()) == 189


def test_the_new_verticals_are_opt_in(monkeypatch):
    """A caller who upgrades and changes nothing must not have 85 tools appear."""
    slugs = {t.slug for t in _build(monkeypatch).tools}
    assert len(slugs) == sum(EXPECTED_COUNTS[p] for p in DEFAULT_ON) == 104
    assert "SCAVIO_EXTRACT" in slugs, "extract is one tool and leads the agent surface"
    assert "SCAVIO_WALMART_SELLER" in slugs, "walmart was already on; its new endpoints ride along"
    for absent in ("SCAVIO_ZILLOW_SEARCH", "SCAVIO_G2_PRODUCT", "SCAVIO_SEC_LOOKUP"):
        assert absent not in slugs


def test_every_tool_calls_a_real_sdk_method(monkeypatch):
    """No tool may target an SDK method that does not exist on the installed scavio."""
    import inspect

    from scavio import ScavioClient

    real = ScavioClient(api_key="test")
    toolkit = _build(monkeypatch, all=True)

    for tool in toolkit.tools:
        values = {
            name: _sample(field.annotation)
            for name, field in tool.input_params.model_fields.items()
        }
        out = tool.execute(tool.input_params(**values), None)
        assert out["ok"] is True, tool.slug

        namespace = out["namespace"]
        owner = real if namespace is None else getattr(real, namespace)
        method = getattr(owner, out["method"], None)
        target = "scavio.extract" if namespace is None else f"scavio.{namespace}.{out['method']}"
        assert method is not None, f"{tool.slug} calls missing {target}"
        accepted = {
            p.name
            for p in inspect.signature(method).parameters.values()
            if p.kind in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY)
        }
        unknown = set(out["kwargs"]) - accepted
        assert not unknown, f"{tool.slug} sends params the SDK rejects: {sorted(unknown)}"


def test_extract_is_a_top_level_method_not_a_namespace(monkeypatch):
    """scavio.extract(url=...), never scavio.extract.extract()."""
    toolkit = _only(monkeypatch, "extract")
    tool = next(t for t in toolkit.tools if t.slug == "SCAVIO_EXTRACT")
    assert set(tool.input_params.model_fields) == {"url", "format", "mode"}
    out = tool.execute(
        tool.input_params(url="https://example.com/pricing", format="markdown", mode="ultra"),
        None,
    )
    assert out["namespace"] is None, "extract must be called on the client, not a namespace"
    assert out["method"] == "extract"
    assert out["kwargs"] == {
        "url": "https://example.com/pricing",
        "format": "markdown",
        "mode": "ultra",
    }


def test_provider_gating(monkeypatch):
    slugs = {t.slug for t in _only(monkeypatch, "reddit").tools}
    assert "SCAVIO_REDDIT_SEARCH" in slugs
    assert len(slugs) == 12
    assert not any(s.startswith("SCAVIO_GOOGLE") for s in slugs)


def test_all_overrides_flags(monkeypatch):
    toolkit = _build(monkeypatch, all=True, enable_reddit=False, enable_tiktok=False)
    slugs = {t.slug for t in toolkit.tools}
    assert "SCAVIO_REDDIT_SEARCH" in slugs
    assert "SCAVIO_TIKTOK_PROFILE" in slugs


def test_google_search_uses_native_v2_params(monkeypatch):
    """v1 retired 2026-08-04. gl/hl/start are passed straight through, never remapped."""
    toolkit = _only(monkeypatch, "google")
    tool = next(t for t in toolkit.tools if t.slug == "SCAVIO_GOOGLE_SEARCH")
    fields = set(tool.input_params.model_fields)
    assert {"gl", "hl", "start", "google_domain", "device"} <= fields
    assert not fields & {"country_code", "language", "page"}, "v1 param names must not exist"
    out = tool.execute(
        tool.input_params(query="ai agents", gl="us", hl="en", start=10, device="mobile", nfpr=True),
        None,
    )
    assert out["method"] == "search"
    assert out["kwargs"] == {
        "query": "ai agents",
        "gl": "us",
        "hl": "en",
        "start": 10,
        "device": "mobile",
        "nfpr": True,
    }


def test_google_start_is_an_offset_not_a_page(monkeypatch):
    """start=0 is the first page and must survive; it is not treated as page 1."""
    toolkit = _only(monkeypatch, "google")
    tool = next(t for t in toolkit.tools if t.slug == "SCAVIO_GOOGLE_SEARCH")
    assert tool.execute(tool.input_params(query="q", start=0), None)["kwargs"] == {"query": "q", "start": 0}
    assert tool.execute(tool.input_params(query="q", start=20), None)["kwargs"] == {"query": "q", "start": 20}


def test_google_v2_verticals_register(monkeypatch):
    slugs = {t.slug for t in _only(monkeypatch, "google").tools}
    assert slugs == {
        "SCAVIO_GOOGLE_SEARCH", "SCAVIO_GOOGLE_AI_MODE", "SCAVIO_GOOGLE_MAPS_SEARCH",
        "SCAVIO_GOOGLE_MAPS_PLACE", "SCAVIO_GOOGLE_MAPS_REVIEWS", "SCAVIO_GOOGLE_SHOPPING",
        "SCAVIO_GOOGLE_SHOPPING_PRODUCT", "SCAVIO_GOOGLE_SHOPPING_STORES", "SCAVIO_GOOGLE_FLIGHTS",
        "SCAVIO_GOOGLE_HOTELS", "SCAVIO_GOOGLE_HOTELS_DETAIL", "SCAVIO_GOOGLE_NEWS",
        "SCAVIO_GOOGLE_TRENDS", "SCAVIO_GOOGLE_TRENDING",
    }


def test_google_ads_and_google_play_do_not_collide_with_google(monkeypatch):
    """Three separate namespaces share the `google` prefix; none may swallow another."""
    google = {t.slug for t in _only(monkeypatch, "google").tools}
    ads = {t.slug for t in _only(monkeypatch, "google_ads").tools}
    play = {t.slug for t in _only(monkeypatch, "google_play").tools}
    assert ads == {"SCAVIO_GOOGLE_ADS_ADVERTISERS", "SCAVIO_GOOGLE_ADS_SEARCH", "SCAVIO_GOOGLE_ADS_CREATIVE"}
    assert play == {"SCAVIO_GOOGLE_PLAY_SEARCH", "SCAVIO_GOOGLE_PLAY_APP", "SCAVIO_GOOGLE_PLAY_REVIEWS"}
    assert not (google & ads) and not (google & play) and not (ads & play)


def test_amazon_product_uses_asin(monkeypatch):
    toolkit = _only(monkeypatch, "amazon")
    tool = next(t for t in toolkit.tools if t.slug == "SCAVIO_AMAZON_PRODUCT")
    out = tool.execute(tool.input_params(asin="B000000000"), None)
    assert out["method"] == "product"
    assert out["kwargs"] == {"asin": "B000000000"}


def test_youtube_tools_register(monkeypatch):
    slugs = {t.slug for t in _only(monkeypatch, "youtube").tools}
    assert slugs == {
        "SCAVIO_YOUTUBE_SEARCH", "SCAVIO_YOUTUBE_SHORTS", "SCAVIO_YOUTUBE_SUGGESTIONS",
        "SCAVIO_YOUTUBE_VIDEO", "SCAVIO_YOUTUBE_COMMENTS",
        "SCAVIO_YOUTUBE_COMMENT_REPLIES", "SCAVIO_YOUTUBE_TRANSCRIPT", "SCAVIO_YOUTUBE_RELATED",
        "SCAVIO_YOUTUBE_CHANNEL_SEARCH", "SCAVIO_YOUTUBE_CHANNEL", "SCAVIO_YOUTUBE_CHANNEL_VIDEOS",
        "SCAVIO_YOUTUBE_CHANNEL_SHORTS", "SCAVIO_YOUTUBE_CHANNEL_COMMUNITY",
        "SCAVIO_YOUTUBE_CHANNEL_RESOLVE", "SCAVIO_YOUTUBE_STREAMS",
    }


def test_youtube_metadata_alias_is_not_exposed(monkeypatch):
    """/youtube/metadata is a deprecated alias of /youtube/video; only /video is offered."""
    slugs = {t.slug for t in _build(monkeypatch, all=True).tools}
    assert "SCAVIO_YOUTUBE_METADATA" not in slugs
    assert "SCAVIO_YOUTUBE_VIDEO" in slugs


def test_youtube_comment_replies_passes_reply_cursor(monkeypatch):
    toolkit = _only(monkeypatch, "youtube")
    tool = next(t for t in toolkit.tools if t.slug == "SCAVIO_YOUTUBE_COMMENT_REPLIES")
    out = tool.execute(tool.input_params(video_id="vid", reply_cursor="rc"), None)
    assert out["method"] == "comment_replies"
    assert out["kwargs"] == {"video_id": "vid", "reply_cursor": "rc"}


def test_reddit_search_takes_only_query_and_cursor(monkeypatch):
    toolkit = _only(monkeypatch, "reddit")
    tool = next(t for t in toolkit.tools if t.slug == "SCAVIO_REDDIT_SEARCH")
    assert set(tool.input_params.model_fields) == {"query", "cursor"}
    out = tool.execute(tool.input_params(query="serpapi alternative", cursor="c1"), None)
    assert out["method"] == "search"
    assert out["kwargs"] == {"query": "serpapi alternative", "cursor": "c1"}


def test_reddit_post_takes_url_or_post_id(monkeypatch):
    toolkit = _only(monkeypatch, "reddit")
    tool = next(t for t in toolkit.tools if t.slug == "SCAVIO_REDDIT_POST")
    assert set(tool.input_params.model_fields) == {"url", "post_id"}
    out = tool.execute(tool.input_params(url="https://www.reddit.com/r/programming/comments/abc123/x/"), None)
    assert out["method"] == "post"
    assert out["kwargs"] == {"url": "https://www.reddit.com/r/programming/comments/abc123/x/"}


def test_reddit_feeds_register(monkeypatch):
    slugs = {t.slug for t in _only(monkeypatch, "reddit").tools}
    assert {
        "SCAVIO_REDDIT_SEARCH_SUGGESTIONS", "SCAVIO_REDDIT_POST_COMMENTS",
        "SCAVIO_REDDIT_COMMENT_REPLIES", "SCAVIO_REDDIT_SUBREDDIT",
        "SCAVIO_REDDIT_SUBREDDIT_POSTS", "SCAVIO_REDDIT_USER", "SCAVIO_REDDIT_USER_POSTS",
        "SCAVIO_REDDIT_USER_COMMENTS", "SCAVIO_REDDIT_POPULAR", "SCAVIO_REDDIT_TRENDING",
    } <= slugs


def test_x_tools_register_and_use_search_wire_name(monkeypatch):
    toolkit = _only(monkeypatch, "x")
    slugs = {t.slug for t in toolkit.tools}
    assert slugs == {
        "SCAVIO_X_SEARCH", "SCAVIO_X_TWEET", "SCAVIO_X_TWEET_COMMENTS",
        "SCAVIO_X_TWEET_RETWEETERS", "SCAVIO_X_USER", "SCAVIO_X_USER_TWEETS",
        "SCAVIO_X_USER_REPLIES", "SCAVIO_X_USER_MEDIA", "SCAVIO_X_USER_FOLLOWERS",
        "SCAVIO_X_USER_FOLLOWINGS", "SCAVIO_X_TRENDING",
    }
    tool = next(t for t in toolkit.tools if t.slug == "SCAVIO_X_SEARCH")
    assert "search" in tool.input_params.model_fields
    assert "query" not in tool.input_params.model_fields
    out = tool.execute(tool.input_params(search="scavio", search_type="Latest"), None)
    assert out["kwargs"] == {"search": "scavio", "search_type": "Latest"}


def test_linkedin_exposes_only_the_nine_live_endpoints(monkeypatch):
    slugs = {t.slug for t in _only(monkeypatch, "linkedin").tools}
    assert slugs == {
        "SCAVIO_LINKEDIN_PERSON", "SCAVIO_LINKEDIN_PERSON_ABOUT", "SCAVIO_LINKEDIN_PERSON_POSTS",
        "SCAVIO_LINKEDIN_COMPANY", "SCAVIO_LINKEDIN_COMPANY_POSTS", "SCAVIO_LINKEDIN_SEARCH_JOBS",
        "SCAVIO_LINKEDIN_JOB", "SCAVIO_LINKEDIN_POST", "SCAVIO_LINKEDIN_POST_COMMENTS",
    }
    # The 5 retired endpoints return 410 unbilled and must never be callable by an agent.
    for retired in (
        "SCAVIO_LINKEDIN_PERSON_CONTACT", "SCAVIO_LINKEDIN_COMPANY_PEOPLE",
        "SCAVIO_LINKEDIN_COMPANY_JOBS", "SCAVIO_LINKEDIN_SEARCH_PEOPLE",
        "SCAVIO_LINKEDIN_SEARCH_POSTS",
    ):
        assert retired not in slugs


def test_linkedin_search_jobs_uses_search_and_post_comments_uses_page(monkeypatch):
    toolkit = _only(monkeypatch, "linkedin")
    jobs = next(t for t in toolkit.tools if t.slug == "SCAVIO_LINKEDIN_SEARCH_JOBS")
    assert set(jobs.input_params.model_fields) == {"search", "location", "cursor"}
    comments = next(t for t in toolkit.tools if t.slug == "SCAVIO_LINKEDIN_POST_COMMENTS")
    assert "page" in comments.input_params.model_fields
    assert "cursor" not in comments.input_params.model_fields


def test_tiktok_shop_tools_register(monkeypatch):
    toolkit = _only(monkeypatch, "tiktok_shop")
    slugs = {t.slug for t in toolkit.tools}
    assert slugs == {
        "SCAVIO_TIKTOK_SHOP_SEARCH", "SCAVIO_TIKTOK_SHOP_SEARCH_SUGGESTIONS",
        "SCAVIO_TIKTOK_SHOP_PRODUCT", "SCAVIO_TIKTOK_SHOP_PRODUCT_REVIEWS",
        "SCAVIO_TIKTOK_SHOP_CATEGORIES", "SCAVIO_TIKTOK_SHOP_CATEGORY_PRODUCTS",
        "SCAVIO_TIKTOK_SHOP_SHOP_PRODUCTS", "SCAVIO_TIKTOK_SHOP_RESOLVE",
    }
    search = next(t for t in toolkit.tools if t.slug == "SCAVIO_TIKTOK_SHOP_SEARCH")
    # `search`, not `query`, and no region param exists on this endpoint.
    assert set(search.input_params.model_fields) == {"search", "cursor"}


def test_walmart_covers_all_seven_endpoints_on_the_live_surface(monkeypatch):
    """The scrape.do rebuild dropped device/delivery_zip/store_id and renamed start_page."""
    toolkit = _only(monkeypatch, "walmart")
    slugs = {t.slug for t in toolkit.tools}
    assert slugs == {
        "SCAVIO_WALMART_SEARCH", "SCAVIO_WALMART_PRODUCT", "SCAVIO_WALMART_REVIEWS",
        "SCAVIO_WALMART_CATEGORY", "SCAVIO_WALMART_OFFERS", "SCAVIO_WALMART_SELLER",
        "SCAVIO_WALMART_SELLER_PRODUCTS",
    }
    search = next(t for t in toolkit.tools if t.slug == "SCAVIO_WALMART_SEARCH")
    fields = set(search.input_params.model_fields)
    assert "page" in fields
    assert not fields & {"device", "delivery_zip", "store_id"}, "params retired with the rebuild"
    product = next(t for t in toolkit.tools if t.slug == "SCAVIO_WALMART_PRODUCT")
    # US only: walmart.ca product pages cannot be fetched, so there is no domain here.
    assert set(product.input_params.model_fields) == {"product_id"}


def test_kuaishou_videos_batch_takes_a_list(monkeypatch):
    toolkit = _only(monkeypatch, "kuaishou")
    tool = next(t for t in toolkit.tools if t.slug == "SCAVIO_KUAISHOU_VIDEOS_BATCH")
    out = tool.execute(tool.input_params(photo_ids=["a", "b"]), None)
    assert out["method"] == "videos_batch"
    assert out["kwargs"] == {"photo_ids": ["a", "b"]}


def test_meta_ads_paths_are_hyphenated(monkeypatch):
    """Meta Ad Library serves /api/v1/meta-ads/*; the path is never derived from the key."""
    from scavio import _spec

    paths = {e.method: e.path for e in _spec._ENDPOINTS if e.namespace == "meta_ads"}
    assert paths == {
        "search": "/api/v1/meta-ads/search",
        "advertiser": "/api/v1/meta-ads/advertiser",
        "ad": "/api/v1/meta-ads/ad",
    }
    slugs = {t.slug for t in _only(monkeypatch, "meta_ads").tools}
    assert slugs == {"SCAVIO_META_ADS_SEARCH", "SCAVIO_META_ADS_ADVERTISER", "SCAVIO_META_ADS_AD"}


def test_lookup_first_endpoints_are_registered(monkeypatch):
    """Four platforms are keyed by an id you have to resolve first; expose the resolver."""
    toolkit = _build(monkeypatch, all=True)
    slugs = {t.slug for t in toolkit.tools}
    for resolver in (
        "SCAVIO_SEC_LOOKUP", "SCAVIO_GLASSDOOR_COMPANIES", "SCAVIO_TRIPADVISOR_LOCATIONS",
        "SCAVIO_GOOGLE_ADS_ADVERTISERS", "SCAVIO_COMPANIES_HOUSE_SEARCH",
        "SCAVIO_KUAISHOU_USER_RESOLVE",
    ):
        assert resolver in slugs


def test_parameterless_tools_execute(monkeypatch):
    toolkit = _build(monkeypatch, all=True)
    for slug, method in (("SCAVIO_TIKTOK_SHOP_CATEGORIES", "categories"),
                         ("SCAVIO_REDDIT_TRENDING", "trending"),
                         ("SCAVIO_AMAZON_OPTIONS", "options")):
        tool = next(t for t in toolkit.tools if t.slug == slug)
        assert set(tool.input_params.model_fields) == set()
        out = tool.execute(tool.input_params(), None)
        assert out["method"] == method
        assert out["kwargs"] == {}


def test_every_tool_description_states_a_credit_cost(monkeypatch):
    toolkit = _build(monkeypatch, all=True)
    missing = [t.slug for t in toolkit.tools if "credit" not in (t.description or "").lower()]
    assert not missing, missing


# Flat-priced platforms: one constant for every endpoint on the platform, taken
# from the frozen per-platform cost in gtm/fanout-naming.json.
FLAT_PLATFORM_CREDITS = {
    "ebay": 1, "target": 1, "home_depot": 2, "zillow": 1, "booking": 1,
    "tripadvisor": 2, "indeed": 2, "airbnb": 1, "glassdoor": 1, "yelp": 2,
    "app_store": 1, "google_play": 2, "sec": 1, "redfin": 1,
    "companies_house": 1, "g2": 5, "capterra": 2, "google_ads": 1, "meta_ads": 1,
}


def test_flat_priced_platforms_state_their_constant(monkeypatch):
    for provider, credits in FLAT_PLATFORM_CREDITS.items():
        for tool in _only(monkeypatch, provider).tools:
            found = re.findall(r"costs? (\d+) credits?", tool.description or "", re.I)
            assert found, f"{tool.slug} states no credit cost"
            assert int(found[0]) == credits, (tool.slug, found, credits)


# The four BODY-PRICED surfaces. Their cost is a function of the request body,
# so a flat "Costs N credits." on any of them would be a lie; each description
# has to carry the thing the price actually varies with.
BODY_PRICED_PHRASES = {
    "SCAVIO_WALMART_SEARCH": ["1 credit on domain", "2 credits on 'com.mx'"],
    "SCAVIO_WALMART_CATEGORY": ["1 credit on domain", "2 credits on 'com.mx'"],
    "SCAVIO_WALMART_PRODUCT": ["body-priced through `domain`"],
    "SCAVIO_WALMART_REVIEWS": ["body-priced through `domain`"],
    "SCAVIO_WALMART_OFFERS": ["body-priced through `domain`"],
    "SCAVIO_WALMART_SELLER": ["body-priced through `domain`"],
    "SCAVIO_WALMART_SELLER_PRODUCTS": ["body-priced through `domain`"],
    "SCAVIO_THREADS_PROFILE": ["2 credits addressed by user_id", "4 credits addressed by username"],
    "SCAVIO_THREADS_USER_POSTS": ["2 credits addressed by user_id", "4 credits addressed by username"],
    "SCAVIO_THREADS_USER_REPLIES": ["2 credits addressed by user_id", "4 credits addressed by username"],
    "SCAVIO_THREADS_POST": ["body-priced by identifier"],
    "SCAVIO_THREADS_POST_COMMENTS": ["body-priced by identifier"],
    "SCAVIO_THREADS_SEARCH_USERS": ["body-priced by identifier"],
    "SCAVIO_EXTRACT": ["Tier-priced by mode", "'ultra' costs 2", "Only a successful extraction is billed"],
}


def test_body_priced_surfaces_never_show_a_flat_cost(monkeypatch):
    by_slug = {t.slug: t.description or "" for t in _build(monkeypatch, all=True).tools}
    for slug, phrases in BODY_PRICED_PHRASES.items():
        for phrase in phrases:
            assert phrase in by_slug[slug], (slug, phrase, by_slug[slug])
    # Kuaishou is priced per endpoint, never per platform: every one says so.
    for tool in _only(monkeypatch, "kuaishou").tools:
        assert "priced PER ENDPOINT (1, 2, 10 or 40)" in (tool.description or ""), tool.slug


def test_known_credit_costs_are_stated(monkeypatch):
    toolkit = _build(monkeypatch, all=True)
    by_slug = {t.slug: t.description for t in toolkit.tools}
    expected = {
        "SCAVIO_GOOGLE_SEARCH": "1 credit",
        "SCAVIO_GOOGLE_FLIGHTS": "1 credit",
        "SCAVIO_YOUTUBE_SEARCH": "2 credits",
        "SCAVIO_YOUTUBE_SHORTS": "2 credits",
        "SCAVIO_YOUTUBE_STREAMS": "3 credits",
        "SCAVIO_YOUTUBE_TRANSCRIPT": "8 credits",
        "SCAVIO_INSTAGRAM_PROFILE": "10 credits",
        "SCAVIO_INSTAGRAM_POST": "8 credits",
        "SCAVIO_INSTAGRAM_COMMENT_REPLIES": "8 credits",
        "SCAVIO_INSTAGRAM_USER_POSTS": "2 credits",
        "SCAVIO_LINKEDIN_PERSON": "1 credit",
        "SCAVIO_LINKEDIN_PERSON_POSTS": "10 credits",
        "SCAVIO_LINKEDIN_JOB": "30 credits",
        "SCAVIO_X_SEARCH": "1 credit",
        "SCAVIO_TIKTOK_SHOP_SEARCH": "1 credit",
        "SCAVIO_REDDIT_SEARCH": "1 credit",
        "SCAVIO_G2_REVIEWS": "5 credits",
        "SCAVIO_KUAISHOU_VIDEOS_BATCH": "40 credits",
        "SCAVIO_KUAISHOU_PROFILE": "10 credits",
        "SCAVIO_AMAZON_OPTIONS": "costs no credits",
    }
    for slug, cost in expected.items():
        assert cost in by_slug[slug], (slug, by_slug[slug])


def test_error_is_returned_as_dict(monkeypatch):
    def boom(**kwargs):
        raise RuntimeError("network down")

    class FailingClient(_FakeClient):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.google.search = boom  # type: ignore[attr-defined]

    monkeypatch.setattr(tools_mod, "ScavioClient", FailingClient)
    flags = {f"enable_{p}": (p == "google") for p in _PROVIDERS}
    toolkit = build_scavio_toolkit(api_key="test", **flags)
    tool = next(t for t in toolkit.tools if t.slug == "SCAVIO_GOOGLE_SEARCH")
    out = tool.execute(tool.input_params(query="x"), None)
    assert out == {"error": "network down"}
