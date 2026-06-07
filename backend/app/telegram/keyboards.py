from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app.models.menu_button import MenuButton


def build_menu(buttons: Sequence[MenuButton]) -> ReplyKeyboardMarkup:
    """Build a ReplyKeyboardMarkup from a list of MenuButton rows."""
    rows: dict[int, list[KeyboardButton]] = defaultdict(list)
    for btn in sorted(buttons, key=lambda b: (b.row, b.position)):
        rows[btn.row].append(KeyboardButton(text=btn.label))

    if not rows:
        return ReplyKeyboardMarkup(keyboard=[], resize_keyboard=True)

    return ReplyKeyboardMarkup(
        keyboard=[rows[r] for r in sorted(rows)],
        resize_keyboard=True,
        one_time_keyboard=False,
    )
