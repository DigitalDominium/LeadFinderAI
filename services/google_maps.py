from __future__ import annotations

import os
from typing import Any

import requests

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"
PLACES_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"


class GoogleMapsError(Exception):
    pass


def geocode_location(location: str) -> tuple[float, float, str]:
    if not GOOGLE_MAPS_API_KEY:
        raise GoogleMapsError("GOOGLE_MAPS_API_KEY is not set in Render environment variables.")
    response = requests.get(
        GEOCODING_URL,
        params={"address": location, "key": GOOGLE_MAPS_API_KEY},
        timeout=12,
    )
    data = response.json()
    if data.get("status") != "OK" or not data.get("results"):
        raise GoogleMapsError(f"Could not geocode location: {location}")
    result = data["results"][0]
    point = result["geometry"]["location"]
    return float(point["lat"]), float(point["lng"]), result.get("formatted_address", location)


def find_business_leads(
    location: str,
    industry: str,
    radius_km: float = 10.0,
    count: int = 10,
) -> tuple[list[dict[str, Any]], str]:
    lat, lng, formatted_location = geocode_location(location)
    radius_m = max(500, min(int(radius_km * 1000), 50000))

    payload = {
        "textQuery": industry,
        "maxResultCount": max(1, min(int(count), 20)),
        "locationBias": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": radius_m,
            }
        },
    }

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": (
            "places.id,places.displayName,places.formattedAddress,"
            "places.nationalPhoneNumber,places.websiteUri,"
            "places.rating,places.userRatingCount,"
            "places.businessStatus,places.primaryType,places.types"
        ),
    }

    response = requests.post(PLACES_SEARCH_URL, json=payload, headers=headers, timeout=20)
    if response.status_code != 200:
        raise GoogleMapsError(f"Places API error {response.status_code}: {response.text[:500]}")

    places = response.json().get("places", [])
    leads: list[dict[str, Any]] = []

    for place in places:
        place_id = place.get("id", "")
        name = place.get("displayName", {}).get("text", "")
        leads.append(
            {
                "place_id": place_id,
                "name": name,
                "address": place.get("formattedAddress", ""),
                "phone": place.get("nationalPhoneNumber", ""),
                "website": place.get("websiteUri", ""),
                "rating": place.get("rating", ""),
                "user_rating_count": place.get("userRatingCount", ""),
                "business_status": place.get("businessStatus", ""),
                "primary_type": place.get("primaryType", ""),
                "types": ", ".join(place.get("types", [])),
                "google_maps_url": f"https://www.google.com/maps/place/?q=place_id:{place_id}" if place_id else "",
                "lead_score": 0,
                "priority": "",
                "logistics_potential": "",
                "suggested_service": "",
                "possible_pain_points": "",
                "reasoning_summary": "",
                "sales_opening_line": "",
                "email_subject": "",
                "email_body": "",
            }
        )

    return leads, formatted_location
