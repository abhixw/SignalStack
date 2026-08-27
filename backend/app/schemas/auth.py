from pydantic import BaseModel, EmailStr, Field
from typing import Optional
import datetime


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: Optional[str] = None
    role: str = "candidate"  # self-registration only allows candidate/recruiter; admin is provisioned separately


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    full_name: Optional[str] = None
    github_username: Optional[str] = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6)
    new_password: str = Field(min_length=8)


class MessageResponse(BaseModel):
    message: str


class GithubOtpVerifyRequest(BaseModel):
    pending_token: str
    otp: str = Field(min_length=6, max_length=6)


class GithubOtpVerifyResponse(BaseModel):
    access_token: Optional[str] = None
    token_type: str = "bearer"
    connected: bool = False


class GithubEmailConfirmRequest(BaseModel):
    pending_token: str
    email: EmailStr
    github_username: str = Field(min_length=1)


class CandidateRegisterStart(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: Optional[str] = None
    github_username: str = Field(min_length=1)
