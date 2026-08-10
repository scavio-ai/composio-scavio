"""Run Scavio tools inside a Composio session.

Prerequisites:
    pip install composio-scavio
    export SCAVIO_API_KEY=sk_...      # from https://dashboard.scavio.dev
    export COMPOSIO_API_KEY=...       # from https://app.composio.dev

This builds the Scavio custom toolkit, binds it to a Composio session, and runs a
Google search tool directly. Wire the same tools into any Composio-supported agent
framework (OpenAI, Anthropic, LangChain, CrewAI, ...).
"""

import os

from composio import Composio

from composio_scavio import build_scavio_toolkit


def main() -> None:
    if not os.getenv("SCAVIO_API_KEY"):
        raise SystemExit("Set SCAVIO_API_KEY first (https://dashboard.scavio.dev).")

    composio = Composio()

    # Expose only the providers you need; here Google (14 tools) plus extract (1).
    # The 21 verticals added in 0.4.0 (Zillow, SEC EDGAR, G2, Meta Ad Library, ...)
    # are opt-in, so they stay off unless you name them or pass all=True.
    scavio = build_scavio_toolkit(
        enable_google=True,
        enable_extract=True,
        enable_amazon=False,
        enable_walmart=False,
        enable_youtube=False,
        enable_reddit=False,
        enable_tiktok=False,
        enable_tiktok_shop=False,
        enable_instagram=False,
        enable_x=False,
        enable_linkedin=False,
    )

    session = composio.create(
        user_id="cookbook-user",
        experimental={"custom_toolkits": [scavio]},
    )

    # Google v2 params are native: gl (country), hl (language), and start, which is a
    # 0-based result OFFSET rather than a page number (0 = page 1, 10 = page 2).
    result = session.tools.execute(
        "SCAVIO_GOOGLE_SEARCH",
        arguments={"query": "best structured search API for AI agents", "gl": "us", "hl": "en"},
    )
    print(result)

    # extract is a CORE endpoint surfaced as one tool: point it at any URL and get the
    # page back as Markdown, plain text or raw HTML. Tier-priced by mode (normal and
    # advanced 1 credit, ultra 2), and only a successful extraction is billed.
    page = session.tools.execute(
        "SCAVIO_EXTRACT",
        arguments={"url": "https://scavio.dev/pricing", "format": "markdown"},
    )
    print(page)


if __name__ == "__main__":
    main()
