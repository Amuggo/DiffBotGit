import requests
import json
import random
import base64
import time

BASE_URL = "http://localhost:9000"
RENDER_URL = f"{BASE_URL}/render"

payload = {
    "prompt": "cat sitting on a chair, realistic",
    "negative_prompt": "ugly, deformed, blurry, low quality, bad anatomy",
    "width": 768,
    "height": 768,
    "num_inference_steps": 30,
    "num_outputs": 1,
    "seed": random.randint(1, 2**32 - 1),
    "sampler_name": "euler_a",
    "guidance_scale": 7.5,
    "use_stable_diffusion_model": "epicrealism_naturalSinRC1VAE"
}

print("🚀 Отправка запроса...")
response = requests.post(RENDER_URL, json=payload, timeout=30)
data = response.json()
stream_url = f"{BASE_URL}{data['stream']}"
print(f"Stream URL: {stream_url}")

print("\n📡 Подключаемся к stream...")
print("="*50)

# Просто подключаемся и читаем всё подряд
resp_stream = requests.get(stream_url, stream=True, timeout=120)

for line in resp_stream.iter_lines():
    if line:
        line_str = line.decode('utf-8')
        
        # Пропускаем пустые строки
        if not line_str.strip():
            continue
        
        # Пробуем парсить JSON
        try:
            obj = json.loads(line_str)
            total_steps = obj['total_steps']
            print(total_steps)
            for i in range(total_steps):
                if "step" in obj:
                    print(f"📊 Шаг {obj['step']}/{obj['total_steps']} | {obj.get('step_time', 0):.2f}с")
            
            if "output" in obj:
                print("\n✅ Генерация завершена!")
                img_data = obj["output"][0].get("data")
                if img_data:
                    if "," in img_data:
                        img_data = img_data.split(",")[1]
                    image_bytes = base64.b64decode(img_data)
                    with open("output.jpg", "wb") as f:
                        f.write(image_bytes)
                    print("💾 Картинка сохранена как output.jpg")
                break
            
            if "status" in obj and obj["status"] == "failed":
                print(f"❌ Ошибка: {obj.get('detail', 'Unknown error')}")
                break
                
        except json.JSONDecodeError:
            # Если не JSON, просто выводим строку
            print(f"📝 {line_str}")

print("\n✅ Скрипт завершён")