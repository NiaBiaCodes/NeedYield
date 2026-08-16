import os
import time
from typing import Optional, Tuple
import httpx

DATASET_TITLE = "Neighborhood Financial Health Digital Mapping and Data Tool"
DATASET_ID = "r3dx-pew9"
DATASET_URL = f"https://data.cityofnewyork.us/resource/{DATASET_ID}.json"
FIELDS_USED = ["borough", "neighborhoods", "nyc_poverty_rate"]

_cache: Optional[Tuple[float, dict[str, float]]] = None


async def fetch_community_need_scores() -> tuple[dict[str, float], str]:
    global _cache
    if _cache and time.time() - _cache[0] < 3600:
        return _cache[1], f"NYC Open Data {DATASET_ID} (cached)"
    headers = {}
    if token := os.getenv("NYC_OPEN_DATA_APP_TOKEN"):
        headers["X-App-Token"] = token
    params = {"$select": ",".join(FIELDS_USED), "$limit": "500"}
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            response = await client.get(DATASET_URL, params=params, headers=headers)
            response.raise_for_status()
        rows = response.json()
        raw: dict[str, list[float]] = {}
        for row in rows:
            try:
                poverty_rate = float(row["nyc_poverty_rate"])
            except (KeyError, TypeError, ValueError):
                continue
            if poverty_rate > 1:
                poverty_rate /= 100
            poverty_rate = max(0.0, min(1.0, poverty_rate))
            for value in (row.get("borough"), row.get("neighborhoods")):
                if value:
                    raw.setdefault(str(value).lower(), []).append(poverty_rate)
        scores = {key: round(sum(values) / len(values), 3) for key, values in raw.items()}
        if not scores:
            raise ValueError("NYC Open Data returned no usable poverty-rate rows")
        _cache = (time.time(), scores)
        return scores, f"NYC Open Data {DATASET_ID}"
    except (httpx.HTTPError, ValueError, TypeError):
        return {}, "NYC Open Data fallback"
