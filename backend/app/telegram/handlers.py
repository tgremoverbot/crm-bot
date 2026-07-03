from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.enums import MaterialKind, ParseMode
from app.telegram.service import handle_start, handle_stop

router = Router(name="main")

# In-memory set of Telegram IDs that have unlocked admin bot mode.
_admin_sessions: set[int] = set()


class SaveMessage(StatesGroup):
    waiting_for_name = State()

_WELCOME = (
    "Assalomu alaykum! 👋\n\n"
    "Arabic tilini o'rganishga xush kelibsiz."
)

_STOP_TEXT = (
    "Siz ro'yxatdan chiqdingiz. Qaytishingizni istalgan vaqt kutamiz! 🤝\n"
    "Qayta boshlash uchun /start buyrug'ini yuboring."
)

_SETTINGS_TEXT = "⚙️ Sozlamalar (tez orada qo'shiladi)."


@router.message(CommandStart())
async def cmd_start(
    message: Message, command: CommandObject, session: AsyncSession
) -> None:
    payload = command.args
    tg = message.from_user

    user, _, _campaign = await handle_start(
        session,
        telegram_id=tg.id,
        chat_id=message.chat.id,
        username=tg.username,
        first_name=tg.first_name,
        last_name=tg.last_name,
        language_code=tg.language_code,
        campaign_slug=payload or None,
    )
    if not payload:
        await message.answer(_WELCOME, reply_markup=ReplyKeyboardRemove())

    # Flush any 0-delay steps immediately, whether enrollment came from a
    # campaign's default auto-flow or the organic-start fallback auto-flow.
    from app.services import scheduler as scheduler_service
    from app.telegram.bot import get_bot
    await scheduler_service.flush_user(session, get_bot(), user.id)


@router.message(Command("stop"))
async def cmd_stop(message: Message, session: AsyncSession) -> None:
    await handle_stop(session, telegram_id=message.from_user.id)
    await message.answer(_STOP_TEXT)


@router.message(Command("settings"))
async def cmd_settings(message: Message) -> None:
    await message.answer(_SETTINGS_TEXT)


@router.message(Command("admin"))
async def cmd_admin(message: Message, command: CommandObject, state: FSMContext) -> None:
    settings = get_settings()
    tid = message.from_user.id

    if not settings.ADMIN_BOT_PASSWORD:
        await message.answer("⚠️ Admin bot mode is not configured.")
        return

    arg = (command.args or "").strip()

    if arg == "logout":
        _admin_sessions.discard(tid)
        await state.clear()
        await message.answer("✅ Logged out of admin mode.")
        return

    if arg == settings.ADMIN_BOT_PASSWORD.strip():
        _admin_sessions.add(tid)
        await message.answer(
            "✅ *Admin mode active.*\n\n"
            "Send me any message — photo, video, document, or text — "
            "and I'll ask you what to call it, then save it so you can use it in Auto-flows.\n\n"
            "Send /admin logout to exit.",
            parse_mode="Markdown",
        )
        return

    await message.answer("❌ Wrong password.")


_KIND_LABELS = {
    "text": "Text",
    "photo": "Photo",
    "video": "Video",
    "document": "File",
    "voice": "Voice",
    "audio": "Audio",
    "video_note": "Video note",
    "animation": "GIF",
    "sticker": "Sticker",
}


def _extract_content(message: Message) -> tuple[MaterialKind, str | None, str | None] | None:
    if message.photo:
        return MaterialKind.PHOTO, message.caption, message.photo[-1].file_id
    if message.video:
        return MaterialKind.VIDEO, message.caption, message.video.file_id
    if message.document:
        return MaterialKind.DOCUMENT, message.caption, message.document.file_id
    if message.voice:
        return MaterialKind.VOICE, message.caption, message.voice.file_id
    if message.audio:
        return MaterialKind.AUDIO, message.caption, message.audio.file_id
    if message.video_note:
        return MaterialKind.VIDEO_NOTE, None, message.video_note.file_id
    if message.animation:
        return MaterialKind.ANIMATION, message.caption, message.animation.file_id
    if message.sticker:
        return MaterialKind.STICKER, None, message.sticker.file_id
    if message.text:
        return MaterialKind.TEXT, message.text, None
    return None


@router.message(F.from_user.func(lambda u: u.id in _admin_sessions), SaveMessage.waiting_for_name)
async def admin_receive_name(message: Message, state: FSMContext, session: AsyncSession) -> None:
    name = (message.text or "").strip()
    if not name:
        await message.answer("Please send a name for this message.")
        return

    data = await state.get_data()
    kind = MaterialKind(data["kind"])
    body = data.get("body")
    file_id = data.get("file_id")

    from app.repositories import materials as material_repo
    material = await material_repo.create(
        session,
        name=name,
        kind=kind,
        body=body,
        file_id=file_id,
        parse_mode=ParseMode.NONE,
        source_chat_id=data.get("source_chat_id"),
        source_message_id=data.get("source_message_id"),
    )
    await session.commit()
    await state.clear()

    kind_label = _KIND_LABELS.get(kind.value, kind.value)
    await message.answer(
        f"✅ *{name}* saved as a {kind_label} message\\.\n\n"
        f"You can now find it in *Messages* in the admin panel and add it to any Auto\\-flow\\. "
        f"It'll be sent exactly as you sent it just now.",
        parse_mode="MarkdownV2",
    )


@router.message(F.from_user.func(lambda u: u.id in _admin_sessions))
async def admin_receive_content(message: Message, state: FSMContext) -> None:
    content = _extract_content(message)
    if content is None:
        await message.answer(
            "⚠️ Unsupported type. Send a photo, video, voice note, audio, "
            "video note, GIF, sticker, document, or text message."
        )
        return

    kind, body, file_id = content
    await state.set_state(SaveMessage.waiting_for_name)
    await state.update_data(
        kind=kind.value,
        body=body,
        file_id=file_id,
        source_chat_id=message.chat.id,
        source_message_id=message.message_id,
    )

    kind_label = _KIND_LABELS.get(kind.value, kind.value)
    await message.answer(
        f"Got it — *{kind_label}* message\\.\n\nWhat do you want to call this message? "
        f"\\(e\\.g\\. _Welcome_, _Week 1 lesson_\\)",
        parse_mode="MarkdownV2",
    )


