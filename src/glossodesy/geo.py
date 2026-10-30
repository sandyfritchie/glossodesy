"""Small geographic helpers."""

from __future__ import annotations

import math

EARTH_RADIUS_KM = 6371.0


def great_circle_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(h))


def country_of(points: list[tuple[float, float]]) -> list[str]:
    """ISO 3166 code (upper case) of the country each point is in.

    Uses the nearest populated place (GeoNames, via reverse_geocoder), which is
    offline and fast but can misjudge points near borders and on remote islands.
    """
    if not points:
        return []
    import reverse_geocoder

    return [r["cc"] for r in reverse_geocoder.search(points, mode=1, verbose=False)]
