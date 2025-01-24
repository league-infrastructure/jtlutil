import jwt
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
from datetime import datetime, timedelta, timezone

def encrypt_token(token, encryption_key):
    cipher = AES.new(encryption_key, AES.MODE_CBC)
    iv = cipher.iv
    encrypted_token = cipher.encrypt(pad(token.encode(), AES.block_size))
    return base64.b64encode(iv + encrypted_token).decode()

def generate_encrypted_jwt(token, secret_key, encryption_key):
    # Encrypt the token
    encrypted_token = encrypt_token(token, encryption_key)

    # Create JWT payload with encrypted token and expiration
    payload = {
        'data': encrypted_token,
        'exp': datetime.now(timezone.utc) + timedelta(hours=1)  # Set expiration to 1 hour
    }

    # Sign the JWT using the secret key
    jwt_token = jwt.encode(payload, secret_key, algorithm='HS256')
    return jwt_token



def decrypt_token(encrypted_token_b64, encryption_key):
    encrypted_token_bytes = base64.b64decode(encrypted_token_b64)
    iv = encrypted_token_bytes[:16]  # Extract the IV (first 16 bytes)
    encrypted_token = encrypted_token_bytes[16:]  # Encrypted message after the IV
    cipher = AES.new(encryption_key, AES.MODE_CBC, iv)
    decrypted_token = unpad(cipher.decrypt(encrypted_token), AES.block_size)
    return decrypted_token.decode()

def verify_and_decrypt_jwt(jwt_token, secret_key, encryption_key):
    try:
        # Verify the JWT signature and get the payload
        payload = jwt.decode(jwt_token, secret_key, algorithms=['HS256'])

        # Extract the encrypted token from the payload
        encrypted_token = payload['data']

        # Decrypt the encrypted token
        decrypted_token = decrypt_token(encrypted_token, encryption_key)
        return decrypted_token
    except jwt.ExpiredSignatureError:
        return "Token has expired", 401
    except jwt.InvalidTokenError:
        return "Invalid token", 401


