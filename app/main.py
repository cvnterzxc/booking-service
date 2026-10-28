from fastapi import FastAPI

app = FastAPI(title="Booking Service", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
