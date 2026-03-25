"""
db/base.py — Base declarativa de SQLAlchemy para los modelos ORM.

Referencia: data-model.md §Configuración de Base de Datos
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models in the API."""

    pass
