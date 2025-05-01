# import jwt

# token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyIiwidHlwZSI6ImFjY2VzcyIsInVzZXJfaWQiOjIsImlhdCI6MTc0Njg4Njc0NSwiZXhwIjoxNzQ2ODg3NjQ1fQ.og4Id_EMpaNUtuVsZ0vzmVy2Jg2s-05iQQ8Y_6bPTF4"  # Hypothetical corrected token
# try:
#     decoded = jwt.decode(token, options={"verify_signature": False})
#     print(decoded)
# except Exception as e:
#     print("Invalid token:", e)
import jwt
from backend.jwt_utils import generate_token

token = generate_token(2, 'access')
print(jwt.decode(token, options={"verify_signature": False}))