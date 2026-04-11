"""
Weather Tools — fetches real weather data from Open-Meteo (free, no API key).
Falls back to mock data in test scenarios.
"""

import os
import requests
from datetime import date, timedelta

_DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"

# Store latitude/longitude for Open-Meteo calls
_STORE_COORDS = {
    "ST001": {"lat": 51.5074, "lon": -0.1278, "city": "London"},
    "ST002": {"lat": 52.4862, "lon": -1.8904, "city": "Birmingham"},
    "ST003": {"lat": 53.4808, "lon": -2.2426, "city": "Manchester"},
    "ST004": {"lat": 53.8008, "lon": -1.5491, "city": "Leeds"},
    "ST005": {"lat": 51.4545, "lon": -2.5879, "city": "Bristol"},
}

_MOCK_WEATHER = {
    "ST001": {"temp_max": 26, "temp_min": 17, "heatwave": True, "rain_mm": 0, "condition": "Sunny & Hot"},
    "ST002": {"temp_max": 17, "temp_min": 11, "heatwave": False, "rain_mm": 12, "condition": "Rainy"},
    "ST003": {"temp_max": 14, "temp_min": 9, "heatwave": False, "rain_mm": 15, "condition": "Heavy Rain"},
    "ST004": {"temp_max": 20, "temp_min": 13, "heatwave": False, "rain_mm": 0, "condition": "Partly Cloudy"},
    "ST005": {"temp_max": 24, "temp_min": 16, "heatwave": False, "rain_mm": 0, "condition": "Warm & Sunny"},
}


def get_weather_forecast(store_id: str, days_ahead: int = 2) -> dict:
    """
    Fetch weather forecast for the next N days for a given store location.

    Args:
        store_id: Store identifier (ST001–ST005)
        days_ahead: Number of forecast days (default 2)

    Returns:
        Dict with temperature, rain, heatwave flag, and demand impact assessment.
    """
    coords = _STORE_COORDS.get(store_id)
    if not coords:
        return {"error": f"Unknown store_id: {store_id}"}

    forecast_days = []

    if not _DEMO_MODE:
        try:
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": coords["lat"],
                "longitude": coords["lon"],
                "daily": ["temperature_2m_max", "temperature_2m_min", "precipitation_sum"],
                "timezone": "Europe/London",
                "forecast_days": days_ahead + 1,
            }
            resp = requests.get(url, params=params, timeout=5)
            resp.raise_for_status()
            data = resp.json()["daily"]

            for i in range(min(days_ahead, len(data["time"]))):
                temp_max = data["temperature_2m_max"][i]
                temp_min = data["temperature_2m_min"][i]
                rain = data["precipitation_sum"][i]
                heatwave = temp_max >= 25
                forecast_days.append({
                    "date": data["time"][i],
                    "temp_max": round(temp_max, 1),
                    "temp_min": round(temp_min, 1),
                    "rain_mm": round(rain, 1),
                    "heatwave": heatwave,
                    "condition": _classify_condition(temp_max, rain),
                })
        except Exception as e:
            # Fallback to mock on any API error
            forecast_days = _mock_forecast(store_id, days_ahead)
    else:
        forecast_days = _mock_forecast(store_id, days_ahead)

    demand_impact = _assess_demand_impact(forecast_days)

    return {
        "store_id": store_id,
        "city": coords["city"],
        "forecast": forecast_days,
        "demand_impact": demand_impact,
        "data_source": "open-meteo.com" if not _DEMO_MODE else "mock",
    }


def _mock_forecast(store_id: str, days_ahead: int) -> list:
    base = _MOCK_WEATHER.get(store_id, {"temp_max": 18, "temp_min": 12, "heatwave": False, "rain_mm": 0, "condition": "Mild"})
    today = date.today()
    return [
        {
            "date": (today + timedelta(days=i)).isoformat(),
            "temp_max": base["temp_max"] + (i * 0.5),
            "temp_min": base["temp_min"],
            "rain_mm": base["rain_mm"],
            "heatwave": base["heatwave"] or base["temp_max"] + (i * 0.5) >= 25,
            "condition": base["condition"],
        }
        for i in range(days_ahead)
    ]


def _classify_condition(temp_max: float, rain_mm: float) -> str:
    if temp_max >= 25:
        return "Sunny & Hot"
    if rain_mm > 10:
        return "Heavy Rain"
    if rain_mm > 2:
        return "Rainy"
    if temp_max >= 18:
        return "Warm & Sunny"
    return "Mild"


def _assess_demand_impact(forecast: list) -> dict:
    """
    Estimate how weather affects perishable demand.
    Heatwave → increased salad/drink demand, decreased hot ready meals.
    Rain → decreased fresh produce demand, increased comfort food.
    """
    if not forecast:
        return {"overall": "NEUTRAL", "notes": []}

    avg_max = sum(d["temp_max"] for d in forecast) / len(forecast)
    total_rain = sum(d["rain_mm"] for d in forecast)
    has_heatwave = any(d["heatwave"] for d in forecast)

    notes = []
    if has_heatwave:
        notes.append("Heatwave detected: +15% demand for salads, beverages, ice cream")
        notes.append("Heatwave detected: accelerated spoilage risk for meat & dairy")
    if total_rain > 5:
        notes.append(f"{total_rain:.0f}mm rain forecast: reduced footfall expected, ~10% lower overall sales")
    if avg_max < 15:
        notes.append("Cool temperatures: higher demand for ready meals and soups")

    overall = "HIGH_RISK" if has_heatwave else ("REDUCED_DEMAND" if total_rain > 5 else "NORMAL")

    return {
        "overall": overall,
        "avg_temp_max": round(avg_max, 1),
        "total_rain_mm": round(total_rain, 1),
        "heatwave": has_heatwave,
        "notes": notes,
    }
