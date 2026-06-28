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
    assert len(slugs) == 32, slugs
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


def test_execution_forwards_params_and_drops_none(monkeypatch):
    toolkit = _build(monkeypatch, enable_google=True, enable_amazon=False, enable_walmart=False,
                     enable_youtube=False, enable_reddit=False, enable_tiktok=False, enable_instagram=False)
    tool = next(t for t in toolkit.tools if t.slug == "SCAVIO_GOOGLE_SEARCH")
    out = tool.execute(tool.input_params(query="ai agents", light_request=True), None)
    assert out["ok"] is True
    assert out["method"] == "search"
    # None-valued optional fields must not be forwarded to the SDK
    assert out["kwargs"] == {"query": "ai agents", "light_request": True}


def test_amazon_product_uses_asin(monkeypatch):
    toolkit = _build(monkeypatch, enable_amazon=True, enable_google=False, enable_walmart=False,
                     enable_youtube=False, enable_reddit=False, enable_tiktok=False, enable_instagram=False)
    tool = next(t for t in toolkit.tools if t.slug == "SCAVIO_AMAZON_PRODUCT")
    out = tool.execute(tool.input_params(asin="B000000000"), None)
    assert out["method"] == "product"
    assert out["kwargs"] == {"asin": "B000000000"}


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
