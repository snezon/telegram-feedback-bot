import telebot
import openai
import threading
import time
from datetime import datetime

# 🔐 Токены
TELEGRAM_TOKEN = "Token"
OPENAI_API_KEY = "OPENAI_API_KEY"

import requests

bot = telebot.TeleBot(TELEGRAM_TOKEN)

forwarded_messages = []
group_messages = []

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

@bot.message_handler(func=lambda msg: msg.chat.type in ['group', 'supergroup'] and msg.text)
def collect_group(msg):
    if msg.chat.id not in group_messages:
        group_messages[msg.chat.id] = []
    group_messages[msg.chat.id].append({
        "sender": msg.from_user.first_name or "Аноним",
        "text": msg.text
    })

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

print("✅ Бот запущен")
threading.Thread(target=daily_report, daemon=True).start()
bot.infinity_polling()
