"""Schemas Pydantic para autenticación."""

from __future__ import annotations

import re
import uuid

from pydantic import BaseModel, EmailStr, field_validator

from app.schemas.phone import validate_ar_phone

PASSWORD_REGEX_LETTER = re.compile(r"[A-Za-z]")
PASSWORD_REGEX_DIGIT = re.compile(r"\d")


def _validate_password(v: str) -> str:
    if len(v) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres")
    if len(v.encode("utf-8")) > 72:
        raise ValueError("La contraseña no puede superar 72 bytes UTF-8")
    if not PASSWORD_REGEX_LETTER.search(v):
        raise ValueError("La contraseña debe contener al menos una letra")
    if not PASSWORD_REGEX_DIGIT.search(v):
        raise ValueError("La contraseña debe contener al menos un dígito")
    return v


class RegistroIn(BaseModel):
    email: EmailStr
    password: str
    nombre: str
    telefono: str
    obra_social: str | None = None

    @field_validator("email")
    @classmethod
    def _norm_email(cls, v: str) -> str:
        return str(v).strip().lower()

    @field_validator("password")
    @classmethod
    def _pw(cls, v: str) -> str:
        return _validate_password(v)

    @field_validator("telefono")
    @classmethod
    def _tel(cls, v: str) -> str:
        return validate_ar_phone(v)

    @field_validator("nombre")
    @classmethod
    def _nombre(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El nombre es obligatorio")
        return v


class LoginIn(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def _norm_email(cls, v: str) -> str:
        return str(v).strip().lower()


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserOut(BaseModel):
    id: uuid.UUID
    email: str | None = None
    rol: str
    nombre: str | None = None
    telefono: str | None = None


class RefreshOut(BaseModel):
    ok: bool = True
