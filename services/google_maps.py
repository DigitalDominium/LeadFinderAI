from __future__ import annotations

import os
import math
from typing import Any

import requests

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")

GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"
PLACES_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
PLACES_DETAIL_URL = "https://places.googleapis.com/v1/places/{place_id}"


class GoogleMapsError(Exception):
    pass


def geocode_location(location: str) -> tuple[float, float, str]:
    resp = requests.get(
        GEOCODING_URL,
        params={"address": location, "key": GOOGLE_MAPS_API_KEY},
        timeout=10,
    )
    data = resp.json()
    if data.get("status") != "OK" or not data.get("results"):
        raise GoogleMapsError(f"Could not geocode location: {location}")
    result = data["results"][0]
    lat = result["geometry"]["location"]["lat"]
    lng = result["geometry"]["location"]["lng"]
    formatted = result.get("formatted_address", location)
    return lat, lng, formatted


def find_business_leads(
    location: str,
    industry: str,
    radius_km: float = 10.0,
    count: int = 10,
) -> tuple[list[dict[str, Any]], str]:
    if not GOOGLE_MAPS_API_KEY:
        raise GoogleMapsError("GOOGLE_MAPS_API_KEY is not set.")

    lat, lng, formatted_location = geocode_location(location)
    radius_m = int(radius_km * 1000)

    payload = {
        "textQuery": industry,
        "maxResultCount": min(count, 20),
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

    resp = requests.post(PLACES_SEARCH_URL, json=payload, headers=headers, timeout=15)
    if resp.status_code != 200:
        raise GoogleMapsError(f"Places API error {resp.status_code}: {resp.text}")

    places = resp.json().get("places", [])
    leads = []
    for place in places:
        place_id = place.get("id", "")
        name = place.get("displayName", {}).get("text", "")
        leads.append({
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
            "lead_score": "",
            "priority": "",
            "logistics_potential": "",
            "suggested_service": "",
            "possible_pain_points": "",
            "reasoning_summary": "",
            "sales_opening_line": "",
            "email_subject": "",
            "email_body": "",
        })

    return leads, formatted_location
