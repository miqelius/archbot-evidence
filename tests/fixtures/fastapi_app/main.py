from fastapi import FastAPI
from routes.orders import router as orders_router
from routes.legacy import router as legacy_router

app = FastAPI()
app.include_router(orders_router, prefix="/api/v1")
app.include_router(legacy_router)

@app.get("/health")
def health():
    return {"ok": True}
