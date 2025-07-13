import logging
import sys

def setup_logger(name: str = "AI_POST_BOT", log_file: str = "bot.log") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    if not logger.hasHandlers():
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    else:
        # Чтобы не добавлять обработчики повторно при повторном вызове
        for handler in logger.handlers:
            if not isinstance(handler, (logging.FileHandler, logging.StreamHandler)):
                logger.addHandler(handler)

    return logger

logger = setup_logger()


def print_progress_bar(current: int, total: int):
    bar_length = 30  # длина прогресс-бара
    done = int(bar_length * current / total)
    bar = '🟩' * done + '⬜' * (bar_length - done)
    # Печатаем прогресс-бар без добавления новой строки, с возвратом каретки
    print(f"\rКлассификация постов: [{bar}] {current}/{total}", end='', flush=True)
    if current == total:
        print()  # перевод строки после окончания