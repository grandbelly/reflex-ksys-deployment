from __future__ import annotations

from typing import Any, Dict, List

from ..db import q


async def tags_list() -> List[Dict[str, Any]]:
    sql = (
        "SELECT DISTINCT tag_name "
        "FROM public.influx_latest "
        "WHERE tag_name IS NOT NULL "
        "ORDER BY tag_name "
        "LIMIT 1000"
    )
    return await q(sql, ())



