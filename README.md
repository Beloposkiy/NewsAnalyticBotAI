# PostAiBot

Telegram-бот для анализа новостной повестки в Telegram-каналах с помощью нейросетевых моделей.  
Бот собирает новости, классифицирует их по категориям, анализирует тональность и формирует PDF-отчёты.

---

## Возможности

- Получение новостей из заданных Telegram-каналов за выбранный период (день, неделя, месяц)  
- Категоризация новостей (политика, экономика, культура, спорт и другие)  
- Анализ тональности постов (позитивная, негативная, нейтральная)  
- Генерация подробных PDF-отчётов с текстом, датой, ссылками и результатами анализа  
- Удобный Telegram-интерфейс с выбором периода и категории для анализа

---

## Установка

1. Клонируйте репозиторий:

    ```bash
   git clone https://github.com/Beloposkiy/PostAiBot.git  
   cd PostAiBot

2. Создайте виртуальное окружение и активируйте его:

    ```bash
   python3.9 -m venv .venv  
   source .venv/bin/activate  # Linux/macOS  
   .venv\Scripts\activate     # Windows

3. Установите зависимости:

    ```bash
   pip install -r requirements.txt

4. Настройте `.env` файл с параметрами:

   - API_ID и API_HASH для Telegram API  
   - Токен Telegram-бота и другие необходимые переменные  

5. Настройте список Telegram-каналов в `data/sources.yaml`.

---

## Запуск

```bash
    python main.py
   ```

---

## Контакты

Автор — George Belopolsky  
GitHub: https://github.com/Beloposkiy  
Email: george.belopolsky@gmail.com