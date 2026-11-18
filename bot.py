import asyncio, os, re, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup as KB, InlineKeyboardButton as Btn
from pyrogram.errors import FloodWait

# ---- Config: environment variables se ----
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
if not (API_ID and API_HASH and BOT_TOKEN):
    raise SystemExit("API_ID, API_HASH, BOT_TOKEN environment variables set karo.")

app = Client("fwdbot", api_id=API_ID, api_hash=API_HASH,
             bot_token=BOT_TOKEN, in_memory=True)
S = {}  # user_id -> state

# ---- Render ke liye chhota health server (free web service sleep/port check) ----
class Ping(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")
    def log_message(self, *a):
        pass

def serve():
    port = int(os.environ.get("PORT", "10000"))
    HTTPServer(("0.0.0.0", port), Ping).serve_forever()

threading.Thread(target=serve, daemon=True).start()

# ---- Bot ----
def parse(link):
    m = re.search(r"t\.me/c/(\d+)/(\d+)", link)
    if m:
        return int("-100" + m.group(1)), int(m.group(2))
    m = re.search(r"t\.me/([A-Za-z0-9_]+)/(\d+)", link)
    if m:
        return m.group(1), int(m.group(2))

@app.on_message(filters.command("start") & filters.private)
async def start(_, m):
    await m.reply("👋 Welcome! /clone se channel clone shuru karo.")

@app.on_message(filters.command("clone") & filters.private)
async def clone(_, m):
    S[m.from_user.id] = {"step": "first"}
    await m.reply("📍 Step 1/3: Range Selection\n\nFirst message ka link bhejo.\nExample: https://t.me/c/12345/100")

@app.on_message(filters.private & ~filters.command(["start", "clone"]))
async def flow(c, m):
    st = S.get(m.from_user.id)
    if not st:
        return
    step = st["step"]
    text = m.text or ""

    if step in ("first", "last"):
        p = parse(text)
        if not p:
            return await m.reply("❌ Link galat hai.")
        if step == "first":
            st["src"], st["a"] = p
            st["step"] = "last"
            return await m.reply(f"✅ Start Message: {p[1]}\n\n📍 Step 2/3: Last message ka link bhejo.")
        st["b"] = p[1]
        st["step"] = "dest"
        return await m.reply(
            f"✅ Range Set: {st['a']} to {st['b']}\n📂 Source: {st['src']}\n\n"
            "📤 Step 3/3: Destination Channel ID (-100xxxx) bhejo ya wahan se koi message forward karo.\n"
            "⚠️ Bot ko Destination me Admin banao!")

    if step == "dest":
        chat = getattr(m, "forward_from_chat", None)
        if chat:
            st["dest"] = chat.id
        else:
            try:
                st["dest"] = int(text.strip())
            except Exception:
                return await m.reply("❌ Sahi ID ya forwarded message bhejo.")
        st["step"] = "find"
        return await m.reply("Caption me FIND karne wala text bhejo (skip karne ke liye: skip):")

    if step == "find":
        st["find"] = None if text.lower() == "skip" else text
        if st["find"] is None:
            st["rep"] = ""
            st["step"] = "confirm"
            return await ask_confirm(m, st)
        st["step"] = "rep"
        return await m.reply("REPLACEMENT text bhejo ya Remove dabao:",
                             reply_markup=KB([[Btn("🗑 Remove", "remove")]]))

    if step == "rep":
        st["rep"] = text
        st["step"] = "confirm"
        return await ask_confirm(m, st)

async def ask_confirm(m, st):
    await m.reply(
        f"📋 Confirm:\nSource: {st['src']}\nRange: {st['a']}–{st['b']}\n"
        f"Dest: {st['dest']}\nFind: {st['find']}\nReplace: {st['rep']!r}",
        reply_markup=KB([[Btn("✅ Start", "go"), Btn("❌ Cancel", "cancel")]]))

@app.on_callback_query()
async def cb(c, q):
    uid = q.from_user.id
    st = S.get(uid)
    if not st:
        return await q.answer("Session nahi mila, /clone karo")
    if q.data == "remove":
        st["rep"] = ""
        st["step"] = "confirm"
        await q.message.delete()
        return await ask_confirm(q.message, st)
    if q.data == "cancel":
        S.pop(uid, None)
        return await q.message.edit("❌ Cancelled")
    if q.data == "go":
        await q.message.edit("🚀 Shuru ho gaya...")
        asyncio.create_task(run(c, q.message, st))
        S.pop(uid, None)

async def run(c, msg, st):
    ok = fail = 0
    for start in range(st["a"], st["b"] + 1, 100):
        ids = list(range(start, min(start + 100, st["b"] + 1)))
        try:
            msgs = await c.get_messages(st["src"], ids)
        except Exception as e:
            await msg.reply(f"❌ Source read error: {e}\nBot source me member hai?")
            return
        for m in msgs:
            if not m or m.empty or m.service:
                continue
            try:
                cap = m.caption.html if m.caption else None
                if cap and st["find"]:
                    cap = cap.replace(st["find"], st["rep"])
                if m.media:
                    await m.copy(st["dest"], caption=cap)
                else:
                    await m.copy(st["dest"])
                ok += 1
                await asyncio.sleep(1.5)
            except FloodWait as e:
                await asyncio.sleep(e.value + 1)
            except Exception:
                fail += 1
        await msg.reply(f"⏳ Progress: ✅ {ok} | ❌ {fail}")
    await msg.reply(f"🎉 Done! ✅ {ok} | ❌ {fail}")

app.run()
