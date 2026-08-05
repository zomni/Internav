from collections.abc import Callable, Generator
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.ai.dataset_export import DatasetExportService
from app.ai.serialization import ModelArtifactStorage
from app.ai.training_pipeline import TrainingPipelineService
from app.application.campaign_service import CampaignService
from app.application.core_hierarchy_service import CoreHierarchyService
from app.application.dataset_service import DatasetService
from app.application.fingerprint_service import FingerprintService
from app.application.floor_plan_service import FloorPlanService
from app.application.grid_service import GridService
from app.application.inference_service import InferenceService
from app.application.model_update_service import ModelUpdateService
from app.application.model_version_service import ModelVersionService
from app.application.user_service import UserService
from app.domain.entities.user import User, UserRole
from app.infrastructure.persistence.repositories.access_point_observation_sqlalchemy_repository import (
    SqlAlchemyAccessPointObservationRepository,
)
from app.infrastructure.persistence.repositories.building_sqlalchemy_repository import (
    SqlAlchemyBuildingRepository,
)
from app.infrastructure.persistence.repositories.campaign_sqlalchemy_repository import (
    SqlAlchemyCampaignRepository,
)
from app.infrastructure.persistence.repositories.cell_sqlalchemy_repository import (
    SqlAlchemyCellRepository,
)
from app.infrastructure.persistence.repositories.dataset_campaign_sqlalchemy_repository import (
    SqlAlchemyDatasetCampaignRepository,
)
from app.infrastructure.persistence.repositories.dataset_sqlalchemy_repository import (
    SqlAlchemyDatasetRepository,
)
from app.infrastructure.persistence.repositories.fingerprint_sqlalchemy_repository import (
    SqlAlchemyFingerprintRepository,
)
from app.infrastructure.persistence.repositories.floor_plan_sqlalchemy_repository import (
    SqlAlchemyFloorPlanRepository,
)
from app.infrastructure.persistence.repositories.floor_sqlalchemy_repository import (
    SqlAlchemyFloorRepository,
)
from app.infrastructure.persistence.repositories.grid_sqlalchemy_repository import (
    SqlAlchemyGridRepository,
)
from app.infrastructure.persistence.repositories.model_version_sqlalchemy_repository import (
    SqlAlchemyModelVersionRepository,
)
from app.infrastructure.persistence.repositories.organization_sqlalchemy_repository import (
    SqlAlchemyOrganizationRepository,
)
from app.infrastructure.persistence.repositories.site_sqlalchemy_repository import (
    SqlAlchemySiteRepository,
)
from app.infrastructure.persistence.repositories.user_sqlalchemy_repository import (
    SqlAlchemyUserRepository,
)
from app.security.tokens import TokenValidationError, decode_token

bearer_scheme = HTTPBearer(auto_error=False)


def get_session(request: Request) -> Generator[Session]:
    session = request.app.state.session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_hierarchy_service(session: Session = Depends(get_session)) -> CoreHierarchyService:
    return CoreHierarchyService(
        SqlAlchemyOrganizationRepository(session),
        SqlAlchemySiteRepository(session),
        SqlAlchemyBuildingRepository(session),
        SqlAlchemyFloorRepository(session),
    )


def get_floor_plan_service(session: Session = Depends(get_session)) -> FloorPlanService:
    return FloorPlanService(
        SqlAlchemyFloorPlanRepository(session),
        SqlAlchemyFloorRepository(session),
        SqlAlchemyGridRepository(session),
        SqlAlchemyCellRepository(session),
    )


def get_grid_service(session: Session = Depends(get_session)) -> GridService:
    return GridService(
        SqlAlchemyGridRepository(session),
        SqlAlchemyCellRepository(session),
        SqlAlchemyFloorRepository(session),
        SqlAlchemyFloorPlanRepository(session),
        SqlAlchemyCampaignRepository(session),
    )


def get_campaign_service(session: Session = Depends(get_session)) -> CampaignService:
    return CampaignService(
        SqlAlchemyCampaignRepository(session),
        SqlAlchemyFloorRepository(session),
    )


def get_fingerprint_service(session: Session = Depends(get_session)) -> FingerprintService:
    return FingerprintService(
        SqlAlchemyFingerprintRepository(session),
        SqlAlchemyCampaignRepository(session),
        SqlAlchemyCellRepository(session),
        SqlAlchemyAccessPointObservationRepository(session),
    )


def get_dataset_service(session: Session = Depends(get_session)) -> DatasetService:
    return DatasetService(
        SqlAlchemyDatasetRepository(session),
        SqlAlchemyDatasetCampaignRepository(session),
        SqlAlchemyCampaignRepository(session),
        SqlAlchemyFingerprintRepository(session),
        SqlAlchemyCellRepository(session),
    )


def get_model_version_service(session: Session = Depends(get_session)) -> ModelVersionService:
    return ModelVersionService(
        SqlAlchemyModelVersionRepository(session),
        SqlAlchemyDatasetRepository(session),
        SqlAlchemyFloorRepository(session),
        training_pipeline=get_training_pipeline_service(session),
    )


def get_training_pipeline_service(
    session: Session = Depends(get_session),
) -> TrainingPipelineService:
    dataset_export_service = DatasetExportService(
        SqlAlchemyDatasetRepository(session),
        SqlAlchemyDatasetCampaignRepository(session),
        SqlAlchemyCampaignRepository(session),
        SqlAlchemyFingerprintRepository(session),
        SqlAlchemyAccessPointObservationRepository(session),
        SqlAlchemyCellRepository(session),
    )
    model_storage = ModelArtifactStorage("./models")
    return TrainingPipelineService(
        SqlAlchemyModelVersionRepository(session),
        SqlAlchemyFingerprintRepository(session),
        dataset_export_service,
        model_storage,
    )


def get_user_service(session: Session = Depends(get_session)) -> UserService:
    return UserService(
        SqlAlchemyUserRepository(session),
    )


def get_model_update_service(session: Session = Depends(get_session)) -> ModelUpdateService:
    return ModelUpdateService(
        SqlAlchemyModelVersionRepository(session),
        SqlAlchemyFloorRepository(session),
    )


def get_inference_service(session: Session = Depends(get_session)) -> InferenceService:
    return InferenceService(
        SqlAlchemyModelVersionRepository(session),
        SqlAlchemyFingerprintRepository(session),
        SqlAlchemyCellRepository(session),
        SqlAlchemyAccessPointObservationRepository(session),
    )


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: Session = Depends(get_session),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required."
        )
    try:
        user_id, _ = decode_token(credentials.credentials, "access", request.app.state.settings)
    except TokenValidationError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)) from error
    user = SqlAlchemyUserRepository(session).get(UUID(str(user_id)))
    if user is None or not user.is_active or user.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is inactive.")
    return user


def require_roles(*roles: UserRole) -> Callable[[User], User]:
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions."
            )
        return user

    return dependency
