from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.telegram.keyboards import MENU_BUTTONS, main_menu
from app.telegram.service import handle_start, handle_stop

router = Router(name="main")

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
