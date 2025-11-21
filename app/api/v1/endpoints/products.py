from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get_products():
    return {"message": "Products endpoint"}

@router.post("/")
async def create_product():
    return {"message": "Create product"}