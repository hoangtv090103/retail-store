from fastapi import FastAPI
from app.api.v1.routes_checkout import router as checkout_router

app = FastAPI()

app.include_router(checkout_router)

@app.get("/health")
async def health():
    return {"status": "ok"}
