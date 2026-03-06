from fastapi import APIRouter

api_router = APIRouter()

@api_router.get("/ping", tags=["System"])
async def ping():
    return {
        "message": "Santi's API is 100% alive, connected and responding!",
        "status": "Success"
    }