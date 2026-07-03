from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.enums import MaterialKind, ParseMode
from app.services.sender import send_material

CHAT_ID = 555


def _make_material(
    kind: MaterialKind,
    *,
    parse_mode: ParseMode = ParseMode.HTML,
    body: str | None = "caption text",
    file_id: str | None = "FILE_ID_123",
    file_url: str | None = "https://cdn.example/file",
    link_url: str | None = "https://example.com",
    disable_web_page_preview: bool = True,
    source_chat_id: int | None = None,
    source_message_id: int | None = None,
) -> MagicMock:
    material = MagicMock()
    material.kind = kind
    material.parse_mode = parse_mode
    material.body = body
    material.file_id = file_id
    material.file_url = file_url
    material.link_url = link_url
    material.disable_web_page_preview = disable_web_page_preview
    material.source_chat_id = source_chat_id
    material.source_message_id = source_message_id
    return material


@pytest.mark.asyncio
async def test_text_uses_send_message() -> None:
    bot = AsyncMock()
    material = _make_material(MaterialKind.TEXT, body="hello", parse_mode=ParseMode.HTML)

    await send_material(bot, CHAT_ID, material)

    bot.send_message.assert_awaited_once_with(
        CHAT_ID,
        "hello",
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    bot.send_photo.assert_not_awaited()
    bot.send_document.assert_not_awaited()
    bot.send_video.assert_not_awaited()


@pytest.mark.asyncio
async def test_text_falls_back_to_empty_string_when_body_none() -> None:
    bot = AsyncMock()
    material = _make_material(MaterialKind.TEXT, body=None, parse_mode=ParseMode.NONE)

    await send_material(bot, CHAT_ID, material)

    bot.send_message.assert_awaited_once_with(
        CHAT_ID,
        "",
        parse_mode=None,
        disable_web_page_preview=True,
    )


@pytest.mark.parametrize(
    ("kind", "method_name", "media_kwarg"),
    [
        (MaterialKind.PHOTO, "send_photo", "photo"),
        (MaterialKind.DOCUMENT, "send_document", "document"),
        (MaterialKind.VIDEO, "send_video", "video"),
    ],
)
@pytest.mark.asyncio
async def test_media_uses_file_id_when_present(
    kind: MaterialKind, method_name: str, media_kwarg: str
) -> None:
    bot = AsyncMock()
    material = _make_material(kind, parse_mode=ParseMode.MARKDOWN_V2)

    await send_material(bot, CHAT_ID, material)

    method = getattr(bot, method_name)
    method.assert_awaited_once_with(
        CHAT_ID,
        caption="caption text",
        parse_mode="MarkdownV2",
        **{media_kwarg: "FILE_ID_123"},
    )
    bot.send_message.assert_not_awaited()


@pytest.mark.parametrize(
    ("kind", "method_name", "media_kwarg"),
    [
        (MaterialKind.PHOTO, "send_photo", "photo"),
        (MaterialKind.DOCUMENT, "send_document", "document"),
        (MaterialKind.VIDEO, "send_video", "video"),
    ],
)
@pytest.mark.asyncio
async def test_media_falls_back_to_file_url_when_no_file_id(
    kind: MaterialKind, method_name: str, media_kwarg: str
) -> None:
    bot = AsyncMock()
    material = _make_material(kind, file_id=None)

    await send_material(bot, CHAT_ID, material)

    method = getattr(bot, method_name)
    method.assert_awaited_once_with(
        CHAT_ID,
        caption="caption text",
        parse_mode="HTML",
        **{media_kwarg: "https://cdn.example/file"},
    )


@pytest.mark.asyncio
async def test_link_uses_send_message_with_link_url_and_no_parse_mode() -> None:
    bot = AsyncMock()
    material = _make_material(
        MaterialKind.LINK, link_url="https://arabic.example", parse_mode=ParseMode.HTML
    )

    await send_material(bot, CHAT_ID, material)

    bot.send_message.assert_awaited_once_with(
        CHAT_ID,
        "https://arabic.example",
        parse_mode=None,
    )
    bot.send_photo.assert_not_awaited()


@pytest.mark.asyncio
async def test_link_falls_back_to_empty_string_when_link_url_none() -> None:
    bot = AsyncMock()
    material = _make_material(MaterialKind.LINK, link_url=None)

    await send_material(bot, CHAT_ID, material)

    bot.send_message.assert_awaited_once_with(
        CHAT_ID,
        "",
        parse_mode=None,
    )


@pytest.mark.parametrize(
    ("kind", "method_name", "media_kwarg"),
    [
        (MaterialKind.VOICE, "send_voice", "voice"),
        (MaterialKind.AUDIO, "send_audio", "audio"),
        (MaterialKind.ANIMATION, "send_animation", "animation"),
    ],
)
@pytest.mark.asyncio
async def test_captionable_media_kinds_use_file_id(
    kind: MaterialKind, method_name: str, media_kwarg: str
) -> None:
    bot = AsyncMock()
    material = _make_material(kind, parse_mode=ParseMode.MARKDOWN_V2)

    await send_material(bot, CHAT_ID, material)

    method = getattr(bot, method_name)
    method.assert_awaited_once_with(
        CHAT_ID,
        caption="caption text",
        parse_mode="MarkdownV2",
        **{media_kwarg: "FILE_ID_123"},
    )
    bot.send_message.assert_not_awaited()


@pytest.mark.parametrize(
    ("kind", "method_name", "media_kwarg"),
    [
        (MaterialKind.VIDEO_NOTE, "send_video_note", "video_note"),
        (MaterialKind.STICKER, "send_sticker", "sticker"),
    ],
)
@pytest.mark.asyncio
async def test_captionless_media_kinds_use_file_id(
    kind: MaterialKind, method_name: str, media_kwarg: str
) -> None:
    bot = AsyncMock()
    material = _make_material(kind)

    await send_material(bot, CHAT_ID, material)

    method = getattr(bot, method_name)
    method.assert_awaited_once_with(CHAT_ID, **{media_kwarg: "FILE_ID_123"})
    bot.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_captured_source_uses_copy_message_regardless_of_kind() -> None:
    """Any material captured via /admin mode is resent byte-for-byte via
    copy_message, bypassing the kind-specific send_* branches entirely."""
    bot = AsyncMock()
    material = _make_material(
        MaterialKind.PHOTO,
        source_chat_id=111,
        source_message_id=222,
    )

    await send_material(bot, CHAT_ID, material)

    bot.copy_message.assert_awaited_once_with(
        CHAT_ID, from_chat_id=111, message_id=222
    )
    bot.send_photo.assert_not_awaited()
    bot.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_captured_text_also_uses_copy_message() -> None:
    """Text captured via /admin mode preserves original formatting/entities
    that a plain body string + parse_mode can't reproduce."""
    bot = AsyncMock()
    material = _make_material(
        MaterialKind.TEXT,
        source_chat_id=111,
        source_message_id=333,
    )

    await send_material(bot, CHAT_ID, material)

    bot.copy_message.assert_awaited_once_with(
        CHAT_ID, from_chat_id=111, message_id=333
    )
    bot.send_message.assert_not_awaited()
