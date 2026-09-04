from pydantic import BaseModel, ConfigDict, EmailStr


class SchoolBase(BaseModel):
    code: str
    name: str
    slug: str


class SchoolResponse(SchoolBase):
    id: int
    is_active: bool
    status: str

    model_config = ConfigDict(from_attributes=True)


class SchoolPublicStatusResponse(BaseModel):
    """Unauthenticated - what the login/registration pages may see about a school resolved by
    slug. Identity and status only: enough to say "pending review" or "not approved" to whoever
    registered it, and nothing about the school's users or data.

    `id` is required, not incidental: this response backs the frontend's useSchool() hook, and the
    student registration form passes school.id to GET /courses/?school_id= to populate its course
    picker. Omitting it shipped a live bug where registration showed "Loading courses…" forever
    with the submit button stuck disabled. It exposes nothing new - the public GET /schools/ list
    already returns ids.
    """
    id: int
    name: str
    slug: str
    status: str
    review_note: str | None = None

    model_config = ConfigDict(from_attributes=True)


class SchoolReviewRequest(BaseModel):
    """Super admin only - approve or reject a pending school signup."""
    status: str
    review_note: str | None = None


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
