from app.schemas.auth import RegisterRequest, LoginRequest
from app.schemas.user import UserResponse

print("========== REGISTER REQUEST ==========")

register = RegisterRequest(
    email="student@test.com",
    password="password123",
    first_name="John",
    last_name="Doe",
    role_id=3
)

print(register)

print("\n========== LOGIN REQUEST ==========")

login = LoginRequest(
    email="student@test.com",
    password="password123"
)

print(login)

print("\n========== USER RESPONSE ==========")

user = UserResponse(
    id=1,
    email="student@test.com",
    first_name="John",
    last_name="Doe",
    role="Student",
    is_active=True
)

print(user)