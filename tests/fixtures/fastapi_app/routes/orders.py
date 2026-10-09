from fastapi import APIRouter

router = APIRouter(prefix="/orders")

@router.get("/")
def list_orders():
    return []

@router.post("/")
def create_order():
    return {}

@router.get("/{order_id:int}")
def get_order(order_id: int):
    return {"id": order_id}
