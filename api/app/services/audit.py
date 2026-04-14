import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


async def log_action(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    action: str,
    project_id: uuid.UUID | None = None,
    args: dict | None = None,
    result: str = "success",
    error_message: str | None = None,
) -> None:
    entry = AuditLog(
        user_id=user_id,
        action=action,
        project_id=project_id,
        args=args,
        result=result,
        error_message=error_message,
    )
    session.add(entry)
    await session.flush()
