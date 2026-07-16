from app.auth.jwt import create_access_token, decode_access_token

token = create_access_token(
    {
        "sub": "laurence@test.com"
    }
)

print(token)

payload = decode_access_token(token)

print(payload)