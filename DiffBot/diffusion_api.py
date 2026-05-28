import os
import time
import base64
import random
import requests
import json

BASE_URL = "http://localhost:9000"
RENDER_URL = f"{BASE_URL}/render"

def generate_image(prompt: str, output_filename: str = "output.jpg", 
                   width: int = 512, height: int = 512, 
                   steps: int = 20, guidance_scale: float = 7.5,
                   seed: int = None, sampler_name: str = "euler_a",
                   use_face_correction: bool = False,
                   progress_callback=None) -> str:
    
    if seed is None or seed == -1:
        seed = random.randint(1, 2**32 - 1)
    
    payload = {
        "prompt": prompt,
        "negative_prompt": "ugly, deformed, blurry, low quality, bad anatomy",
        "seed": seed,
        "width": width,
        "height": height,
        "num_outputs": 1,
        "num_inference_steps": steps,
        "guidance_scale": guidance_scale,
        "sampler_name": sampler_name,
        "use_stable_diffusion_model": "epicrealism_naturalSinRC1VAE",
    }
    
    if use_face_correction:
        payload["use_face_correction"] = "GFPGANv1.3"
    
    print(f"🎨 Отправка запроса в EasyDiffusion...")
    print(f"   Параметры: {width}×{height}, {steps} steps, CFG={guidance_scale}, seed={seed}")
    
    try:
        response = requests.post(RENDER_URL, json=payload, timeout=30)
        print(f"   Ответ сервера: статус {response.status_code}")
    except requests.exceptions.ConnectionError:
        raise Exception("Не удалось подключиться к EasyDiffusion. Запущен ли сервер?")
    
    if response.status_code != 200:
        raise Exception(f"Ошибка: {response.status_code}, {response.text[:300]}")
    
    result = response.json()
    print(f"   Получен ответ, ключи: {list(result.keys())}")
    
    # Пробуем получить картинку
    output_data = None
    
    # Вариант 1: прямой output в ответе
    if "output" in result:
        output_data = result
        print("   Картинка найдена в поле 'output'")
    
    # Вариант 2: нужно подождать по stream
    elif "stream" in result:
        stream_url = f"{BASE_URL}{result['stream']}"
        print(f"   Ожидание по stream: {stream_url}")
        
        # Ждём с таймаутом
        wait_time = steps * 2 + 10
        print(f"   Ожидание ~{wait_time} секунд...")
        
        start_time = time.time()
        last_progress = 0
        
        while time.time() - start_time < wait_time:
            elapsed = int(time.time() - start_time)
            
            if progress_callback:
                progress_callback(elapsed, wait_time)
            
            # Каждые 5 секунд проверяем статус
            if elapsed - last_progress >= 5:
                last_progress = elapsed
                print(f"   Ожидание... {elapsed}/{wait_time} сек")
            
            time.sleep(2)
        
        # После ожидания пробуем получить результат
        try:
            stream_response = requests.get(stream_url, timeout=10)
            if stream_response.status_code == 200:
                stream_data = stream_response.json()
                if "output" in stream_data:
                    output_data = stream_data
                    print("   Картинка получена из stream")
                else:
                    print(f"   В stream нет output, ключи: {list(stream_data.keys())}")
        except Exception as e:
            print(f"   Ошибка получения stream: {e}")
    
    if not output_data:
        raise Exception("Не удалось получить результат генерации")
    
    # Извлекаем картинку
    output_list = output_data.get("output", [])
    if not output_list:
        raise Exception("Поле 'output' пустое")
    
    if isinstance(output_list, list) and len(output_list) > 0:
        img_data = output_list[0].get("data")
        actual_seed = output_list[0].get("seed", seed)
    else:
        img_data = output_list.get("data")
        actual_seed = output_list.get("seed", seed)
    
    if not img_data:
        raise Exception("Не найден ключ 'data' с картинкой")
    
    print(f"🎲 Фактический seed: {actual_seed}")
    
    if "," in img_data:
        img_data = img_data.split(",")[1]
    
    image_bytes = base64.b64decode(img_data)
    
    # Сохраняем в папку generated_photos
    bot_dir = os.path.dirname(os.path.abspath(__file__))
    photos_dir = os.path.join(bot_dir, "generated_photos")
    os.makedirs(photos_dir, exist_ok=True)
    
    final_path = os.path.join(photos_dir, output_filename)
    
    with open(final_path, "wb") as fh:
        fh.write(image_bytes)
    
    print(f"✅ Картинка сохранена: {final_path}")
    return final_path