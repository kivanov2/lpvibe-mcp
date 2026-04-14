from minio import Minio


class MinIOAdminService:
    def __init__(self, endpoint: str, access_key: str, secret_key: str, secure: bool = False):
        self._client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)

    def _bucket_name(self, project_name: str) -> str:
        return f"project-{project_name}-files"

    def create_bucket(self, project_name: str) -> str:
        bucket = self._bucket_name(project_name)
        if not self._client.bucket_exists(bucket):
            self._client.make_bucket(bucket)
        return bucket

    def delete_bucket(self, project_name: str) -> None:
        bucket = self._bucket_name(project_name)
        if not self._client.bucket_exists(bucket):
            return
        objects = self._client.list_objects(bucket, recursive=True)
        for obj in objects:
            self._client.remove_object(bucket, obj.object_name)
        self._client.remove_bucket(bucket)
