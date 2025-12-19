# backend/app/utils.py
from __future__ import annotations

from datetime import date, datetime
from typing import Any


def to_date_obj(v: Any) -> date | None:
    """
    Accepts:
      - None
      - datetime/date
      - 'YYYY-MM-DD' string
    Returns:
      - date or None
    """
    if v is None or v == "":
        return None
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, str):
        # '2026-04-08' 형태만 지원 (MVP)
        return date.fromisoformat(v[:10])
    return None


def sanitize_for_json(obj: Any) -> Any:
    """
    JSON 직렬화 가능하게 변환:
      - datetime/date => isoformat 문자열
      - dict/list => 재귀 변환
      - 그 외 => 그대로
    """
    if obj is None:
        return None
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_for_json(x) for x in obj]
    return obj
