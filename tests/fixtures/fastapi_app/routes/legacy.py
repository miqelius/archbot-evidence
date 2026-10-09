from fastapi import APIRouter

router = APIRouter(prefix="/legacy")

@router.api_route("/ping", methods=["GET", "POST"])
def ping():
    return "pong"
