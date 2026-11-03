from pydantic import BaseModel, Field


class OrderCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=100)
    quantity: int = Field(gt=0, le=10000)


class OrderResponse(BaseModel):
    id: str
    sku: str
    quantity: int
    status: str
