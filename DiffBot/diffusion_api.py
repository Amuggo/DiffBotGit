import os
import time
import base64
import random
import requests

BASE_URL = "http://localhost:9000"
RENDER_URL = f"{BASE_URL}/render"

def generate_image(prompt: str, output_filename: str = "output.jpg", 
                   width: int = 512, height: int = 512, 
                   steps: int = 20, guidance_scale: float = 7.5,
                   seed: int = None) -> str:
    
    # Отладка
    print(f"🔍 [generate_image] Параметры:")
    print(f"   width={width}, height={height}, steps={steps}, cfg={guidance_scale}, seed={seed}")
    
    # Если seed не указан или -1 — генерируем случайный
    if seed is None or seed == -1:
        seed = random.randint(1, 2**32 - 1)
    
    # ВАЖНО: используем num_inference_steps, а не steps
    payload = {
        "prompt": prompt,
        "negative_prompt": "ugly, deformed, blurry, low quality, bad anatomy",
        "width": width,
        "height": height,
        "num_inference_steps": steps,  # ← исправлено!
        "num_outputs": 1,
        "seed": seed,
        "sampler_name": "euler_a",
        "guidance_scale": guidance_scale,
        "use_stable_diffusion_model": "epicrealism_naturalSinRC1VAE", 
        "stream_progress_updates": False
    }
    
    print(f"🎨 Отправляю в EasyDiffusion: {width}×{height}, {steps} steps (num_inference_steps={steps}), CFG={guidance_scale}, seed={seed}")
    
    response = requests.post(RENDER_URL, json=payload, timeout=15)
    
    if response.status_code != 200:
        raise Exception(f"EasyDiffusion отклонил запрос. Статус: {response.status_code}, Ответ: {response.text[:200]}")
        
    init_data = response.json()
    stream_endpoint = init_data.get("stream")
    
    if not stream_endpoint:
        raise Exception(f"Не удалось получить ID потока. Ответ: {init_data}")
    
    stream_url = f"{BASE_URL}{stream_endpoint}"
    time.sleep(5)
    
    final_task_data = None
    for attempt in range(25):
        try:
            check_response = requests.get(stream_url, timeout=10)
            
            if check_response.status_code == 200:
                text_data = check_response.text.strip()
                
                if "}{" in text_data:
                    text_data = text_data.split("}{")[-1]
                    if not text_data.startswith("{"): text_data = "{" + text_data
                    if not text_data.endswith("}"): text_data = text_data + "}"
                
                try:
                    data_chunk = check_response.json()
                except:
                    import json
                    data_chunk = json.loads(text_data)

                if "output" in data_chunk:
                    final_task_data = data_chunk
                    break
        except requests.exceptions.RequestException:
            pass
            
        time.sleep(2)
        print(f"⏱ Ожидание... (попытка {attempt+1}/25)")

    if not final_task_data:
        raise Exception("Время ожидания истекло. Генерация не завершилась.")

    output_list = final_task_data.get("output", [])
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
        
    image_bytes = base64.b64decode(img_data.encode('utf-8'))
    
    current_bot_dir = os.path.dirname(os.path.abspath(__file__))
    final_path = os.path.join(current_bot_dir, output_filename)
    
    with open(final_path, "wb") as fh:
        fh.write(image_bytes)
        
    print(f"✅ Картинка сохранена: {final_path}")
    return final_path