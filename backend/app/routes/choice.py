from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.choice import (
    ChoiceCreate,
    ChoiceUpdate,
    ChoiceResponse
)
from app.services.choice_service import ChoiceService

router = APIRouter(
    prefix="/choices",
    tags=["Choices"]
)


@router.post(
    "",
    response_model=ChoiceResponse
)
def create_choice(
    request: ChoiceCreate,
    db: Session = Depends(get_db)
):
    return ChoiceService.create(request, db)


@router.get(
    "",
    response_model=list[ChoiceResponse]
)
def get_choices(
    db: Session = Depends(get_db)
):
    return ChoiceService.get_all(db)


@router.get(
    "/{choice_id}",
    response_model=ChoiceResponse
)
def get_choice(
    choice_id: int,
    db: Session = Depends(get_db)
):
    return ChoiceService.get_by_id(choice_id, db)


@router.put(
    "/{choice_id}",
    response_model=ChoiceResponse
)
def update_choice(
    choice_id: int,
    request: ChoiceUpdate,
    db: Session = Depends(get_db)
):
    return ChoiceService.update(choice_id, request, db)


@router.delete(
    "/{choice_id}"
)
def delete_choice(
    choice_id: int,
    db: Session = Depends(get_db)
):
    return ChoiceService.delete(choice_id, db)