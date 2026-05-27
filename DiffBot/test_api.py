import requests

BASE_URL = "http://localhost:9000"

# Проверяем доступные эндпоинты
endpoints = [
    "/upscale",
    "/api/upscale",
    "/v1/upscale",
    "/render/upscale",
    "/image/upscale",
    "/control/upscale",
    "/sdapi/v1/extra-single-image",  # для Automatic1111
    "/sdapi/v1/extra-batch-images",   # для Automatic1111
]

for endpoint in endpoints:
    url = f"{BASE_URL}{endpoint}"
    try:
        response = requests.get(url, timeout=5)
        print(f"{endpoint}: {response.status_code}")
    except:
        print(f"{endpoint}: ERROR")

# Проверяем корневой эндпоинт
try:
    response = requests.get(BASE_URL, timeout=5)
    print(f"\nКорневой эндпоинт: {response.status_code}")
    print(f"Ответ: {response.text[:200]}")
except Exception as e:
    print(f"Ошибка: {e}")

# Пробуем получить документацию API
try:
    response = requests.get(f"{BASE_URL}/docs", timeout=5)
    if response.status_code == 200:
        print(f"\nДокументация API доступна: {BASE_URL}/docs")
except:
    pass

try:
    response = requests.get(f"{BASE_URL}/openapi.json", timeout=5)
    if response.status_code == 200:
        print(f"\nOpenAPI доступен: {BASE_URL}/openapi.json")
        print(response.text[:500])
except:
    pass