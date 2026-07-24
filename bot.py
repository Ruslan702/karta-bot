import logging
import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from yookassa import Payment, Configuration

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN")
YOOKASSA_SHOP_ID = os.environ.get("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET_KEY = os.environ.get("YOOKASSA_SECRET_KEY")
# =========================================

# Настройка ЮKassa
if YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY:
    Configuration.account_id = YOOKASSA_SHOP_ID
    Configuration.secret_key = YOOKASSA_SECRET_KEY

# Загрузка данных
with open("questions.json", "r", encoding="utf-8") as f:
    QUESTIONS = json.load(f)

with open("personality_types.json", "r", encoding="utf-8") as f:
    PERSONALITY_TYPES = json.load(f)

# 12 архетипов души
ARCHETYPES = {
    "M": "Проводник Истины",
    "A": "Алхимик Реальности",
    "S": "Странник Вечности",
    "R": "Разрушитель Иллюзий",
    "L": "Слияние Душ",
    "Z": "Зеркало Истины",
    "Ar": "Архитектор Порядка",
    "C": "Целитель Миров",
    "V": "Воин Света",
    "H": "Хранитель Земли",
    "T": "Творец Вселенной",
    "D": "Светлое Дитя"
}

def calculate_archetype(scores):
    """Определяет основной и вторичный архетипы"""
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    primary = sorted_scores[0][0]
    secondary = sorted_scores[1][0]
    
    primary_name = ARCHETYPES.get(primary, "Проводник Истины")
    secondary_name = ARCHETYPES.get(secondary, "Алхимик Реальности")
    
    combo_name = f"{primary_name}-{secondary_name}"
    
    if combo_name not in PERSONALITY_TYPES:
        combo_name = primary_name
    
    return combo_name, sorted_scores

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
    context.user_data["scores"] = {k: 0 for k in ARCHETYPES.keys()}
    context.user_data["current_question"] = 0
    context.user_data["answers"] = []
    
    welcome = f"""👋 Привет, {update.effective_user.first_name}!

<b>Кто ты на самом деле</b>

12 вопросов — и ты узнаешь:
• Свой архетип души
• Миссию в этом воплощении
• Кармические блоки и ключи

🎁 После теста — персональный отчёт

Это не развлечение. Это зеркало.
Твоя душа говорит через него.

Готов услышать?"""
    
    keyboard = [[InlineKeyboardButton("🚀 Начать тест", callback_data="start_test")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await send_or_edit_message(update, welcome, reply_markup)

async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["scores"] = {k: 0 for k in ARCHETYPES.keys()}
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
    
    for archetype, points in answer["scores"].items():
        context.user_data["scores"][archetype] += points
    
    context.user_data["current_question"] += 1
    return await ask_question(update, context)

async def show_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    scores = context.user_data["scores"]
    archetype_name, sorted_scores = calculate_archetype(scores)
    context.user_data["archetype_name"] = archetype_name
    
    primary_key = sorted_scores[0][0]
    primary_name = ARCHETYPES.get(primary_key, "Проводник Истины")
    data = PERSONALITY_TYPES.get(primary_name, PERSONALITY_TYPES["Проводник Истины"])
    
    scores_text = "\n".join([
        f"  {'✨' if i == 0 else '◦'} {ARCHETYPES.get(k, k)}: {v} баллов"
        for i, (k, v) in enumerate(sorted_scores[:4])
    ])
    
    result = f"""🎯 <b>Твой архетип души:</b> {archetype_name}

<i>{data['tagline']}</i>

📊 <b>Твой профиль:</b>
{scores_text}

💡 <b>Кратко о тебе:</b>
{data['core'][:200]}...

✨ <b>Твоя главная суперсила:</b>
{data['strengths'][0]}

💎 <b>Скрытый талант:</b>
{data['hidden_talent'][:150]}...

---
📄 <b>Полный портал души (399 ₽) включает:</b>
• Миссия в этом воплощении
• Прошлая жизнь — кем ты был
• Кармические блоки и как их снять
• Как активировать свой код
• Роль в матрице / Вселенной
• Совместимость со всеми 12 архетипами

💰 <b>Открыть портал души:</b> 399 ₽"""
    
    keyboard = [
        [InlineKeyboardButton("📄 Открыть портал души — 399 ₽", callback_data="buy_report")],
        [InlineKeyboardButton("🔄 Пройти заново", callback_data="start_test")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await send_or_edit_message(update, result, reply_markup)

async def buy_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    archetype_name = context.user_data.get("archetype_name", "Проводник Истины")
    user_id = update.effective_user.id
    
    # Проверяем, настроена ли ЮKassa
    if not YOOKASSA_SHOP_ID or not YOOKASSA_SECRET_KEY:
        # Режим без оплаты (если ключи не добавлены)
        text = f"""💳 <b>Открытие портала души</b>

Архетип: {archetype_name}
Сумма: 399 ₽

⚠️ <b>Платёжная система временно недоступна</b>

Но вы можете открыть портал бесплатно в рамках тестирования! 👇"""
        
        keyboard = [
            [InlineKeyboardButton("📄 Открыть портал бесплатно", callback_data="get_free_report")],
            [InlineKeyboardButton("◀️ Назад к результату", callback_data="back_to_result")],
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return
    
    # Создаём реальный платёж через ЮKassa
    try:
        payment = Payment.create({
            "amount": {
                "value": "399.00",
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": f"https://t.me/{context.bot.username}"
            },
            "capture": True,
            "description": f"Портал души: {archetype_name}",
            "metadata": {
                "user_id": str(user_id),
                "product": "report",
                "archetype": archetype_name
            }
        })
        
        # Сохраняем ID платежа
        context.user_data["payment_id"] = payment.id
        pay_url = payment.confirmation.confirmation_url
        
        text = f"""💳 <b>Открытие портала души</b>

Архетип: {archetype_name}
Сумма: 399 ₽

Нажмите кнопку ниже для оплаты 👇"""
        
        keyboard = [
            [InlineKeyboardButton("💳 Оплатить 399 ₽", url=pay_url)],
            [InlineKeyboardButton("✅ Я оплатил(а)", callback_data="check_payment")],
            [InlineKeyboardButton("◀️ Назад", callback_data="back_to_result")],
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Payment creation error: {e}")
        await query.edit_message_text(
            "❌ Ошибка создания платежа. Попробуйте позже.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Назад", callback_data="back_to_result")]
            ])
        )

async def get_free_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Тестовый режим — полный портал души бесплатно"""
    query = update.callback_query
    await query.answer()
    
    archetype_name = context.user_data.get("archetype_name", "Проводник Истины")
    
    primary_key = context.user_data.get("scores", {})
    if primary_key:
        sorted_scores = sorted(primary_key.items(), key=lambda x: x[1], reverse=True)
        primary_name = ARCHETYPES.get(sorted_scores[0][0], "Проводник Истины")
    else:
        primary_name = "Проводник Истины"
    
    data = PERSONALITY_TYPES.get(primary_name, PERSONALITY_TYPES["Проводник Истины"])
    
    report = f"""🧪 <b>ТЕСТОВЫЙ РЕЖИМ — ПОЛНЫЙ ПОРТАЛ ДУШИ</b>

🎯 <b>Твой архетип:</b> {archetype_name}
<i>{data['tagline']}</i>

━━━━━━━━━━━━━━━━━━━━━

🌟 <b>МИССИЯ В ЭТОМ ВОПЛОЩЕНИИ</b>
{data['mission']}

━━━━━━━━━━━━━━━━━━━━━

🕰 <b>ПРОШЛАЯ ЖИЗНЬ</b>
{data['past_life']}

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

⛓ <b>КАРМИЧЕСКИЙ БЛОК</b>
{data['karmic_block']}

━━━━━━━━━━━━━━━━━━━━━

🔑 <b>КАК АКТИВИРОВАТЬ СВОЙ КОД</b>
{data['activation']}

━━━━━━━━━━━━━━━━━━━━━

🌐 <b>ТВОЯ РОЛЬ В МАТРИЦЕ</b>
{data['matrix_role']}

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
{data['compatibility']}

━━━━━━━━━━━━━━━━━━━━━

⚠️ <b>Это тестовая версия.</b>
После запуска полный портал души будет стоить 399 ₽.

💬 <b>Понравилось? Поделись с другом!</b>"""
    
    await query.edit_message_text(report, parse_mode="HTML")
    await send_subscription_offer(update, context, archetype_name)

async def check_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    payment_id = context.user_data.get("payment_id")
    archetype_name = context.user_data.get("archetype_name", "Проводник Истины")
    
    if not payment_id:
        await query.edit_message_text(
            "❌ Платёж не найден. Попробуйте снова.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📄 Открыть портал — 399 ₽", callback_data="buy_report")],
                [InlineKeyboardButton("◀️ Назад", callback_data="back_to_result")]
            ])
        )
        return
    
    try:
        payment = Payment.find_one(payment_id)
        
        if payment.status == "succeeded":
            # Оплата прошла — отправляем отчёт
            await query.edit_message_text("✅ <b>Оплата подтверждена!</b>\n\nОткрываю твой портал души...", parse_mode="HTML")
            
            primary_key = context.user_data.get("scores", {})
            if primary_key:
                sorted_scores = sorted(primary_key.items(), key=lambda x: x[1], reverse=True)
                primary_name = ARCHETYPES.get(sorted_scores[0][0], "Проводник Истины")
            else:
                primary_name = "Проводник Истины"
            
            data = PERSONALITY_TYPES.get(primary_name, PERSONALITY_TYPES["Проводник Истины"])
            
            report = f"""📄 <b>ПОЛНЫЙ ПОРТАЛ ДУШИ</b>

🎯 <b>Твой архетип:</b> {archetype_name}
<i>{data['tagline']}</i>

━━━━━━━━━━━━━━━━━━━━━

🌟 <b>МИССИЯ В ЭТОМ ВОПЛОЩЕНИИ</b>
{data['mission']}

━━━━━━━━━━━━━━━━━━━━━

🕰 <b>ПРОШЛАЯ ЖИЗНЬ</b>
{data['past_life']}

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

⛓ <b>КАРМИЧЕСКИЙ БЛОК</b>
{data['karmic_block']}

━━━━━━━━━━━━━━━━━━━━━

🔑 <b>КАК АКТИВИРОВАТЬ СВОЙ КОД</b>
{data['activation']}

━━━━━━━━━━━━━━━━━━━━━

🌐 <b>ТВОЯ РОЛЬ В МАТРИЦЕ</b>
{data['matrix_role']}

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
{data['compatibility']}

━━━━━━━━━━━━━━━━━━━━━

💬 <b>Понравилось? Поделись с другом!</b>"""
            
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=report,
                parse_mode="HTML"
            )
            await send_subscription_offer(update, context, archetype_name)
            
        elif payment.status in ["pending", "waiting_for_capture"]:
            await query.edit_message_text(
                "⏳ <b>Платёж обрабатывается...</b>\n\nПопробуйте проверить через минуту.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Проверить снова", callback_data="check_payment")],
                    [InlineKeyboardButton("◀️ Назад", callback_data="back_to_result")]
                ]),
                parse_mode="HTML"
            )
        else:
            await query.edit_message_text(
                "❌ <b>Платёж не завершён</b>\n\nПопробуйте оплатить снова.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💳 Оплатить снова", callback_data="buy_report")],
                    [InlineKeyboardButton("◀️ Назад", callback_data="back_to_result")]
                ]),
                parse_mode="HTML"
            )
            
    except Exception as e:
        logger.error(f"Payment check error: {e}")
        await query.edit_message_text(
            "❌ Ошибка проверки платежа. Попробуйте позже.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Проверить снова", callback_data="check_payment")],
                [InlineKeyboardButton("◀️ Назад", callback_data="back_to_result")]
            ])
        )

async def send_subscription_offer(update, context, archetype_name):
    """Отправка предложения подписки"""
    sub_text = f"""📬 <b>Коды недели для {archetype_name}</b>

Каждое воскресенье:
✨ Энергетическая практика под твой архетип
🎯 Мини-задание для роста осознанности
💡 Ключи взаимодействия с другими архетипами

💰 <b>199 ₽/месяц</b>
Отмена в любой момент."""
    
    keyboard = [
        [InlineKeyboardButton("📬 Получить коды — 199 ₽/мес", callback_data="buy_subscription")],
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
    
    archetype_name = context.user_data.get("archetype_name", "Проводник Истины")
    user_id = update.effective_user.id
    
    if not YOOKASSA_SHOP_ID or not YOOKASSA_SECRET_KEY:
        text = """💳 <b>Оформление подписки</b>

Тариф: Коды недели
Сумма: 199 ₽/месяц

⚠️ <b>Платёжная система временно недоступна</b>"""
        
        keyboard = [
            [InlineKeyboardButton("◀️ Назад", callback_data="back_to_result")],
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return
    
    try:
        payment = Payment.create({
            "amount": {
                "value": "199.00",
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": f"https://t.me/{context.bot.username}"
            },
            "capture": True,
            "description": f"Коды недели: {archetype_name}",
            "metadata": {
                "user_id": str(user_id),
                "product": "subscription",
                "archetype": archetype_name
            }
        })
        
        context.user_data["sub_payment_id"] = payment.id
        pay_url = payment.confirmation.confirmation_url
        
        text = f"""💳 <b>Оформление подписки</b>

Тариф: Коды недели
Сумма: 199 ₽/месяц

Нажмите кнопку ниже для оплаты 👇"""
        
        keyboard = [
            [InlineKeyboardButton("💳 Оплатить 199 ₽", url=pay_url)],
            [InlineKeyboardButton("✅ Я оплатил(а)", callback_data="confirm_sub")],
            [InlineKeyboardButton("◀️ Назад", callback_data="back_to_result")],
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Subscription payment error: {e}")
        await query.edit_message_text(
            "❌ Ошибка создания платежа. Попробуйте позже.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Назад", callback_data="back_to_result")]
            ])
        )

async def confirm_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    payment_id = context.user_data.get("sub_payment_id")
    archetype_name = context.user_data.get("archetype_name", "Проводник Истины")
    
    if not payment_id:
        await query.edit_message_text(
            "❌ Платёж не найден.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📬 Получить коды — 199 ₽/мес", callback_data="buy_subscription")],
                [InlineKeyboardButton("◀️ Назад", callback_data="back_to_result")]
            ])
        )
        return
    
    try:
        payment = Payment.find_one(payment_id)
        
        if payment.status == "succeeded":
            await query.edit_message_text(
                f"🎉 <b>Подписка оформлена!</b>\n\n"
                f"Архетип: {archetype_name}\n"
                f"Следующий код: в это воскресенье\n\n"
                f"Ты можешь отменить подписку в любой момент через /cancel",
                parse_mode="HTML"
            )
        else:
            await query.edit_message_text(
                "⏳ <b>Платёж ещё обрабатывается...</b>\n\nПопробуйте проверить позже.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Проверить снова", callback_data="confirm_sub")],
                    [InlineKeyboardButton("◀️ Назад", callback_data="back_to_result")]
                ]),
                parse_mode="HTML"
            )
            
    except Exception as e:
        logger.error(f"Subscription check error: {e}")
        await query.edit_message_text(
            "❌ Ошибка проверки. Попробуйте позже.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Проверить снова", callback_data="confirm_sub")],
                [InlineKeyboardButton("◀️ Назад", callback_data="back_to_result")]
            ])
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
