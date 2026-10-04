from app.core.config import (
    DATA_MODE_MOCK,
    get_data_mode,
    validate_mock_mode,
)
from app.database import database_url, engine
from app.mock.seed import (
    prepare_mock_database,
)


def initialize_mock_database() -> None:
    if get_data_mode() != DATA_MODE_MOCK:
        return

    validate_mock_mode(database_url)

    prepare_mock_database(
        engine,
        reset=False,
    )