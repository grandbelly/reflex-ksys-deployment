from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ..db import q


async def qc_rules(tag_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch QC rules. Returns raw rows to allow flexible schema.

    We intentionally select all columns to adapt to differing column names
    (e.g., min_allowed|min_value|min|lower, max_allowed|max_value|max|upper).
    """
    sql = """
        SELECT *
        FROM public.influx_qc_rule
        WHERE (%s::text IS NULL OR tag_name = %s)
        LIMIT 1000
    """
    params: Tuple[Optional[str], Optional[str]] = (tag_name, tag_name)
    return await q(sql, params)


