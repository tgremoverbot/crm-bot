from __future__ import annotations

from aiogram import Bot

from app.models.enums import MaterialKind, ParseMode
from app.models.material import Material


def _parse_mode(pm: ParseMode) -> str | None:
    return None if pm == ParseMode.NONE else pm.value


async def send_material(bot: Bot, chat_id: int, material: Material) -> None:
    """Dispatch a Material to a Telegram chat.

    Messages captured via the bot's /admin mode carry a source_chat_id +
    source_message_id and are resent with copy_message, which reproduces the
    original message exactly (media, caption, formatting) regardless of type.
    This is the primary path for anything other than text typed directly into
    the admin panel. Materials without a captured source (built by hand in the
    web form, or created before this feature existed) fall back to the
    kind-specific send below.
    """
    if material.source_chat_id is not None and material.source_message_id is not None:
        await bot.copy_message(
            chat_id,
            from_chat_id=material.source_chat_id,
            message_id=material.source_message_id,
        )
        return

    pm = _parse_mode(material.parse_mode)
    kind = material.kind
    file_ref = material.file_id or material.file_url

    if kind == MaterialKind.TEXT:
        await bot.send_message(
            chat_id,
            material.body or "",
            parse_mode=pm,
            disable_web_page_preview=material.disable_web_page_preview,
        )
    elif kind == MaterialKind.PHOTO:
        await bot.send_photo(chat_id, photo=file_ref, caption=material.body, parse_mode=pm)
    elif kind == MaterialKind.DOCUMENT:
        await bot.send_document(chat_id, document=file_ref, caption=material.body, parse_mode=pm)
    elif kind == MaterialKind.VIDEO:
        await bot.send_video(chat_id, video=file_ref, caption=material.body, parse_mode=pm)
    elif kind == MaterialKind.VOICE:
        await bot.send_voice(chat_id, voice=file_ref, caption=material.body, parse_mode=pm)
    elif kind == MaterialKind.AUDIO:
        await bot.send_audio(chat_id, audio=file_ref, caption=material.body, parse_mode=pm)
    elif kind == MaterialKind.VIDEO_NOTE:
        await bot.send_video_note(chat_id, video_note=file_ref)
    elif kind == MaterialKind.ANIMATION:
        await bot.send_animation(chat_id, animation=file_ref, caption=material.body, parse_mode=pm)
    elif kind == MaterialKind.STICKER:
        await bot.send_sticker(chat_id, sticker=file_ref)
    elif kind == MaterialKind.LINK:
        await bot.send_message(chat_id, material.link_url or "", parse_mode=None)
