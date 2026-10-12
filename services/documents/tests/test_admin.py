from unittest.mock import MagicMock

from app.admin import create_indexes


def test_create_indexes_ensures_indexes_on_shared_repository(monkeypatch) -> None:
    repository = MagicMock()
    monkeypatch.setattr(create_indexes, "get_document_repository", lambda: repository)

    create_indexes.main()

    repository.ensure_indexes.assert_called_once_with()
