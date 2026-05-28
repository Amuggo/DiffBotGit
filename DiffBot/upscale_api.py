import os
import base64
import requests

BASE_URL = "http://localhost:9000"
UPSCALE_URL = f"{BASE_URL}/upscale"

AVAILABLE_UPSCALE_MODELS = {
    "realesrgan_4x": "RealESRGAN 4x",
    "realesrgan_2x": "RealESRGAN 2x",
    "esrgan_4x": "ESRGAN 4x",
    "swinir_4x": "SwinIR 4x",
    "lanczos": "Lanczos (обычный)"
}

def upscale_image(input_path: str, output_filename: str = "upscaled.jpg", 
                  scale: int = 2, 
                  use_upscale: str = "realesrgan_4x",
                  codeformer_upscale_faces: bool = True,
                  codeformer_fidelity: float = 0.5) -> str:
    
    with open(input_path, "rb") as f:
        image_base64 = base64.b64encode(f.read()).decode('utf-8')
    
    # Собираем payload, исключая параметры, которые могут вызвать ошибку
    payload = {
        "image": image_base64,
        "num_outputs": 1
    }
    
    # Добавляем только те параметры, которые точно нужны и в правильном формате
    payload["upscale_amount"] = scale
    
    if use_upscale:
        payload["use_upscale"] = use_upscale
    
    # codeformer_upscale_faces ожидает строку "yes" или "no"
    payload["codeformer_upscale_faces"] = "yes" if codeformer_upscale_faces else "no"
    payload["codeformer_fidelity"] = codeformer_fidelity
    
    print(f"🔼 Upscale: коэффициент {scale}x")
    print(f"   use_upscale: {use_upscale}")
    print(f"   codeformer_upscale_faces: {payload['codeformer_upscale_faces']}")
    print(f"   codeformer_fidelity: {codeformer_fidelity}")
    
    response = requests.post(UPSCALE_URL, json=payload, timeout=60)
    
    if response.status_code != 200:
        raise Exception(f"Upscale не удался. Статус: {response.status_code}, Ответ: {response.text[:500]}")
    
    result_data = response.json()
    
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