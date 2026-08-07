from pydantic import BaseModel, ConfigDict, EmailStr


class SchoolBase(BaseModel):
    code: str
    name: str
    slug: str


class SchoolResponse(SchoolBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class SchoolRegisterRequest(BaseModel):
    """Creates a School and its founding Admin account together - the first-ever way to create an
    admin user in this codebase (previously always a raw DB seed, no route existed)."""
    code: str
    name: str
    # Pre-filled client-side from `name` (editable) - the school's login URL, e.g.
    # "arellano-university" for /arellano-university/login.
    slug: str
    username: str
    email: EmailStr
    password: str
    first_name: str
    last_name: str
