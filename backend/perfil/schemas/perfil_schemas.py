# perfil/schemas/perfil_schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional


class PerfilCreate(BaseModel):
    usuario: Optional[str] = Field(
        default=None, description="owner user id/email")
    puesto: str
    educacion: List[str] = []
    atributos: List[str] = []
    experiencia: List[str] = []
    idiomas: List[str] = []
    edad: int
    activo: bool = False
    publicado: bool = False


class PerfilOut(BaseModel):
    id: str
    owner: Optional[str]
    puesto: str
    educacion: List[str] = Field(default_factory=list)
    atributos: List[str] = Field(default_factory=list)
    experiencia: List[str] = Field(default_factory=list)
    idiomas: List[str] = Field(default_factory=list)
    edad: int
    perfil: str
    vector: List[float]
    activo: bool
    publicado: bool
    timestamp: float
