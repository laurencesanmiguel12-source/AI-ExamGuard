from pydantic import BaseModel


class CSVImportRowError(BaseModel):
    row: int
    message: str


class CSVImportResponse(BaseModel):
    created: int
    errors: list[CSVImportRowError] = []
