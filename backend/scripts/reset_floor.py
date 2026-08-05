"""Reset Piso 2 capture data before regenerating its grid from a real SVG plan.

Fingerprints reference cells through a RESTRICT foreign key, and the fingerprint
repositories only expose soft-delete, so the rows must be physically removed
before the placeholder grid's cells can be deleted. The grid removal itself is
performed through the HTTP API to keep domain rules in charge.
"""

import sys
from pathlib import Path
from uuid import UUID

from sqlalchemy import delete, select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config.settings import Settings  # noqa: E402
from app.infrastructure.persistence.database import (  # noqa: E402
    create_session_factory,
    create_sqlite_engine,
    transaction,
)
from app.infrastructure.persistence.models import (  # noqa: E402
    AccessPointObservationModel,
    FingerprintModel,
)
from app.infrastructure.persistence.repositories.cell_sqlalchemy_repository import (  # noqa: E402
    SqlAlchemyCellRepository,
)

FLOOR_ID = UUID("bc41c259-bbe1-475a-8a80-79ec7510a79d")
GRID_ID = UUID("7451805a-19d1-4788-8285-c49a8ff7f371")


def main() -> None:
    settings = Settings.from_env()
    engine = create_sqlite_engine(settings.database_url)
    session_factory = create_session_factory(engine)

    with transaction(session_factory) as session:
        cell_repo = SqlAlchemyCellRepository(session)
        cells = cell_repo.list_by_grid(GRID_ID)
        cell_ids = [str(cell.id) for cell in cells]
        print(f"Grid {GRID_ID}: {len(cell_ids)} cells")

        fingerprint_ids = list(
            session.scalars(
                select(FingerprintModel.id).where(FingerprintModel.cell_id.in_(cell_ids))
            ).all()
        )
        print(f"Fingerprints bound to grid cells: {len(fingerprint_ids)}")

        deleted_obs = session.execute(
            delete(AccessPointObservationModel).where(
                AccessPointObservationModel.fingerprint_id.in_(fingerprint_ids)
            )
        ).rowcount
        deleted_fps = session.execute(
            delete(FingerprintModel).where(FingerprintModel.cell_id.in_(cell_ids))
        ).rowcount
        print(f"Deleted observations: {deleted_obs}")
        print(f"Deleted fingerprints: {deleted_fps}")

    print("Done. Use the HTTP API to unlock, delete and re-generate the grid.")


if __name__ == "__main__":
    main()
