"""
Service layer for Organization and Department business logic.
"""

from math import ceil
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.organization import DepartmentRepository, OrganizationRepository
from app.schemas.organization import (
    AttachParticipantsRequest,
    DepartmentCreateRequest,
    DepartmentListResponse,
    DepartmentResponse,
    DepartmentUpdateRequest,
    OrganizationCreateRequest,
    OrganizationDetailResponse,
    OrganizationListResponse,
    OrganizationResponse,
    OrganizationUpdateRequest,
)


class OrganizationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.org_repo = OrganizationRepository(db)
        self.dept_repo = DepartmentRepository(db)

    # --- Organization CRUD ---

    async def create_organization(self, request: OrganizationCreateRequest) -> OrganizationResponse:
        existing = await self.org_repo.get_by_name(request.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Организация с именем '{request.name}' уже существует",
            )
        org = await self.org_repo.create(name=request.name, description=request.description)
        return OrganizationResponse(
            id=org.id,
            name=org.name,
            description=org.description,
            created_at=org.created_at,
            departments_count=0,
            participants_count=0,
        )

    async def get_organization(self, org_id: UUID) -> OrganizationDetailResponse:
        org = await self.org_repo.get_by_id_with_departments(org_id)
        if not org:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Организация не найдена")

        dept_responses = []
        for dept in org.departments:
            count = await self.dept_repo.get_participants_count(dept.id)
            dept_responses.append(
                DepartmentResponse(
                    id=dept.id,
                    organization_id=dept.organization_id,
                    name=dept.name,
                    description=dept.description,
                    created_at=dept.created_at,
                    participants_count=count,
                )
            )
        dept_responses.sort(key=lambda d: d.name)

        return OrganizationDetailResponse(
            id=org.id,
            name=org.name,
            description=org.description,
            created_at=org.created_at,
            departments=dept_responses,
        )

    async def search_organizations(
        self, query: str | None = None, page: int = 1, size: int = 20
    ) -> OrganizationListResponse:
        orgs, total = await self.org_repo.search(query=query, page=page, size=size)
        items = []
        for org in orgs:
            dept_count = await self.org_repo.get_departments_count(org.id)
            part_count = await self.org_repo.get_participants_count(org.id)
            items.append(
                OrganizationResponse(
                    id=org.id,
                    name=org.name,
                    description=org.description,
                    created_at=org.created_at,
                    departments_count=dept_count,
                    participants_count=part_count,
                )
            )
        pages = ceil(total / size) if total > 0 else 0
        return OrganizationListResponse(items=items, total=total, page=page, size=size, pages=pages)

    async def update_organization(self, org_id: UUID, request: OrganizationUpdateRequest) -> OrganizationResponse:
        org = await self.org_repo.get_by_id(org_id)
        if not org:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Организация не найдена")

        if request.name is not None and request.name != org.name:
            existing = await self.org_repo.get_by_name(request.name)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Организация с именем '{request.name}' уже существует",
                )

        org = await self.org_repo.update(org, name=request.name, description=request.description)
        dept_count = await self.org_repo.get_departments_count(org.id)
        part_count = await self.org_repo.get_participants_count(org.id)
        return OrganizationResponse(
            id=org.id,
            name=org.name,
            description=org.description,
            created_at=org.created_at,
            departments_count=dept_count,
            participants_count=part_count,
        )

    async def delete_organization(self, org_id: UUID) -> None:
        org = await self.org_repo.get_by_id(org_id)
        if not org:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Организация не найдена")
        await self.org_repo.delete(org)

    # --- Department CRUD ---

    async def create_department(self, org_id: UUID, request: DepartmentCreateRequest) -> DepartmentResponse:
        org = await self.org_repo.get_by_id(org_id)
        if not org:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Организация не найдена")

        existing = await self.dept_repo.get_by_org_and_name(org_id, request.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Отдел '{request.name}' уже существует в этой организации",
            )

        dept = await self.dept_repo.create(
            organization_id=org_id, name=request.name, description=request.description
        )
        return DepartmentResponse(
            id=dept.id,
            organization_id=dept.organization_id,
            name=dept.name,
            description=dept.description,
            created_at=dept.created_at,
            participants_count=0,
        )

    async def list_departments(self, org_id: UUID) -> DepartmentListResponse:
        org = await self.org_repo.get_by_id(org_id)
        if not org:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Организация не найдена")

        depts = await self.dept_repo.list_by_organization(org_id)
        items = []
        for dept in depts:
            count = await self.dept_repo.get_participants_count(dept.id)
            items.append(
                DepartmentResponse(
                    id=dept.id,
                    organization_id=dept.organization_id,
                    name=dept.name,
                    description=dept.description,
                    created_at=dept.created_at,
                    participants_count=count,
                )
            )
        return DepartmentListResponse(items=items, total=len(items))

    async def update_department(
        self, org_id: UUID, dept_id: UUID, request: DepartmentUpdateRequest
    ) -> DepartmentResponse:
        dept = await self._get_department_in_org(org_id, dept_id)

        if request.name is not None and request.name != dept.name:
            existing = await self.dept_repo.get_by_org_and_name(org_id, request.name)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Отдел '{request.name}' уже существует в этой организации",
                )

        dept = await self.dept_repo.update(dept, name=request.name, description=request.description)
        count = await self.dept_repo.get_participants_count(dept.id)
        return DepartmentResponse(
            id=dept.id,
            organization_id=dept.organization_id,
            name=dept.name,
            description=dept.description,
            created_at=dept.created_at,
            participants_count=count,
        )

    async def delete_department(self, org_id: UUID, dept_id: UUID) -> None:
        dept = await self._get_department_in_org(org_id, dept_id)
        await self.dept_repo.delete(dept)

    # --- Participants in department ---

    async def list_department_participants(self, org_id: UUID, dept_id: UUID):
        await self._get_department_in_org(org_id, dept_id)
        return await self.dept_repo.list_participants(dept_id)

    async def attach_participants(
        self, org_id: UUID, dept_id: UUID, request: AttachParticipantsRequest
    ) -> int:
        await self._get_department_in_org(org_id, dept_id)
        return await self.dept_repo.attach_participants(dept_id, request.participant_ids)

    async def detach_participant(self, org_id: UUID, dept_id: UUID, participant_id: UUID) -> None:
        await self._get_department_in_org(org_id, dept_id)
        detached = await self.dept_repo.detach_participant(participant_id)
        if not detached:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Участник не найден или не привязан к этому отделу",
            )

    # --- helpers ---

    async def _get_department_in_org(self, org_id: UUID, dept_id: UUID):
        dept = await self.dept_repo.get_by_id(dept_id)
        if not dept or dept.organization_id != org_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Отдел не найден")
        return dept
