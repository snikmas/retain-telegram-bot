from telegram import InlineKeyboardButton


def parse_photo(photo_obj, card_type=None):
    """
    For now, stores the file_id so we can send it back later.
    OCR / image-to-text can be added here.
    """
    return {'front': photo_obj.file_id, 'back': '', 'is_photo': True}


def parse_text(content, card_type=None):
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


def get_buttons(items, prefix):
    buttons = []
    for item in items:
        buttons.append([
            InlineKeyboardButton(
                item['name'],
                callback_data=f"{prefix}_{item['id']}"
            )
        ])
    return buttons
