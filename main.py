import asyncio
import re
import json
import os
import http.server
import socketserver
import threading
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
from telethon.tl.types import InputMediaDice
from telethon import Button

# --- RENDER UCHUN SOXTA PORT OCHISH (MUHIM) ---
def run_dummy_server():
    # Render avtomatik taqdim etadigan portni oladi, bo'lmasa 8080 ishlatadi
    PORT = int(os.environ.get("PORT", 8080))
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Render uchun soxta server {PORT} portda ishga tushdi")
        httpd.serve_forever()

# Serverni alohida oqimda (thread) ishga tushiramiz
threading.Thread(target=run_dummy_server, daemon=True).start()

# --- ASOSIY MA'LUMOTLAR ---
API_ID = 20429961
API_HASH = '4ad3a141f391112f26aa88ee88f2c7b0'
BOT_TOKEN = '8161847784:AAGFYJ2bsdHRuwgrZPnhwU4MEQgrDmUI7Qs'

DB_FILE = 'users_db.json'

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f)

db = load_db()
bot = TelegramClient('bot_final_manager', API_ID, API_HASH)
user_clients = {}
running_tasks = {}

def clean_input(text):
    return re.sub(r'[^\w]', '', text)

# USERBOT FUNKSIYALARI
async def setup_user_handlers(client, owner_id):
    @client.on(events.NewMessage(pattern='/01'))
    async def slot_engine(e):
        if not e.out:
            return
        try:
            await e.delete()
        except:
            pass

        task_key = f"{owner_id}_{e.chat_id}"
        running_tasks[task_key] = True

        while running_tasks.get(task_key):
            try:
                msg = await client.send_message(e.chat_id, file=InputMediaDice(emoticon="🎰"))
                if msg.media.value == 64:
                    running_tasks[task_key] = False
                    link = f"https://t.me/c/{str(e.chat_id).replace('-100', '')}/{msg.id}"
                    await bot.send_message(owner_id, f"🎊 777 TUSHDI!\n📍 Link: {link} 🔥")
                    break
                await asyncio.sleep(0.5)
            except Exception as ex:
                print(f"Xato: {ex}")
                break

    @client.on(events.NewMessage(pattern='/02'))
    async def stop_engine(e):
        if not e.out:
            return
        try:
            await e.delete()
        except:
            pass
        task_key = f"{owner_id}_{e.chat_id}"
        running_tasks[task_key] = False
        await bot.send_message(owner_id, f"🛑 To'xtatildi!")

async def main():
    await bot.start(bot_token=BOT_TOKEN)
    print("🚀 Bot ishga tushdi!")

    # Bazadagi sessiyalarni yuklash
    for cid, info in db.items():
        if info.get('session'):
            try:
                cl = TelegramClient(StringSession(info['session']), API_ID, API_HASH)
                await cl.connect()
                if await cl.is_user_authorized():
                    user_clients[int(cid)] = cl
                    asyncio.create_task(setup_user_handlers(cl, int(cid)))
            except:
                continue

    @bot.on(events.NewMessage(pattern='/start'))
    async def start_handler(event):
        cid = str(event.chat_id)
        buttons = [[Button.inline("👤 Mening Profilim", b"profile")], [Button.inline("📝 Eslatma", b"eslatma")]]

        if cid in db and db[cid].get('logged_in'):
            await event.respond("🏠 Asosiy menyu", buttons=buttons)
        else:
            db[cid] = {'step': 'phone'}
            save_db(db)
            await event.respond("👋 Xush kelibsiz!\n\nUlanish uchun Telegram raqamingizni yuboring 📲")

    @bot.on(events.CallbackQuery)
    async def callback_handler(event):
        cid = str(event.chat_id)
        if event.data == b"profile":
            info = db.get(cid, {})
            text = f"👤 Profil:\n📞 Raqam: `{info.get('phone')}`\n🆔 Nik: {info.get('name')}\n✅ Ulangan" if info.get(
                'logged_in') else "❌ Ro'yxatdan o'ting!"
            await event.answer(text, alert=True)
        elif event.data == b"eslatma":
            await event.answer("📝 Eslatma:\n/01 boshlaydi 🔥\n/02 tugatadi 🛑", alert=True)

    @bot.on(events.NewMessage)
    async def login_flow(event):
        cid = str(event.chat_id)
        if cid not in db or db[cid].get('logged_in') or event.text.startswith('/'): 
            return
        text = event.text.strip()

        if db[cid]['step'] == 'phone' and text.startswith('+'):
            db[cid]['phone'] = text
            cl = TelegramClient(StringSession(), API_ID, API_HASH)
            await cl.connect()
            try:
                sent = await cl.send_code_request(text)
                user_clients[event.chat_id] = cl
                db[cid].update({'hash': sent.phone_code_hash, 'step': 'code'})
                save_db(db)
                await event.respond("📩 SMS kodni nuqtalar bilan yuboring: 1.2.3.4.5 🔢")
            except Exception as e:
                await event.respond(f"❌ Xato: {e}")

        elif db[cid]['step'] == 'code':
            client = user_clients.get(event.chat_id)
            try:
                await client.sign_in(db[cid]['phone'], clean_input(text), phone_code_hash=db[cid]['hash'])
                await success_login(event, client, event.chat_id)
            except SessionPasswordNeededError:
                db[cid]['step'] = '2fa'
                save_db(db)
                await event.respond("🔐 2-bosqichli parolni nuqtalar bilan yuboring: 🔑")
            except Exception as e:
                await event.respond(f"❌ Xato: {e}")

    async def success_login(event, client, chat_id):
        me = await client.get_me()
        db[str(chat_id)].update(
            {'logged_in': True, 'session': client.session.save(), 'name': me.first_name, 'step': 'done'})
        save_db(db)
        await event.respond(f"🎉 Profil ulandi!\n👤 {me.first_name}\n\n📝 /01 boshlaydi /02 tugatadi 🔥")
        asyncio.create_task(setup_user_handlers(client, chat_id))

    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())

