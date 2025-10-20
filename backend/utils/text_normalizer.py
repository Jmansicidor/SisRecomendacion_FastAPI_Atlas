# utils/text_normalizer.py
import re
import unicodedata
import difflib

try:
    from rapidfuzz.fuzz import partial_ratio as _fuzzy_ratio
except Exception:
    def _fuzzy_ratio(a: str, b: str) -> int:
        return int(difflib.SequenceMatcher(None, a, b).ratio() * 100)

# ================================================================
# 📘 DICCIONARIO DE ABREVIATURAS COMUNES EN CV
# ================================================================
ABREVIATURAS = {
    # Profesiones y títulos
    "lic": "licenciado", "lic.": "licenciado", "licda": "licenciada", "licda.": "licenciada", "lic": "licenciada",
    "ing": "ingeniero", "ing.": "ingeniero", "ingra": "ingeniera", "ingra.": "ingeniera", "ing": "ingeniera",
    "tec": "tecnico", "tec.": "tecnico", "tecn.": "tecnico", "téc.": "tecnico", "tec": "tecnica", "tec.": "tecnica", "tecn.": "tecnica", "téc.": "tecnica",
    "prof": "profesor", "prof.": "profesor", "dra": "doctora", "dr": "doctor", "dr.": "doctor", "prof": "profesora", "prof.": "profesora", "dr": "doctora",
    "cont": "contador", "cont.": "contador", "contad.": "contador", "ctdor": "contador",
    "adm": "administracion", "adm.": "administracion", "admvo": "administrativo", "admva": "administrativa",
    "coord": "coordinador", "coord.": "coordinador", "sup": "supervisor", "supv": "supervisor",
    "ger": "gerente", "dir": "director", "dir.": "director", "jef": "jefe", "asist": "asistente",

    # Áreas y departamentos
    "rrhh": "recursos humanos", "rh": "recursos humanos",
    "fin": "finanzas", "fin.": "finanzas",
    "contab": "contabilidad", "compras.": "compras",
    "mkt": "marketing", "mk": "marketing",
    "com": "comercial", "ventas.": "ventas", "log": "logistica",
    "prod": "produccion", "sist": "sistemas", "it": "tecnologia",
    "qa": "aseguramiento de calidad", "qa/qc": "control de calidad",

    # Educación
    "sec": "secundario", "sec.": "secundario",
    "prim": "primario", "prim.": "primario", "prim": "primaria", "prim.": "primaria",
    "univ": "universidad", "univ.": "universidad",
    "uni": "universidad", "univ": "universidad", "u.": "universidad",
    "fac": "facultad", "inst": "instituto", "inst.": "instituto",

    # Idiomas y certificaciones
    "ingl": "ingles", "inglés": "ingles", "ing": "ingles", "esp": "espanol", "fr": "frances",
    "toefl": "toefl", "ielts": "ielts", "b2": "ingles intermedio", "c1": "ingles avanzado",

    # Informática / Tecnología
    "prog": "programacion", "dev": "desarrollador", "soft": "software", "app": "aplicacion",
    "db": "base de datos", "bd": "base de datos", "sqlsrv": "sql server",
    "js": "javascript", "ts": "typescript", "py": "python", "cs": "csharp",
    "hr": "human resources", "ux": "experiencia de usuario", "ui": "interfaz de usuario",
    "itil": "itil", "aws": "amazon web services", "gcp": "google cloud",
    "api": "interfaz de programacion", "erp": "planificacion de recursos empresariales",
    "crm": "gestion de relaciones con clientes", "excel": "office", "word": "office", "powerpoint": "office",
    "oficce": "Excel", "Oficce": "Word", "Ppt": "PowerPoint",
    # Lugares
    "bsas": "buenos aires", "caba": "ciudad autonoma de buenos aires",
    "arg": "argentina", "mx": "mexico", "mx.": "mexico", "esp": "espana",

    # Estudios
    "mat": "materia", "carr": "carrera", "post": "posgrado", "maestr": "maestria",
    "dip": "diplomatura", "cap": "capacitacion", "tecnicatura": "tecnico", "tecnicatura": "tecnica",
    "tecnico": "tecnicatura", "tecnica": "tecnicatura", "superior": "tecnicatura",
    # Otros
    "exp": "experiencia", "ref": "referencia", "cv": "curriculum vitae",
}

# ================================================================
# 📗 SINÓNIMOS (para agrupar variantes semánticas)
# ================================================================
SINONIMOS = {
    # Recursos Humanos
    "rrhh": "recursos humanos", "humanos": "recursos humanos",
    "seleccion": "reclutamiento", "recruiting": "reclutamiento",
    "reclutador": "reclutamiento", "headhunter": "reclutamiento",
    "talento": "recursos humanos", "nomina": "recursos humanos",

    # Tecnología / Programación
    "backend": "backend", "servidor": "backend", "api": "backend",
    "frontend": "frontend", "ui": "frontend", "ux": "frontend",
    "fullstack": "fullstack", "web": "fullstack",
    "dev": "desarrollador", "developer": "desarrollador",
    "programador": "desarrollador", "programadora": "desarrollador",
    "software": "desarrollo de software", "apps": "aplicaciones",
    "sistemas": "tecnologia", "informatico": "tecnologia",
    "qa": "calidad", "tester": "calidad",
    "data": "datos", "bigdata": "datos", "etl": "datos",
    "ml": "machine learning", "ia": "inteligencia artificial",
    "dl": "deep learning", "ai": "inteligencia artificial",
    "sql": "base de datos", "postgres": "base de datos", "mysql": "base de datos",
    "mongo": "base de datos", "nosql": "base de datos",

    # Educación
    "profesorado": "docencia", "docente": "docencia", "enseñanza": "docencia",
    "formador": "docencia", "educador": "docencia",
    "estudiante": "alumno", "alumna": "alumno",

    # Finanzas / Administración
    "adm": "administracion", "administrativo": "administracion",
    "contable": "contabilidad", "financiero": "finanzas",
    "presupuestos": "finanzas", "tesoreria": "finanzas",
    "facturacion": "administracion", "pago": "finanzas",

    # Logística / Producción
    "logistica": "logistica", "supply": "logistica",
    "almacen": "logistica", "inventario": "logistica",
    "produccion": "produccion", "fabricacion": "produccion",
    "planta": "produccion",

    # Marketing / Ventas
    "mkt": "marketing", "marketing": "marketing",
    "ventas": "ventas", "comercial": "ventas",
    "promocion": "marketing", "publicidad": "marketing",
    "community": "marketing", "social": "marketing",
    "branding": "marketing", "seo": "marketing", "sem": "marketing",

    # Idiomas
    "ingles": "ingles", "english": "ingles",
    "espanol": "espanol", "spanish": "espanol",
    "frances": "frances", "french": "frances",
    "portugues": "portugues", "portuguese": "portugues",

    # General
    "experiencia": "experiencia", "trayectoria": "experiencia",
    "referencias": "referencia", "contacto": "referencia",
    "analista": "analista", "consultor": "consultor",
    "consultora": "consultor", "asesor": "consultor", "asesora": "consultor",
    "proyecto": "proyectos", "proyectos": "proyectos",
    "auditor": "auditoria", "auditoria": "auditoria",
    "auditora": "auditoria",
    "gestion": "gestion", "manager": "gestion", "gerente": "gestion",
    "lider": "liderazgo", "liderazgo": "liderazgo", "jefe": "liderazgo", "jefa": "liderazgo",
    "coordinador": "liderazgo", "coordinadora": "liderazgo",    "supervisor": "liderazgo", "supervisora": "liderazgo",
    "trabajo": "trabajo en equipo", "equipo": "trabajo en equipo", "colaboracion": "trabajo en equipo",
    "comunicacion": "comunicacion", "comunicador": "comunicacion", "comunicadora": "comunicacion",
    "organizacion": "organizacion", "organizador": "organizacion", "organizadora": "organizacion",
    "resolucion": "resolucion de problemas", "problemas": "resolucion de problemas",
    "creatividad": "creatividad", "creativo": "creatividad", "creativa": "creatividad",
    "adaptabilidad": "adaptabilidad", "flexibilidad": "adaptabilidad",  "adaptable": "adaptabilidad",
    "puntualidad": "puntualidad", "responsabilidad": "responsabilidad", "responsable": "responsabilidad",
    "proactivo": "proactividad", "proactiva": "proactividad", "proactividad": "proactividad",   "iniciativa": "proactividad",   "autonomia": "proactividad",
    "metodologia": "metodologia", "metodico": "metodologia", "metodica": "metodologia",
    "detallista": "atencion al detalle", "detalle": "atencion al detalle", "detallado": "atencion al detalle",
    "puntual": "puntualidad", "responsable": "responsabilidad",
    "lider": "liderazgo", "liderazgo": "liderazgo",
    "gestion": "gestion", "manager": "gestion", "gerente": "gestion",   "jefe": "liderazgo", "jefa": "liderazgo",
    "coordinador": "liderazgo", "coordinadora": "liderazgo",    "supervisor": "liderazgo", "supervisora": "liderazgo",
}

# ================================================================
# ⚙️ FUNCIONES PRINCIPALES
# ================================================================


def normalizar_texto(s: str) -> str:
    """Minúsculas, sin tildes, sin signos, expande abreviaturas."""
    s = (s or "").casefold()
    s = "".join(c for c in unicodedata.normalize("NFD", s)
                if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    tokens = s.split()
    tokens = [ABREVIATURAS.get(t, t) for t in tokens]
    return " ".join(tokens)


def tokens_norm(x) -> set[str]:
    """Tokeniza, normaliza y aplica sinónimos."""
    if isinstance(x, (list, tuple)):
        x = " ".join(str(it) for it in x)
    s = normalizar_texto(str(x or ""))
    toks = {t for t in re.findall(r"\w+", s)}
    toks = {SINONIMOS.get(t, t) for t in toks}
    return toks


def soft_jaccard(A: set[str], B: set[str], thr: int = 87) -> float:
    """Jaccard 'suave': fuzzy matching para coincidencias aproximadas."""
    if not A or not B:
        return 0.0
    used, inter = set(), 0
    for a in A:
        best, best_sc = None, 0
        for b in B:
            if b in used:
                continue
            sc = _fuzzy_ratio(a, b)
            if sc > best_sc:
                best_sc, best = sc, b
        if best_sc >= thr and best is not None:
            inter += 1
            used.add(best)
    union = len(A | B)
    return inter / union if union else 0.0
