"""Endpoints CRUD y resumen para obligaciones financieras."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.financial_account import FinancialAccount
from ..schemas.financial_account import (
    FinancialAccountCreate,
    FinancialAccountRead,
    FinancialAccountsSummary,
    FinancialAccountUpdate,
)
from ..services.clock import bogota_today
from ..services.financial_accounts import account_to_read, build_accounts_summary

router = APIRouter(prefix="/financial-accounts", tags=["Tarjetas y préstamos"])


def get_or_404(db: Session, account_id: int) -> FinancialAccount:
    account = db.get(FinancialAccount, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Cuenta financiera no encontrada")
    return account


@router.get("/summary", response_model=FinancialAccountsSummary)
def accounts_summary(db: Session = Depends(get_db)) -> FinancialAccountsSummary:
    return build_accounts_summary(db, bogota_today())


@router.get("", response_model=list[FinancialAccountRead])
def list_accounts(db: Session = Depends(get_db)) -> list[FinancialAccountRead]:
    accounts = list(db.scalars(select(FinancialAccount).order_by(FinancialAccount.id)).all())
    today = bogota_today()
    return [account_to_read(account, today) for account in accounts]


@router.post("", response_model=FinancialAccountRead, status_code=status.HTTP_201_CREATED)
def create_account(
    payload: FinancialAccountCreate, db: Session = Depends(get_db)
) -> FinancialAccountRead:
    account = FinancialAccount(**payload.model_dump())
    db.add(account)
    db.commit()
    db.refresh(account)
    return account_to_read(account, bogota_today())


@router.get("/{account_id}", response_model=FinancialAccountRead)
def get_account(account_id: int, db: Session = Depends(get_db)) -> FinancialAccountRead:
    return account_to_read(get_or_404(db, account_id), bogota_today())


@router.put("/{account_id}", response_model=FinancialAccountRead)
def update_account(
    account_id: int,
    payload: FinancialAccountUpdate,
    db: Session = Depends(get_db),
) -> FinancialAccountRead:
    account = get_or_404(db, account_id)
    for key, value in payload.model_dump().items():
        setattr(account, key, value)
    db.commit()
    db.refresh(account)
    return account_to_read(account, bogota_today())


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(account_id: int, db: Session = Depends(get_db)) -> Response:
    account = get_or_404(db, account_id)
    db.delete(account)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
