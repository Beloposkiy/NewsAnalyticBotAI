import logging
import warnings

def setup_logger(name: str = None) -> logging.Logger:
    warnings.filterwarnings("ignore", category=FutureWarning, module="huggingface_hub")

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        formatter = logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s")

        file_handler = logging.FileHandler("newsbot.log", mode="a", encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger
