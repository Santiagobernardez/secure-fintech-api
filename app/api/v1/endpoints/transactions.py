"""
api/v1/endpoints/transactions.py

Transaction endpoints — ALL routes require a valid JWT.
The `CurrentUser` dependency (injected via Depends) acts as the auth gate:
if the token is missing or invalid, the request is rejected before any
business logic runs.

Financial logic:
  - Amounts are validated as positive Decimal values (no floats)
  - Transactions are immutable after creation (no PUT/DELETE endpoints)
  - Each user can only read their own transactions (row-level isolation)
"""

import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import CurrentUser, get_current_user
from app.db.session import get_db
from app.models.transaction import Transaction, TransactionStatus
from app.schemas.transaction import TransactionCreate, TransactionList, TransactionResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/",
    response_model=TransactionList,
    summary="List transactions for the authenticated user",
    dependencies=[Depends(get_current_user)],  # Explicit auth gate on list endpoint
)
async def list_transactions(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    limit: int = 20,
    offset: int = 0,
) -> TransactionList:
    """
    Return paginated transactions belonging to the authenticated user only.
    Users cannot access other users' transactions (row-level isolation).
    """
    # Clamp limit to prevent DoS via large page requests
    limit = min(limit, 100)

    count_result = await db.execute(
        select(func.count(Transaction.id)).where(Transaction.owner_id == current_user.id)
    )
    total = count_result.scalar_one()

    result = await db.execute(
        select(Transaction)
        .where(Transaction.owner_id == current_user.id)
        .order_by(Transaction.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    items = result.scalars().all()

    return TransactionList(total=total, items=items)


@router.get(
    "/{transaction_id}",
    response_model=TransactionResponse,
    summary="Get a single transaction by ID",
)
async def get_transaction(
    transaction_id: UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> Transaction:
    """
    Fetch a specific transaction.
    Returns HTTP 404 if the transaction does not belong to the authenticated user
    (avoids leaking whether the record exists at all — IDOR protection).
    """
    result = await db.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.owner_id == current_user.id,  # Row-level ownership check
        )
    )
    txn = result.scalar_one_or_none()

    if txn is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    return txn


@router.post(
    "/",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a new transaction",
)
async def create_transaction(
    payload: TransactionCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> Transaction:
    """
    Create a new transaction record linked to the authenticated user.
    Status is set to COMPLETED immediately (simplified model).
    In production, PENDING → COMPLETED would be handled by an async worker.
    """
    txn = Transaction(
        owner_id=current_user.id,
        transaction_type=payload.transaction_type,
        status=TransactionStatus.COMPLETED,
        amount=payload.amount,
        currency=payload.currency,
        description=payload.description,
        reference_id=payload.reference_id or None,  # Falls back to model default
        processed_at=datetime.now(timezone.utc),
    )

    db.add(txn)
    await db.flush()
    await db.refresh(txn)

    logger.info(
        "Transaction created: id=%s type=%s amount=%s user=%s",
        txn.id, txn.transaction_type, txn.amount, current_user.email,
    )
    return txn
