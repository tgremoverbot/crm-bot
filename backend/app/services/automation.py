from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ScheduledMessageStatus, SourceKind
from app.models.scheduled_message import ScheduledMessage
from app.models.sequence import Sequence
from app.models.user import User
from app.repositories import events as event_repo
from app.repositories import scheduled as scheduled_repo
from app.repositories import sequences as seq_repo

# Statuses that mean "already in-flight — don't create a duplicate"
_SKIP_STATUSES = {
    ScheduledMessageStatus.PENDING,
    ScheduledMessageStatus.PROCESSING,
    ScheduledMessageStatus.FAILED,
}


async def enroll_user_in_sequence(
    session: AsyncSession,
    user: User,
    sequence: Sequence,
    *,
    now: datetime | None = None,
) -> list[ScheduledMessage]:
    """Materialise one ScheduledMessage per SequenceStep.

    - Skips steps that are PENDING/FAILED/SENT (already in-flight or delivered).
    - Resets FAILED_TERMINAL steps back to PENDING so they get retried.
    - Safe to call for both new and returning users.
    """
    now = now or datetime.now(timezone.utc)
    steps = await seq_repo.list_steps(session, sequence.id)

    # Fetch all existing scheduled messages for this user+sequence
    existing: list[ScheduledMessage] = list(
        (await session.scalars(
            select(ScheduledMessage).where(
                ScheduledMessage.source_id == sequence.id,
                ScheduledMessage.user_id == user.id,
                ScheduledMessage.idempotency_key.isnot(None),
            )
        )).all()
    )
    existing_by_key: dict[str, ScheduledMessage] = {m.idempotency_key: m for m in existing}

    messages: list[ScheduledMessage] = []
    for step in steps:
        # A step's material_id becomes NULL if its message was deleted while the
        # sequence was inactive. Skip such orphaned steps entirely — there's
        # nothing to schedule and the FK would reject a NULL-material message.
        if step.material_id is None:
            continue

        key = f"seq:{sequence.id}:step:{step.id}:user:{user.id}"
        existing_msg = existing_by_key.get(key)

        if existing_msg is not None:
            if existing_msg.status in _SKIP_STATUSES:
                continue
            # FAILED_TERMINAL — reset so the scheduler retries it
            existing_msg.status = ScheduledMessageStatus.PENDING
            existing_msg.scheduled_at = now + timedelta(minutes=step.delay_minutes)
            existing_msg.attempts = 0
            existing_msg.last_error = None
            await session.flush()
            messages.append(existing_msg)
            continue

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
