from __future__ import annotations
import base64
from io import BytesIO
import json
import time
from typing import Any, Dict, List
from dotenv import load_dotenv
from openai import OpenAI
from pdf2image import convert_from_path, convert_from_bytes

load_dotenv()

# ===============================
#  OpenAI client (público)
# ===============================


def get_openai_client() -> OpenAI:
    """Devuelve un cliente OpenAI (usa OPENAI_API_KEY de entorno)."""
    from os import getenv
    return OpenAI(api_key=getenv("OPENAI_API_KEY"))


# ===============================
#  Helpers de post-proceso
# ===============================

def _as_list_of_str(x) -> List[str]:
    """Aplana y convierte a lista de strings cualquier estructura anidada.
    Priorizamos claves típicas (titulo, empresa, etc.) cuando hay objetos.
    """
    out: List[str] = []

    def _walk(v):
        if isinstance(v, (list, tuple, set)):
            for it in v:
                _walk(it)
        elif isinstance(v, dict):
            prefer = []
            for k in (
                "titulo", "puesto", "rol", "cargo",
                "institucion", "centro", "empresa",
                "anio", "desde", "hasta", "periodo",
                "descripcion", "detalle", "skill", "tecnologia", "nivel",
            ):
                if k in v and v[k]:
                    prefer.append(str(v[k]))
            if prefer:
                out.append(" ".join(prefer))
            else:
                out.append(" ".join(str(val) for val in v.values() if val))
        else:
            s = "" if v is None else str(v).strip()
            if s:
                out.append(s)

    _walk(x)
    return out


def _to_text(v) -> str:
    """Convierte cualquier valor en una cadena plana 'a, b, c'."""
    return ", ".join(_as_list_of_str(v))


def _parse_code_fenced_json(content: str) -> Dict[str, Any]:
    """Extrae JSON incluso si viene en ```json ... ``` o con texto alrededor."""
    txt = (content or "").strip()
    if "```json" in txt:
        try:
            txt = txt.split("```json", 1)[1].split("```", 1)[0]
        except Exception:
            pass
    elif "```" in txt:
        try:
            txt = txt.split("```", 1)[1].split("```", 1)[0]
        except Exception:
            pass
    return json.loads(txt.strip())


def sanitize_gpt_payload(d: Dict[str, Any]) -> Dict[str, str]:
    """Normaliza TODO a strings planas, apto para guardar en Mongo."""
    d = d or {}
    return {
        "nombre_completo": _to_text(d.get("nombre_completo", "")),
        "correo_electronico": _to_text(d.get("correo_electronico", "")),
        "numero_de_telefono": _to_text(d.get("numero_de_telefono", "")),
        "formacion_academica": _to_text(d.get("formacion_academica", "")),
        "experiencia_laboral": _to_text(d.get("experiencia_laboral", "")),
        "habilidades_tecnicas": _to_text(d.get("habilidades_tecnicas", "")),
        "idiomas": _to_text(d.get("idiomas", "")),
    }


# ===============================
#  Prompts
# ===============================

SYSTEM_PROMPT = (
    "Eres un extractor de datos de CV. "
    "Devuelve exclusivamente un JSON con las siguientes claves y tipos:\n"
    '{\n'
    '  "nombre_completo": "string",\n'
    '  "correo_electronico": "string",\n'
    '  "numero_de_telefono": "string",\n'
    '  "formacion_academica": ["string", "..."],\n'
    '  "experiencia_laboral": ["string", "..."],\n'
    '  "habilidades_tecnicas": ["string", "..."]\n'
    '  "idiomas": ["string", "..."]\n'
    '}\n'
    "No incluyas comentarios ni texto fuera del JSON. "
    "Si un campo no está, déjalo vacío o con []."
)

USER_INSTRUCTIONS_VISION = (
    "Analiza la(s) imagen(es) del CV y devuelve SOLO el JSON con las claves indicadas. "
    "No agregues texto adicional."
)


# ===============================
#  API pública
# ===============================


def _pil_image_to_b64_jpeg(im) -> str:
    buf = BytesIO()
    im.save(buf, format="JPEG")  # nada a disco
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"


def _build_vision_payload_from_images(imgs) -> List[Dict[str, Any]]:
    content_payload = [{"type": "text", "text": USER_INSTRUCTIONS_VISION}]
    for im in imgs:
        data_url = _pil_image_to_b64_jpeg(im)
        content_payload.append({
            "type": "image_url",
            "image_url": {"url": data_url}
        })
    return content_payload


def reed_cv(archivo_pdf: str, first_page: int = 1, last_page: int = 2, dpi: int = 300) -> Dict[str, str]:

    try:
        imgs = convert_from_path(archivo_pdf, dpi=dpi,
                                 first_page=first_page, last_page=last_page)
        if not imgs:
            raise RuntimeError("No se pudieron generar imágenes del PDF.")

        content_payload = _build_vision_payload_from_images(imgs)
        client = get_openai_client()
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": SYSTEM_PROMPT},
                      {"role": "user", "content": content_payload}],
            temperature=0,
        )
        content = resp.choices[0].message.content
        data = _parse_code_fenced_json(content)
        return sanitize_gpt_payload(data)

    except Exception as e:
        print(f"❌ Error en reed_cv: {e}")
        return {
            "nombre_completo": "",
            "correo_electronico": "",
            "numero_de_telefono": "",
            "formacion_academica": "",
            "experiencia_laboral": "",
            "habilidades_tecnicas": "",
            "idiomas": "",
        }


def build_cv_text_from_gpt(analisis: Dict[str, Any]) -> str:
    """Construye el *texto para embeddings* usando SOLO lo relevante extraído por GPT:
    formación + experiencia + habilidades. Reduce ruido para mejorar similitud.
    """
    if not analisis:
        return ""
    partes = [
        _to_text(analisis.get("formacion_academica", "")),
        _to_text(analisis.get("experiencia_laboral", "")),
        _to_text(analisis.get("habilidades_tecnicas", "")),
        _to_text(analisis.get("idiomas", "")),
    ]
    return " \n".join([p for p in partes if p]).strip()


def _build_vision_payload_from_images(imgs) -> List[Dict[str, Any]]:
    """Arma el payload de Vision usando una lista de PIL.Image."""
    content_payload = [{"type": "text", "text": USER_INSTRUCTIONS_VISION}]
    for idx, im in enumerate(imgs):
        fname = f"_cv_{int(time.time())}_{idx+1}.jpg"
        im.save(fname, "JPEG")
        with open(fname, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        content_payload.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
        })
    return content_payload


def reed_cv_bytes(pdf_bytes: bytes, first_page: int = 1, last_page: int = 2, dpi: int = 300) -> Dict[str, str]:
    """Convierte las primeras páginas del PDF (en bytes) a imágenes y usa GPT-4o Visión."""
    try:
        imgs = convert_from_bytes(
            pdf_bytes, dpi=dpi, first_page=first_page, last_page=last_page)
        if not imgs:
            raise RuntimeError(
                "No se pudieron generar imágenes del PDF (bytes).")

        content_payload = _build_vision_payload_from_images(imgs)

        client = get_openai_client()
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": content_payload},
            ],
            temperature=0,
        )
        content = resp.choices[0].message.content
        data = _parse_code_fenced_json(content)
        return sanitize_gpt_payload(data)

    except Exception as e:
        print(f"❌ Error en reed_cv_bytes: {e}")
        return {
            "nombre_completo": "",
            "correo_electronico": "",
            "numero_de_telefono": "",
            "formacion_academica": "",
            "experiencia_laboral": "",
            "habilidades_tecnicas": "",
            "idiomas": "",
        }
