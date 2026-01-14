from uuid import UUID
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, status, HTTPException, Path

from src.container import Container
from src.api.schemas.response_schemas.schemas import OrderResponse
from src.api.schemas.request_schemas.schemas import CreateNewOrder
from src.usecase.orders.orders_usecase import OrderUseCase
from src.entity.orders import CreateOrder, OrderId
from src.exceptions import OrderNotFoundError, OrderCreationError, RepositoryError, AppError

router = APIRouter(
    prefix="/api/v1",
    tags=["Сервис заказов"]
)

@router.post(
    "/orders/new/",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED
)
@inject
async def new_order(
        body: CreateNewOrder,
        uc: OrderUseCase = Depends(Provide[Container.usecase.order_usecase])
):
    """
    Endpoint создания заказа.
    """
    payload = CreateOrder(
        user_id=body.user_id,
        products=body.products,
        amount=body.amount
    )

    try:
        result = await uc.create_order(payload)
        return result
    except OrderCreationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) from e
    except (RepositoryError, AppError) as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error: %s" % str(e)
        ) from e


@router.get(
    "/orders/{order_id}/status",
    response_model=OrderResponse,
    status_code=status.HTTP_200_OK
)
@inject
async def get_order_status(
        order_id: UUID = Path(..., description="ID заказа"),
        uc: OrderUseCase = Depends(Provide[Container.usecase.order_usecase])
):
    """
    Endpoint для получения статуса заказа по ID
    """
    try:
        order = await uc.get_order_status(OrderId(order_id))
        return OrderResponse(
            id=order.id,
            status=order.status,
            created_at=order.created_at
        )
    except OrderNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        ) from e
    except (RepositoryError, AppError) as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error: %s" % str(e)
        ) from e
