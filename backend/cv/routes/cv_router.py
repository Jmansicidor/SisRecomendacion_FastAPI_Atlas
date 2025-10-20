# cv/routes/cv_router.py
from io import BytesIO
from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException, Query
from cv.schemas.cv_schemas import CVCreate, CVOut, CVProfileUpdate, CVWithAnalysisOut
from cv.services.cv_service import actualizar_perfil_usuario, guardar_cv, obtener_cv_por_email, count_cv, cargar_cv, resubir_cv
from core.database import get_db
from fastapi.responses import StreamingResponse

cv_router = APIRouter(prefix="/cv", tags=["cv"])


@cv_router.post("/", response_model=dict)
async def crear_cv(
    # JSON string con al menos firstname, lastname, mail
    meta: str = Form(...),
    file: UploadFile = File(...),
    db=Depends(get_db)
):
    try:
        payload = CVCreate.model_validate_json(meta)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"meta inválido: {e}")

    file_bytes = await file.read()
    cv_id, err = await guardar_cv(db, file_bytes, payload.model_dump())
    if err:
        raise HTTPException(status_code=400, detail=err)
    return {"id": cv_id}


@cv_router.get("/by-email", response_model=CVOut | CVWithAnalysisOut | dict)
async def get_cv_by_email(
    email: str,
    full: bool = Query(False),
    db=Depends(get_db),
):
    doc = await obtener_cv_por_email(db, email)
    if not doc:
        return {}

    if not full:
        return CVOut(
            id=str(doc["_id"]),
            nombre=doc.get("nombre", ""),
            apellido=doc.get("apellido", ""),
            ciudad=doc.get("ciudad", ""),
            direccion=doc.get("direccion", ""),
            email=doc.get("email", ""),
            cv_file_id=doc.get("cv_file_id"),
        )
    return CVWithAnalysisOut(
        id=str(doc["_id"]),
        nombre=doc.get("nombre", ""),
        apellido=doc.get("apellido", ""),
        ciudad=doc.get("ciudad", ""),
        direccion=doc.get("direccion", ""),
        email=doc.get("email", ""),
        cv_file_id=doc.get("cv_file_id"),
        fecha_nacimiento=doc.get("fecha_nacimiento"),
        edad=doc.get("edad"),
        timestamp=float(doc.get("timestamp", 0.0)),
        cv_analisis_gpt=doc.get("cv_analisis_gpt") or {},
    )


@cv_router.get("/file/{file_id}")
async def download_file(file_id: str, inline: bool = False, db=Depends(get_db)):
    data, filename = await cargar_cv(db, file_id)
    if not data:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    mode = "inline" if inline else "attachment"
    headers = {"Content-Disposition": f'{mode}; filename="{filename}"'}
    return StreamingResponse(BytesIO(data), media_type="application/pdf", headers=headers)


@cv_router.get("/file/by-email")
async def download_by_email(email: str, inline: bool = False, db=Depends(get_db)):
    doc = await obtener_cv_por_email(db, email)
    if not doc or not doc.get("cv_file_id"):
        raise HTTPException(
            status_code=404, detail="CV no encontrado para ese email")
    data, filename = await cargar_cv(db, doc["cv_file_id"])
    if not data:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    mode = "inline" if inline else "attachment"
    headers = {"Content-Disposition": f'{mode}; filename="{filename}"'}
    return StreamingResponse(BytesIO(data), media_type="application/pdf", headers=headers)


@cv_router.get("/count")
async def count_curriculums(db=Depends(get_db)):
    n = await count_cv(db)
    return {"count": n}


@cv_router.put("/profile", response_model=dict)
async def update_profile(body: CVProfileUpdate, db=Depends(get_db)):
    ok, err = await actualizar_perfil_usuario(db, body.email, body.model_dump(exclude_none=True))
    if not ok:
        raise HTTPException(
            status_code=400, detail=err or "No se pudo actualizar el perfil")
    return {"ok": True}

# Re-subir CV (reemplazo o historial)


@cv_router.post("/reupload", response_model=dict)
async def reupload_cv(
    email: str = Form(...),
    keep_history: bool = Form(False),
    file: UploadFile = File(...),
    db=Depends(get_db)
):
    new_bytes = await file.read()
    doc_id, err = await resubir_cv(db, email, new_bytes, keep_history=keep_history)
    if err:
        raise HTTPException(status_code=400, detail=err)
    return {"id": doc_id, "keep_history": keep_history}
