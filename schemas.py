from pydantic import BaseModel


class Credentials(BaseModel):
    access_token: str


class RegisterInfo(BaseModel):
    email: str
    password: str
    platform: str


class LoginInfo(BaseModel):
    email: str
    password: str


class AdditionalInfo(BaseModel):
    name: str
    phone_number: str = None
    occupation: str = None


class PostCreate(BaseModel):
    title: str
    body: str
