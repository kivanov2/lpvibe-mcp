import inspect

import httpx


def generate_ssh_keypair() -> tuple[str, str]:
    """Return (private_key_openssh, public_key_openssh) for a fresh ed25519 key."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import (
        Encoding,
        NoEncryption,
        PrivateFormat,
        PublicFormat,
    )

    key = Ed25519PrivateKey.generate()
    priv = key.private_bytes(Encoding.PEM, PrivateFormat.OpenSSH, NoEncryption()).decode()
    pub = key.public_key().public_bytes(Encoding.OpenSSH, PublicFormat.OpenSSH).decode()
    return priv, pub


class CoolifyService:
    def __init__(
        self,
        api_url: str,
        api_token: str,
        server_uuid: str,
        project_uuid: str,
        environment_name: str,
        deploy_key_uuid: str = "",
    ):
        self.server_uuid = server_uuid
        self.project_uuid = project_uuid
        self.environment_name = environment_name
        self.deploy_key_uuid = deploy_key_uuid
        self._client = httpx.AsyncClient(
            base_url=api_url,
            headers={
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
            },
            timeout=60.0,
        )

    async def create_coolify_project(self, name: str) -> str:
        resp = await self._client.post("/api/v1/projects", json={"name": name})
        resp.raise_for_status()
        data = resp.json()
        return data["uuid"]

    async def delete_coolify_project(self, project_uuid: str) -> None:
        resp = await self._client.delete(f"/api/v1/projects/{project_uuid}")
        resp.raise_for_status()

    async def create_private_key(self, name: str, private_key: str) -> str:
        resp = await self._client.post(
            "/api/v1/security/keys",
            json={"name": name, "private_key": private_key},
        )
        resp.raise_for_status()
        return resp.json()["uuid"]

    async def find_private_key_uuids(self, name: str) -> list[str]:
        # ponytail: name-based lookup instead of storing uuid on Project; add a column if key count grows
        resp = await self._client.get("/api/v1/security/keys")
        resp.raise_for_status()
        return [key["uuid"] for key in resp.json() if key.get("name") == name]

    async def delete_private_key(self, key_uuid: str) -> None:
        resp = await self._client.delete(f"/api/v1/security/keys/{key_uuid}")
        resp.raise_for_status()

    async def create_app(self, name: str, repo_url: str, env_vars: dict[str, str], project_uuid: str | None = None, private_key_uuid: str | None = None) -> dict:
        key_uuid = private_key_uuid or self.deploy_key_uuid
        if key_uuid and repo_url.startswith("https://github.com/"):
            path = repo_url.removeprefix("https://github.com/")
            git_url = f"git@github.com:{path}"
            endpoint = "/api/v1/applications/private-deploy-key"
            extra = {"private_key_uuid": key_uuid}
        else:
            git_url = repo_url
            endpoint = "/api/v1/applications/public"
            extra = {}

        resp = await self._client.post(
            endpoint,
            json={
                "name": name,
                "server_uuid": self.server_uuid,
                "project_uuid": project_uuid or self.project_uuid,
                "environment_name": self.environment_name,
                "git_repository": git_url,
                "git_branch": "main",
                "build_pack": "dockerfile",
                "ports_exposes": "8000",
                "instant_deploy": False,
                **extra,
            },
        )
        resp.raise_for_status()
        app_data = resp.json()
        if inspect.isawaitable(app_data):
            app_data = await app_data
        app_uuid = app_data["uuid"]

        for key, value in env_vars.items():
            await self._client.post(
                f"/api/v1/applications/{app_uuid}/envs",
                json={"key": key, "value": value},
            )

        return app_data

    async def deploy_app(self, app_uuid: str) -> dict:
        # /deploy takes query params (uuid or tag), not a JSON body
        resp = await self._client.post("/api/v1/deploy", params={"uuid": app_uuid, "force": "true"})
        resp.raise_for_status()
        result = resp.json()
        if inspect.isawaitable(result):
            result = await result
        return result

    async def get_deploy_status(self, app_uuid: str) -> dict:
        resp = await self._client.get(f"/api/v1/applications/{app_uuid}")
        resp.raise_for_status()
        result = resp.json()
        if inspect.isawaitable(result):
            result = await result
        return result

    async def get_app_logs(self, app_uuid: str, lines: int = 100) -> str:
        resp = await self._client.get(f"/api/v1/applications/{app_uuid}/logs", params={"lines": lines})
        resp.raise_for_status()
        return resp.text

    async def exec_command(self, app_uuid: str, command: str) -> dict:
        resp = await self._client.post(
            f"/api/v1/applications/{app_uuid}/execute",
            json={"command": command},
            timeout=120.0,
        )
        resp.raise_for_status()
        return resp.json()

    async def delete_app(self, app_uuid: str) -> None:
        resp = await self._client.delete(
            f"/api/v1/applications/{app_uuid}",
            params={"delete_volumes": True},
        )
        resp.raise_for_status()

    async def close(self):
        await self._client.aclose()
