import os
import time
import base64
import random
import requests

BASE_URL = "http://localhost:9000"
RENDER_URL = f"{BASE_URL}/render"

def generate_image(prompt: str, output_filename: str = "output.jpg") -> str:
    payload = {
        "prompt": prompt,
        "negative_prompt": "ugly, deformed, blurry, low quality, bad anatomy",
        "width": 512,
        "height": 512,
        "steps": 20,
        "num_outputs": 1,
        "seed": random.randint(100000000, 999999999),
        "sampler_name": "euler_a",
        "guidance_scale": 7.5,
        "use_stable_diffusion_model": "epicrealism_naturalSinRC1VAE", 
        "stream_progress_updates": False # Отключаем спам шагов
    }

    # 1. Отправляем задачу в EasyDiffusion
    print("🎨 Бот отправил промпт в EasyDiffusion...")
    response = requests.post(RENDER_URL, json=payload, timeout=15)
    
    if response.status_code != 200:
        raise Exception(f"EasyDiffusion отклонил запрос. Статус: {response.status_code}")
        
    init_data = response.json()
    stream_endpoint = init_data.get("stream") # /image/stream/2109841636944
    
    if not stream_endpoint:
        raise Exception(f"Не удалось получить ID потока. Ответ сервера: {init_data}")
        
    print(f"⏳ Задача зарегистрирована. Видеокарта RTX 3050 считает кадр...")
    
    # 2. Даем видеокарте гарантированное время на генерацию (20 шагов ~ 8-12 секунд)
    # Сделаем умное ожидание: проверяем эндпоинт, пока он не отдаст финальный JSON
    stream_url = f"{BASE_URL}{stream_endpoint}"
    
    # Делаем паузу перед первой проверкой, чтобы сеть успела просчитаться
    time.sleep(5) 
    
    final_task_data = None
    for attempt in range(25): # Проверяем до 50 секунд
        try:
            # Опрашиваем поток. Когда задача активна, он может висеть или отдавать статус.
            # Когда задача завершена — он мгновенно выплевывает финальный JSON с картинкой.
            check_response = requests.get(stream_url, timeout=10)
            
            if check_response.status_code == 200:
                text_data = check_response.text.strip()
                
                # Защита от слипшихся строк: берем только последний завершенный JSON пакет
                if "}{" in text_data:
                    # Разделяем и берем самую последнюю часть, где лежит картинка
                    text_data = text_data.split("}{")[-1]
                    if not text_data.startswith("{"): text_data = "{" + text_data
                    if not text_data.endswith("}"): text_data = text_data + "}"
                
                try:
                    data_chunk = check_response.json()
                except:
                    import json
                    data_chunk = json.loads(text_data)

                # Проверяем, появились ли данные картинки
                if "output" in data_chunk:
                    final_task_data = data_chunk
                    break
        except requests.exceptions.RequestException:
            pass
            
        time.sleep(2)
        print(f"⏱ Ожидание рендера на ПК... (проверка {attempt+1})")

    if not final_task_data:
        raise Exception("Время ожидания истекло. Видеокарта не отдала картинку вовремя.")

    # 3. Извлекаем картинку
    output_list = final_task_data.get("output", [])
    if not output_list:
        raise Exception("Поле 'output' пустое, генерация сбросилась.")
        
    # В EasyDiffusion 3.5 в output лежит список. Достаем первый элемент.
    if isinstance(output_list, list) and len(output_list) > 0:
        img_data = output_list[0].get("data")
    else:
        img_data = output_list.get("data")
        
    if not img_data:
        raise Exception("В финальном JSON ответа не найден ключ 'data' с кодом картинки.")
        
    # Отрезаем префикс Base64, если он есть
    if "," in img_data:
        img_data = img_data.split(",")[1]
        
    # Декодируем и сохраняем файл
    image_bytes = base64.b64decode(img_data.encode('utf-8'))
    
    current_bot_dir = os.path.dirname(os.path.abspath(__file__))
    final_path = os.path.join(current_bot_dir, output_filename)
    
    with open(final_path, "wb") as fh:
        fh.write(image_bytes)
        
    print(f"🎉 Картинка успешно сохранена: {final_path}")
    return final_path
