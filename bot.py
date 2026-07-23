import logging
import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN")
YOOKASSA_SHOP_ID = os.environ.get("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET_KEY = os.environ.get("YOOKASSA_SECRET_KEY")
# =========================================

# Загрузка данных
with open("questions.json", "r", encoding="utf-8") as f:
    QUESTIONS = json.load(f)

with open("personality_types.json", "r", encoding="utf-8") as f:
    PERSONALITY_TYPES = json.load(f)

TYPE_MAP = {
    ("I", "S"): "Искатель-Строитель",
    ("H", "M"): "Хранитель-Мечтатель",
    ("S", "H"): "Строитель-Хранитель",
    ("M", "I"): "Мечтатель-Искатель",
    ("I", "H"): "Искатель-Хранитель",
    ("S", "M"): "Строитель-Мечтатель",
    ("H", "I"): "Хранитель-Искатель",
    ("M", "S"): "Мечтатель-Строитель",
}

def calculate_type(scores):
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    first = sorted_scores[0][0]
    second = sorted_scores[1][0]
    type_name = TYPE_MAP.get((first, second)) or TYPE_MAP.get((second, first)) or "Искатель-Строитель"
    return type_name, sorted_scores

async def send_or_edit_message(update, text, reply_markup, parse_mode="HTML"):
    if update.callback_query:
        await update.callback_query.answer()
        try:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        except Exception:
            await update.callback_query.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    elif update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["scores"] = {"I": 0, "H": 0, "S": 0, "M": 0}
    context.user_data["current_question"] = 0
    context.user_data["answers"] = []
    
    welcome = f"""👋 Привет, {update.effective_user.first_name}!

<b>Кто ты на самом деле</b>

15 вопросов — и ты узнаешь:
• Свой тип личности
• Скрытые таланты
• Как взаимодействовать с близкими

🎁 После теста — персональный прогноз

Готов?"""
    
    keyboard = [[InlineKeyboardButton("🚀 Начать тест", callback_data="start_test")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await send_or_edit_message(update, welcome, reply_markup)

async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["scores"] = {"I": 0, "H": 0, "S": 0, "M": 0}
    context.user_data["current_question"] = 0
    context.user_data["answers"] = []
    await ask_question(update, context)

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q_idx = context.user_data["current_question"]
    
    if q_idx >= len(QUESTIONS):
        return await show_result(update, context)
    
    question = QUESTIONS[q_idx]
    progress = f"❓ Вопрос {q_idx + 1} из {len(QUESTIONS)}"
    
    text = f"{progress}\n\n<b>{question['question']}</b>"
    
    keyboard = []
    for i, answer in enumerate(question["answers"]):
        keyboard.append([InlineKeyboardButton(answer["text"], callback_data=f"answer_{i}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await send_or_edit_message(update, text, reply_markup)

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    answer_idx = int(query.data.split("_")[1])
    q_idx = context.user_data["current_question"]
    answer = QUESTIONS[q_idx]["answers"][answer_idx]
    
    for category, points in answer["scores"].items():
        context.user_data["scores"][category] += points
    
    context.user_data["current_question"] += 1
    return await ask_question(update, context)

async def show_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    scores = context.user_data["scores"]
    type_name, sorted_scores = calculate_type(scores)
    context.user_data["type_name"] = type_name
    data = PERSONALITY_TYPES[type_name]
    
    scores_text = "\n".join([
        f"  {'🔥' if k=='I' else '🌙' if k=='H' else '🌳' if k=='S' else '🚀'} "
        f"{'Искатель' if k=='I' else 'Хранитель' if k=='H' else 'Строитель' if k=='S' else 'Мечтатель'}: {v} баллов"
        for k, v in sorted_scores
    ])
    
    result = f"""🎯 <b>Твой тип личности:</b> {type_name}

{data['tagline']}

📊 <b>Твой профиль:</b>
{scores_text}

💡 <b>Кратко о тебе:</b>
{data['core']}

✨ <b>Твоя главная суперсила:</b>
{data['strengths'][0]}

💎 <b>Скрытый талант:</b>
{data['hidden_talent']}

---
📄 <b>Полный отчёт (399 ₽) включает:</b>
• Все 4 суперсилы
• Подробный разбор в отношениях
• Как ведёшь себя под стрессом
• Совет на сегодня
• Совместимость со всеми 8 типами

💰 <b>Получить полный отчёт:</b> 399 ₽"""
    
    keyboard = [
        [InlineKeyboardButton("📄 Получить полный отчёт — 399 ₽", callback_data="buy_report")],
        [InlineKeyboardButton("🔄 Пройти заново", callback_data="start_test")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await send_or_edit_message(update, result, reply_markup)

async def buy_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    type_name = context.user_data.get("type_name", "Искатель-Строитель")
    
    if not YOOKASSA_SHOP_ID or not YOOKASSA_SECRET_KEY:
        text = f"""💳 <b>Оплата отчёта</b>

Товар: Полный отчёт «{type_name}»
Сумма: 399 ₽

⚠️ <b>Платёжная система временно недоступна</b>

Но вы можете получить отчёт бесплатно в рамках тестирования! 👇"""
        
        keyboard = [
            [InlineKeyboardButton("📄 Получить отчёт бесплатно", callback_data="get_free_report")],
            [InlineKeyboardButton("◀️ Назад к результату", callback_data="back_to_result")],
        ]
    else:
        text = f"""💳 <b>Оплата отчёта</b>

Товар: Полный отчёт «{type_name}»
Сумма: 399 ₽

Для оплаты перейдите по ссылке:
[ССЫЛКА_НА_ОПЛАТУ_ЮKASSA]

После оплаты нажмите кнопку ниже 👇"""
        
        keyboard = [
            [InlineKeyboardButton("✅ Я оплатил(а)", callback_data="check_payment")],
            [InlineKeyboardButton("◀️ Назад к результату", callback_data="back_to_result")],
        ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def get_free_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Тестовый режим — полный отчёт бесплатно"""
    query = update.callback_query
    await query.answer()
    
    type_name = context.user_data.get("type_name", "Искатель-Строитель")
    data = PERSONALITY_TYPES[type_name]
    scores = context.user_data["scores"]
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    report = f"""🧪 <b>ТЕСТОВЫЙ РЕЖИМ — ПОЛНЫЙ ОТЧЁТ БЕСПЛАТНО</b>

🎯 <b>Твой тип личности:</b> {type_name}
<i>{data['tagline']}</i>

━━━━━━━━━━━━━━━━━━━━━

📊 <b>ТВОЙ ПРОФИЛЬ</b>

{chr(10).join([
    f"  {'🔥' if k=='I' else '🌙' if k=='H' else '🌳' if k=='S' else '🚀'} "
    f"{'Искатель' if k=='I' else 'Хранитель' if k=='H' else 'Строитель' if k=='S' else 'Мечтатель'}: {v} баллов"
    for k, v in sorted_scores
])}

━━━━━━━━━━━━━━━━━━━━━

💡 <b>КТО ТЫ</b>
{data['core']}

━━━━━━━━━━━━━━━━━━━━━

✨ <b>ТВОИ СУПЕРСИЛЫ</b>

{chr(10).join([f"  ✨ {s}" for s in data['strengths']])}

━━━━━━━━━━━━━━━━━━━━━

💎 <b>СКРЫТЫЙ ТАЛАНТ</b>
{data['hidden_talent']}

━━━━━━━━━━━━━━━━━━━━━

💕 <b>В ОТНОШЕНИЯХ</b>
{data['in_relationships']}

━━━━━━━━━━━━━━━━━━━━━

😰 <b>ПОД СТРЕССОМ</b>
{data['under_stress']}

━━━━━━━━━━━━━━━━━━━━━

✨ <b>СОВЕТ НА СЕГОДНЯ</b>
{data['advice_today']}

━━━━━━━━━━━━━━━━━━━━━

📄 <b>СОВМЕСТИМОСТЬ</b>

Подробная таблица совместимости со всеми 8 типами:
• Искатель-Строитель + Хранитель-Мечтатель = Идеальная пара
• Искатель-Строитель + Строитель-Хранитель = Надёжный союз
• Искатель-Строитель + Мечтатель-Искатель = Взаимное вдохновение
• Искатель-Строитель + Искатель-Хранитель = Сильная команда
• Искатель-Строитель + Строитель-Мечтатель = Амбициозный тандем
• Искатель-Строитель + Хранитель-Искатель = Баланс приключений
• Искатель-Строитель + Мечтатель-Строитель = Два лидера

(Полная таблица для всех 8 типов)

━━━━━━━━━━━━━━━━━━━━━

⚠️ <b>Это тестовая версия.</b>
После запуска полный отчёт будет стоить 399 ₽.

💬 <b>Понравилось? Поделись с другом!</b>"""
    
    await query.edit_message_text(report, parse_mode="HTML")
    
    # Предложение подписки
    await send_subscription_offer(update, context, type_name)

async def check_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    type_name = context.user_data.get("type_name", "Искатель-Строитель")
    data = PERSONALITY_TYPES[type_name]
    scores = context.user_data["scores"]
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    # Здесь будет проверка оплаты через ЮKassa API
    # Пока — имитация успешной оплаты
    
    await query.edit_message_text(
        f"✅ <b>Оплата подтверждена!</b>\n\n"
        f"Отправляю твой персональный отчёт «{type_name}»...",
        parse_mode="HTML"
    )
    
    # Отправляем полный отчёт (платная версия — без пометки ТЕСТОВЫЙ)
    report = f"""📄 <b>ПОЛНЫЙ ОТЧЁТ</b>

🎯 <b>Твой тип личности:</b> {type_name}
<i>{data['tagline']}</i>

━━━━━━━━━━━━━━━━━━━━━

📊 <b>ТВОЙ ПРОФИЛЬ</b>

{chr(10).join([
    f"  {'🔥' if k=='I' else '🌙' if k=='H' else '🌳' if k=='S' else '🚀'} "
    f"{'Искатель' if k=='I' else 'Хранитель' if k=='H' else 'Строитель' if k=='S' else 'Мечтатель'}: {v} баллов"
    for k, v in sorted_scores
])}

━━━━━━━━━━━━━━━━━━━━━

💡 <b>КТО ТЫ</b>
{data['core']}

━━━━━━━━━━━━━━━━━━━━━

✨ <b>ТВОИ СУПЕРСИЛЫ</b>

{chr(10).join([f"  ✨ {s}" for s in data['strengths']])}

━━━━━━━━━━━━━━━━━━━━━

💎 <b>СКРЫТЫЙ ТАЛАНТ</b>
{data['hidden_talent']}

━━━━━━━━━━━━━━━━━━━━━

💕 <b>В ОТНОШЕНИЯХ</b>
{data['in_relationships']}

━━━━━━━━━━━━━━━━━━━━━

😰 <b>ПОД СТРЕССОМ</b>
{data['under_stress']}

━━━━━━━━━━━━━━━━━━━━━

✨ <b>СОВЕТ НА СЕГОДНЯ</b>
{data['advice_today']}

━━━━━━━━━━━━━━━━━━━━━

📄 <b>СОВМЕСТИМОСТЬ</b>

Подробная таблица совместимости со всеми 8 типами:
• Искатель-Строитель + Хранитель-Мечтатель = Идеальная пара
• Искатель-Строитель + Строитель-Хранитель = Надёжный союз
• Искатель-Строитель + Мечтатель-Искатель = Взаимное вдохновение
• Искатель-Строитель + Искатель-Хранитель = Сильная команда
• Искатель-Строитель + Строитель-Мечтатель = Амбициозный тандем
• Искатель-Строитель + Хранитель-Искатель = Баланс приключений
• Искатель-Строитель + Мечтатель-Строитель = Два лидера

(Полная таблица для всех 8 типов)

━━━━━━━━━━━━━━━━━━━━━

💬 <b>Понравилось? Поделись с другом!</b>"""
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=report,
        parse_mode="HTML"
    )
    
    # Предложение подписки
    await send_subscription_offer(update, context, type_name)

async def send_subscription_offer(update, context, type_name):
    """Отправка предложения подписки"""
    sub_text = f"""📬 <b>Еженедельные прогнозы для {type_name}</b>

Каждое воскресенье:
✨ Прогноз на неделю
🎯 Мини-задание для твоего типа
💡 Совет по взаимодействию с другими

💰 <b>199 ₽/месяц</b>
Отмена в любой момент."""
    
    keyboard = [
        [InlineKeyboardButton("📬 Подписаться — 199 ₽/мес", callback_data="buy_subscription")],
        [InlineKeyboardButton("👥 Проверить друга", callback_data="start_test")],
    ]
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=sub_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

async def buy_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = """💳 <b>Оформление подписки</b>

Тариф: Еженедельные прогнозы
Сумма: 199 ₽/месяц

Для оплаты перейдите по ссылке:
[ССЫЛКА_НА_ОПЛАТУ_ПОДПИСКИ]

После оплаты нажмите кнопку ниже 👇"""
    
    keyboard = [
        [InlineKeyboardButton("✅ Я оплатил(а)", callback_data="confirm_sub")],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_to_result")],
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def confirm_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    type_name = context.user_data.get("type_name", "Искатель-Строитель")
    
    await query.edit_message_text(
        f"🎉 <b>Подписка оформлена!</b>\n\n"
        f"Тип: {type_name}\n"
        f"Следующий прогноз: в это воскресенье\n\n"
        f"Ты можешь отменить подписку в любой момент через /cancel",
        parse_mode="HTML"
    )

async def back_to_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await show_result(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "Действие отменено. Напиши /start, чтобы начать заново."
    if update.message:
        await update.message.reply_text(text)
    elif update.callback_query:
        await update.callback_query.answer()
        try:
            await update.callback_query.edit_message_text(text)
        except Exception:
            await update.callback_query.message.reply_text(text)

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CallbackQueryHandler(start_test, pattern="^start_test$"))
    application.add_handler(CallbackQueryHandler(handle_answer, pattern="^answer_"))
    application.add_handler(CallbackQueryHandler(buy_report, pattern="^buy_report$"))
    application.add_handler(CallbackQueryHandler(get_free_report, pattern="^get_free_report$"))
    application.add_handler(CallbackQueryHandler(check_payment, pattern="^check_payment$"))
    application.add_handler(CallbackQueryHandler(buy_subscription, pattern="^buy_subscription$"))
    application.add_handler(CallbackQueryHandler(confirm_subscription, pattern="^confirm_sub$"))
    application.add_handler(CallbackQueryHandler(back_to_result, pattern="^back_to_result$"))
    
    print("🤖 Бот запущен! Напишите ему в Telegram.")
    application.run_polling()

if __name__ == "__main__":
    main()
