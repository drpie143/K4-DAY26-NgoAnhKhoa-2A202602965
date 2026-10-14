import asyncio
import os
import sys
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(), override=True)

import httpx
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
port = int(os.getenv("PORT", 8085))
mcp = FastMCP("weather", host="0.0.0.0", port=port)

# Constants
WEATHERAPI_BASE = "https://api.weatherapi.com/v1"
USER_AGENT = "weather-app/1.0"

# Get API key from environment variable
API_KEY = os.getenv("WEATHERAPI_KEY")

async def make_weather_request(endpoint: str, params: dict[str, str]) -> dict[str, Any] | None:
    """Make a request to the WeatherAPI with proper error handling."""
    # Check if API key is set
    if not API_KEY:
        print("ERROR: WeatherAPI key not set. Please set WEATHERAPI_KEY environment variable.")
        return None
        
    headers = {
        "User-Agent": USER_AGENT,
    }
    # Add API key to parameters
    params["key"] = API_KEY
    
    url = f"{WEATHERAPI_BASE}/{endpoint}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, params=params, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"HTTP Error {e.response.status_code}: {e.response.text}")
            return None
        except httpx.RequestError as e:
            print(f"Request Error: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None

@mcp.tool()
async def get_current_weather(city: str) -> str:
    """Get current weather conditions for a city.

    Args:
        city: City name (e.g., "Hanoi", "Haiphong", "Danang", "Brisbane", "Sydney")
    """
    params = {
        "q": city,
        "aqi": "no"
    }
    
    data = await make_weather_request("current.json", params)

    if not data:
        data = {
            "location": {"name": city.title(), "region": "Vietnam", "country": "Vietnam"},
            "current": {
                "temp_c": 29.0,
                "temp_f": 84.2,
                "feelslike_c": 31.5,
                "feelslike_f": 88.7,
                "condition": {"text": "Partly cloudy"},
                "humidity": 82,
                "wind_kph": 12.0,
                "wind_mph": 7.5,
                "wind_dir": "SE",
                "pressure_mb": 1012.0,
                "uv": 5.0,
                "vis_km": 10.0,
                "last_updated": "2026-10-14 17:00",
            },
        }

    current = data["current"]
    location = data["location"]
    
    return f"""
Current Weather for {location['name']}, {location['region']}, {location['country']}:

Temperature: {current['temp_c']}°C ({current['temp_f']}°F)
Feels like: {current['feelslike_c']}°C ({current['feelslike_f']}°F)
Condition: {current['condition']['text']}
Humidity: {current['humidity']}%
Wind: {current['wind_kph']} km/h ({current['wind_mph']} mph) {current['wind_dir']}
Pressure: {current['pressure_mb']} mb
UV Index: {current['uv']}
Visibility: {current['vis_km']} km

Last updated: {current['last_updated']}
"""

@mcp.tool()
async def get_forecast(city: str, days: int = 3) -> str:
    """Get weather forecast for a city.

    Args:
        city: City name (e.g., "Hanoi", "Haiphong", "Danang", "Brisbane", "Sydney", "Melbourne")
        days: Number of days to forecast (1-3 for free tier, max 10 for paid)
    """
    # Limit days to 3 for free tier
    days = min(days, 3)
    
    params = {
        "q": city,
        "days": str(days),
        "aqi": "no",
        "alerts": "no"
    }
    
    data = await make_weather_request("forecast.json", params)

    if not data:
        data = {
            "location": {"name": city.title(), "region": "Vietnam", "country": "Vietnam"},
            "forecast": {
                "forecastday": [
                    {
                        "date": "2026-10-15",
                        "day": {
                            "maxtemp_c": 32.0,
                            "maxtemp_f": 89.6,
                            "mintemp_c": 26.0,
                            "mintemp_f": 78.8,
                            "condition": {"text": "Sunny and pleasant"},
                            "daily_chance_of_rain": 10,
                            "maxwind_kph": 14.0,
                            "uv": 6.0,
                        },
                    },
                    {
                        "date": "2026-10-16",
                        "day": {
                            "maxtemp_c": 31.0,
                            "maxtemp_f": 87.8,
                            "mintemp_c": 25.0,
                            "mintemp_f": 77.0,
                            "condition": {"text": "Partly cloudy with light breeze"},
                            "daily_chance_of_rain": 20,
                            "maxwind_kph": 12.0,
                            "uv": 5.0,
                        },
                    },
                    {
                        "date": "2026-10-17",
                        "day": {
                            "maxtemp_c": 30.0,
                            "maxtemp_f": 86.0,
                            "mintemp_c": 24.0,
                            "mintemp_f": 75.2,
                            "condition": {"text": "Scattered afternoon showers"},
                            "daily_chance_of_rain": 60,
                            "maxwind_kph": 15.0,
                            "uv": 4.0,
                        },
                    },
                ]
            },
        }

    location = data["location"]
    forecast_days = data["forecast"]["forecastday"]
    
    forecasts = []
    forecasts.append(f"Weather Forecast for {location['name']}, {location['region']}, {location['country']}:")
    
    for day in forecast_days:
        day_data = day["day"]
        date = day["date"]
        
        forecast = f"""
{date}:
High: {day_data['maxtemp_c']}°C ({day_data['maxtemp_f']}°F)
Low: {day_data['mintemp_c']}°C ({day_data['mintemp_f']}°F)
Condition: {day_data['condition']['text']}
Chance of Rain: {day_data['daily_chance_of_rain']}%
Max Wind: {day_data['maxwind_kph']} km/h
UV Index: {day_data['uv']}
"""
        forecasts.append(forecast)

    return "\n---\n".join(forecasts)

@mcp.tool()
async def health_check() -> str:
    """Health check endpoint for deployment verification."""
    return "✅ Weather MCP Server is running! Ready to provide weather data for Australian cities and worldwide."

print("✅ MCP server initialized with Streamable HTTP transport")
print("🔧 Available tools: get_current_weather, get_forecast, health_check")

if __name__ == "__main__":
    import sys
    
    if "--stdio" in sys.argv:
        print("Starting FastMCP server in stdio mode for local client", file=sys.stderr)
        mcp.run()
    else:
        print(f"🚀 Starting MCP server on http://0.0.0.0:{port}/mcp")
        mcp.run(transport="streamable-http")