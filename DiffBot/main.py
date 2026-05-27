import os
import telebot
import requests
# Импортируем нашу функцию из соседнего файла
from diffusion_api import generate_image 

TOKEN = "8696382759:AAG7JkFL1FNfsV1rqUEmJE307MMkidcIMIc"
bot = telebot.TeleBot(TOKEN)

ALLOWED_USERS = [6738379690, 5233742292]

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "🎨 Привет! Отправь мне текстовый промпт на английском, и я сгенерирую картинку через EasyDiffusion!")

@bot.message_handler(func=lambda message: True)
def handle_generation(message):
    if message.from_user.id not in ALLOWED_USERS:
        bot.reply_to(message, "🔒 Доступ закрыт. Этот бот приватный.")
        return
        
    prompt = message.text
    if prompt.startswith('/'):
        return

    status_msg = bot.reply_to(message, "⏳ Отправил запрос на ваш ПК. Генерация началась...")
    
    # Имя файла делаем уникальным для юзера, чтобы избежать конфликтов при одновременных запросах
    filename = f"output_{message.from_user.id}.jpg"

    try:
        # Вызываем функцию из нашего модуля
        image_path = generate_image(prompt, filename)
        
        # Отправляем результат
        with open(image_path, 'rb') as photo:
            bot.send_photo(message.chat.id, photo, caption=f"✨ Готово по запросу: {prompt}")
            
        # Чистим за собой временный файл
        if os.path.exists(image_path):
            os.remove(image_path)
            
        bot.delete_message(message.chat.id, status_msg.message_id)

    except requests.exceptions.ConnectionError:
        bot.edit_message_text("❌ Не удалось подключиться к EasyDiffusion. Проверьте, запущен ли сервер на ПК.", message.chat.id, status_msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"💥 Произошла ошибка: {str(e)}", message.chat.id, status_msg.message_id)
        # На всякий случай удаляем файл, если ошибка произошла ПОСЛЕ создания файла, но ДО отправки
        if os.path.exists(filename):
            os.remove(filename)

print("🤖 Бот-генератор запущен...")
bot.infinity_polling()