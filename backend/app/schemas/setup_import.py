from pydantic import BaseModel


class SetupImportRowError(BaseModel):
    """One row that could not be imported. `row` is the line number in the uploaded file, header
    included, so an admin can go straight to it in their spreadsheet."""
    row: int
    message: str


class SetupImportResponse(BaseModel):
    created_courses: int = 0
    created_subjects: int = 0
    created_instructors: int = 0
    # Rows whose record already existed. Reported separately from errors on purpose: re-uploading
    # a sheet after adding a few rows is a normal thing to do, not a mistake.
    skipped_existing: int = 0
    errors: list[SetupImportRowError] = []
    # True when this run was a dry run and nothing was written. The counts mean "would create"
    # rather than "created", and the UI has to say so - a preview that reads like a receipt is
    # worse than no preview, because it leaves someone believing the import already happened.
    preview: bool = False
