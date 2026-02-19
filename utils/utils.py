from telegram import InlineKeyboardButton, PhotoSize


def parse_photo(photo_obj: PhotoSize, caption: str | None = None) -> dict[str, str | bool]:
    """Stores the file_id as front. Caption (if any) becomes the back."""
    return {'front': photo_obj.file_id, 'back': caption.strip() if caption else '', 'is_photo': True}


def parse_text(content: str, card_type: str | None = None) -> dict[str, str]:
    """
    returns: {'front': str, 'back': str}
    """
    text = content.strip()

    if '|' in text:
        parts = text.split('|', 1)
        return {'front': parts[0].strip(), 'back': parts[1].strip()}

    if '\n' in text:
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if len(lines) >= 2:
            return {'front': lines[0], 'back': '\n'.join(lines[1:])}

    return {'front': text, 'back': ''}


def get_buttons(items: list[dict[str, str | int]], prefix: str) -> list[list[InlineKeyboardButton]]:
    buttons: list[list[InlineKeyboardButton]] = []
    for item in items:
        buttons.append([
            InlineKeyboardButton(
                item['name'],
                callback_data=f"{prefix}_{item['id']}"
            )
        ])
    return buttons
