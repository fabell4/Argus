from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Argus API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "argus-backend"}


@app.get("/api/v1/power/summary", tags=["power"])
def power_summary() -> dict[str, float]:
    return {
        "daily_kwh": 24.7,
        "weekly_kwh": 168.3,
        "monthly_kwh": 721.4,
    }
