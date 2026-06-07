from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.telegram.keyboards import MENU_BUTTONS, main_menu
from app.telegram.service import handle_start, handle_stop

router = Router(name="main")

# In-memory set of Telegram IDs that have unlocked admin bot mode.
# Cleared on bot restart — teacher re-authenticates with /admin <password>.
_admin_sessions: set[int] = set()

_WELCOME = (
    "Assalomu alaykum! 👋\n\n"
    "Arabic tilini o'rganishga xush kelibsiz.\n"
    "Quyidagi tugmalardan birini tanlang:"
)

_STOP_TEXT = (
    "Siz ro'yxatdan chiqdingiz. Qaytishingizni istalgan vaqt kutamiz! 🤝\n"
    "Qayta boshlash uchun /start buyrug'ini yuboring."
)

_SETTINGS_TEXT = "⚙️ Sozlamalar (tez orada qo'shiladi)."

_MENU_RESPONSES: dict[str, str] = {
    "materials": (
        "📚 *Foydali materiallar*\n\n"
        "Darslik va qo'llanmalar tez orada qo'shiladi."
    ),
    "youtube": (
        "🎥 *YouTube darsliklar*\n\n"
        "Video darsliklar tez orada qo'shiladi."
    ),
    "pdf": (
        "📄 *PDF qo'llanmalar*\n\n"
        "PDF fayllar tez orada qo'shiladi."
    ),
    "about": (
        "ℹ️ *Kurs haqida*\n\n"
        "Kurs tafsilotlari tez orada qo'shiladi."
    ),
    "question": (
        "❓ *Savol yuborish*\n\n"
        "Savolingizni yozing, tez orada javob beramiz."
    ),
}


@router.message(CommandStart())
async def cmd_start(
    message: Message, command: CommandObject, session: AsyncSession
) -> None:
    payload = command.args  # text after /start, or None
    tg = message.from_user

    await handle_start(
        session,
        telegram_id=tg.id,
        chat_id=message.chat.id,
        username=tg.username,
        first_name=tg.first_name,
        last_name=tg.last_name,
        language_code=tg.language_code,
        campaign_slug=payload or None,
    )
    await message.answer(_WELCOME, reply_markup=main_menu())


@router.message(Command("stop"))
async def cmd_stop(message: Message, session: AsyncSession) -> None:
    await handle_stop(session, telegram_id=message.from_user.id)
    await message.answer(_STOP_TEXT)


@router.message(Command("settings"))
async def cmd_settings(message: Message) -> None:
    await message.answer(_SETTINGS_TEXT)


@router.message(F.text.in_(MENU_BUTTONS.keys()))
async def handle_menu_button(message: Message, session: AsyncSession) -> None:
    key = MENU_BUTTONS[message.text]
    user = await _get_or_none(session, message.from_user.id)
    user_id = user.id if user else None

    from app.repositories import events as event_repo

    await event_repo.log(
        session,
        type="menu_clicked",
        user_id=user_id,
        payload={"button": message.text, "key": key},
    )
    text = _MENU_RESPONSES.get(key, "Tez orada qo'shiladi.")
    await message.answer(text, parse_mode="Markdown")


async def _get_or_none(session, telegram_id: int):
    from app.repositories import users as user_repo
    return await user_repo.get_by_telegram_id(session, telegram_id)


@router.message(Command("admin"))
async def cmd_admin(message: Message, command: CommandObject) -> None:
    settings = get_settings()
    tid = message.from_user.id

    if not settings.ADMIN_BOT_PASSWORD:
        await message.answer("⚠️ Admin bot mode is not configured.")
        return

    arg = (command.args or "").strip()

    if arg == "logout":
        _admin_sessions.discard(tid)
        await message.answer("✅ Logged out of admin mode.")
        return

    if arg == settings.ADMIN_BOT_PASSWORD:
        _admin_sessions.add(tid)
        await message.answer(
            "✅ *Admin mode active.*\n\n"
            "Send me any message — photo, video, document, or text — "
            "and I'll reply with its Telegram file ID.\n\n"
            "Paste that ID into the admin panel under:\n"
            "*Messages → New Message → Advanced: use existing file ID*\n\n"
            "Send /admin logout to exit.",
            parse_mode="Markdown",
        )
        return

    await message.answer("❌ Wrong password.")


@router.message(F.from_user.func(lambda u: u.id in _admin_sessions))
async def admin_file_id(message: Message) -> None:
    lines: list[str] = []

    if message.photo:
        file_id = message.photo[-1].file_id
        lines.append(f"📷 *Kind:* photo")
        lines.append(f"`{file_id}`")
    elif message.video:
        lines.append(f"🎥 *Kind:* video")
        lines.append(f"`{message.video.file_id}`")
    elif message.document:
        lines.append(f"📄 *Kind:* document (file)")
        lines.append(f"`{message.document.file_id}`")
    elif message.text:
        lines.append("📝 *Kind:* text")
        lines.append("Copy the message text above and paste it into the *Message text* field.")
        await message.answer("\n".join(lines), parse_mode="Markdown")
        return
    else:
        await message.answer("⚠️ Unsupported message type. Send a photo, video, document, or text.")
        return

    lines.append("\nPaste this into *Messages → New Message → Advanced: use existing file ID*.")
    await message.answer("\n".join(lines), parse_mode="Markdown")
