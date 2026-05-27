import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import requests
from diffusion_api import generate_image 

TOKEN = "8696382759:AAG7JkFL1FNfsV1rqUEmJE307MMkidcIMIc"
bot = telebot.TeleBot(TOKEN)

ALLOWED_USERS = [6738379690, 5233742292]

# Хранилище настроек для каждого пользователя
user_settings = {}

def get_user_settings(user_id):
    """Получить настройки пользователя или создать стандартные"""
    if user_id not in user_settings:
        user_settings[user_id] = {
            'width': 512,
            'height': 512,
            'steps': 20,
            'guidance_scale': 7.5  # это и есть denoising (CFG scale)
        }
    return user_settings[user_id]

def settings_keyboard(user_id):
    """Создать клавиатуру с текущими настройками"""
    settings = get_user_settings(user_id)
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    # Кнопки размера
    keyboard.add(
        InlineKeyboardButton(f"📐 Размер: {settings['width']}×{settings['height']}", callback_data="size_menu")
    )
    
    # Кнопки шагов и денойзинга
    keyboard.add(
        InlineKeyboardButton(f"🔢 Шаги: {settings['steps']}", callback_data="steps_menu"),
        InlineKeyboardButton(f"🎨 Denoising: {settings['guidance_scale']}", callback_data="cfg_menu")
    )
    
    # Кнопка сброса
    keyboard.add(
        InlineKeyboardButton("🔄 Сбросить настройки", callback_data="reset_settings")
    )
    
    # Кнопка генерации
    keyboard.add(
        InlineKeyboardButton("✨ Готово, генерируй!", callback_data="generate_from_settings")
    )
    
    return keyboard

def size_keyboard():
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
        keyboard.add(InlineKeyboardButton(label, callback_data=f"size_{w}_{h}"))
    
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_settings"))
    return keyboard

def steps_keyboard(current_steps):
    """Клавиатура выбора количества шагов"""
    keyboard = InlineKeyboardMarkup(row_width=3)
    steps_options = [15, 20, 25, 30, 35, 40]
    
    buttons = []
    for steps in steps_options:
        marker = "✅ " if steps == current_steps else ""
        buttons.append(InlineKeyboardButton(f"{marker}{steps}", callback_data=f"steps_{steps}"))
    
    keyboard.add(*buttons)
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_settings"))
    return keyboard

def cfg_keyboard(current_cfg):
    """Клавиатура выбора denoising (CFG scale)"""
    keyboard = InlineKeyboardMarkup(row_width=3)
    cfg_options = [5.0, 6.0, 7.0, 7.5, 8.0, 9.0, 10.0, 12.0]
    
    buttons = []
    for cfg in cfg_options:
        marker = "✅ " if cfg == current_cfg else ""
        buttons.append(InlineKeyboardButton(f"{marker}{cfg}", callback_data=f"cfg_{cfg}"))
    
    keyboard.add(*buttons)
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_settings"))
    return keyboard

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, 
        "🎨 Привет! Я бот для генерации изображений через EasyDiffusion!\n\n"
        "📝 Как использовать:\n"
        "1. Нажми /settings чтобы настроить параметры\n"
        "2. Или просто отправь мне текстовый промпт на английском\n\n"
        "⚙️ Можно менять:\n"
        "• Размер картинки\n"
        "• Количество шагов (качество генерации)\n"
        "• Denoising (насколько сильно меняется картинка)"
    )

@bot.message_handler(commands=['settings'])
def show_settings(message):
    """Показать текущие настройки"""
    user_id = message.from_user.id
    if user_id not in ALLOWED_USERS:
        bot.reply_to(message, "🔒 Доступ закрыт.")
        return
    
    settings = get_user_settings(user_id)
    text = (f"⚙️ *Текущие настройки:*\n\n"
            f"📐 Размер: `{settings['width']}×{settings['height']}`\n"
            f"🔢 Шаги: `{settings['steps']}`\n"
            f"🎨 Denoising (CFG): `{settings['guidance_scale']}`\n\n"
            f"👇 Нажми на кнопку, чтобы изменить параметр:")
    
    bot.send_message(message.chat.id, text, 
                     reply_markup=settings_keyboard(user_id),
                     parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    if user_id not in ALLOWED_USERS:
        bot.answer_callback_query(call.id, "Доступ закрыт")
        return
    
    if call.data == "size_menu":
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                      reply_markup=size_keyboard())
    
    elif call.data == "steps_menu":
        current_steps = get_user_settings(user_id)['steps']
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                      reply_markup=steps_keyboard(current_steps))
    
    elif call.data == "cfg_menu":
        current_cfg = get_user_settings(user_id)['guidance_scale']
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                      reply_markup=cfg_keyboard(current_cfg))
    
    elif call.data.startswith("size_"):
        _, w, h = call.data.split("_")
        settings = get_user_settings(user_id)
        settings['width'] = int(w)
        settings['height'] = int(h)
        bot.answer_callback_query(call.id, f"✅ Размер изменён на {w}×{h}")
        
        # Обновляем клавиатуру
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                      reply_markup=settings_keyboard(user_id))
    
    elif call.data.startswith("steps_"):
        steps = int(call.data.split("_")[1])
        settings = get_user_settings(user_id)
        settings['steps'] = steps
        bot.answer_callback_query(call.id, f"✅ Шагов: {steps}")
        
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                      reply_markup=settings_keyboard(user_id))
    
    elif call.data.startswith("cfg_"):
        cfg = float(call.data.split("_")[1])
        settings = get_user_settings(user_id)
        settings['guidance_scale'] = cfg
        bot.answer_callback_query(call.id, f"✅ Denoising: {cfg}")
        
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                      reply_markup=settings_keyboard(user_id))
    
    elif call.data == "reset_settings":
        user_settings[user_id] = {
            'width': 512,
            'height': 512,
            'steps': 20,
            'guidance_scale': 7.5
        }
        bot.answer_callback_query(call.id, "✅ Настройки сброшены!")
        
        bot.edit_message_text("⚙️ *Настройки сброшены к стандартным:*\n\n"
                             "📐 Размер: `512×512`\n"
                             "🔢 Шаги: `20`\n"
                             "🎨 Denoising: `7.5`\n\n"
                             "👇 Настройте параметры:",
                             call.message.chat.id,
                             call.message.message_id,
                             reply_markup=settings_keyboard(user_id),
                             parse_mode='Markdown')
    
    elif call.data == "back_to_settings":
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                      reply_markup=settings_keyboard(user_id))
    
    elif call.data == "generate_from_settings":
        bot.answer_callback_query(call.id, "🎨 Начинаю генерацию...")
        # Вызываем генерацию с текущим промптом
        # Для этого нужно сохранить последний промпт пользователя
        # Пока просто закроем меню и скажем отправить промпт
        bot.edit_message_text("📝 Отправьте текстовый промпт на английском языке, "
                             "и я сгенерирую картинку с вашими настройками.",
                             call.message.chat.id,
                             call.message.message_id)
        bot.clear_step_handler_by_chat_id(call.message.chat.id)

@bot.message_handler(func=lambda message: True)
def handle_generation(message):
    if message.from_user.id not in ALLOWED_USERS:
        bot.reply_to(message, "🔒 Доступ закрыт. Этот бот приватный.")
        return
        
    prompt = message.text
    if prompt.startswith('/'):
        return
    
    # Получаем настройки пользователя
    settings = get_user_settings(message.from_user.id)
    
    # Показываем статус
    status_msg = bot.reply_to(message, 
        f"⏳ Генерация началась...\n"
        f"📐 {settings['width']}×{settings['height']} | "
        f"🔢 {settings['steps']} шагов | "
        f"🎨 CFG: {settings['guidance_scale']}\n"
        f"🎨 Промпт: {prompt[:50]}..."
    )
    
    filename = f"output_{message.from_user.id}.jpg"

    try:
        # Передаём настройки в функцию генерации
        image_path = generate_image(
            prompt=prompt,
            output_filename=filename,
            width=settings['width'],
            height=settings['height'],
            steps=settings['steps'],
            guidance_scale=settings['guidance_scale']
        )
        
        # Отправляем результат
        with open(image_path, 'rb') as photo:
            caption = (f"✨ *Готово!*\n\n"
                      f"📝 Промпт: `{prompt}`\n"
                      f"📐 {settings['width']}×{settings['height']}\n"
                      f"🔢 {settings['steps']} шагов\n"
                      f"🎨 CFG: {settings['guidance_scale']}")
            
            bot.send_photo(message.chat.id, photo, 
                          caption=caption,
                          parse_mode='Markdown')
            
        # Удаляем временный файл
        if os.path.exists(image_path):
            os.remove(image_path)
            
        # Удаляем статусное сообщение
        bot.delete_message(message.chat.id, status_msg.message_id)

    except requests.exceptions.ConnectionError:
        bot.edit_message_text("❌ Не удалось подключиться к EasyDiffusion. Проверьте, запущен ли сервер на ПК.", 
                            message.chat.id, status_msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"💥 Ошибка: {str(e)}", 
                            message.chat.id, status_msg.message_id)
        if os.path.exists(filename):
            os.remove(filename)

print("🤖 Бот-генератор с настройками запущен...")
bot.infinity_polling()