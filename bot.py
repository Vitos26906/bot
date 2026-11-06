import html
import json
import os
import random
import string
import traceback
import datetime
import telebot
from telebot import types

TOKEN = os.environ.get("TOKEN", "9244180965:AAEppnCYinXmz9tM_xcxPZe9DAV20h0pMdA")

BOT_USERNAME = "AnonAsk8oBot"
SHOW_SENDER = True

ADMIN_IDS = {741050372, 1210447328}  # @Vitos_126, @Enchantix333
ADMIN_USERNAMES = set()

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

STORE_FILE = "codes.json"

codes = {}
owner_of = {}
pending = {}
last_sent = {}
last_target = {}
blocked = {}
stats = {}
visitors = {}
users = {}

def load_store():
    global codes, owner_of, pending, last_target, blocked, stats, visitors, users
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
            stats = {int(k): v for k, v in data.get("stats", {}).items()}
            visitors = {int(k): v for k, v in data.get("visitors", {}).items()}
            users = {int(k): v for k, v in data.get("users", {}).items()}
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
            "stats": {str(k): v for k, v in stats.items()},
            "visitors": {str(k): v for k, v in visitors.items()},
            "users": {str(k): v for k, v in users.items()},
        }, f)

load_store()

def emoji(emoji_id, fallback):
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'

ROCKET     = emoji("5264842920858494775", "🚀")
BOLT       = emoji("5265122617718743423", "⚡️")
TG_ICON    = emoji("5352877806122447940", "✈️")
TIKTOK_ICON = emoji("5353034628263330616", "🎵")
INSTA_ICON = emoji("5355097780228470775", "📷")
CHECK      = emoji("5265026513530528912", "✔️")
NEW_MSG    = emoji("5778137984276632041", "💬")
REPLY      = emoji("5816895683256390576", "↩️")
CHART      = emoji("5463211586061607447", "📊")
OUTBOX     = emoji("5264759912025564026", "📤")
CROWN      = emoji("5262853268668687515", "👑")
EYES       = "👀"

cancel_kb = types.InlineKeyboardMarkup()
cancel_kb.add(types.InlineKeyboardButton("❌ Отменить отправку",
                                         callback_data="cancel"))

after_kb = types.InlineKeyboardMarkup()
after_kb.add(types.InlineKeyboardButton("🔼 Отправить ещё одно",
                                        callback_data="send_another"))
after_kb.add(types.InlineKeyboardButton("🗑 Удалить сообщение",
                                        callback_data="delete_msg"))

def owner_kb(sender_id):
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("😟 Заблокировать",
                                      callback_data=f"block_{sender_id}"),
           types.InlineKeyboardButton("🎨 Ответить",
                                      callback_data=f"reply_{sender_id}"))
    return kb

def unblock_kb(sender_id):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🙂 Разблокировать",
                                      callback_data=f"unblock_{sender_id}"))
    return kb

def sender_name(user):
    if user.username:
        return "@" + user.username
    return user.first_name or "Аноним"

def is_admin(user):
    return user.id in ADMIN_IDS

def moscow_now():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3)))

def moscow_today():
    return moscow_now().strftime("%Y-%m-%d")

def remember_user(user):
    if user.id in users:
        return
    users[user.id] = {
        "name": user.first_name or "Аноним",
        "username": ("@" + user.username) if user.username else "нет username",
        "first_seen": moscow_now().strftime("%d.%m.%Y %H:%M"),
    }
    save_store()

def get_stats(user_id):
    today = moscow_today()
    s = stats.get(user_id)
    if not s or s.get("date") != today:
        s = {"date": today,
             "msgs_today": 0, "msgs_total": 0,
             "clicks_today": 0, "clicks_total": 0}
        stats[user_id] = s
    return s

def add_click(user_id, visitor_user):
    s = get_stats(user_id)
    s["clicks_today"] += 1
    s["clicks_total"] += 1

    vis = visitors.setdefault(user_id, [])
    name = visitor_user.first_name or "Аноним"
    username = ("@" + visitor_user.username) if visitor_user.username else "нет username"
    vis.append({
        "id": visitor_user.id,
        "name": name,
        "username": username,
        "time": moscow_now().strftime("%d.%m %H:%M"),
    })
    save_store()

def add_message(user_id):
    s = get_stats(user_id)
    s["msgs_today"] += 1
    s["msgs_total"] += 1
    save_store()

def intro_text():
    return (
        f"{ROCKET} Здесь можно отправить <b>анонимное сообщение</b> человеку, "
        "который опубликовал эту ссылку.\n\n"
        f"{BOLT} <b>Напишите сюда всё, что хотите ему передать, "
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

def send_link_message(user_id):
    code = new_code(user_id)
    link = f"https://t.me/{BOT_USERNAME}?start={code}"
    text = (
        f"<b>Начни получать анонимные сообщения прямо сейчас {ROCKET}</b>\n\n"
        "Твоя ссылка 👇\n"
        f'<blockquote><a href="{link}">t.me/{BOT_USERNAME}?start={code}</a></blockquote>\n\n'
        f"<b>Размести эту ссылку ☝️ в описании профиля {TG_ICON}/{TIKTOK_ICON}/{INSTA_ICON}, "
        "чтобы начать получать анонимные сообщения 💬</b>"
    )
    link_kb = types.InlineKeyboardMarkup()
    link_kb.add(types.InlineKeyboardButton("✈️ Поделиться ссылкой",
                                           url=f"https://t.me/share/url?url={link}"))
    bot.send_message(user_id, text, reply_markup=link_kb,
                     disable_web_page_preview=True)

@bot.message_handler(commands=["admin"])
def admin_cmd(message):
    user = message.from_user
    if not is_admin(user):
        bot.send_message(message.chat.id, "🚫 Эта команда только для администратора.")
        return

    uid = message.chat.id
    total_users = len(users)
    total_links = len(codes)
    total_msgs = sum(s.get("msgs_total", 0) for s in stats.values())
    total_clicks = sum(s.get("clicks_total", 0) for s in stats.values())

    text = (
        f"{CHART} <b>Админ-панель</b>\n\n"
        f"👤 Пользователей бота: <b>{total_users}</b>\n"
        f"🔗 Создано ссылок: <b>{total_links}</b>\n"
        f"{NEW_MSG} Всего отправлено сообщений: <b>{total_msgs}</b>\n"
        f"{EYES} Всего переходов по ссылкам: <b>{total_clicks}</b>\n\n"
        f"<b>Пользователи и их посетители:</b>\n\n"
    )

    if not users:
        text += "Пока пусто."
    else:
        parts = []
        for user_id, u in list(users.items())[-10:]:
            parts.append(
                f"👤 <a href='tg://user?id={user_id}'>{html.escape(u['name'])}</a> "
                f"(<code>{user_id}</code>) · {html.escape(u['username'])}\n"
                f"    👥 Посетители его ссылки:")
            vis = visitors.get(user_id, [])
            if not vis:
                parts.append("    — никого")
            else:
                for v in vis[-10:]:
                    parts.append(
                        f"    👤 <code>{v['id']}</code> · {html.escape(v['name'])} "
                        f"· {html.escape(v['username'])} · {v['time']}")
        text += "\n".join(parts)

    text += ("\n\n💡 Команды:\n"
             "/visitors — ваши посетители\n"
             "/mystats — ваша статистика\n\n"
             f"🆔 Ваш ID: <code>{user.id}</code>")

    bot.send_message(uid, text, disable_web_page_preview=True)

@bot.message_handler(commands=["visitors"])
def visitors_cmd(message):
    user_id = message.chat.id
    vis = visitors.get(user_id, [])
    if not vis:
        bot.send_message(user_id, f"{EYES} Пока никто не открывал вашу ссылку.")
        return

    lines = []
    for v in vis[-20:]:
        lines.append(f"👤 <a href='tg://user?id={v['id']}'>{html.escape(v['name'])}</a>\n"
                     f"ID: <code>{v['id']}</code> · {html.escape(v['username'])}\n"
                     f"🕐 {v['time']}")
    text = (f"{EYES} <b>Кто открывал вашу ссылку</b> (последние {len(lines)}):\n\n"
            + "\n\n".join(lines))
    bot.send_message(user_id, text, disable_web_page_preview=True)

@bot.message_handler(commands=["mystats"])
def mystats(message):
    user_id = message.chat.id
    code = owner_of.get(user_id)
    if not code:
        bot.send_message(user_id, "Чтобы получить свою ссылку, напиши /start")
        return

    s = get_stats(user_id)
    link = f"https://t.me/{BOT_USERNAME}?start={code}"

    today_block = (f"<blockquote><i>💬 Сообщений: {s['msgs_today']}\n"
                   f"{EYES} Переходов по ссылке: {s['clicks_today']}\n"
                   f"{CROWN} Популярность: {min(10, s['clicks_today'] // 10)}/10</i></blockquote>")
    total_block = (f"<blockquote><i>💬 Сообщений: {s['msgs_total']}\n"
                   f"{EYES} Переходов по ссылке: {s['clicks_total']}\n"
                   f"{CROWN} Популярность: {min(10, s['clicks_total'] // 10)}/10</i></blockquote>")

    text = (
        f"{CHART} <b>Статистика профиля</b>\n\n"
        f"{OUTBOX} <b>Сегодня:</b>\n"
        f"{today_block}\n\n"
        f"{OUTBOX} <b>За всё время:</b>\n"
        f"{total_block}\n\n"
        f"<i>Чтобы поднять {CROWN} уровень популярности, "
        f"распространяйте свою персональную ссылку:</i>\n"
        f'<a href="{link}">👉 {link}</a>'
    )
    link_kb = types.InlineKeyboardMarkup()
    link_kb.add(types.InlineKeyboardButton("✈️ Поделиться ссылкой",
                                           url=f"https://t.me/share/url?url={link}"))
    bot.send_message(user_id, text, reply_markup=link_kb,
                     disable_web_page_preview=True)

@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.chat.id
    remember_user(message.from_user)
    parts = message.text.split(maxsplit=1)

    if len(parts) > 1:
        code = parts[1].strip()
        if code in codes:
            owner = codes[code]
            add_click(owner, message.from_user)
            if user_id != owner:
                try:
                    bot.send_message(owner,
                                     f"{EYES} По вашей ссылке открыл бот: "
                                     f"<a href='tg://user?id={user_id}'>{html.escape(message.from_user.first_name or 'Аноним')}</a> "
                                     f"(ID: <code>{user_id}</code>)",
                                     disable_web_page_preview=True)
                except Exception:
                    pass
            if user_id != owner and user_id in blocked.get(owner, set()):
                bot.send_message(user_id, "🚫 Владелец этой ссылки заблокировал вас.")
                return
            pending[user_id] = owner
            save_store()
            bot.send_message(user_id, intro_text(), reply_markup=cancel_kb)
        else:
            bot.send_message(user_id,
                             "🔗 Эта ссылка устарела. Попросите у владельца новую.")
        return

    send_link_message(user_id)

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
                                      reply_markup=unblock_kb(sender))
    except Exception:
        pass
    bot.answer_callback_query(call.id, "🚫 Отправитель заблокирован.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("unblock_"))
def unblock(call):
    owner = call.message.chat.id
    sender = int(call.data.split("_")[1])
    blocked.get(owner, set()).discard(sender)
    save_store()
    try:
        bot.edit_message_reply_markup(owner, call.message.message_id,
                                      reply_markup=owner_kb(sender))
    except Exception:
        pass
    bot.answer_callback_query(call.id, "🙂 Отправитель разблокирован.")

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
        send_link_message(uid)
        return

    target = pending.pop(uid)
    save_store()
    last_target[uid] = target
    save_store()

    conf = bot.send_message(uid, f"{CHECK} Сообщение отправлено, ожидайте ответ!",
                            reply_to_message_id=message.message_id,
                            reply_markup=after_kb)
    last_sent[uid] = (conf.message_id, message.message_id)

    add_message(target)

    from_line = ""
    if SHOW_SENDER and uid != target:
        from_line = f"\n\n👤 От: {html.escape(sender_name(message.from_user))}"

    header = f"{NEW_MSG} У тебя новое анонимное сообщение!"
    footer = f"\n\n{REPLY} Свайпни для ответа."

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
