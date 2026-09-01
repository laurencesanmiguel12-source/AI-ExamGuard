from pydantic import BaseModel, ConfigDict, EmailStr


class SchoolBase(BaseModel):
    code: str
    name: str
    slug: str


class SchoolResponse(SchoolBase):
    id: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class SchoolUpdate(BaseModel):
    """Super admin only. Deactivating blocks login for every one of this school's users (except
    other super admins, whose access isn't school-scoped) without deleting any of its data."""
    code: str | None = None
    name: str | None = None
    slug: str | None = None
    is_active: bool | None = None


class SchoolRegisterRequest(BaseModel):
    """Creates a School and its founding Admin account together - the first-ever way to create an
    admin user in this codebase (previously always a raw DB seed, no route existed)."""
    code: str
    name: str
    # Pre-filled client-side from `name` (editable) - the school's login URL, e.g.
    # "arellano-university" for /arellano-university/login.
    slug: str
    email: EmailStr
    password: str
    first_name: str
    last_name: str
