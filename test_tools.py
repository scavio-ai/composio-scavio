"""Tests for composio-scavio. The Scavio SDK client is mocked, so no key or network is used."""

import composio_scavio.tools as tools_mod
from composio_scavio import build_scavio_toolkit


class _Recorder:
    """Stands in for a Scavio SDK namespace; records calls and returns a canned dict."""

    def __init__(self, calls):
        self._calls = calls

    def __getattr__(self, method):
        def _call(**kwargs):
            self._calls.append((method, kwargs))
            return {"ok": True, "method": method, "kwargs": kwargs}

        return _call


_NAMESPACES = (
    "google", "amazon", "walmart", "youtube", "reddit", "tiktok",
    "tiktok_shop", "instagram", "x", "linkedin",
)

# Tool count per provider, and therefore the coverage contract of this package.
# Total = 97 = every live Scavio endpoint (98 minus the deprecated /youtube/metadata
# alias, which is not exposed) minus the 5 retired LinkedIn endpoints, which are
# never registered.
EXPECTED_COUNTS = {
    "google": 14,
    "amazon": 3,
    "walmart": 2,
    "youtube": 15,
    "reddit": 12,
    "tiktok": 11,
    "tiktok_shop": 8,
    "instagram": 12,
    "x": 11,
    "linkedin": 9,
}


class _FakeClient:
    def __init__(self, *args, **kwargs):
        self.calls = []
        for ns in _NAMESPACES:
            setattr(self, ns, _Recorder(self.calls))


def _build(monkeypatch, **kwargs):
    monkeypatch.setattr(tools_mod, "ScavioClient", _FakeClient)
    return build_scavio_toolkit(api_key="test", **kwargs)


def _only(monkeypatch, provider):
    """Build a toolkit with exactly one provider enabled."""
    flags = {f"enable_{ns}": (ns == provider) for ns in _NAMESPACES}
    return _build(monkeypatch, **flags)


def test_all_tools_register(monkeypatch):
    toolkit = _build(monkeypatch, all=True)
    slugs = [t.slug for t in toolkit.tools]
    assert len(slugs) == 97, len(slugs)
    assert len(set(slugs)) == len(slugs), "slugs must be unique"
    assert all(s.startswith("SCAVIO_") for s in slugs)


def test_per_provider_coverage(monkeypatch):
    """Every provider registers exactly the number of tools it has live endpoints."""
    actual = {ns: len(_only(monkeypatch, ns).tools) for ns in _NAMESPACES}
    assert actual == EXPECTED_COUNTS
    assert sum(actual.values()) == 97


def test_every_tool_calls_a_real_sdk_method(monkeypatch):
    """No tool may target an SDK method that does not exist on the installed scavio."""
    import inspect

    from scavio import ScavioClient

    real = ScavioClient(api_key="test")
    toolkit = _build(monkeypatch, all=True)
    client = tools_mod.ScavioClient  # the fake class; instances record onto .calls

    for tool in toolkit.tools:
        values = {}
        for name, field in tool.input_params.model_fields.items():
            annotation = str(field.annotation)
            if "int" in annotation and "str" not in annotation:
                values[name] = 1
            elif "bool" in annotation and "str" not in annotation:
                values[name] = True
            elif "list" in annotation:
                values[name] = ["x"]
            else:
                values[name] = "x"
        out = tool.execute(tool.input_params(**values), None)
        assert out["ok"] is True, tool.slug

        namespace = tool.slug.split("_")[1].lower()
        if tool.slug.startswith("SCAVIO_TIKTOK_SHOP_"):
            namespace = "tiktok_shop"
        method = getattr(getattr(real, namespace), out["method"], None)
        assert method is not None, f"{tool.slug} calls missing scavio.{namespace}.{out['method']}"
        accepted = {
            p.name
            for p in inspect.signature(method).parameters.values()
            if p.kind in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY)
        }
        unknown = set(out["kwargs"]) - accepted
        assert not unknown, f"{tool.slug} sends params the SDK rejects: {sorted(unknown)}"

    assert client is tools_mod.ScavioClient


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


def test_parameterless_tools_execute(monkeypatch):
    toolkit = _build(monkeypatch, all=True)
    for slug, method in (("SCAVIO_TIKTOK_SHOP_CATEGORIES", "categories"),
                         ("SCAVIO_REDDIT_TRENDING", "trending")):
        tool = next(t for t in toolkit.tools if t.slug == slug)
        assert set(tool.input_params.model_fields) == set()
        out = tool.execute(tool.input_params(), None)
        assert out["method"] == method
        assert out["kwargs"] == {}


def test_every_tool_description_states_a_credit_cost(monkeypatch):
    toolkit = _build(monkeypatch, all=True)
    missing = [t.slug for t in toolkit.tools if "credit" not in (t.description or "").lower()]
    assert not missing, missing


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
    flags = {f"enable_{ns}": (ns == "google") for ns in _NAMESPACES}
    toolkit = build_scavio_toolkit(api_key="test", **flags)
    tool = next(t for t in toolkit.tools if t.slug == "SCAVIO_GOOGLE_SEARCH")
    out = tool.execute(tool.input_params(query="x"), None)
    assert out == {"error": "network down"}
