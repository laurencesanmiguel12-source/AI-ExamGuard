from fastapi import APIRouter
from sqlalchemy import text

from app.core.database import engine

router = APIRouter()


@router.get("/database")
def database_test():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    return {
        "database": "connected"
    }