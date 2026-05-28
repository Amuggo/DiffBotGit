import os
import json
import time
import shutil
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import requests
from diffusion_api import generate_image
from upscale_api import upscale_image, AVAILABLE_UPSCALE_MODELS
from settings import (
    get_user_settings, save_user_settings, get_settings_text, 
    handle_settings_callback, main_settings_keyboard
)
PHOTO_STORAGE = "generated_photos"
os.makedirs(PHOTO_STORAGE, exist_ok=True)
TOKEN = "8696382759:AAG7JkFL1FNfsV1rqUEmJE307MMkidcIMIc"
bot = telebot.TeleBot(TOKEN)

ALLOWED_USERS_FILE = "allowed_users.json"

def load_allowed_users():
    global ALLOWED_USERS
    if os.path.exists(ALLOWED_USERS_FILE):
        with open(ALLOWED_USERS_FILE, 'r') as f:
            ALLOWED_USERS = json.load(f)
    else:
        ALLOWED_USERS = [6738379690, 5233742292]
        save_allowed_users()

def save_allowed_users():
    with open(ALLOWED_USERS_FILE, 'w') as f:
        json.dump(ALLOWED_USERS, f, indent=2)

def is_admin(user_id):
    return ALLOWED_USERS and ALLOWED_USERS[0] == user_id

load_allowed_users()

# Папка для хранения сгенерированных картинок (не удаляем сразу)
PHOTO_STORAGE = "generated_photos"
os.makedirs(PHOTO_STORAGE, exist_ok=True)

# Хранилища
last_photo = {}  # user_id -> путь к последней картинке
user_state = {}  # временные состояния

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, 
        "🎨 *Бот для генерации изображений Stable Diffusion*\n\n"
        "📝 *Как использовать:*\n"
        "1. Нажми /settings — настрой параметры\n"
        "2. Или просто отправь промпт\n\n"
        "⚙️ *Команды:*\n"
        "/settings — настройки\n"
        "/access — управление доступом (админ)\n"
        "/upscale — увеличить последнюю картинку\n"
        "/last — показать последнюю картинку",
        parse_mode='Markdown')

@bot.message_handler(commands=['settings'])
def show_settings(message):
    if message.from_user.id not in ALLOWED_USERS:
        bot.reply_to(message, "🔒 Доступ закрыт.")
        return
    
    text = get_settings_text(message.from_user.id) + "\n👇 Выбери, что изменить:"
    bot.send_message(message.chat.id, text, 
                     reply_markup=main_settings_keyboard(message.from_user.id),
                     parse_mode='Markdown')

@bot.message_handler(commands=['access'])
def manage_access(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "🔒 Только администратор.")
        return
    
    keyboard = ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(KeyboardButton("📱 Отправить контакт", request_contact=True))
    
    bot.reply_to(message, "👥 *Управление доступом*\n\nНажми кнопку или отправь ID числом:", 
                 reply_markup=keyboard, parse_mode='Markdown')
    
    inline_keyboard = InlineKeyboardMarkup(row_width=2)
    inline_keyboard.add(
        InlineKeyboardButton("📋 Список", callback_data="access_list"),
        InlineKeyboardButton("❌ Удалить", callback_data="access_remove_menu")
    )
    bot.send_message(message.chat.id, "Действия:", reply_markup=inline_keyboard)

@bot.message_handler(commands=['upscale'])
def handle_upscale_command(message):
    user_id = message.from_user.id
    if user_id not in ALLOWED_USERS:
        bot.reply_to(message, "🔒 Доступ закрыт.")
        return
    
    if user_id not in last_photo or not os.path.exists(last_photo[user_id]):
        bot.reply_to(message, "❌ Нет картинки для увеличения. Сначала сгенерируй изображение или используй /last чтобы показать последнюю.")
        return
    
    # Сохраняем пользователя в состоянии
    user_state[user_id] = {'step': 'select_scale'}
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🔼 2x", callback_data="upscale_scale_2"),
        InlineKeyboardButton("🔼 4x", callback_data="upscale_scale_4")
    )
    keyboard.add(InlineKeyboardButton("🔙 Отмена", callback_data="upscale_cancel"))
    
    bot.reply_to(message, "🔍 *Upscale*\n\nВыбери коэффициент увеличения:", 
                 reply_markup=keyboard, parse_mode='Markdown')

@bot.message_handler(commands=['last'])
def show_last_photo(message):
    """Показать последнюю сгенерированную картинку"""
    user_id = message.from_user.id
    if user_id not in ALLOWED_USERS:
        bot.reply_to(message, "🔒 Доступ закрыт.")
        return
    
    if user_id not in last_photo or not os.path.exists(last_photo[user_id]):
        bot.reply_to(message, "❌ Нет сохранённой картинки. Сначала сгенерируй изображение.")
        return
    
    with open(last_photo[user_id], 'rb') as photo:
        bot.send_photo(message.chat.id, photo, caption="🖼 Твоя последняя картинка\n\n🔼 /upscale — увеличить")

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    if not is_admin(message.from_user.id):
        return
    
    contact_user_id = message.contact.user_id
    name = f"{message.contact.first_name or ''} {message.contact.last_name or ''}".strip()
    
    if contact_user_id not in ALLOWED_USERS:
        ALLOWED_USERS.append(contact_user_id)
        save_allowed_users()
        bot.reply_to(message, f"✅ {name} (ID: `{contact_user_id}`) добавлен.", parse_mode='Markdown')
    else:
        bot.reply_to(message, f"⚠️ {name} уже в списке.")

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    if user_id not in ALLOWED_USERS:
        bot.answer_callback_query(call.id, "Доступ закрыт")
        return
    
    data = call.data
    
    # ===== УПРАВЛЕНИЕ ДОСТУПОМ =====
    if data == "access_list":
        users_list = "\n".join([f"• `{uid}`" + (" 👑 админ" if i == 0 else "") for i, uid in enumerate(ALLOWED_USERS)])
        bot.send_message(call.message.chat.id, f"📋 *Список:*\n\n{users_list}", parse_mode='Markdown')
        bot.answer_callback_query(call.id)
        return
    
    elif data == "access_remove_menu":
        if len(ALLOWED_USERS) <= 1:
            bot.answer_callback_query(call.id, "❌ Нельзя удалить админа")
            return
        
        keyboard = InlineKeyboardMarkup(row_width=1)
        for uid in ALLOWED_USERS[1:]:
            try:
                user = bot.get_chat(uid)
                name = f"{user.first_name or ''} {user.last_name or ''}".strip() or str(uid)
            except:
                name = str(uid)
            keyboard.add(InlineKeyboardButton(f"❌ {name[:30]}", callback_data=f"remove_{uid}"))
        keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_access"))
        
        bot.edit_message_text("👥 *Выбери пользователя:*", call.message.chat.id, 
                            call.message.message_id, reply_markup=keyboard, parse_mode='Markdown')
        bot.answer_callback_query(call.id)
        return
    
    elif data.startswith("remove_"):
        uid_to_remove = int(data.split("_")[1])
        if uid_to_remove in ALLOWED_USERS:
            ALLOWED_USERS.remove(uid_to_remove)
            save_allowed_users()
            bot.answer_callback_query(call.id, "✅ Удалён")
            bot.edit_message_text("✅ Пользователь удалён.", call.message.chat.id, call.message.message_id)
        return
    
    elif data == "back_to_access":
        inline_keyboard = InlineKeyboardMarkup(row_width=2)
        inline_keyboard.add(
            InlineKeyboardButton("📋 Список", callback_data="access_list"),
            InlineKeyboardButton("❌ Удалить", callback_data="access_remove_menu")
        )
        bot.edit_message_text("👥 *Управление доступом*", call.message.chat.id,
                            call.message.message_id, reply_markup=inline_keyboard, parse_mode='Markdown')
        return
    
    # ===== UPSCALE =====
    elif data == "upscale_cancel":
        if user_id in user_state:
            del user_state[user_id]
        bot.edit_message_text("❌ Upscale отменён.", call.message.chat.id, call.message.message_id)
        bot.answer_callback_query(call.id)
        return
    
    elif data == "upscale_scale_2":
        if user_id not in user_state:
            user_state[user_id] = {}
        user_state[user_id]['scale'] = 2
        user_state[user_id]['step'] = 'select_model'
        show_model_menu(call.message, user_id)
        bot.answer_callback_query(call.id)
        return
    
    elif data == "upscale_scale_4":
        if user_id not in user_state:
            user_state[user_id] = {}
        user_state[user_id]['scale'] = 4
        user_state[user_id]['step'] = 'select_model'
        show_model_menu(call.message, user_id)
        bot.answer_callback_query(call.id)
        return
    
    elif data.startswith("upscale_model_"):
        model = data.replace("upscale_model_", "")
        user_state[user_id]['model'] = model
        user_state[user_id]['step'] = 'select_face'
        show_face_menu(call.message, user_id)
        bot.answer_callback_query(call.id)
        return
    
    elif data == "upscale_face_on":
        user_state[user_id]['face'] = True
        start_upscale(call.message, user_id)
        bot.answer_callback_query(call.id)
        return
    
    elif data == "upscale_face_off":
        user_state[user_id]['face'] = False
        start_upscale(call.message, user_id)
        bot.answer_callback_query(call.id)
        return
    
    # ===== НАСТРОЙКИ (вызываем из settings.py) =====
    result = handle_settings_callback(call, bot, user_id, data)
    
    if result == "need_custom_size":
        bot.register_next_step_handler_by_chat_id(call.message.chat.id, handle_custom_size)
    elif result == "need_custom_seed":
        bot.register_next_step_handler_by_chat_id(call.message.chat.id, handle_custom_seed)

def show_model_menu(message, user_id):
    """Показать меню выбора модели апскейла"""
    keyboard = InlineKeyboardMarkup(row_width=1)
    
    for model_id, model_name in AVAILABLE_UPSCALE_MODELS.items():
        keyboard.add(InlineKeyboardButton(f"📷 {model_name}", callback_data=f"upscale_model_{model_id}"))
    
    keyboard.add(InlineKeyboardButton("🔙 Отмена", callback_data="upscale_cancel"))
    
    bot.edit_message_text(
        f"🔍 *Upscale {user_state[user_id]['scale']}x*\n\n"
        f"📷 Выбери модель апскейла:",
        message.chat.id,
        message.message_id,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

def show_face_menu(message, user_id):
    """Показать меню выбора восстановления лиц"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("✅ Включить (GFPGAN)", callback_data="upscale_face_on"),
        InlineKeyboardButton("❌ Выключить", callback_data="upscale_face_off")
    )
    keyboard.add(InlineKeyboardButton("🔙 Отмена", callback_data="upscale_cancel"))
    
    bot.edit_message_text(
        f"🔍 *Upscale {user_state[user_id]['scale']}x*\n"
        f"📷 Модель: {AVAILABLE_UPSCALE_MODELS.get(user_state[user_id]['model'], user_state[user_id]['model'])}\n\n"
        f"🎭 Восстанавливать лица?",
        message.chat.id,
        message.message_id,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

def start_upscale(message, user_id):
    """Запустить процесс upscale"""
    scale = user_state[user_id]['scale']
    model = user_state[user_id].get('model', 'realesrgan_4x')
    face = user_state[user_id].get('face', True)
    
    source_path = last_photo[user_id]
    
    if not os.path.exists(source_path):
        bot.edit_message_text("❌ Файл картинки не найден. Сначала сгенерируй новое изображение.",
                            message.chat.id, message.message_id)
        return
    
    filename = f"upscaled_{user_id}_{scale}x_{model}.jpg"
    
    status_msg = bot.edit_message_text(
        f"🔼 *Upscale {scale}x*\n"
        f"📷 Модель: {AVAILABLE_UPSCALE_MODELS.get(model, model)}\n"
        f"🎭 Лица: {'восстановлены' if face else 'без изменений'}\n\n"
        f"⏳ Обработка...",
        message.chat.id,
        message.message_id,
        parse_mode='Markdown'
    )
    
    try:
        # Преобразуем boolean в "yes"/"no" для API
        face_str = "yes" if face else "no"
        
        result_path = upscale_image(
            input_path=source_path,
            output_filename=filename,
            scale=scale,
            use_upscale=model,
            codeformer_upscale_faces=face_str,  # ← теперь строка
            codeformer_fidelity=0.5
        )
        
        with open(result_path, 'rb') as photo:
            bot.send_photo(message.chat.id, photo, 
                          caption=f"✨ *Готово!*\n🔼 {scale}x\n📷 {AVAILABLE_UPSCALE_MODELS.get(model, model)}\n🎭 Лица: {'восстановлены' if face else 'без изменений'}",
                          parse_mode='Markdown')
        
        if os.path.exists(result_path):
            os.remove(result_path)
        
        bot.edit_message_text(f"✅ Upscale завершён!", message.chat.id, status_msg.message_id)
        
        if user_id in user_state:
            del user_state[user_id]
        
    except Exception as e:
        bot.edit_message_text(f"💥 Ошибка upscale: {str(e)}", 
                            message.chat.id, status_msg.message_id)

def handle_custom_size(message):
    if message.from_user.id not in ALLOWED_USERS:
        return
    
    try:
        w, h = map(int, message.text.strip().split())
        w, h = max(256, min(1536, w)), max(256, min(1536, h))
        settings = get_user_settings(message.from_user.id)
        settings['width'], settings['height'] = w, h
        save_user_settings(message.from_user.id, settings)
        bot.reply_to(message, f"✅ Размер: {w}×{h}")
    except:
        bot.reply_to(message, "❌ Формат: `1024 768`", parse_mode='Markdown')
    show_settings(message)

def handle_custom_seed(message):
    if message.from_user.id not in ALLOWED_USERS:
        return
    
    try:
        seed = int(message.text.strip())
        settings = get_user_settings(message.from_user.id)
        settings['seed'] = seed
        save_user_settings(message.from_user.id, settings)
        bot.reply_to(message, f"✅ Seed: {seed}")
    except:
        bot.reply_to(message, "❌ Отправь целое число")
    show_settings(message)

def add_user_by_id(message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        new_id = int(message.text.strip())
        if new_id not in ALLOWED_USERS:
            ALLOWED_USERS.append(new_id)
            save_allowed_users()
            bot.reply_to(message, f"✅ ID `{new_id}` добавлен.", parse_mode='Markdown')
    except:
        pass

@bot.message_handler(func=lambda message: True)
@bot.message_handler(func=lambda message: True)
def handle_generation(message):
    if message.from_user.id not in ALLOWED_USERS:
        bot.reply_to(message, "🔒 Доступ закрыт.")
        return
    
    if is_admin(message.from_user.id) and message.text.strip().isdigit() and len(message.text.strip()) > 5:
        add_user_by_id(message)
        return
    
    prompt = message.text
    if prompt.startswith('/'):
        return
    
    settings = get_user_settings(message.from_user.id)
    
    # Примерное время
    estimated_total = int(settings['steps'] * 1.8) + 10
    
    status_msg = bot.reply_to(message, 
        f"⏳ *Генерация началась...*\n\n"
        f"📐 {settings['width']}×{settings['height']}\n"
        f"🔢 {settings['steps']} steps\n"
        f"🎨 CFG: {settings['guidance_scale']}\n\n"
        f"⏱ Ориентировочное время: ~{estimated_total} секунд",
        parse_mode='Markdown')
    
    filename = f"output_{message.from_user.id}_{int(time.time())}.jpg"
    
    last_update_time = time.time()
    
    def update_progress(elapsed, total_estimated):
        nonlocal last_update_time
        current_time = time.time()
        if current_time - last_update_time >= 5:
            last_update_time = current_time
            remaining = max(0, total_estimated - elapsed)
            try:
                bot.edit_message_text(
                    f"⏳ *Генерация...* (прошло {elapsed}с, осталось ~{remaining}с)\n\n"
                    f"📐 {settings['width']}×{settings['height']}\n"
                    f"🔢 {settings['steps']} steps",
                    message.chat.id,
                    status_msg.message_id,
                    parse_mode='Markdown'
                )
            except:
                pass
    
    try:
        image_path = generate_image(
            prompt=prompt, 
            output_filename=filename,
            width=settings['width'], 
            height=settings['height'],
            steps=settings['steps'], 
            guidance_scale=settings['guidance_scale'],
            seed=settings['seed'] if settings['seed'] != -1 else None,
            use_face_correction=False,
            progress_callback=update_progress
        )
        
        # Сохраняем путь к картинке (НЕ УДАЛЯЕМ)
        last_photo[message.from_user.id] = image_path
        
        # Отправляем фото
        with open(image_path, 'rb') as photo:
            bot.send_photo(
                message.chat.id, 
                photo, 
                caption=f"✨ *Готово!*\n\n"
                       f"📝 `{prompt[:100]}`\n\n"
                       f"🔼 /upscale — увеличить\n"
                       f"🖼 /last — показать последнюю",
                parse_mode='Markdown'
            )
        
        # Удаляем только статусное сообщение, фото НЕ УДАЛЯЕМ
        bot.delete_message(message.chat.id, status_msg.message_id)
        
    except Exception as e:
        error_text = str(e)
        print(f"❌ Ошибка генерации: {error_text}")
        bot.edit_message_text(f"💥 *Ошибка генерации*\n`{error_text[:200]}`", 
                            message.chat.id, 
                            status_msg.message_id,
                            parse_mode='Markdown')
    
    filename = os.path.join(PHOTO_STORAGE, f"output_{message.from_user.id}.jpg")
    
    last_update_time = time.time()
    
    def update_progress(elapsed, total_estimated):
        nonlocal last_update_time
        current_time = time.time()
        # Обновляем раз в 5 секунд
        if current_time - last_update_time >= 5:
            last_update_time = current_time
            remaining = max(0, total_estimated - elapsed)
            try:
                bot.edit_message_text(
                    f"⏳ *Генерация...* (прошло {elapsed}с, осталось ~{remaining}с)\n\n"
                    f"📐 {settings['width']}×{settings['height']}\n"
                    f"🔢 {settings['steps']} steps\n"
                    f"🎨 CFG: {settings['guidance_scale']}",
                    message.chat.id,
                    status_msg.message_id,
                    parse_mode='Markdown'
                )
            except:
                pass
    
    try:
        image_path = generate_image(
            prompt=prompt, 
            output_filename=filename,
            width=settings['width'], 
            height=settings['height'],
            steps=settings['steps'], 
            guidance_scale=settings['guidance_scale'],
            seed=settings['seed'] if settings['seed'] != -1 else None,
            use_face_correction=False,
            progress_callback=update_progress
        )
        
        last_photo[message.from_user.id] = image_path
        
        with open(image_path, 'rb') as photo:
            bot.send_photo(
                message.chat.id, 
                photo, 
                caption=f"✨ *Готово!*\n\n"
                       f"📝 `{prompt[:100]}`\n\n"
                       f"🔼 /upscale — увеличить\n"
                       f"🖼 /last — показать последнюю",
                parse_mode='Markdown'
            )
        
        bot.delete_message(message.chat.id, status_msg.message_id)
        
    except Exception as e:
        bot.edit_message_text(f"💥 *Ошибка*\n`{str(e)[:200]}`", 
                            message.chat.id, status_msg.message_id,
                            parse_mode='Markdown')
    
    try:
        image_path = generate_image(
            prompt=prompt, 
            output_filename=filename,
            width=settings['width'], 
            height=settings['height'],
            steps=settings['steps'], 
            guidance_scale=settings['guidance_scale'],
            seed=settings['seed'] if settings['seed'] != -1 else None,
            progress_callback=update_progress
        )
        
        # Сохраняем путь к картинке
        last_photo[message.from_user.id] = image_path
        
        # Финальное сообщение
        bot.edit_message_text(
            f"✅ *Генерация завершена!*\n\n"
            f"📐 {settings['width']}×{settings['height']}\n"
            f"🔢 {settings['steps']} steps\n"
            f"🎨 CFG: {settings['guidance_scale']}\n\n"
            f"📤 Отправляю картинку...",
            message.chat.id,
            status_msg.message_id,
            parse_mode='Markdown'
        )
        
        # Отправляем фото
        with open(image_path, 'rb') as photo:
            bot.send_photo(
                message.chat.id, 
                photo, 
                caption=f"✨ *Готово!*\n\n"
                       f"📝 `{prompt[:100]}`\n\n"
                       f"🔼 /upscale — увеличить\n"
                       f"🖼 /last — показать последнюю",
                parse_mode='Markdown'
            )
        
        # Удаляем статусное сообщение через 3 секунды
        time.sleep(3)
        bot.delete_message(message.chat.id, status_msg.message_id)
        
    except Exception as e:
        error_text = str(e)
        bot.edit_message_text(
            f"💥 *Ошибка генерации*\n\n`{error_text[:300]}`", 
            message.chat.id, 
            status_msg.message_id,
            parse_mode='Markdown'
        )
        
        if os.path.exists(filename):
            os.remove(filename)
  

print("🤖 Бот запущен!")
print(f"👥 Разрешённые пользователи: {ALLOWED_USERS}")
print(f"👑 Администратор: {ALLOWED_USERS[0] if ALLOWED_USERS else 'не задан'}")
print(f"📁 Картинки сохраняются в: {PHOTO_STORAGE}")
bot.infinity_polling()