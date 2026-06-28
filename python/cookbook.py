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

    # Expose only the providers you need; here just Google.
    scavio = build_scavio_toolkit(
        enable_google=True,
        enable_amazon=False,
        enable_walmart=False,
        enable_youtube=False,
        enable_reddit=False,
        enable_tiktok=False,
        enable_instagram=False,
    )

    session = composio.create(
        user_id="cookbook-user",
        experimental={"custom_toolkits": [scavio]},
    )

    result = session.tools.execute(
        "SCAVIO_GOOGLE_SEARCH",
        arguments={"query": "best structured search API for AI agents", "light_request": True},
    )
    print(result)


if __name__ == "__main__":
    main()
