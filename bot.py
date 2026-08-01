import os, logging, asyncio, requests, hashlib, time, json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
BOT_TOKEN = "7762673968:AAEP_lnlGwyT1K6ucnJsE7v9bhrAE_uaYr4"
ADMIN_ID = 6040546032
API_BASE = "https://api.temp-mail.org"
HEADERS = {"Accept": "application/json", "User-Agent": "BlackWebBot/2.0"}

def _md5(text): return hashlib.md5(text.encode()).hexdigest()

def _request(endpoint, method="GET", data=None):
    try:
        r = requests.get(f"{API_BASE}{endpoint}", headers=HEADERS, timeout=15) if method == "GET" else requests.post(f"{API_BASE}{endpoint}", json=data, headers=HEADERS, timeout=15)
        return r.json() if r.status_code == 200 else None
    except: return None

def gen_email():
    h = _md5(str(int(time.time())))
    dr = _request("/domains")
    if not dr: return None, None
    doms = [d["name"] for d in dr] if isinstance(dr, list) else dr.get("domains", [])
    if not doms: return None, None
    return h[:10] + "@" + doms[0], _md5(h[:10] + "@" + doms[0])

def check_mail(md5): r = _request(f"/request/mail/id/{md5}/"); return r if isinstance(r, list) else []

def load_j(path, dft):
    try:
        with open(path) as f: return json.load(f)
    except: return dft

def save_j(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f: json.dump(data, f, indent=2)

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    appr = load_j("/tmp/approved.json", [])
    if uid not in appr and uid != ADMIN_ID:
        await update.message.reply_text("⏳ طلبك قيد المراجعة من الأدمن.")
        try: await ctx.bot.send_message(ADMIN_ID, f"طلب جديد من {uid}\n/approve {uid}")
        except: pass
        return
    kb = [[InlineKeyboardButton("📧 إنشاء بريد", callback_data="gen"), InlineKeyboardButton("📥 البريد الوارد", callback_data="inbox")]]
    await update.message.reply_text("🛡️ *BLACK WEB* © 2026\n\n⚠️ البريد المؤقت لا يصلح للحسابات البنكية.", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

async def btn(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if q.data == "gen":
        e, m = gen_email()
        if not e: await q.message.reply_text("❌ فشل. أعد المحاولة."); return
        save_j("/tmp/inbox.json", {str(q.from_user.id): {"email": e, "md5": m}})
        await q.message.reply_text(f"📧 *بريدك:*\n`{e}`", parse_mode="Markdown")
    elif q.data == "inbox":
        ib = load_j("/tmp/inbox.json", {}).get(str(q.from_user.id), {})
        msgs = check_mail(ib.get("md5", ""))
        if not msgs: await q.message.reply_text("📭 فارغ."); return
        txt = "📥 *البريد الوارد:*\n\n"
        for i, m in enumerate(msgs[:10], 1): txt += f"{i}. *{m.get('mail_subject','?')[:40]}*\n   من: {m.get('mail_from','?')}\n\n"
        await q.message.reply_text(txt, parse_mode="Markdown")

async def approve(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        uid = int(ctx.args[0]); a = load_j("/tmp/approved.json", [])
        if uid not in a: a.append(uid); save_j("/tmp/approved.json", a)
        await ctx.bot.send_message(uid, "✅ تمت الموافقة! استخدم /start")
        await update.message.reply_text(f"✅ {uid}")
    except: await update.message.reply_text("/approve <id>")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("approve", approve))
    app.add_handler(CallbackQueryHandler(btn))
    print("🛡️ BLACK WEB Bot running...")
    app.run_polling()

if __name__ == "__main__": main()
