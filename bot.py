import os
import html
import json
import os
import random
import string
import traceback
import telebot
from telebot import types

TOKEN = os.environ.get("TOKEN", "9244180965:AAEppnCYinXmz9tM_xcxPZe9DAV20h0pMdA")

BOT_USERNAME = "AnonAsk8oBot"
SHOW_SENDER = True

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

STORE_FILE = "codes.json"

codes = {}
owner_of = {}
pending = {}
last_sent = {}
last_target = {}
blocked = {}

def load_store():
    global codes, owner_of, pending, last_target, blocked
    try:
        if os.path.exists(STORE_FILE):
            with open(STORE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            codes = {k: int(v) for k, v in data.get("codes", {}).items()}
            owner_of = {int(k): v for k, v in data.get("owner_of", {}).items()}
            pending = {int(k): int(v) for k, v in data.get("pending", {}).items()}
            last_target = {int(k): int(v)
                           for k, v in data.get("last_target", {}).items()}
            blocked = {int(k): set(map(int, v))
                       for k, v in data.get("blocked", {}).items()}
    except Exception:
        traceback.print_exc()

def save_store():
    with open(STORE_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "codes": codes,
            "owner_of": {str(k): v for k, v in owner_of.items()},
            "pending": {str(k): v for k, v in pending.items()},
            "last_target": {str(k): v for k, v in last_target.items()},
            "blocked": {str(k): list(v) for k, v in blocked.items()},
        }, f)

load_store()

cancel_kb = types.InlineKeyboardMarkup()
cancel_kb.add(types.InlineKeyboardButton("❌ Отменить отправку",
                                         callback_data="cancel"))

after_kb = types.InlineKeyboardMarkup()
after_kb.add(types.InlineKeyboardButton("↗️ Отправить ещё одно",
                                        callback_data="send_another"))
after_kb.add(types.InlineKeyboardButton("🗑 Удалить сообщение",
                                        callback_data="delete_msg"))

def owner_kb(sender_id):
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("😕 Заблокировать",
                                      callback_data=f"block_{sender_id}"),
           types.InlineKeyboardButton("🎨 Ответить",
                                      callback_data=f"reply_{sender_id}"))
    return kb

def sender_name(user):
    if user.username:
        return "@" + user.username
    return user.first_name or "Аноним"

def intro_text():
    return (
        "🚀 Здесь можно отправить <b>анонимное сообщение</b> человеку, "
        "который опубликовал эту ссылку.\n\n"
        "⚡ <b>Напишите сюда всё, что хотите ему передать, "
        "и через несколько секунд он получит ваше сообщение, "
        "но не будет знать от кого.</b>\n\n"
        "<blockquote>Отправить можно: текст, фото, видео, стикеры, "
        "голосовые и видеосообщения (кружки)</blockquote>"
    )

def new_code(user_id):
    if user_id in owner_of:
        return owner_of[user_id]
    while True:
        code = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
        if code not in codes:
            codes[code] = user_id
            owner_of[user_id] = code
            save_store()
            return code

@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.chat.id
    parts = message.text.split(maxsplit=1)

    if len(parts) > 1:
        code = parts[1].strip()
        if code in codes:
            owner = codes[code]
            if user_id in blocked.get(owner, set()):
                bot.send_message(user_id, "🚫 Владелец этой ссылки заблокировал вас.")
                return
            pending[user_id] = owner
            save_store()
            bot.send_message(user_id, intro_text(), reply_markup=cancel_kb)
        else:
            bot.send_message(user_id,
                             "🔗 Эта ссылка устарела. Попросите у владельца новую.")
        return

    code = new_code(user_id)
    link = f"https://t.me/{BOT_USERNAME}?start={code}"
    text = (
        "<b>Начни получать анонимные сообщения прямо сейчас 🚀</b>\n\n"
        "Твоя ссылка 👇\n"
        f'<blockquote><a href="{link}">t.me/{BOT_USERNAME}?start={code}</a></blockquote>\n\n'
        "Размести эту ссылку ☝️ в описании профиля ✈️/🎵/📷, "
        "чтобы начать получать анонимные сообщения 💬"
    )
    link_kb = types.InlineKeyboardMarkup()
    link_kb.add(types.InlineKeyboardButton("✈️ Поделиться ссылкой",
                                           url=f"https://t.me/share/url?url={link}"))
    bot.send_message(user_id, text, reply_markup=link_kb)

@bot.callback_query_handler(func=lambda c: c.data == "cancel")
def cancel(call):
    uid = call.message.chat.id
    if uid in pending:
        pending.pop(uid)
        save_store()
        try:
            bot.edit_message_reply_markup(uid, call.message.message_id,
                                          reply_markup=None)
        except Exception:
            pass
        bot.answer_callback_query(call.id)
        bot.send_message(uid, "Отправка отменена 🙂")
    else:
        bot.answer_callback_query(call.id)
        bot.send_message(uid, "Отменять нечего — вы и не писали сообщение.")

@bot.callback_query_handler(func=lambda c: c.data == "send_another")
def send_another(call):
    uid = call.message.chat.id
    if uid in last_target:
        pending[uid] = last_target[uid]
        save_store()
        bot.answer_callback_query(call.id)
        bot.send_message(uid, intro_text(), reply_markup=cancel_kb)
    else:
        bot.answer_callback_query(call.id)
        bot.send_message(uid, "Сначала отправьте сообщение по чьей-нибудь ссылке.")

@bot.callback_query_handler(func=lambda c: c.data == "delete_msg")
def delete_msg(call):
    uid = call.message.chat.id
    if uid in last_sent:
        conf_id, orig_id = last_sent.pop(uid)
        bot.answer_callback_query(call.id)
        try:
            bot.delete_message(uid, conf_id)
            bot.delete_message(uid, orig_id)
        except Exception:
            pass
    else:
        bot.answer_callback_query(call.id)
        bot.send_message(uid, "Удалять нечего — сообщений ещё не было.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("block_"))
def block(call):
    owner = call.message.chat.id
    sender = int(call.data.split("_")[1])
    blocked.setdefault(owner, set()).add(sender)
    save_store()
    try:
        bot.edit_message_reply_markup(owner, call.message.message_id,
                                      reply_markup=None)
    except Exception:
        pass
    bot.answer_callback_query(call.id, "🚫 Отправитель заблокирован.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("reply_"))
def reply(call):
    owner = call.message.chat.id
    sender = int(call.data.split("_")[1])
    pending[owner] = sender
    save_store()
    try:
        bot.edit_message_reply_markup(owner, call.message.message_id,
                                      reply_markup=None)
    except Exception:
        pass
    bot.answer_callback_query(call.id)
    bot.send_message(owner, intro_text(), reply_markup=cancel_kb)

@bot.message_handler(func=lambda m: True,
                     content_types=["text", "photo", "video", "voice",
                                    "video_note", "sticker", "audio", "document"])
def handle(message):
    uid = message.chat.id
    if uid not in pending:
        bot.send_message(uid, "Чтобы получить свою ссылку, напиши /start")
        return

    target = pending.pop(uid)
    save_store()
    last_target[uid] = target
    save_store()

    conf = bot.send_message(uid, "✅ Сообщение отправлено, ожидайте ответ!",
                            reply_to_message_id=message.message_id,
                            reply_markup=after_kb)
    last_sent[uid] = (conf.message_id, message.message_id)

    from_line = ""
    if SHOW_SENDER and uid != target:
        from_line = f"\n\n👤 От: {html.escape(sender_name(message.from_user))}"

    header = "➡️ У тебя новое анонимное сообщение!"
    footer = "\n\n↩️ Свайпни для ответа."

    try:
        if message.text:
            body = "<blockquote>" + html.escape(message.text) + "</blockquote>"
            bot.send_message(target, f"{header}{from_line}\n\n{body}\n{footer}",
                             reply_markup=owner_kb(uid))
        else:
            bot.send_message(target, header + from_line + footer,
                             reply_markup=owner_kb(uid))
            bot.copy_message(target, uid, message.message_id)
    except Exception as e:
        traceback.print_exc()
        bot.send_message(uid,
                         f"⚠️ Не удалось доставить сообщение получателю.\nПричина: {e}")

bot.polling(none_stop=True)
