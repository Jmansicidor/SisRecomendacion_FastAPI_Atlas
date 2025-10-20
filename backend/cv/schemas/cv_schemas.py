# cv/schemas/cv_schemas.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import date


class CVCreate(BaseModel):
    firstname: str
    lastname: str
    city: str
    address: str
    mail: EmailStr
    extracted_data: Dict[str, Any] = {}
    fecha_nacimiento: Optional[date] = None
    edad: Optional[int] = None
    cv_text: Optional[str] = None
    cv_vector: Optional[List[float]] = None
    tokens_formacion: Optional[List[str]] = None
    tokens_habilidades: Optional[List[str]] = None
    tokens_experiencia: Optional[List[str]] = None


class CVOut(BaseModel):
    id: str
    nombre: str
    apellido: str
    ciudad: str
    direccion: str
    email: EmailStr
    cv_file_id: Optional[str] = None


class CVWithAnalysisOut(BaseModel):
    id: str
    nombre: str
    apellido: str
    ciudad: str
    direccion: str
    email: EmailStr
    cv_file_id: Optional[str] = None
    fecha_nacimiento: Optional[str] = None
    edad: Optional[int] = None
    timestamp: float
    cv_analisis_gpt: Dict[str, Any] = {}


class CVProfileUpdate(BaseModel):    
    email: EmailStr = Field(...,
                            description="Email del usuario dueño del perfil")
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    ciudad: Optional[str] = None
    direccion: Optional[str] = None
    fecha_nacimiento: Optional[str] = None  # ISO string (yyyy-mm-dd)
    edad: Optional[int] = None
