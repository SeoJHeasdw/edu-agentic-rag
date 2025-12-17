from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import random
from datetime import datetime, timedelta
from typing import List

app = FastAPI(title="Mock Weather API", version="1.0.0")


class WeatherInfo(BaseModel):
    city: str
    temperature: int
    condition: str
    humidity: int
    wind_speed: int
    uv_index: int
    timestamp: str


class WeatherForecast(BaseModel):
    city: str
    date: str
    high_temp: int
    low_temp: int
    condition: str
    rain_chance: int


WEATHER_DATA = {
    "seoul": {"temp": 24, "condition": "맑음", "humidity": 65},
    "busan": {"temp": 26, "condition": "흐림", "humidity": 70},
    "incheon": {"temp": 23, "condition": "비", "humidity": 80},
    "daegu": {"temp": 28, "condition": "맑음", "humidity": 55},
    "gwangju": {"temp": 25, "condition": "구름많음", "humidity": 72},
}

WEATHER_CONDITIONS = ["맑음", "흐림", "비", "눈", "구름많음", "안개", "뇌우"]


@app.get("/")
async def root():
    return {"service": "weather-service", "status": "running"}


@app.get("/weather/{city}", response_model=WeatherInfo)
async def get_weather(city: str):
    city_lower = city.lower()

    base_data = WEATHER_DATA.get(city_lower)
    if base_data is None:
        # unknown city -> random
        return WeatherInfo(
            city=city,
            temperature=random.randint(15, 35),
            condition=random.choice(WEATHER_CONDITIONS),
            humidity=random.randint(40, 90),
            wind_speed=random.randint(5, 25),
            uv_index=random.randint(1, 10),
            timestamp=datetime.now().isoformat(),
        )

    temp_variation = random.randint(-2, 2)
    current_temp = base_data["temp"] + temp_variation
    return WeatherInfo(
        city=city,
        temperature=current_temp,
        condition=base_data["condition"],
        humidity=base_data["humidity"] + random.randint(-5, 5),
        wind_speed=random.randint(5, 25),
        uv_index=random.randint(1, 10),
        timestamp=datetime.now().isoformat(),
    )


@app.get("/weather/{city}/forecast", response_model=List[WeatherForecast])
async def get_weather_forecast(city: str, days: int = 3):
    if days > 7:
        raise HTTPException(status_code=400, detail="최대 7일까지만 예보 가능합니다")

    base_temp = WEATHER_DATA.get(city.lower(), {"temp": 25})["temp"]
    forecasts: List[WeatherForecast] = []
    for i in range(days):
        date_str = (datetime.now() + timedelta(days=i + 1)).strftime("%Y-%m-%d")
        high_temp = base_temp + random.randint(-3, 3) + random.randint(3, 8)
        low_temp = high_temp - random.randint(5, 12)
        forecasts.append(
            WeatherForecast(
                city=city,
                date=date_str,
                high_temp=high_temp,
                low_temp=low_temp,
                condition=random.choice(WEATHER_CONDITIONS),
                rain_chance=random.randint(0, 100),
            )
        )
    return forecasts


@app.get("/weather/current/{city}")
async def get_current_conditions(city: str):
    weather = await get_weather(city)
    return {
        "city": weather.city,
        "temperature": f"{weather.temperature}°C",
        "condition": weather.condition,
        "summary": f"{weather.city}은 현재 {weather.temperature}도, {weather.condition}입니다.",
    }


@app.get("/cities")
async def get_available_cities():
    return {"cities": list(WEATHER_DATA.keys()), "total": len(WEATHER_DATA)}

"""
Weather service (mock) - FastAPI app.
Derived from code/example/mock_apis/weather_api.py
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import random
import json
import os
from datetime import datetime, timedelta
from typing import List

app = FastAPI(title="Weather Service (Mock)", version="1.0.0")


class WeatherInfo(BaseModel):
    city: str
    temperature: int
    condition: str
    humidity: int
    wind_speed: int
    uv_index: int
    timestamp: str


class WeatherForecast(BaseModel):
    city: str
    date: str
    high_temp: int
    low_temp: int
    condition: str
    rain_chance: int


def load_weather_data():
    data_path = os.path.join(os.path.dirname(__file__), "data", "weather_data.json")
    if os.path.exists(data_path):
        with open(data_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "seoul": {"temp": 24, "condition": "맑음", "humidity": 65},
        "busan": {"temp": 26, "condition": "흐림", "humidity": 70},
        "incheon": {"temp": 23, "condition": "비", "humidity": 80},
        "daegu": {"temp": 28, "condition": "맑음", "humidity": 55},
        "gwangju": {"temp": 25, "condition": "구름많음", "humidity": 72},
    }


WEATHER_DATA = load_weather_data()
WEATHER_CONDITIONS = ["맑음", "흐림", "비", "눈", "구름많음", "안개", "뇌우"]


@app.get("/")
async def root():
    return {"service": "weather-service", "status": "running"}


@app.get("/cities")
async def cities():
    return {"cities": list(WEATHER_DATA.keys()), "total": len(WEATHER_DATA)}


@app.get("/weather/{city}", response_model=WeatherInfo)
async def get_weather(city: str):
    city_lower = city.lower()
    if city_lower in WEATHER_DATA:
        base = WEATHER_DATA[city_lower]
        temp_variation = random.randint(-2, 2)
        current_temp = base["temp"] + temp_variation
        return WeatherInfo(
            city=city,
            temperature=current_temp,
            condition=base["condition"],
            humidity=base["humidity"] + random.randint(-5, 5),
            wind_speed=random.randint(5, 25),
            uv_index=random.randint(1, 10),
            timestamp=datetime.now().isoformat(),
        )
    return WeatherInfo(
        city=city,
        temperature=random.randint(15, 35),
        condition=random.choice(WEATHER_CONDITIONS),
        humidity=random.randint(40, 90),
        wind_speed=random.randint(5, 25),
        uv_index=random.randint(1, 10),
        timestamp=datetime.now().isoformat(),
    )


@app.get("/weather/{city}/forecast", response_model=List[WeatherForecast])
async def forecast(city: str, days: int = 3):
    if days > 7:
        raise HTTPException(status_code=400, detail="최대 7일까지만 예보 가능합니다")
    base_temp = WEATHER_DATA.get(city.lower(), {"temp": 25})["temp"]
    out: List[WeatherForecast] = []
    for i in range(days):
        d = (datetime.now() + timedelta(days=i + 1)).strftime("%Y-%m-%d")
        high = base_temp + random.randint(-3, 3) + random.randint(3, 8)
        low = high - random.randint(5, 12)
        out.append(
            WeatherForecast(
                city=city,
                date=d,
                high_temp=high,
                low_temp=low,
                condition=random.choice(WEATHER_CONDITIONS),
                rain_chance=random.randint(0, 100),
            )
        )
    return out


@app.get("/weather/current/{city}")
async def current_simple(city: str):
    w = await get_weather(city)
    return {
        "city": w.city,
        "temperature": f"{w.temperature}°C",
        "condition": w.condition,
        "summary": f"{w.city}은 현재 {w.temperature}도, {w.condition}입니다.",
    }

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import random
from datetime import datetime, timedelta
from typing import List


app = FastAPI(title="Weather Service (Mock)", version="1.0.0")


class WeatherInfo(BaseModel):
    city: str
    temperature: int
    condition: str
    humidity: int
    wind_speed: int
    uv_index: int
    timestamp: str


class WeatherForecast(BaseModel):
    city: str
    date: str
    high_temp: int
    low_temp: int
    condition: str
    rain_chance: int


WEATHER_DATA = {
    "seoul": {"temp": 24, "condition": "맑음", "humidity": 65},
    "busan": {"temp": 26, "condition": "흐림", "humidity": 70},
    "incheon": {"temp": 23, "condition": "비", "humidity": 80},
    "daegu": {"temp": 28, "condition": "맑음", "humidity": 55},
    "gwangju": {"temp": 25, "condition": "구름많음", "humidity": 72},
}
WEATHER_CONDITIONS = ["맑음", "흐림", "비", "눈", "구름많음", "안개", "뇌우"]


@app.get("/")
async def root():
    return {"service": "weather-service", "status": "running"}


@app.get("/weather/{city}", response_model=WeatherInfo)
async def get_weather(city: str):
    city_lower = city.lower()
    base_data = WEATHER_DATA.get(city_lower)
    if base_data:
        temp_variation = random.randint(-2, 2)
        current_temp = base_data["temp"] + temp_variation
        return WeatherInfo(
            city=city,
            temperature=current_temp,
            condition=base_data["condition"],
            humidity=base_data["humidity"] + random.randint(-5, 5),
            wind_speed=random.randint(5, 25),
            uv_index=random.randint(1, 10),
            timestamp=datetime.now().isoformat(),
        )
    return WeatherInfo(
        city=city,
        temperature=random.randint(15, 35),
        condition=random.choice(WEATHER_CONDITIONS),
        humidity=random.randint(40, 90),
        wind_speed=random.randint(5, 25),
        uv_index=random.randint(1, 10),
        timestamp=datetime.now().isoformat(),
    )


@app.get("/weather/{city}/forecast", response_model=List[WeatherForecast])
async def get_weather_forecast(city: str, days: int = 3):
    if days > 7:
        raise HTTPException(status_code=400, detail="최대 7일까지만 예보 가능합니다")
    base_temp = WEATHER_DATA.get(city.lower(), {"temp": 25})["temp"]
    forecasts: List[WeatherForecast] = []
    for i in range(days):
        date = (datetime.now() + timedelta(days=i + 1)).strftime("%Y-%m-%d")
        high_temp = base_temp + random.randint(-3, 3) + random.randint(3, 8)
        low_temp = high_temp - random.randint(5, 12)
        forecasts.append(
            WeatherForecast(
                city=city,
                date=date,
                high_temp=high_temp,
                low_temp=low_temp,
                condition=random.choice(WEATHER_CONDITIONS),
                rain_chance=random.randint(0, 100),
            )
        )
    return forecasts


@app.get("/weather/current/{city}")
async def get_current_conditions(city: str):
    weather = await get_weather(city)
    return {
        "city": weather.city,
        "temperature": f"{weather.temperature}°C",
        "condition": weather.condition,
        "summary": f"{weather.city}은 현재 {weather.temperature}도, {weather.condition}입니다.",
    }


