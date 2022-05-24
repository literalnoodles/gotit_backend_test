from pydoc import plain
import jwt
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import RedirectResponse
from passlib.context import CryptContext
from playhouse.shortcuts import model_to_dict
from exception import RequiresExtraInfoException
from models import User
from datetime import datetime, timedelta


class AuthHandler():
    security = HTTPBearer()
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    secret = "SECRET"

    def encode_token(self, user_email):
        payload = {
            "exp": datetime.utcnow() + timedelta(days=0, minutes=300),
            "iat": datetime.utcnow(),
            "sub": user_email
        }

        return jwt.encode(
            payload,
            self.secret,
            algorithm="HS256"
        )

    def decode_token(self, token):
        try:
            payload = jwt.decode(token, self.secret, algorithms=['HS256'])
            user = (User.select()
                        .where(User.email == payload['sub'])
                        .first())
            if not user:
                raise HTTPException(status_code=401, detail="User not exists")
            self.user = user
            return model_to_dict(user)
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail='Expired token')
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

    def auth_wrapper(
            self,
            auth: HTTPAuthorizationCredentials = Security(security)):
        return self.decode_token(auth.credentials)

    def verify_information(
            self,
            auth: HTTPAuthorizationCredentials = Security(security)):
        if not self.user:
            self.user = self.decode_token(auth.credentials)
        # if not add extra information -> redirect to form
        if not self.user.name:
            raise RequiresExtraInfoException
