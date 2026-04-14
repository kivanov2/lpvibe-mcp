from unittest.mock import MagicMock, patch

from app.services.minio_admin import MinIOAdminService


def _make_svc():
    return MinIOAdminService(endpoint="localhost:9000", access_key="admin", secret_key="pass", secure=False)


def test_create_bucket():
    svc = _make_svc()
    with patch.object(svc._client, "bucket_exists", return_value=False), \
         patch.object(svc._client, "make_bucket") as mock_make:
        result = svc.create_bucket("my-svc")
        assert result == "project-my-svc-files"
        mock_make.assert_called_once_with("project-my-svc-files")


def test_create_bucket_already_exists():
    svc = _make_svc()
    with patch.object(svc._client, "bucket_exists", return_value=True), \
         patch.object(svc._client, "make_bucket") as mock_make:
        result = svc.create_bucket("my-svc")
        assert result == "project-my-svc-files"
        mock_make.assert_not_called()


def test_delete_bucket():
    svc = _make_svc()
    with patch.object(svc._client, "bucket_exists", return_value=True), \
         patch.object(svc._client, "list_objects", return_value=[]), \
         patch.object(svc._client, "remove_bucket") as mock_rm:
        svc.delete_bucket("my-svc")
        mock_rm.assert_called_once_with("project-my-svc-files")
