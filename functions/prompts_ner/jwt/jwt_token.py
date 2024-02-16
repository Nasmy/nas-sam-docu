""" JWT related functions"""
from typing import Union
from datetime import datetime, timedelta
from jose import JWTError, jwt


class JWT:
    """contains JWT related functions"""

    def __init__(self):
        self.secret_key = "74192c43d038bdc5d11a354d6c950ddb5d1fe6a2c21a122fbb10f3e2eeb49cd9"
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 1440

    def create_access_token(self, data: dict):
        """Create a JWT with expiration"""
        expires_delta = timedelta(minutes=self.access_token_expire_minutes)

        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        issued_at = datetime.utcnow()
        to_encode.update({"exp": expire, "iat": issued_at})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def decode_jwt(self, token):
        return jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
