"""
Вспомогательные функции для работы с файлами, кэшами, отчётами и сессиями.
"""

import os
import shutil

def save_file(content: bytes, filename: str, folder: str = "reports") -> str:
    """
    Сохраняет бинарные данные в файл.
    :param content: Данные (байты)
    :param filename: Имя файла
    :param folder: Папка для сохранения
    :return: Путь к файлу
    """
    if not os.path.exists(folder):
        os.makedirs(folder)
    path = os.path.join(folder, filename)
    with open(path, "wb") as f:
        f.write(content)
    return path

def clear_old_reports(folder: str = "reports", keep_last: int = 20):
    """
    Удаляет старые отчёты, оставляя только последние N.
    """
    files = sorted(
        [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".pdf")],
        key=os.path.getmtime
    )
    if len(files) > keep_last:
        for f in files[:-keep_last]:
            os.remove(f)