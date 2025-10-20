# metricas/services/token_utils.py
import unicodedata
import re


def _norm_token(s: str) -> str:
    s = (s or "").strip().lower()
    s = "".join(c for c in unicodedata.normalize(
        "NFKD", s) if not unicodedata.combining(c))
    s = re.sub(r"\s+", " ", s)
    return s


def _tokset(xs) -> set[str]:
    if not xs:
        return set()
    out = []
    if isinstance(xs, (list, tuple, set)):
        for x in xs:
            if isinstance(x, (list, tuple, set)):
                out.extend([_norm_token(str(z)) for z in x if z])
            else:
                out.append(_norm_token(str(x)))
    else:
        for part in str(xs).split(","):
            out.append(_norm_token(part))
    return {t for t in out if t}


def jaccard(a, b) -> float:
    A, B = _tokset(a), _tokset(b)
    if not A and not B:
        return 0.0
    u = len(A | B)
    if u == 0:
        return 0.0
    return len(A & B) / u
