import os
import telebot
import requests
import threading
import time
from datetime import datetime

# Получаем токен из переменных окружения
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Инициализация бота
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Хранилище сообщений
forwarded_messages = []
group_messages = {}

# Функция отправки запроса в n8n + OpenAI
def ask_openai(prompt):
    try:
        response = requests.post(
            "https://n8n-lat.solowey.ru/webhook/c15cba7e-615e-4494-ba01-decf742c8c7c",
            json={"prompt": prompt},
            timeout=20
        )
        return response.text.strip()
    except Exception as e:
        return f"⚠️ Ошибка от n8n: {str(e)}"

# Обработка пересланных сообщений в личку
@bot.message_handler(func=lambda msg: msg.chat.type == "private" and msg.text)
def handle_forward(msg):
    sender = msg.forward_sender_name or \
             (msg.forward_from_chat.title if msg.forward_from_chat else "Неизвестный источник")
    forwarded_messages.append({"text": msg.text, "sender": sender})

    if len(forwarded_messages) >= 3:
        text = "\n\n".join([f"{m['sender']}: {m['text']}" for m in forwarded_messages[-30:]])
        prompt = f"""
Проанализируй этот диалог:

1. Общий тон общения.
2. Стиль каждого участника (по имени).
3. Конфликты, предложения, токсичность.
4. Примеры фраз.
5. Что можно улучшить?

Диалог:
{text}
"""
        reply = ask_openai(prompt)
        bot.reply_to(msg, f"🧠 Анализ:\n\n{reply}")
        forwarded_messages.clear()

# Сбор сообщений из группового чата
@bot.message_handler(func=lambda msg: msg.chat.type in ['group', 'supergroup'] and msg.text)
def collect_group(msg):
    if msg.chat.id not in group_messages:
        group_messages[msg.chat.id] = []
    group_messages[msg.chat.id].append({
        "sender": msg.from_user.first_name or "Аноним",
        "text": msg.text
    })

# Команда для анализа по запросу
@bot.message_handler(commands=['analyze'])
def analyze_chat(msg):
    chat_id = msg.chat.id
    messages = group_messages.get(chat_id, [])
    if not messages:
        bot.reply_to(msg, "⚠️ Нет сообщений для анализа.")
        return

    text = "\n\n".join([f"{m['sender']}: {m['text']}" for m in messages[-30:]])
    prompt = f"""
Проанализируй чат:

1. Общий тон.
2. Кто конструктивен, кто нет.
3. Были ли конфликты или предложения.
4. Примеры фраз.
5. Что можно улучшить?

Диалог:
{text}
"""
    reply = ask_openai(prompt)
    bot.send_message(chat_id, f"📊 Анализ:\n\n{reply}")
    group_messages[chat_id] = []

# Ежедневный автоотчёт в 23:59
def daily_report():
    while True:
        now = datetime.now()
        if now.hour == 23 and now.minute == 59:
            for chat_id, messages in group_messages.items():
                if not messages:
                    continue
                text = "\n\n".join([f"{m['sender']}: {m['text']}" for m in messages[-30:]])
                prompt = f"""
Сделай итог анализа общения за день:

- Общий тон
- Конфликты, предложения
- Кто как общался
- Что можно улучшить

Диалог:
{text}
"""
                reply = ask_openai(prompt)
                bot.send_message(chat_id, f"🌙 Итог дня:\n\n{reply}")
                group_messages[chat_id] = []
            time.sleep(60)
        else:
            time.sleep(20)

# Запуск бота
print("✅ Бот запущен")
threading.Thread(target=daily_report, daemon=True).start()
bot.infinity_polling()
