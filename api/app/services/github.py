import inspect

import httpx


class GitHubService:
    def __init__(self, token: str, org: str):
        self.org = org
        self._client = httpx.AsyncClient(
            base_url="https://api.github.com",
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github+json",
            },
            timeout=30.0,
        )

    async def create_repo(self, name: str, private: bool = True) -> dict:
        resp = await self._client.post(
            f"/orgs/{self.org}/repos",
            json={"name": name, "private": private, "auto_init": True},
        )
        resp.raise_for_status()
        result = resp.json()
        if inspect.isawaitable(result):
            result = await result
        return {"html_url": result["html_url"], "clone_url": result["clone_url"]}

    async def delete_repo(self, name: str) -> None:
        resp = await self._client.delete(f"/repos/{self.org}/{name}")
        resp.raise_for_status()

    async def close(self):
        await self._client.aclose()
