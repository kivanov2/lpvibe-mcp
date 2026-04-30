import httpx

from app.config import settings

_FUNCTION_TEMPLATE = """\
module.exports = async ({ page, context: { url, expression } }) => {
  await page.goto(url, { waitUntil: 'networkidle0' });
  const result = await page.evaluate(expression);
  return { data: result, type: 'application/json' };
};
"""


class BrowserClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(base_url=settings.browserless_url, timeout=60.0)

    def _params(self) -> dict:
        return {"token": settings.browserless_token} if settings.browserless_token else {}

    async def screenshot(self, url: str, full_page: bool = False) -> bytes:
        resp = await self._client.post(
            "/screenshot",
            params=self._params(),
            json={"url": url, "options": {"fullPage": full_page, "type": "png"}},
        )
        resp.raise_for_status()
        return resp.content

    async def content(self, url: str) -> str:
        resp = await self._client.post(
            "/content",
            params=self._params(),
            json={"url": url},
        )
        resp.raise_for_status()
        return resp.text

    async def evaluate(self, url: str, expression: str) -> dict:
        resp = await self._client.post(
            "/function",
            params=self._params(),
            json={
                "code": _FUNCTION_TEMPLATE,
                "context": {"url": url, "expression": expression},
            },
        )
        resp.raise_for_status()
        return resp.json()

    async def close(self) -> None:
        await self._client.aclose()
