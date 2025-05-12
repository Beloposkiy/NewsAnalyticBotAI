import os
import requests
import sys
from tqdm import tqdm

# Папка, куда будет скачана модель
MODEL_DIR = "models/rubert-sentiment"
os.makedirs(MODEL_DIR, exist_ok=True)

# Ссылки на все необходимые файлы модели
files = {
    "config.json": "https://huggingface.co/blanchefort/rubert-base-cased-sentiment/resolve/main/config.json",
    "pytorch_model.bin": "https://huggingface.co/blanchefort/rubert-base-cased-sentiment/resolve/main/pytorch_model.bin",
    "tokenizer_config.json": "https://huggingface.co/blanchefort/rubert-base-cased-sentiment/resolve/main/tokenizer_config.json",
    "vocab.txt": "https://huggingface.co/blanchefort/rubert-base-cased-sentiment/resolve/main/vocab.txt",
    "special_tokens_map.json": "https://huggingface.co/blanchefort/rubert-base-cased-sentiment/resolve/main/special_tokens_map.json",
}

# Скачивание с прогресс-баром
for filename, url in files.items():
    local_path = os.path.join(MODEL_DIR, filename)
    if os.path.exists(local_path):
        print(f"✅ Уже скачан: {filename}")
        continue

    print(f"⬇️ Скачиваем {filename}...")

    try:
        with requests.get(url, stream=True) as response:
            response.raise_for_status()
            total = int(response.headers.get("content-length", 0))

            with open(local_path, "wb") as f, tqdm(
                total=total,
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
                desc=filename,
                initial=0,
                ascii=True,
                file=sys.stdout  # 👉 выводим прогресс-бар в stdout (не будет красным)
            ) as bar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        bar.update(len(chunk))

        print(f"✅ Скачан: {filename}")
    except Exception as e:
        print(f"❌ Ошибка при скачивании {filename}: {e}")
        print(f"❌ Ошибка при скачивании {filename}: {e}")