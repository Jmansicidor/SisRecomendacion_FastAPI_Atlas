# user/routes/user_router.py (ejemplos)
from fastapi import APIRouter, Depends, HTTPException, status
from auth.services.auth_service import get_current_active_user

from user.schemas.user import UserSchema, UserCreate
from user.models.user import User, Role
from user.services.user_service import get_users, get_user, create_user, delete_user, add_role, remove_role
from core.database import get_db
from auth.utils.permissions import require_roles, require_admin 
user_router = APIRouter(prefix="/users", tags=["Users"])


@user_router.get("/", response_model=list[UserSchema], dependencies=[Depends(require_roles("admin"))])
async def list_users(db=Depends(get_db)):
    return await get_users(db)

# /me sin rol especial (solo autenticado y activo)


@user_router.get("/me", response_model=UserSchema)
async def me(current_user: User = Depends(get_current_active_user)):
    return UserSchema(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        is_active=current_user.is_active,
        roles=current_user.roles,
    )
# Admin: asignar/quitar rol


@user_router.post("/{user_id}/roles/{role}", dependencies=[Depends(require_roles("admin"))])
async def grant_role(user_id: str, role: Role, db=Depends(get_db)):
    ok = await add_role(db, user_id, role)
    if not ok:
        raise HTTPException(
            status_code=404, detail="User not found or not modified")
    return {"message": f"role {role.value} granted"}


@user_router.delete("/{user_id}/roles/{role}", dependencies=[Depends(require_roles("admin"))])
async def revoke_role(user_id: str, role: Role, db=Depends(get_db)):
    ok = await remove_role(db, user_id, role)
    if not ok:
        raise HTTPException(
            status_code=404, detail="User not found or not modified")
    return {"message": f"role {role.value} removed"}
