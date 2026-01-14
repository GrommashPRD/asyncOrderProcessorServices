from pydantic import BaseModel, Field, field_validator

class Product(BaseModel):
    """
    Модель товара в заказе
    """
    product_id: str = Field(..., min_length=1, description="ID товара")
    quantity: int = Field(..., gt=0, description="Количество товара")


class CreateNewOrder(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=255, description="ID клиента")
    products: list[Product] = Field(
        ...,
        min_length=1,
        description="Список товаров в заказе"
    )
    amount: str = Field(..., min_length=1, max_length=255, description="Сумма заказа")
