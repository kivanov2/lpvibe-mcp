from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    platform_api_url: str = "https://api.main.loyaltyapp-tools.com"

    jwt_signing_key: str = "changeme-in-production"

    mcp_service_user_id: str = ""
    mcp_service_github_login: str = "mcp-server"
    mcp_service_github_id: int = 0

    mcp_client_token: str = ""

    mcp_host: str = "0.0.0.0"
    mcp_port: int = 8001


settings = Settings()
