from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

MENU_BUTTONS = {
    "📚 Foydali materiallar": "materials",
    "🎥 YouTube darsliklar": "youtube",
    "📄 PDF qo'llanmalar": "pdf",
    "ℹ️ Kurs haqida": "about",
    "❓ Savol yuborish": "question",
}


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📚 Foydali materiallar"),
                KeyboardButton(text="🎥 YouTube darsliklar"),
            ],
            [
                KeyboardButton(text="📄 PDF qo'llanmalar"),
                KeyboardButton(text="ℹ️ Kurs haqida"),
            ],
            [KeyboardButton(text="❓ Savol yuborish")],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )
