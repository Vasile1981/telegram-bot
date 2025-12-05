
import telebot
from openai import OpenAI
from datetime import datetime, timedelta

# ===== НАСТРОЙКИ =====
# сюда ВСТАВЬ свои реальные значения

BOT_TOKEN = ""
OPENAI_API_KEY = ""

FREE_MESSAGES = 3          # сколько бесплатных ответов
SUBSCRIPTION_DAYS = 30     # на сколько дней открывать доступ после активации

# ===== КЛИЕНТЫ =====
bot = telebot.TeleBot(BOT_TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY)

# ===== ПАМЯТЬ ПРО ПОЛЬЗОВАТЕЛЕЙ (пока в оперативке) =====
# users[user_id] = {"free_left": int, "paid_until": datetime | None}
users = {}


def get_user(user_id: int):
    """Получить/создать запись о пользователе."""
    if user_id not in users:
        users[user_id] = {
            "free_left": FREE_MESSAGES,
            "paid_until": None,
        }
    return users[user_id]


def is_paid(user_id: int) -> bool:
    """Есть ли у пользователя оплаченный доступ сейчас."""
    info = get_user(user_id)
    if not info["paid_until"]:
        return False
    return info["paid_until"] > datetime.utcnow()


# ===== ЗАПРОС К CHATGPT =====

def ask_gpt(prompt: str) -> str:
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system",
                 "content": "Ты дружелюбный помощник. Отвечай коротко и по делу."},
                {"role": "user", "content": prompt},
            ],
        )
        return completion.choices[0].message.content
    except Exception as e:
        print("Ошибка OpenAI:", e)
        return "Извини, я сейчас не могу ответить. Попробуй ещё раз позже."


# ===== КОМАНДЫ БОТА =====

@bot.message_handler(commands=["start", "help"])
def start_handler(m):
    user_id = m.from_user.id
    info = get_user(user_id)

    text = (
        "Привет! Я бот-помощник 🤖\n\n"
        f"У тебя есть {info['free_left']} бесплатных сообщений.\n"
        "Пиши любой вопрос — я отвечу.\n\n"
        "Платный доступ пока включается вручную командой:\n"
        "`/activate КОД`\n"
        "(позже тут сделаем оплату через Crypto Bot)."
    )
    bot.send_message(m.chat.id, text, parse_mode="Markdown")


@bot.message_handler(commands=["activate"])
def activate(m):
    """
    ВРЕМЕННО: любое слово после /activate будет считаться «кодом»
    и включит подписку на SUBSCRIPTION_DAYS дней.
    Потом сюда прикрутим настоящий платеж через Crypto Bot.
    """
    user_id = m.from_user.id
    parts = m.text.split()

    if len(parts) < 2:
        bot.send_message(m.chat.id, "Напиши: /activate КОД")
        return

    # здесь потом будем проверять код оплаты
    # а пока просто даём подписку
    info = get_user(user_id)
    info["paid_until"] = datetime.utcnow() + timedelta(days=SUBSCRIPTION_DAYS)

    until_str = info["paid_until"].strftime("%d.%m.%Y")
    bot.send_message(
        m.chat.id,
        f"Подписка активирована до {until_str} ✅\n"
        "Пиши вопросы — лимитов нет.",
    )


@bot.message_handler(content_types=["text"])
def chat_handler(m):
    user_id = m.from_user.id
    info = get_user(user_id)

    # если есть оплаченный доступ — просто отвечаем
    if is_paid(user_id):
        reply = ask_gpt(m.text)
        bot.send_message(m.chat.id, reply)
        return

    # если бесплатные сообщения ещё есть
    if info["free_left"] > 0:
        info["free_left"] -= 1
        reply = ask_gpt(m.text)
        bot.send_message(
            m.chat.id,
            f"{reply}\n\n"
            f"Бесплатных сообщений осталось: {info['free_left']}",
        )
        return

    # бесплатные закончились
    bot.send_message(
        m.chat.id,
        "Бесплатные сообщения закончились 😔\n\n"
        "Скоро тут появится оплата через Crypto Bot, и доступ будет включаться автоматически.\n"
        "Пока можешь прислать команду /activate КОД (мы включим вручную).",
    )


if __name__ == "__main__":
    print("Бот запущен...")
    bot.infinity_polling(skip_pending=True)
