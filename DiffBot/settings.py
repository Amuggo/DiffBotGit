import os
import json
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

SETTINGS_FILE = "user_settings.json"

def load_settings():
    """Загрузить настройки из файла"""
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_settings(settings):
    """Сохранить настройки в файл"""
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)

# Глобальное хранилище настроек
user_settings = load_settings()

def get_user_settings(user_id):
    """Получить настройки пользователя или создать стандартные"""
    user_id = str(user_id)
    if user_id not in user_settings:
        user_settings[user_id] = {
            'width': 512,
            'height': 512,
            'steps': 20,
            'guidance_scale': 7.5,
            'seed': -1,
            'model': "epicrealism_naturalSinRC1VAE"
        }
        save_settings(user_settings)
    return user_settings[user_id]

def save_user_settings(user_id, settings):
    """Сохранить настройки конкретного пользователя"""
    user_settings[str(user_id)] = settings
    save_settings(user_settings)

def reset_user_settings(user_id):
    """Сбросить настройки пользователя к стандартным"""
    user_settings[str(user_id)] = {
        'width': 512,
        'height': 512,
        'steps': 20,
        'guidance_scale': 7.5,
        'seed': -1,
        'model': "epicrealism_naturalSinRC1VAE"
    }
    save_settings(user_settings)

def get_settings_text(user_id):
    """Получить текст с текущими настройками"""
    settings = get_user_settings(user_id)
    return (f"⚙️ *Текущие настройки:*\n\n"
            f"📐 Размер: `{settings['width']}×{settings['height']}`\n"
            f"🔢 Шаги: `{settings['steps']}`\n"
            f"🎨 Denoising (CFG): `{settings['guidance_scale']}`\n"
            f"🎲 Seed: `{settings['seed'] if settings['seed'] != -1 else 'случайный'}`\n")

def main_settings_keyboard(user_id):
    """Главная клавиатура настроек"""
    settings = get_user_settings(user_id)
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    keyboard.add(
        InlineKeyboardButton(f"📐 {settings['width']}×{settings['height']}", callback_data="noop"),
        InlineKeyboardButton(f"🔢 {settings['steps']} steps", callback_data="noop"),
    )
    keyboard.add(
        InlineKeyboardButton(f"🎨 CFG: {settings['guidance_scale']}", callback_data="noop"),
        InlineKeyboardButton(f"🎲 Seed: {settings['seed'] if settings['seed'] != -1 else 'random'}", callback_data="noop"),
    )
    keyboard.add(
        InlineKeyboardButton("📏 Размер (предустановки)", callback_data="size_presets"),
        InlineKeyboardButton("✏️ Размер (свой)", callback_data="size_custom")
    )
    keyboard.add(
        InlineKeyboardButton("🔢 Шаги", callback_data="steps_menu"),
        InlineKeyboardButton("🎨 Denoising (CFG)", callback_data="cfg_menu")
    )
    keyboard.add(
        InlineKeyboardButton("🎲 Seed (случайный)", callback_data="seed_random"),
        InlineKeyboardButton("🔢 Seed (свой)", callback_data="seed_custom")
    )
    keyboard.add(
        InlineKeyboardButton("🔄 Сброс настроек", callback_data="reset_settings")
    )
    keyboard.add(
        InlineKeyboardButton("✨ Генерировать с этими настройками", callback_data="generate_from_settings")
    )
    
    return keyboard

def size_presets_keyboard():
    """Клавиатура с предустановками размера"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    sizes = [
        ("512×512", 512, 512),
        ("768×512", 768, 512),
        ("512×768", 512, 768),
        ("768×768", 768, 768),
        ("1024×1024", 1024, 1024),
        ("1024×768", 1024, 768),
        ("768×1024", 768, 1024)
    ]
    
    for label, w, h in sizes:
        keyboard.add(InlineKeyboardButton(label, callback_data=f"size_{w}_{h}"))
    
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_settings"))
    return keyboard

def steps_keyboard(current_steps):
    """Клавиатура выбора шагов"""
    keyboard = InlineKeyboardMarkup(row_width=4)
    steps_options = [15, 20, 25, 30, 35, 40, 45, 50]
    
    buttons = []
    for steps in steps_options:
        marker = "✅ " if steps == current_steps else ""
        buttons.append(InlineKeyboardButton(f"{marker}{steps}", callback_data=f"steps_{steps}"))
    
    keyboard.add(*buttons)
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_settings"))
    return keyboard

def cfg_keyboard(current_cfg):
    """Клавиатура выбора CFG scale"""
    keyboard = InlineKeyboardMarkup(row_width=3)
    cfg_options = [5.0, 6.0, 7.0, 7.5, 8.0, 9.0, 10.0, 12.0, 14.0, 16.0]
    
    buttons = []
    for cfg in cfg_options:
        marker = "✅ " if cfg == current_cfg else ""
        buttons.append(InlineKeyboardButton(f"{marker}{cfg}", callback_data=f"cfg_{cfg}"))
    
    keyboard.add(*buttons)
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_settings"))
    return keyboard

def handle_settings_callback(call, bot, user_id, data):
    """
    Обработать callback от настроек.
    Возвращает True если callback был обработан, иначе False
    """
    settings = get_user_settings(user_id)
    
    # noop — ничего не делаем
    if data == "noop":
        bot.answer_callback_query(call.id)
        return True
    
    # Размер (предустановки)
    elif data == "size_presets":
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                      reply_markup=size_presets_keyboard())
        return True
    
    # Размер (ручной ввод)
    elif data == "size_custom":
        bot.answer_callback_query(call.id, "Отправь ширину и высоту через пробел, например: 1024 768")
        bot.edit_message_text("✏️ Отправь размер картинки в формате:\n`ширина высота`\n\nПример: `1024 768`",
                            call.message.chat.id, call.message.message_id,
                            parse_mode='Markdown')
        # Возвращаем специальный флаг для внешней обработки
        call.is_custom_size = True
        return "need_custom_size"
    
    # Предустановка размера
    elif data.startswith("size_"):
        _, w, h = data.split("_")
        settings['width'] = int(w)
        settings['height'] = int(h)
        save_user_settings(user_id, settings)
        bot.answer_callback_query(call.id, f"✅ Размер: {w}×{h}")
        text = get_settings_text(user_id) + "\n👇 Продолжи настройку:"
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                            reply_markup=main_settings_keyboard(user_id), parse_mode='Markdown')
        return True
    
    # Шаги
    elif data == "steps_menu":
        current_steps = settings['steps']
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                      reply_markup=steps_keyboard(current_steps))
        return True
    
    elif data.startswith("steps_"):
        steps = int(data.split("_")[1])
        settings['steps'] = steps
        save_user_settings(user_id, settings)
        bot.answer_callback_query(call.id, f"✅ Шагов: {steps}")
        text = get_settings_text(user_id) + "\n👇 Продолжи настройку:"
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                            reply_markup=main_settings_keyboard(user_id), parse_mode='Markdown')
        return True
    
    # CFG
    elif data == "cfg_menu":
        current_cfg = settings['guidance_scale']
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                      reply_markup=cfg_keyboard(current_cfg))
        return True
    
    elif data.startswith("cfg_"):
        cfg = float(data.split("_")[1])
        settings['guidance_scale'] = cfg
        save_user_settings(user_id, settings)
        bot.answer_callback_query(call.id, f"✅ Denoising: {cfg}")
        text = get_settings_text(user_id) + "\n👇 Продолжи настройку:"
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                            reply_markup=main_settings_keyboard(user_id), parse_mode='Markdown')
        return True
    
    # Seed
    elif data == "seed_random":
        settings['seed'] = -1
        save_user_settings(user_id, settings)
        bot.answer_callback_query(call.id, "✅ Seed: случайный")
        text = get_settings_text(user_id) + "\n👇 Продолжи настройку:"
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                            reply_markup=main_settings_keyboard(user_id), parse_mode='Markdown')
        return True
    
    elif data == "seed_custom":
        bot.answer_callback_query(call.id, "Отправь число (seed)")
        bot.edit_message_text("✏️ Отправь seed (целое число):\n\n"
                            "Одинаковый seed + одинаковый промпт + одинаковые настройки = одинаковый результат",
                            call.message.chat.id, call.message.message_id)
        return "need_custom_seed"
    
    # Сброс
    elif data == "reset_settings":
        reset_user_settings(user_id)
        bot.answer_callback_query(call.id, "✅ Настройки сброшены!")
        text = get_settings_text(user_id) + "\n👇 Настрой параметры:"
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                            reply_markup=main_settings_keyboard(user_id), parse_mode='Markdown')
        return True
    
    # Назад
    elif data == "back_to_settings":
        text = get_settings_text(user_id) + "\n👇 Выбери, что изменить:"
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                            reply_markup=main_settings_keyboard(user_id), parse_mode='Markdown')
        return True
    
    # Генерация из настроек
    elif data == "generate_from_settings":
        bot.answer_callback_query(call.id, "📝 Отправь промпт")
        bot.edit_message_text("📝 *Отправь текстовый промпт на английском языке*\n\n"
                             "Пример: `a beautiful sunset over mountains, digital art, 4k`",
                             call.message.chat.id, call.message.message_id,
                             parse_mode='Markdown')
        return True
    
    return False