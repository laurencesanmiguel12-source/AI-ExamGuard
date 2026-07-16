from app.auth.jwt import create_access_token, verify_access_token

payload = {
    "sub": "1",
    "email": "admin@test.com",
    "role": "Admin"
}

token = create_access_token(payload)

print("TOKEN")
print(token)

decoded = verify_access_token("this_is_not_a_real_token")

print("\nDECODED")
print(decoded)