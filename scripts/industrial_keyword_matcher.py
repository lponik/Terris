"""Shared keyword matching rules for industrial keep filtering."""

from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any

# Known false-positive expansions to block.
KEEP_DENYLIST_TOKENS = [
    "POLYNESIAN",
    "NEWSPAPER",
    "PAPERWORK",
]
KEEP_DENYLIST_TOKEN_SET = set(KEEP_DENYLIST_TOKENS)

# Context rules for ambiguous keywords.
KEEP_CONTEXT_RULES: dict[str, dict[str, list[str]]] = {
    "PAPER": {
        "requires_any_tokens": ["MILL", "PULP"],
    }
}


def normalize_text(text: str) -> str:
    return " ".join(tokenize(text))


def tokenize(text: str) -> list[str]:
    if not text:
        return []
    parts = re.split(r"[^A-Za-z0-9]+", str(text).upper())
    return [part for part in parts if part]


def _match_paper_context(tokens: list[str], token_set: set[str], normalized_text: str) -> bool:
    if "PULP" in token_set:
        return True
    if "PAPER" in token_set and ("MILL" in token_set or "PULP" in token_set):
        return True
    if "PAPER MILL" in normalized_text:
        return True
    if "PAPERMILL" in tokens:
        return True
    return False


def match_keep_keyword(name: str, keyword: str) -> bool:
    if not name or not keyword:
        return False

    keyword_upper = str(keyword).upper().strip()
    if not keyword_upper:
        return False

    normalized_text = normalize_text(name)
    if not normalized_text:
        return False

    tokens = tokenize(normalized_text)
    token_set = set(tokens)
    if token_set & KEEP_DENYLIST_TOKEN_SET:
        return False

    if keyword_upper == "PAPER":
        return _match_paper_context(tokens, token_set, normalized_text)

    if len(keyword_upper) <= 4:
        for token in tokens:
            if token in KEEP_DENYLIST_TOKENS:
                continue
            if token.startswith(keyword_upper):
                return True
        return False

    return keyword_upper in normalized_text


def match_any_keep(name: str, keywords: Sequence[str]) -> str | None:
    if not name:
        return None
    for keyword in keywords:
        if match_keep_keyword(name, keyword):
            return keyword
    return None


def build_keep_matcher_rules() -> dict[str, Any]:
    return {
        "short_keyword_mode": "token_startswith",
        "denylist_tokens": KEEP_DENYLIST_TOKENS,
        "context_rules": KEEP_CONTEXT_RULES,
    }


def build_keep_audit(
    *,
    method: str,
    kept_rows: int,
    keep_keyword_hits: dict[str, int],
    keep_keywords: Sequence[str],
) -> dict[str, Any]:
    top_keywords = [
        {"keyword": keyword, "count": count}
        for keyword, count in sorted(
            ((str(key), int(value)) for key, value in keep_keyword_hits.items() if int(value) > 0),
            key=lambda item: (-item[1], item[0]),
        )[:10]
    ]
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "method": method,
        "kept_rows": int(kept_rows),
        "kept_top_keywords": top_keywords,
        "keep_keywords": [str(keyword) for keyword in keep_keywords],
        "denylist_tokens": KEEP_DENYLIST_TOKENS,
        "context_rules": KEEP_CONTEXT_RULES,
    }
