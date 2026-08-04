"""Generate scavio-openapi.json, the Composio catalog submission artifact.

Source of truth is ``scavio._spec.ENDPOINTS`` from the installed Scavio Python
SDK: it declares every endpoint's path, HTTP method, wire field names, types,
required-ness and credit cost, and it is regenerated from the backend zod
schemas. Do NOT use ``backend/scripts/export-openapi.ts`` - it mounts only 8 of
the 15 route apps and structurally cannot see Google v2, X, LinkedIn or
TikTok Shop.

Emitted surface (100 paths):
  - 98 billable data endpoints, including the deprecated /api/v1/youtube/metadata
    alias (marked deprecated, it duplicates /api/v1/youtube/video)
  - GET /api/v1/amazon/options and GET /api/v1/usage, both free
The 5 retired LinkedIn endpoints are deliberately omitted: they always answer
410 unbilled, so a catalog tool built from them could only ever fail.
Google v1 (/api/v1/google) is omitted too - it was retired on 2026-08-04.

Run:  python scripts/gen_openapi.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict

from scavio._spec import ENDPOINTS

OUT = Path(__file__).resolve().parent.parent / "scavio-openapi.json"

# Retired upstream: always 410, never billed. Never advertise these as tools.
RETIRED = {
    "linkedin_person_contact",
    "linkedin_company_people",
    "linkedin_company_jobs",
    "linkedin_search_people",
    "linkedin_search_posts",
}

# /api/v1/youtube/metadata is a deprecated alias of /api/v1/youtube/video. The SDK
# points both methods at /video, so the alias path has to be restored here.
ALIAS_PATHS = {"youtube_metadata": "/api/v1/youtube/metadata"}

# GET /api/v1/amazon/options is a static marketplace list. It is not one of the 98
# billable endpoints and needs no API key; the SDK registry just never overrode the
# default cost of 1. Canonical wins.
FREE = {"amazon_options"}

TAGS = {
    "google": "Google",
    "youtube": "YouTube",
    "amazon": "Amazon",
    "walmart": "Walmart",
    "reddit": "Reddit",
    "tiktok": "TikTok",
    "tiktok_shop": "TikTok Shop",
    "instagram": "Instagram",
    "x": "X",
    "linkedin": "LinkedIn",
    "account": "Account",
}

TAG_DESCRIPTIONS = {
    "Google": "Google v2 SERP and verticals: web search, AI Mode, Maps, Shopping, Flights, Hotels, News and Trends. 1 credit each. Responses are FLAT (no data wrapper) and carry organic_results[].link / .snippet.",
    "YouTube": "YouTube search, video, comments, transcript, channel and stream data.",
    "Amazon": "Amazon product search, product detail and seller offers. Marketplace is selected with a two-letter country code.",
    "Walmart": "Walmart product search and product detail.",
    "Reddit": "Reddit search, posts, comments, subreddit and user feeds.",
    "TikTok": "TikTok profiles, videos, comments, hashtags and search.",
    "TikTok Shop": "TikTok Shop product search, product detail, reviews, categories, shop listings and URL resolution.",
    "Instagram": "Instagram profiles, posts, reels, stories, comments and search. Credits vary per endpoint.",
    "X": "X (Twitter) search, posts, replies, user profiles, timelines and trends.",
    "LinkedIn": "LinkedIn people, companies, posts, comments and jobs. Credits vary per endpoint.",
    "Account": "Credit balance and usage. Free.",
}

_LITERAL = re.compile(r'^Optional\[Literal\[(.*)\]\]$')


def json_schema_for(annotation: str) -> Dict[str, Any]:
    """Map an SDK type annotation onto a JSON Schema fragment."""
    match = _LITERAL.match(annotation)
    if match:
        values = [v.strip().strip('"').strip("'") for v in match.group(1).split(",")]
        return {"type": "string", "enum": values}
    if annotation in ("str", "Optional[str]"):
        return {"type": "string"}
    if annotation == "Optional[int]":
        return {"type": "integer"}
    if annotation == "Optional[bool]":
        return {"type": "boolean"}
    if annotation == "Optional[list[str]]":
        return {"type": "array", "items": {"type": "string"}}
    raise ValueError(f"unmapped annotation: {annotation}")


def envelope_response(summary: str, flat: bool) -> Dict[str, Any]:
    if flat:
        schema = {
            "type": "object",
            "description": "Flat response: the provider payload is spread at the top level, there is no data key.",
            "additionalProperties": True,
            "properties": {
                "response_time": {"type": "number"},
                "credits_used": {"type": "number"},
                "credits_remaining": {"type": "number"},
                "cached": {"type": "boolean", "description": "True when served from the v2 cache. Cached responses still bill."},
            },
            "required": ["response_time", "credits_used", "credits_remaining"],
        }
    else:
        schema = {
            "type": "object",
            "properties": {
                "data": {"description": "The endpoint payload."},
                "response_time": {"type": "number"},
                "credits_used": {"type": "number"},
                "credits_remaining": {"type": "number"},
            },
            "required": ["data", "response_time"],
        }
    return {"description": summary, "content": {"application/json": {"schema": schema}}}


ERROR_SCHEMA = {
    "type": "object",
    "properties": {
        "error": {"type": "string"},
        "details": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"path": {"type": "string"}, "message": {"type": "string"}},
            },
        },
    },
    "required": ["error"],
}


def error_responses() -> Dict[str, Any]:
    return {
        "400": {"description": "Invalid request", "content": {"application/json": {"schema": ERROR_SCHEMA}}},
        "401": {"description": "Missing or invalid API key", "content": {"application/json": {"schema": ERROR_SCHEMA}}},
        "402": {"description": "Out of credits", "content": {"application/json": {"schema": ERROR_SCHEMA}}},
        "429": {
            "description": "Rate, concurrency or usage limit exceeded",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "error": {"type": "string"},
                            "limit": {"type": "number"},
                            "used": {"type": "number"},
                            "plan": {"type": "string"},
                        },
                        "required": ["error"],
                    }
                }
            },
        },
        "502": {"description": "Upstream data source unavailable", "content": {"application/json": {"schema": ERROR_SCHEMA}}},
    }


def describe(endpoint, credits: int) -> str:
    """Build the operation description: summary, credit cost, and any one-of rule."""
    parts = [f"{endpoint.summary}."]
    if credits == 0:
        parts.append("Free: this endpoint does not consume credits.")
    else:
        unit = "credit" if credits == 1 else "credits"
        parts.append(f"Costs {credits} {unit}.")
    for group in endpoint.one_of:
        names = ", ".join(group)
        parts.append(f"Provide exactly one of: {names}.")
    if endpoint.namespace == "google":
        parts.append(
            "Google v2. The response is flat (no data wrapper) and results are organic_results[] "
            "with link and snippet. `start` is a 0-based result offset, not a page number."
        )
    return " ".join(parts)


def build() -> Dict[str, Any]:
    paths: Dict[str, Any] = {}

    for key, endpoint in ENDPOINTS.items():
        if key in RETIRED:
            continue
        path = ALIAS_PATHS.get(key, endpoint.path)
        credits = 0 if key in FREE else endpoint.credits
        operation: Dict[str, Any] = {
            "operationId": key,
            "tags": [TAGS[endpoint.namespace]],
            "summary": endpoint.summary,
            "description": describe(endpoint, credits),
            "security": [] if key in FREE else [{"Bearer": []}],
            "x-credits": credits,
        }
        if key in ALIAS_PATHS:
            operation["deprecated"] = True
            operation["description"] = (
                f"{operation['description']} DEPRECATED alias of POST {endpoint.path}; use that instead."
            )

        if endpoint.params:
            properties: Dict[str, Any] = {}
            required: list[str] = []
            for param in endpoint.params:
                schema = json_schema_for(param.annotation)
                if param.doc:
                    schema["description"] = param.doc
                properties[param.wire_field] = schema
                if param.required:
                    required.append(param.wire_field)
            body_schema: Dict[str, Any] = {"type": "object", "properties": properties}
            if required:
                body_schema["required"] = required
            if endpoint.http == "POST":
                operation["requestBody"] = {
                    "required": True,
                    "content": {"application/json": {"schema": body_schema}},
                }
            else:
                operation["parameters"] = [
                    {
                        "name": name,
                        "in": "query",
                        "required": name in required,
                        "schema": {k: v for k, v in schema.items() if k != "description"},
                        "description": schema.get("description", ""),
                    }
                    for name, schema in properties.items()
                ]
        elif endpoint.http == "POST":
            # Body is still required by the backend even when the schema is empty.
            operation["requestBody"] = {
                "required": True,
                "content": {"application/json": {"schema": {"type": "object", "properties": {}}}},
            }

        flat = endpoint.namespace == "google"
        operation["responses"] = {"200": envelope_response(endpoint.summary, flat), **error_responses()}
        paths.setdefault(path, {})[endpoint.http.lower()] = operation

    # Credit balance / usage: free, not part of the SDK endpoint registry.
    paths["/api/v1/usage"] = {
        "get": {
            "operationId": "account_usage",
            "tags": ["Account"],
            "summary": "Usage and Credit Balance",
            "description": "Return the current plan, credit balance and usage. Free: this endpoint does not consume credits.",
            "security": [{"Bearer": []}],
            "x-credits": 0,
            "responses": {
                "200": {
                    "description": "Usage and Credit Balance",
                    "content": {"application/json": {"schema": {"type": "object", "additionalProperties": True}}},
                },
                "401": {"description": "Missing or invalid API key", "content": {"application/json": {"schema": ERROR_SCHEMA}}},
            },
        }
    }

    return {
        "openapi": "3.1.0",
        "info": {
            "title": "Scavio Search API",
            "version": "1.0.0",
            "description": (
                "Real-time structured search over Google, YouTube, Amazon, Walmart, Reddit, TikTok, "
                "TikTok Shop, Instagram, X and LinkedIn. 98 billable endpoints plus two free ones. "
                "Google runs on POST /api/v2/google and its 13 verticals; the v1 path /api/v1/google was "
                "retired on 2026-08-04 and returns 410. The 5 retired LinkedIn endpoints "
                "(person/contact, company/people, company/jobs, search/people, search/posts) always "
                "return 410 unbilled and are deliberately not listed. Every endpoint's credit cost is on "
                "the x-credits field of its operation."
            ),
            "contact": {"name": "Scavio", "url": "https://scavio.dev", "email": "scavio.dev@gmail.com"},
            "license": {"name": "Proprietary", "url": "https://scavio.dev/terms"},
        },
        "servers": [{"url": "https://api.scavio.dev"}],
        "security": [{"Bearer": []}],
        "tags": [{"name": name, "description": desc} for name, desc in TAG_DESCRIPTIONS.items()],
        "components": {
            "securitySchemes": {
                "Bearer": {
                    "type": "http",
                    "scheme": "bearer",
                    "description": "Your Scavio API key, sent as 'Authorization: Bearer <key>'.",
                }
            }
        },
        "paths": paths,
    }


def main() -> None:
    spec = build()
    OUT.write_text(json.dumps(spec, indent=2) + "\n")
    operations = sum(len(methods) for methods in spec["paths"].values())
    billable = sum(
        1
        for methods in spec["paths"].values()
        for op in methods.values()
        if op.get("x-credits", 0) > 0
    )
    print(f"wrote {OUT} - {len(spec['paths'])} paths, {operations} operations, {billable} billable")


if __name__ == "__main__":
    main()
