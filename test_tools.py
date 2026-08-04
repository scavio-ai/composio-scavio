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


class _FakeClient:
    def __init__(self, *args, **kwargs):
        self.calls = []
        for ns in ("google", "amazon", "walmart", "youtube", "reddit", "tiktok", "instagram"):
            setattr(self, ns, _Recorder(self.calls))


def _build(monkeypatch, **kwargs):
    monkeypatch.setattr(tools_mod, "ScavioClient", _FakeClient)
    return build_scavio_toolkit(api_key="test", **kwargs)


def test_all_tools_register(monkeypatch):
    toolkit = _build(monkeypatch, all=True)
    slugs = [t.slug for t in toolkit.tools]
    assert len(slugs) == 47, slugs
    assert len(set(slugs)) == len(slugs), "slugs must be unique"
    assert all(s.startswith("SCAVIO_") for s in slugs)


def test_provider_gating(monkeypatch):
    toolkit = _build(
        monkeypatch,
        enable_google=False,
        enable_amazon=False,
        enable_walmart=False,
        enable_youtube=False,
        enable_reddit=True,
        enable_tiktok=False,
        enable_instagram=False,
    )
    slugs = {t.slug for t in toolkit.tools}
    assert slugs == {"SCAVIO_REDDIT_SEARCH", "SCAVIO_REDDIT_POST"}


def test_all_overrides_flags(monkeypatch):
    toolkit = _build(monkeypatch, all=True, enable_reddit=False, enable_tiktok=False)
    slugs = {t.slug for t in toolkit.tools}
    assert "SCAVIO_REDDIT_SEARCH" in slugs
    assert "SCAVIO_TIKTOK_PROFILE" in slugs


def test_google_maps_public_params_to_v2(monkeypatch):
    toolkit = _build(monkeypatch, enable_google=True, enable_amazon=False, enable_walmart=False,
                     enable_youtube=False, enable_reddit=False, enable_tiktok=False, enable_instagram=False)
    tool = next(t for t in toolkit.tools if t.slug == "SCAVIO_GOOGLE_SEARCH")
    out = tool.execute(
        tool.input_params(query="ai agents", country_code="us", language="en", page=2, device="mobile", nfpr=True),
        None,
    )
    assert out["ok"] is True
    assert out["method"] == "search"
    # Public v1-style args are mapped to v2 wire params; page -> start offset; None dropped.
    assert out["kwargs"] == {
        "query": "ai agents",
        "gl": "us",
        "hl": "en",
        "start": 10,
        "device": "mobile",
        "nfpr": True,
    }


def test_google_page_one_sends_no_start(monkeypatch):
    toolkit = _build(monkeypatch, enable_google=True, enable_amazon=False, enable_walmart=False,
                     enable_youtube=False, enable_reddit=False, enable_tiktok=False, enable_instagram=False)
    tool = next(t for t in toolkit.tools if t.slug == "SCAVIO_GOOGLE_SEARCH")
    out = tool.execute(tool.input_params(query="ai agents", page=1), None)
    assert out["kwargs"] == {"query": "ai agents"}


def test_amazon_product_uses_asin(monkeypatch):
    toolkit = _build(monkeypatch, enable_amazon=True, enable_google=False, enable_walmart=False,
                     enable_youtube=False, enable_reddit=False, enable_tiktok=False, enable_instagram=False)
    tool = next(t for t in toolkit.tools if t.slug == "SCAVIO_AMAZON_PRODUCT")
    out = tool.execute(tool.input_params(asin="B000000000"), None)
    assert out["method"] == "product"
    assert out["kwargs"] == {"asin": "B000000000"}


def test_youtube_tools_register(monkeypatch):
    toolkit = _build(monkeypatch, enable_google=False, enable_amazon=False, enable_walmart=False,
                     enable_youtube=True, enable_reddit=False, enable_tiktok=False, enable_instagram=False)
    slugs = {t.slug for t in toolkit.tools}
    assert slugs == {
        "SCAVIO_YOUTUBE_SEARCH", "SCAVIO_YOUTUBE_SHORTS", "SCAVIO_YOUTUBE_SUGGESTIONS",
        "SCAVIO_YOUTUBE_VIDEO", "SCAVIO_YOUTUBE_METADATA", "SCAVIO_YOUTUBE_COMMENTS",
        "SCAVIO_YOUTUBE_COMMENT_REPLIES", "SCAVIO_YOUTUBE_TRANSCRIPT", "SCAVIO_YOUTUBE_RELATED",
        "SCAVIO_YOUTUBE_CHANNEL_SEARCH", "SCAVIO_YOUTUBE_CHANNEL", "SCAVIO_YOUTUBE_CHANNEL_VIDEOS",
        "SCAVIO_YOUTUBE_CHANNEL_SHORTS", "SCAVIO_YOUTUBE_CHANNEL_COMMUNITY",
        "SCAVIO_YOUTUBE_CHANNEL_RESOLVE", "SCAVIO_YOUTUBE_STREAMS",
    }


def test_youtube_metadata_is_alias_of_video(monkeypatch):
    toolkit = _build(monkeypatch, enable_google=False, enable_amazon=False, enable_walmart=False,
                     enable_youtube=True, enable_reddit=False, enable_tiktok=False, enable_instagram=False)
    tool = next(t for t in toolkit.tools if t.slug == "SCAVIO_YOUTUBE_METADATA")
    out = tool.execute(tool.input_params(video_id="dQw4w9WgXcQ"), None)
    assert out["method"] == "metadata"
    assert out["kwargs"] == {"video_id": "dQw4w9WgXcQ"}


def test_youtube_comment_replies_passes_reply_cursor(monkeypatch):
    toolkit = _build(monkeypatch, enable_google=False, enable_amazon=False, enable_walmart=False,
                     enable_youtube=True, enable_reddit=False, enable_tiktok=False, enable_instagram=False)
    tool = next(t for t in toolkit.tools if t.slug == "SCAVIO_YOUTUBE_COMMENT_REPLIES")
    out = tool.execute(tool.input_params(video_id="vid", reply_cursor="rc"), None)
    assert out["method"] == "comment_replies"
    assert out["kwargs"] == {"video_id": "vid", "reply_cursor": "rc"}


def test_reddit_search_takes_only_query_and_cursor(monkeypatch):
    toolkit = _build(monkeypatch, enable_google=False, enable_amazon=False, enable_walmart=False,
                     enable_youtube=False, enable_reddit=True, enable_tiktok=False, enable_instagram=False)
    tool = next(t for t in toolkit.tools if t.slug == "SCAVIO_REDDIT_SEARCH")
    assert set(tool.input_params.model_fields) == {"query", "cursor"}
    out = tool.execute(tool.input_params(query="serpapi alternative", cursor="c1"), None)
    assert out["method"] == "search"
    assert out["kwargs"] == {"query": "serpapi alternative", "cursor": "c1"}


def test_reddit_post_takes_url_only(monkeypatch):
    toolkit = _build(monkeypatch, enable_google=False, enable_amazon=False, enable_walmart=False,
                     enable_youtube=False, enable_reddit=True, enable_tiktok=False, enable_instagram=False)
    tool = next(t for t in toolkit.tools if t.slug == "SCAVIO_REDDIT_POST")
    out = tool.execute(tool.input_params(url="https://www.reddit.com/r/programming/comments/abc123/x/"), None)
    assert out["method"] == "post"
    assert out["kwargs"] == {"url": "https://www.reddit.com/r/programming/comments/abc123/x/"}


def test_error_is_returned_as_dict(monkeypatch):
    def boom(**kwargs):
        raise RuntimeError("network down")

    class FailingClient(_FakeClient):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.google.search = boom  # type: ignore[attr-defined]

    monkeypatch.setattr(tools_mod, "ScavioClient", FailingClient)
    toolkit = build_scavio_toolkit(api_key="test", enable_google=True, enable_amazon=False,
                                   enable_walmart=False, enable_youtube=False, enable_reddit=False,
                                   enable_tiktok=False, enable_instagram=False)
    tool = next(t for t in toolkit.tools if t.slug == "SCAVIO_GOOGLE_SEARCH")
    out = tool.execute(tool.input_params(query="x"), None)
    assert out == {"error": "network down"}
