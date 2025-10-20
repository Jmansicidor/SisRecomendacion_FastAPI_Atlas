# auth/utils/permissions.py
from typing import Any, Iterable, Set
from fastapi import Depends, HTTPException, status

from user.models.user import User  # tu modelo Pydantic interno (con roles)
from auth.services.auth_service import get_current_active_user


def _to_str_set(items: Iterable[Any]) -> Set[str]:
    """
    Normaliza una colección de roles (str o Enum) a un set[str].
    - Si el item tiene atributo .value (Enum), usa ese valor.
    - Si es str u otro, lo castea a str.
    """
    out: Set[str] = set()
    for x in items:
        if x is None:
            continue
        if hasattr(x, "value"):
            out.add(str(getattr(x, "value")))
        else:
            out.add(str(x))
    return out


def require_roles(*allowed: Any):

    allowed_set = _to_str_set(allowed)
    if not allowed_set:
        raise ValueError("require_roles necesita al menos un rol permitido")

    async def checker(current_user: User = Depends(get_current_active_user)) -> User:
        user_roles = _to_str_set(getattr(current_user, "roles", []))
        if not user_roles.intersection(allowed_set):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role",
            )
        return current_user

    return checker


# Atajos convenientes
def require_admin():
    """Guard que exige rol 'admin'."""
    return require_roles("admin")


def require_any_role(*roles: Any):
    """Alias semántico: al menos uno de los roles."""
    return require_roles(*roles)


def require_all_roles(*roles: Any):
    """
    Verifica que el usuario tenga TODOS los roles indicados.
    Útil para casos específicos.
    """
    required = _to_str_set(roles)

    async def checker(current_user: User = Depends(get_current_active_user)) -> User:
        user_roles = _to_str_set(getattr(current_user, "roles", []))
        if not required.issubset(user_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role",
            )
        return current_user

    return checker
