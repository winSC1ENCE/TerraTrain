from unittest.mock import patch, MagicMock
import pytest
from terratrain.db.migrate import apply_migrations, run_migrations


def test_apply_migrations_finds_ini_and_executes_upgrade():
    with patch("terratrain.db.migrate.command.upgrade") as mock_upgrade:
        apply_migrations()
        mock_upgrade.assert_called_once()


@pytest.mark.asyncio
async def test_run_migrations_async_wrapper():
    with patch("terratrain.db.migrate.apply_migrations") as mock_apply:
        await run_migrations()
        mock_apply.assert_called_once()
