from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import SourceKind
from app.models.scheduled_message import ScheduledMessage
from app.models.sequence import Sequence
from app.models.user import User
from app.repositories import events as event_repo
from app.repositories import scheduled as scheduled_repo
from app.repositories import sequences as seq_repo


async def enroll_user_in_sequence(
    session: AsyncSession,
    user: User,
    sequence: Sequence,
    *,
    now: datetime | None = None,
) -> list[ScheduledMessage]:
    """Materialise one ScheduledMessage per SequenceStep.

    Uses an idempotency_key so calling twice for the same user+step is a no-op
    at the DB level (unique constraint prevents duplicates).
    """
    now = now or datetime.now(timezone.utc)
    steps = await seq_repo.list_steps(session, sequence.id)
    messages: list[ScheduledMessage] = []
    for step in steps:
        key = f"seq:{sequence.id}:step:{step.id}:user:{user.id}"
        scheduled_at = now + timedelta(minutes=step.delay_minutes)
        msg = await scheduled_repo.create(
            session,
            user_id=user.id,
            material_id=step.material_id,
            scheduled_at=scheduled_at,
            source_kind=SourceKind.SEQUENCE,
            source_id=sequence.id,
            idempotency_key=key,
        )
        messages.append(msg)
    await event_repo.log(
        session,
        type="sequence_enrolled",
        user_id=user.id,
        payload={"sequence_id": str(sequence.id), "steps_scheduled": len(messages)},
    )
    return messages
