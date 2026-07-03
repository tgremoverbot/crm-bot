from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_db
from app.models.admin_user import AdminUser
from app.repositories import materials as material_repo
from app.schemas.material import MaterialCreate, MaterialOut, MaterialUpdate

router = APIRouter()


@router.get("", response_model=list[MaterialOut])
async def list_materials(
    session: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> list[MaterialOut]:
    items = await material_repo.list_materials(session)
    return [MaterialOut.model_validate(m) for m in items]


@router.post("", response_model=MaterialOut, status_code=status.HTTP_201_CREATED)
async def create_material(
    body: MaterialCreate,
    session: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> MaterialOut:
    material = await material_repo.create(session, **body.model_dump())
    return MaterialOut.model_validate(material)


@router.patch("/{material_id}", response_model=MaterialOut)
async def update_material(
    material_id: UUID,
    body: MaterialUpdate,
    session: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> MaterialOut:
    material = await material_repo.get_by_id(session, material_id)
    if not material:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Material not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(material, field, value)
    await session.flush()
    await session.refresh(material)
    return MaterialOut.model_validate(material)


@router.delete("/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_material(
    material_id: UUID,
    session: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> None:
    material = await material_repo.get_by_id(session, material_id)
    if not material:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Material not found")

    # Proactive guard: block deletion only when the message is used by a step of
    # an *active* auto-flow. Historical usage (inactive flows, broadcasts,
    # scheduled messages) no longer blocks deletion — those FKs are SET NULL.
    active_flows = await material_repo.active_flow_names_using(session, material_id)
    if active_flows:
        if len(active_flows) == 1:
            detail = (
                f'This message is used in the active auto-flow '
                f'"{active_flows[0]}" and can\'t be deleted. Remove it '
                f'from that flow (or deactivate the flow) first.'
            )
        else:
            names = ", ".join(f'"{n}"' for n in active_flows)
            detail = (
                f"This message is used in active auto-flows ({names}) and can't "
                f"be deleted. Remove it from those flows (or deactivate them) "
                f"first."
            )
        raise HTTPException(status.HTTP_409_CONFLICT, detail)

    await session.delete(material)
    try:
        # Flush inside the handler so a constraint violation surfaces here as a
        # 409 rather than silently rolling back in get_db's post-yield commit.
        # The active-flow guard above handles the common case with a precise
        # message; this remains as a defensive fallback.
        await session.flush()
    except IntegrityError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "This message is still referenced and can't be deleted. Remove it "
            "from any auto-flow it's used in first.",
        ) from exc
