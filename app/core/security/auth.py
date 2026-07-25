from datetime import datetime, timedelta
from uuid6 import uuid7
from fastapi import HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from app.config import settings
import hashlib
from app.models.auth.refresh import RefreshToken
from user_agents import parse

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v2.5/token")


class TokenManager:

    def __init__(self, secret_key: str, algorithm: str):
        self.secret_key = secret_key
        self.algorithm = algorithm


    def create_token(self, data: dict, expires_delta: timedelta) -> str:
        payload = data.copy()

        expire = datetime.utcnow() + expires_delta

        payload.update({
            "exp": expire,
            "iat": datetime.utcnow(), # Issued at(iat)
            "jti": str(uuid7()), # jwt token ID(jti), even tokens have ids
            "iss": "auth-api" # Issuer(service or any api) - iss
        })

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)


    def create_access_token(self, user_id: str) -> str:
        return self.create_token(
            {"sub": user_id, "type": "access"},
            timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )


    def create_refresh_token(self, user_id: str) -> str:
        return self.create_token(
            {"sub": user_id, "type": "refresh"},
            timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        )

    def decode_token(self, token: str) -> dict:
        try:
            return jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                issuer="auth-api"
            )

        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")

        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")


    def verify_token_type(self, payload: dict, expected_type: str) -> dict:
        if payload.get("type") != expected_type:
            raise HTTPException(status_code=401, detail="Invalid token type")

        return payload



token_manager = TokenManager(settings.SECRET_KEY, settings.ALGORITHM)