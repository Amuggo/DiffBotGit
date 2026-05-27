import os
import time
import base64
import requests

BASE_URL = "http://localhost:9000"
UPSCALE_URL = f"{BASE_URL}/upscale"

# Доступные модели upscale (замените на те, что установлены у вас)
AVAILABLE_UPSCALE_MODELS = {
    "realesrgan_4x": "RealESRGAN 4x",
    "realesrgan_2x": "RealESRGAN 2x",
    "esrgan_4x": "ESRGAN 4x",
    "swinir_4x": "SwinIR 4x",
    "lanczos": "Lanczos (обычный)"
}

def upscale_image(input_path: str, output_filename: str = "upscaled.jpg", 
                  scale: int = 2, face_restoration: bool = True,
                  upscale_model: str = "realesrgan_4x") -> str:
    """
    Увеличить изображение через EasyDiffusion
    
    Args:
        input_path: путь к исходному изображению
        output_filename: имя для сохранения результата
        scale: коэффициент увеличения (2, 4)
        face_restoration: восстанавливать лица (GFPGAN)
        upscale_model: модель апскейла (из AVAILABLE_UPSCALE_MODELS)
    
    Returns:
        путь к сохранённому изображению
    """
    
    # Читаем исходное изображение и кодируем в base64
    with open(input_path, "rb") as f:
        image_base64 = base64.b64encode(f.read()).decode('utf-8')
    
    payload = {
        "image": image_base64,
        "scale": scale,
        "face_restoration": face_restoration,
        "upscale_model": upscale_model,
        "num_outputs": 1
    }
    
    print(f"🔼 Upscale: коэффициент {scale}x, модель: {upscale_model}, восстановление лиц: {face_restoration}")
    
    response = requests.post(UPSCALE_URL, json=payload, timeout=60)
    
    if response.status_code != 200:
        raise Exception(f"Upscale не удался. Статус: {response.status_code}, Ответ: {response.text[:200]}")
    
    result_data = response.json()
    
    # Извлекаем картинку из ответа
    output_list = result_data.get("output", [])
    if not output_list:
        raise Exception("Поле 'output' пустое")
    
    if isinstance(output_list, list) and len(output_list) > 0:
        img_data = output_list[0].get("data")
    else:
        img_data = output_list.get("data")
    
    if not img_data:
        raise Exception("Не найден ключ 'data' с картинкой")
    
    if "," in img_data:
        img_data = img_data.split(",")[1]
    
    image_bytes = base64.b64decode(img_data.encode('utf-8'))
    
    current_bot_dir = os.path.dirname(os.path.abspath(__file__))
    final_path = os.path.join(current_bot_dir, output_filename)
    
    with open(final_path, "wb") as fh:
        fh.write(image_bytes)
    
    print(f"✅ Upscale завершён: {final_path}")
    return final_path