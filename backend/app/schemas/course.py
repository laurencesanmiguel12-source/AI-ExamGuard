from pydantic import BaseModel, ConfigDict


class CourseBase(BaseModel):
    code: str
    name: str


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    code: str | None = None
    name: str | None = None


class CourseResponse(CourseBase):
    id: int
    school_id: int

    model_config = ConfigDict(from_attributes=True)