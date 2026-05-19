from __future__ import annotations

from aiogram import Bot

from app.models.enums import MaterialKind, ParseMode
from app.models.material import Material


def _parse_mode(pm: ParseMode) -> str | None:
    return None if pm == ParseMode.NONE else pm.value


async def send_material(bot: Bot, chat_id: int, material: Material) -> None:
    """Dispatch a Material to a Telegram chat using the appropriate send method."""
    pm = _parse_mode(material.parse_mode)
    kind = material.kind

    if kind == MaterialKind.TEXT:
        await bot.send_message(
            chat_id,
            material.body or "",
            parse_mode=pm,
            disable_web_page_preview=material.disable_web_page_preview,
        )
    elif kind == MaterialKind.PHOTO:
        await bot.send_photo(
            chat_id,
            photo=material.file_id or material.file_url,
            caption=material.body,
            parse_mode=pm,
        )
    elif kind == MaterialKind.DOCUMENT:
        await bot.send_document(
            chat_id,
            document=material.file_id or material.file_url,
            caption=material.body,
            parse_mode=pm,
        )
    elif kind == MaterialKind.VIDEO:
        await bot.send_video(
            chat_id,
            video=material.file_id or material.file_url,
            caption=material.body,
            parse_mode=pm,
        )
    elif kind == MaterialKind.LINK:
        await bot.send_message(chat_id, material.link_url or "", parse_mode=None)
