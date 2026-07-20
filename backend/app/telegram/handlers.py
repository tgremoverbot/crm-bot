from __future__ import annotations

from datetime import datetime, timezone

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.broadcast import BroadcastStatus
from app.models.enums import MaterialKind, ParseMode
from app.telegram.service import handle_start, handle_stop

router = Router(name="main")

# In-memory set of Telegram IDs that have unlocked admin bot mode.
_admin_sessions: set[int] = set()


class SaveMessage(StatesGroup):
    waiting_for_name = State()


class SendToAll(StatesGroup):
    waiting_for_post = State()
    waiting_for_confirm = State()


_BTN_SEND_ALL = "📣 Send to everyone"
_BTN_CANCEL = "❌ Cancel"

_ADMIN_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=_BTN_SEND_ALL)]],
    resize_keyboard=True,
    is_persistent=True,
)

_CONFIRM_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Send now", callback_data="bcast:send"),
            InlineKeyboardButton(text="❌ Cancel", callback_data="bcast:cancel"),
        ]
    ]
)

_CANCEL_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=_BTN_CANCEL)]],
    resize_keyboard=True,
    is_persistent=True,
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
        await message.answer(
            "✅ Logged out of admin mode.", reply_markup=ReplyKeyboardRemove()
        )
        return

    if arg == settings.ADMIN_BOT_PASSWORD.strip():
        _admin_sessions.add(tid)
        await message.answer(
            "✅ *Admin mode active.*\n\n"
            "Send me any message — photo, video, document, or text — "
            "and I'll ask you what to call it, then save it so you can use it in Auto-flows.\n\n"
            "Or tap *📣 Send to everyone* to broadcast a post to all subscribers "
            "right away.\n\n"
            "Send /admin logout to exit.",
            parse_mode="Markdown",
            reply_markup=_ADMIN_KEYBOARD,
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


def _is_admin(user) -> bool:
    return user.id in _admin_sessions


@router.message(
    F.from_user.func(_is_admin),
    (F.text == _BTN_CANCEL) | (F.text == "/cancel"),
)
async def admin_cancel(message: Message, state: FSMContext) -> None:
    """Escape hatch out of any admin sub-flow, back to the default save mode."""
    await state.clear()
    await message.answer(
        "Cancelled. Send me a message to save it, or tap 📣 Send to everyone.",
        reply_markup=_ADMIN_KEYBOARD,
    )


@router.message(F.from_user.func(_is_admin), F.text == _BTN_SEND_ALL)
async def admin_send_to_all_start(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    from app.repositories import broadcasts as broadcast_repo

    count = await broadcast_repo.count_recipients(session, None)
    if count == 0:
        await message.answer(
            "⚠️ There are no active subscribers to send to yet.",
            reply_markup=_ADMIN_KEYBOARD,
        )
        return

    await state.clear()
    await state.set_state(SendToAll.waiting_for_post)
    await message.answer(
        f"📣 Broadcast mode.\n\n"
        f"Send or forward the post you want to deliver to all *{count}* "
        f"subscribers. It'll go out exactly as you send it here.\n\n"
        f"I'll ask you to confirm before anything is sent.",
        parse_mode="Markdown",
        reply_markup=_CANCEL_KEYBOARD,
    )


@router.message(F.from_user.func(_is_admin), SendToAll.waiting_for_post)
async def admin_broadcast_receive_post(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    content = _extract_content(message)
    if content is None:
        await message.answer(
            "⚠️ Unsupported type. Send a photo, video, voice note, audio, "
            "video note, GIF, sticker, document, or text message."
        )
        return

    from app.repositories import broadcasts as broadcast_repo

    kind, body, file_id = content
    count = await broadcast_repo.count_recipients(session, None)

    await state.set_state(SendToAll.waiting_for_confirm)
    await state.update_data(
        kind=kind.value,
        body=body,
        file_id=file_id,
        source_chat_id=message.chat.id,
        source_message_id=message.message_id,
    )

    kind_label = _KIND_LABELS.get(kind.value, kind.value)
    await message.answer(
        f"Ready to broadcast this *{kind_label}* post (shown above) to "
        f"*{count}* subscribers.\n\nSend it?",
        parse_mode="Markdown",
        reply_markup=_CONFIRM_KEYBOARD,
    )


@router.callback_query(F.data == "bcast:cancel")
async def admin_broadcast_cancel(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await query.message.edit_reply_markup(reply_markup=None)
    await query.message.answer(
        "Cancelled — nothing was sent.", reply_markup=_ADMIN_KEYBOARD
    )
    await query.answer()


@router.callback_query(F.data == "bcast:send")
async def admin_broadcast_confirm(
    query: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot
) -> None:
    if not _is_admin(query.from_user):
        await query.answer("Admin mode is not active.", show_alert=True)
        return

    data = await state.get_data()
    if await state.get_state() != SendToAll.waiting_for_confirm.state or not data:
        await query.answer("This broadcast has expired. Start again.", show_alert=True)
        return

    from app.repositories import broadcasts as broadcast_repo
    from app.repositories import materials as material_repo
    from app.services import broadcast as broadcast_service

    await state.clear()
    await query.message.edit_reply_markup(reply_markup=None)
    await query.answer()

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    material = await material_repo.create(
        session,
        name=f"Broadcast {stamp}",
        kind=MaterialKind(data["kind"]),
        body=data.get("body"),
        file_id=data.get("file_id"),
        parse_mode=ParseMode.NONE,
        source_chat_id=data.get("source_chat_id"),
        source_message_id=data.get("source_message_id"),
    )
    bc = await broadcast_repo.create(
        session,
        name=f"Bot broadcast {stamp}",
        material_id=material.id,
        segment_id=None,
        notify_chat_id=query.message.chat.id,
    )

    recipients = await broadcast_repo.count_recipients(session, None)
    if recipients > broadcast_service.INLINE_SEND_LIMIT:
        # Too many to send inside this webhook request without risking a
        # Telegram timeout and a retried (duplicate) update. SCHEDULED with no
        # scheduled_at is due immediately, so the next scheduler tick takes it
        # and reports back to notify_chat_id.
        bc.status = BroadcastStatus.SCHEDULED
        await session.commit()
        await query.message.answer(
            f"📤 Queued for {recipients} subscribers. Sending starts within a "
            f"minute — I'll report back here when it's done.",
            reply_markup=_ADMIN_KEYBOARD,
        )
        return

    # Small audience: send inline so the admin gets the result immediately.
    # send_broadcast flips the status to SENDING before the first recipient, so
    # a concurrent scheduler tick can never pick this up as well.
    await session.commit()
    await query.message.answer(f"📤 Sending to {recipients} subscribers…")
    result = await broadcast_service.send_broadcast(session, bot, bc)
    await query.message.answer(
        broadcast_service.format_report(result), reply_markup=_ADMIN_KEYBOARD
    )


@router.message(F.from_user.func(_is_admin), SaveMessage.waiting_for_name)
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


@router.message(F.from_user.func(_is_admin))
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


