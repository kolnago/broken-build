"""Open-Meteo client (no API key needed)."""

from datetime import datetime

import httpx

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# WMO weather interpretation codes, https://open-meteo.com/en/docs
WMO_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Dense drizzle",
    56: "Freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Rain",
    65: "Heavy rain",
    66: "Freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Rain showers",
    82: "Violent rain showers",
    85: "Snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Thunderstorm with heavy hail",
}


async def get_weather(city: str) -> dict:
    """Get current weather and a 3-day forecast for a city.

    Args:
        city: City name, e.g. "Prague".

    Returns:
        Current temperature (°C), condition, wind speed (km/h) and 3 days of min/max
        temperatures, or {"error": ...} if the city can't be found.
    """
    async with httpx.AsyncClient(timeout=10) as client:
        geo = await client.get(GEOCODE_URL, params={"name": city, "count": 1})
        geo.raise_for_status()
        results = geo.json().get("results") or []
        if not results:
            return {"error": f"City not found: {city}"}
        place = results[0]

        fc = await client.get(
            FORECAST_URL,
            params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current": "temperature_2m,weather_code,wind_speed_10m",
                "daily": "temperature_2m_min,temperature_2m_max,weather_code",
                "forecast_days": 3,
                "timezone": "auto",
            },
        )
        fc.raise_for_status()
        data = fc.json()

    current = data["current"]
    daily = data["daily"]
    return {
        "city": place["name"],
        "country": place.get("country", ""),
        "temperature_c": current["temperature_2m"],
        "condition": WMO_CODES.get(current["weather_code"], "Unknown"),
        "wind_kmh": current["wind_speed_10m"],
        "fetched_at": datetime.now().strftime("%H:%M:%S"),
        "forecast": [
            {
                "date": daily["time"][i],
                "min_c": daily["temperature_2m_min"][i],
                "max_c": daily["temperature_2m_max"][i],
                "condition": WMO_CODES.get(daily["weather_code"][i], "Unknown"),
            }
            for i in range(len(daily["time"]))
        ],
    }
