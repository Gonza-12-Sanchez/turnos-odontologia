"""Validador de teléfono AR en capa de aplicación (Pydantic), D-08."""

from __future__ import annotations

import re

from pydantic import BaseModel, field_validator

AR_PHONE_REGEX = re.compile(r"^\+54\s?9?\s?\d{2,4}[\s-]?\d{6,8}$")


def validate_ar_phone(value: str) -> str:
    if not AR_PHONE_REGEX.match(value):
        raise ValueError("Teléfono con formato AR inválido")
    return value


class ArPhoneModel(BaseModel):
    telefono: str

    @field_validator("telefono")
    @classmethod
    def _validate_telefono(cls, v: str) -> str:
        return validate_ar_phone(v)
