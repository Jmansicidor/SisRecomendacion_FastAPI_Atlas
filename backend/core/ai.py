# core/ai.py
from __future__ import annotations
from typing import List
import os
import numpy as np
from openai import OpenAI

# Config por env
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")
# Si querés recortar dimensiones (opcional):
EMBED_DIM = os.getenv("EMBED_DIM")
EMBED_DIM = int(EMBED_DIM) if (EMBED_DIM and EMBED_DIM.isdigit()) else None

_client: OpenAI | None = None


def _client_singleton() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def _embed_texts_sync(texts: List[str]) -> List[List[float]]:
    client = _client_singleton()
    kwargs = {"model": EMBED_MODEL, "input": texts}
    if EMBED_DIM:  # opcional, ej 768/1024
        kwargs["dimensions"] = EMBED_DIM
    resp = client.embeddings.create(**kwargs)
    return [item.embedding for item in resp.data]


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Mantiene la misma firma que tu implementación anterior.
    Llamala como venías haciendo:
        await anyio.to_thread.run_sync(embed_texts, [texto])
    para no bloquear el event loop.
    """
    return _embed_texts_sync(texts)


def cosine(a: List[float], b: List[float]) -> float:
    va = np.asarray(a, dtype=np.float32)
    vb = np.asarray(b, dtype=np.float32)
    na = float(np.linalg.norm(va)) or 1e-8
    nb = float(np.linalg.norm(vb)) or 1e-8
    return float((va @ vb) / (na * nb))
