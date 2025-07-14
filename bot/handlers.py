from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from bot.keyboards import get_period_keyboard, get_categories_keyboard
from core.filters import filter_news_by_period
from core.categorizer import classify_and_analyze
from core.sentimenter import analyze_sentiment
from core.report_builder import build_pdf_report
from services.telegram_api import fetch_news_from_channels
from shared.constants import PERIODS, CATEGORY_LABELS
from config.logger import logger

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    logger.info(f"Команда /start от пользователя {message.from_user.id}")

    # Получаем payload после /start
    payload = message.text.split(" ", 1)
    if len(payload) > 1:
        param = payload[1].strip().lower()
        logger.info(f"Payload после /start: {param}")

        if param == "topics":
            # Переход напрямую в cmd_topics
            await state.clear()
            await message.answer(
                "Выберите период анализа:",
                reply_markup=get_period_keyboard()
            )
            await state.set_state("waiting_for_period")
            return

    # Обычный /start без параметров
    await message.answer(
        "Привет! Я бот для анализа новостной повестки в Telegram.\n\n"
        "Доступные команды:\n"
        "/topics — топ-новости по категориям."
    )

@router.message(Command("topics"))
async def cmd_topics(message: types.Message, state: FSMContext):
    logger.info(f"Команда /topics от пользователя {message.from_user.id}")
    await state.clear()
    await message.answer(
        "Выберите период анализа:",
        reply_markup=get_period_keyboard()
    )
    await state.set_state("waiting_for_period")

@router.callback_query(F.data.in_(PERIODS))
async def period_selected(callback: types.CallbackQuery, state: FSMContext):
    period = callback.data
    logger.info(f"Пользователь {callback.from_user.id} выбрал период: {period}")
    await state.update_data(period=period)
    await callback.message.edit_text(
        f"Период выбран: {period.capitalize()}.\n"
        "Теперь выберите категорию поста:",
        reply_markup=get_categories_keyboard()
    )
    await state.set_state("waiting_for_category")
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("category_"))
async def category_selected(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer("Начинаю обработку...")

    category_key = callback.data.removeprefix("category_")
    logger.info(f"Пользователь {callback.from_user.id} выбрал категорию: {category_key}")

    data = await state.get_data()
    period = data.get("period")
    if period is None:
        await callback.message.answer("Пожалуйста, сначала выберите период анализа через команду /topics.")
        return

    category_name = CATEGORY_LABELS.get(category_key, "Другое")

    period_to_days = {
        'day': 1,
        'week': 7,
        'month': 30
    }
    days = period_to_days.get(period, 30)

    cached_news = data.get("classified_news")
    cached_period = data.get("classified_period")

    if cached_news is None or cached_period != period:
        loading_msg = None
        try:
            loading_msg = await callback.message.answer("Идёт загрузка и классификация постов...")
            all_news = await fetch_news_from_channels(period_days=days)
            logger.info(f"Получено постов из каналов: {len(all_news)}")
        except Exception as e:
            logger.error(f"Ошибка при получении постов: {e}")
            if loading_msg:
                await loading_msg.edit_text("Ошибка при получении постов. Попробуйте позже.")
            else:
                await callback.message.answer("Ошибка при получении постов. Попробуйте позже.")
            return

        news_in_period = filter_news_by_period(all_news, period)
        logger.info(f"Постов после фильтра по периоду '{period}': {len(news_in_period)}")

        analyzed_news = classify_and_analyze(news_in_period)

        for post in analyzed_news:
            text = post.get("text", "")
            sentiment_label, sentiment_score = analyze_sentiment(text)
            post["sentiment"] = sentiment_label
            post["sentiment_score"] = sentiment_score

        await state.update_data(classified_news=analyzed_news, classified_period=period)
    else:
        analyzed_news = cached_news
        loading_msg = None

    filtered_news = [post for post in analyzed_news if category_key in post.get('categories', [])]
    logger.info(f"Постов после фильтра по категории '{category_key}': {len(filtered_news)}")

    if not filtered_news:
        if loading_msg:
            await loading_msg.edit_text(f"Нет постов в категории \"{category_name}\" за выбранный период.")
        else:
            await callback.message.answer(f"Нет постов в категории \"{category_name}\" за выбранный период.")
        return

    if loading_msg:
        await loading_msg.edit_text(f"Найдено {len(filtered_news)} постов в категории \"{category_name}\" за период {period}.")
    else:
        await callback.message.answer(f"Найдено {len(filtered_news)} постов в категории \"{category_name}\" за период {period}.")

    try:
        pdf_path = build_pdf_report(filtered_news, period, category_key)
        logger.info(f"PDF отчет сформирован: {pdf_path}")
        await callback.message.answer_document(
            types.FSInputFile(pdf_path),
            caption=f"Отчёт по категории \"{category_name}\" за {period.capitalize()}."
        )
    except Exception as e:
        logger.error(f"Ошибка при формировании отчёта: {e}")
        if loading_msg:
            await loading_msg.edit_text(f"Произошла ошибка при формировании отчёта.\n{e}")
        else:
            await callback.message.answer(f"Произошла ошибка при формировании отчёта.\n{e}")
