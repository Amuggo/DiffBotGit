import os
import json
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import requests
from diffusion_api import generate_image

TOKEN = "8696382759:AAG7JkFL1FNfsV1rqUEmJE307MMkidcIMIc"
bot = telebot.TeleBot(TOKEN)

ALLOWED_USERS = [6738379690, 5233742292]
ALLOWED_USERS_FILE = "allowed_users.json"

# Файл для сохранения настроек пользователей
USER_SETTINGS_FILE = "user_settings.json"

def load_allowed_users():
    global ALLOWED_USERS
    if os.path.exists(ALLOWED_USERS_FILE):
        with open(ALLOWED_USERS_FILE, 'r') as f:
            ALLOWED_USERS = json.load(f)
    else:
        save_allowed_users()

def save_allowed_users():
    with open(ALLOWED_USERS_FILE, 'w') as f:
        json.dump(ALLOWED_USERS, f, indent=2)

def load_user_settings():
    if os.path.exists(USER_SETTINGS_FILE):
        with open(USER_SETTINGS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_user_settings(settings):
    with open(USER_SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)

def is_admin(user_id):
    return ALLOWED_USERS and ALLOWED_USERS[0] == user_id

load_allowed_users()
user_settings = load_user_settings()

def get_user_settings(user_id):
    user_id = str(user_id)
    if user_id not in user_settings:
        user_settings[user_id] = {
            'width': 512,
            'height': 512,
            'steps': 20,
            'guidance_scale': 7.5
        }
        save_user_settings(user_settings)
    return user_settings[user_id]

def save_user_settings_for_user(user_id, settings):
    user_settings[str(user_id)] = settings
    save_user_settings(user_settings)

def get_settings_text(user_id):
    s = get_user_settings(user_id)
    return (f"⚙️ *Текущие настройки:*\n\n"
            f"📐 Размер: `{s['width']}×{s['height']}`\n"
            f"🔢 Шаги: `{s['steps']}`\n"
            f"🎨 CFG: `{s['guidance_scale']}`")

def main_keyboard():
    """Главная клавиатура с кнопками (ReplyKeyboard)"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("🎨 Сгенерировать"),
        KeyboardButton("⚙️ Настройки")
    )
    keyboard.add(
        KeyboardButton("👥 Доступ"),
        KeyboardButton("ℹ️ Помощь")
    )
    return keyboard

def settings_keyboard():
    """Инлайн-клавиатура настроек"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📐 Размер", callback_data="menu_size"),
        InlineKeyboardButton("🔢 Шаги", callback_data="menu_steps"),
        InlineKeyboardButton("🎨 Denoising (CFG)", callback_data="menu_cfg"),
        InlineKeyboardButton("🔄 Сброс", callback_data="settings_reset"),
        InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")
    )
    return keyboard

def size_keyboard(current_width, current_height):
    """Клавиатура выбора размера"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    sizes = [
        ("512×512", 512, 512),
        ("768×512", 768, 512),
        ("512×768", 512, 768),
        ("768×768", 768, 768),
        ("1024×1024", 1024, 1024)
    ]
    for label, w, h in sizes:
        marker = "✅ " if w == current_width and h == current_height else ""
        keyboard.add(InlineKeyboardButton(f"{marker}{label}", callback_data=f"size_{w}_{h}"))
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_settings"))
    return keyboard

def steps_keyboard(current_steps):
    """Клавиатура выбора шагов"""
    keyboard = InlineKeyboardMarkup(row_width=4)
    steps_options = [15, 20, 25, 30, 35, 40]
    buttons = []
    for steps in steps_options:
        marker = "✅ " if steps == current_steps else ""
        buttons.append(InlineKeyboardButton(f"{marker}{steps}", callback_data=f"steps_{steps}"))
    keyboard.add(*buttons)
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_settings"))
    return keyboard

def cfg_keyboard(current_cfg):
    """Клавиатура выбора CFG"""
    keyboard = InlineKeyboardMarkup(row_width=3)
    cfg_options = [5.0, 6.0, 7.0, 7.5, 8.0, 9.0, 10.0]
    buttons = []
    for cfg in cfg_options:
        marker = "✅ " if cfg == current_cfg else ""
        buttons.append(InlineKeyboardButton(f"{marker}{cfg}", callback_data=f"cfg_{cfg}"))
    keyboard.add(*buttons)
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_settings"))
    return keyboard

def access_keyboard():
    """Инлайн-клавиатура управления доступом"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📋 Список пользователей", callback_data="access_list"),
        InlineKeyboardButton("➕ Добавить пользователя", callback_data="access_add"),
        InlineKeyboardButton("➖ Удалить пользователя", callback_data="access_remove"),
        InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")
    )
    return keyboard

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(
        message.chat.id,
        "🎨 *Привет! Я бот для генерации изображений через EasyDiffusion!*\n\n"
        "Просто отправь текстовый промпт на английском, и я сгенерирую картинку.\n\n"
        "👇 Используй кнопки для управления:",
        parse_mode='Markdown',
        reply_markup=main_keyboard()
    )

@bot.message_handler(func=lambda message: message.text == "🎨 Сгенерировать")
def prompt_generation(message):
    bot.reply_to(message, "📝 *Отправь промпт на английском:*", parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == "⚙️ Настройки")
def show_settings(message):
    if message.from_user.id not in ALLOWED_USERS:
        bot.reply_to(message, "🔒 Доступ закрыт.")
        return
    text = get_settings_text(message.from_user.id) + "\n\n👇 Что хочешь изменить?"
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=settings_keyboard())

@bot.message_handler(func=lambda message: message.text == "👥 Доступ")
def show_access(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "🔒 Только администратор.")
        return
    bot.send_message(message.chat.id, "👥 *Управление доступом*\n\nВыбери действие:", 
                     parse_mode='Markdown', reply_markup=access_keyboard())

@bot.message_handler(func=lambda message: message.text == "ℹ️ Помощь")
def show_help(message):
    bot.send_message(
        message.chat.id,
        "📖 *Помощь*\n\n"
        "• Отправь промпт на английском — получу картинку\n"
        "• Используй кнопку ⚙️ Настройки — измени параметры\n"
        "• Доступ только для разрешённых пользователей\n\n"
        "⚙️ *Что можно настроить:*\n"
        "📐 Размер — от 512×512 до 1024×1024\n"
        "🔢 Шаги — качество генерации (15-40)\n"
        "🎨 CFG — насколько сильно ИИ следует промпту",
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    
    if user_id not in ALLOWED_USERS:
        bot.answer_callback_query(call.id, "Доступ закрыт")
        return
    
    # Навигация
    if call.data == "back_to_main":
        bot.edit_message_text("🎨 *Главное меню*\n\nИспользуй кнопки ниже:", 
                            call.message.chat.id, call.message.message_id,
                            parse_mode='Markdown', reply_markup=None)
        bot.send_message(call.message.chat.id, "Выбери действие:", reply_markup=main_keyboard())
        bot.answer_callback_query(call.id)
        return
    
    if call.data == "back_to_settings":
        text = get_settings_text(user_id) + "\n\n👇 Что хочешь изменить?"
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                            parse_mode='Markdown', reply_markup=settings_keyboard())
        bot.answer_callback_query(call.id)
        return
    
    # Настройки
    if call.data == "menu_size":
        s = get_user_settings(user_id)
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                      reply_markup=size_keyboard(s['width'], s['height']))
        bot.answer_callback_query(call.id)
        return
    
    if call.data == "menu_steps":
        s = get_user_settings(user_id)
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                      reply_markup=steps_keyboard(s['steps']))
        bot.answer_callback_query(call.id)
        return
    
    if call.data == "menu_cfg":
        s = get_user_settings(user_id)
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                      reply_markup=cfg_keyboard(s['guidance_scale']))
        bot.answer_callback_query(call.id)
        return
    
    if call.data == "settings_reset":
        user_settings[str(user_id)] = {'width': 512, 'height': 512, 'steps': 20, 'guidance_scale': 7.5}
        save_user_settings(user_settings)
        bot.answer_callback_query(call.id, "✅ Настройки сброшены!")
        text = get_settings_text(user_id) + "\n\n👇 Что хочешь изменить?"
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                            parse_mode='Markdown', reply_markup=settings_keyboard())
        return
    
    # Изменение размера
    if call.data.startswith("size_"):
        _, w, h = call.data.split("_")
        s = get_user_settings(user_id)
        s['width'] = int(w)
        s['height'] = int(h)
        save_user_settings_for_user(user_id, s)
        bot.answer_callback_query(call.id, f"✅ Размер: {w}×{h}")
        text = get_settings_text(user_id) + "\n\n👇 Что хочешь изменить?"
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                            parse_mode='Markdown', reply_markup=settings_keyboard())
        return
    
    # Изменение шагов
    if call.data.startswith("steps_"):
        steps = int(call.data.split("_")[1])
        s = get_user_settings(user_id)
        s['steps'] = steps
        save_user_settings_for_user(user_id, s)
        bot.answer_callback_query(call.id, f"✅ Шагов: {steps}")
        text = get_settings_text(user_id) + "\n\n👇 Что хочешь изменить?"
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                            parse_mode='Markdown', reply_markup=settings_keyboard())
        return
    
    # Изменение CFG
    if call.data.startswith("cfg_"):
        cfg = float(call.data.split("_")[1])
        s = get_user_settings(user_id)
        s['guidance_scale'] = cfg
        save_user_settings_for_user(user_id, s)
        bot.answer_callback_query(call.id, f"✅ CFG: {cfg}")
        text = get_settings_text(user_id) + "\n\n👇 Что хочешь изменить?"
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                            parse_mode='Markdown', reply_markup=settings_keyboard())
        return
    
    # Управление доступом
    if call.data == "access_list":
        users = "\n".join([f"• `{uid}`" + (" 👑 админ" if i == 0 else "") for i, uid in enumerate(ALLOWED_USERS)])
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, f"📋 *Список пользователей:*\n\n{users}\n\nВсего: {len(ALLOWED_USERS)}", 
                        parse_mode='Markdown')
        return
    
    if call.data == "access_add":
        bot.answer_callback_query(call.id, "Отправь ID пользователя")
        bot.send_message(call.message.chat.id, "✏️ Отправь числовой ID пользователя для добавления:")
        bot.register_next_step_handler(call.message, add_user_step)
        return
    
    if call.data == "access_remove":
        if len(ALLOWED_USERS) <= 1:
            bot.answer_callback_query(call.id, "❌ Нельзя удалить единственного администратора!")
            return
        keyboard = InlineKeyboardMarkup(row_width=1)
        for uid in ALLOWED_USERS[1:]:
            keyboard.add(InlineKeyboardButton(str(uid), callback_data=f"remove_{uid}"))
        keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_access"))
        bot.edit_message_text("👥 *Выбери пользователя для удаления:*", 
                            call.message.chat.id, call.message.message_id,
                            reply_markup=keyboard, parse_mode='Markdown')
        bot.answer_callback_query(call.id)
        return
    
    if call.data.startswith("remove_"):
        uid = int(call.data.split("_")[1])
        if uid in ALLOWED_USERS:
            ALLOWED_USERS.remove(uid)
            save_allowed_users()
            bot.answer_callback_query(call.id, "✅ Пользователь удалён")
            bot.edit_message_text("✅ Пользователь удалён.", call.message.chat.id, call.message.message_id)
        return
    
    if call.data == "back_to_access":
        bot.edit_message_text("👥 *Управление доступом*\n\nВыбери действие:", 
                            call.message.chat.id, call.message.message_id,
                            parse_mode='Markdown', reply_markup=access_keyboard())
        bot.answer_callback_query(call.id)
        return

def add_user_step(message):
    if not is_admin(message.from_user.id):
        return
    try:
        new_id = int(message.text.strip())
        if new_id not in ALLOWED_USERS:
            ALLOWED_USERS.append(new_id)
            save_allowed_users()
            bot.reply_to(message, f"✅ Пользователь `{new_id}` добавлен.", parse_mode='Markdown')
        else:
            bot.reply_to(message, f"⚠️ Пользователь уже есть в списке.")
    except:
        bot.reply_to(message, "❌ Отправь числовой ID пользователя.")

@bot.message_handler(func=lambda message: True)
def handle_generation(message):
    if message.from_user.id not in ALLOWED_USERS:
        bot.reply_to(message, "🔒 Доступ закрыт.")
        return
    
    prompt = message.text
    if prompt.startswith('/') or prompt in ["🎨 Сгенерировать", "⚙️ Настройки", "👥 Доступ", "ℹ️ Помощь"]:
        return
    
    settings = get_user_settings(message.from_user.id)
    
    status_msg = bot.reply_to(message, 
        f"⏳ *Генерация началась...*\n\n"
        f"📐 {settings['width']}×{settings['height']}\n"
        f"🔢 {settings['steps']} steps\n"
        f"🎨 CFG: {settings['guidance_scale']}",
        parse_mode='Markdown'
    )
    
    filename = f"output_{message.from_user.id}.jpg"

    try:
        image_path = generate_image(
            prompt=prompt,
            output_filename=filename,
            width=settings['width'],
            height=settings['height'],
            steps=settings['steps'],
            guidance_scale=settings['guidance_scale']
        )
        
        with open(image_path, 'rb') as photo:
            bot.send_photo(message.chat.id, photo, 
                          caption=f"✨ *Готово!*\n\n📝 `{prompt[:100]}`",
                          parse_mode='Markdown')
            
        if os.path.exists(image_path):
            os.remove(image_path)
            
        bot.delete_message(message.chat.id, status_msg.message_id)

    except requests.exceptions.ConnectionError:
        bot.edit_message_text("❌ Не удалось подключиться к EasyDiffusion.", 
                            message.chat.id, status_msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"💥 Ошибка: {str(e)}", 
                            message.chat.id, status_msg.message_id)
        if os.path.exists(filename):
            os.remove(filename)

print("🤖 Бот запущен!")
bot.infinity_polling()