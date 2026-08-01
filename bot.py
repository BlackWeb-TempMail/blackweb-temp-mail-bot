import os, logging, requests, hashlib, time, json, re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8939492217:AAH_hSy3yDH3WQ7qRPGM5QcPDb5v4ALUwg4"
ADMIN_ID = 6040546032
DATA_DIR = "/home/user/botdata"
GUERRILLA_API = "https://api.guerrillamail.com/ajax.php"
os.makedirs(DATA_DIR, exist_ok=True)

def load_json(n, d): 
    try: 
        with open(os.path.join(DATA_DIR, n)) as f: return json.load(f)
    except: return d

def save_json(n, d):
    with open(os.path.join(DATA_DIR, n), "w") as f: json.dump(d, f, ensure_ascii=False, indent=2)

# ===== GuerrillaMail API =====
def gm_new_email():
    """Create new GuerrillaMail inbox"""
    r = requests.get(f"{GUERRILLA_API}?f=get_email_address", timeout=10)
    if r.status_code == 200:
        d = r.json()
        return {"email": d["email_addr"], "sid": d["sid_token"]}
    return None

def gm_check_inbox(sid, seq=0):
    """Check inbox for new messages"""
    r = requests.get(f"{GUERRILLA_API}?f=check_email&sid_token={sid}&seq={seq}", timeout=10)
    if r.status_code == 200:
        return r.json()
    return None

def gm_fetch_email(sid, mail_id):
    """Fetch full email by ID"""
    r = requests.get(f"{GUERRILLA_API}?f=fetch_email&sid_token={sid}&email_id={mail_id}", timeout=10)
    if r.status_code == 200:
        return r.json()
    return None

def gm_delete_email(sid, mail_id):
    """Delete an email"""
    requests.get(f"{GUERRILLA_API}?f=del_email&sid_token={sid}&email_ids[]={mail_id}", timeout=10)

def gm_forget_email(email_addr):
    """Forget/abandon an email address"""
    requests.get(f"{GUERRILLA_API}?f=forget_me&email_addr={email_addr}", timeout=10)

# ===== Keyboards =====
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📧 إنشاء بريد وهمي", callback_data="gen")],
        [InlineKeyboardButton("📥 البريد الوارد", callback_data="inbox")],
        [InlineKeyboardButton("🔄 بريد جديد (حذف القديم)", callback_data="new_email")],
        [InlineKeyboardButton("ℹ️ معلومات", callback_data="info")],
        [InlineKeyboardButton("🛡️ BLACK WEB", callback_data="brand")]
    ])

def email_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📥 تحديث الوارد", callback_data="inbox"),
         InlineKeyboardButton("🔄 جديد", callback_data="gen")],
        [InlineKeyboardButton("🗑️ حذف البريد", callback_data="delete_email")],
        [InlineKeyboardButton("🔙 القائمة", callback_data="menu")]
    ])

# ===== Handlers =====
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    uname = update.effective_user.first_name or "مستخدم"
    approved = load_json("approved.json", [])
    blocked = load_json("blocked.json", [])
    
    if uid in blocked:
        await update.message.reply_text("🚫 تم حظرك.")
        return
    
    if uid == str(ADMIN_ID) and uid not in approved:
        approved.append(uid)
        save_json("approved.json", approved)
    
    if uid not in approved:
        pending = load_json("pending.json", {})
        if uid not in pending:
            pending[uid] = {"name": uname, "time": time.time()}
            save_json("pending.json", pending)
            try:
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ موافقة", callback_data=f"ap_{uid}"),
                     InlineKeyboardButton("❌ رفض", callback_data=f"rj_{uid}")]
                ])
                await ctx.bot.send_message(ADMIN_ID,
                    f"🛡️ *طلب جديد*\n👤 {uname}\n🆔 `{uid}`\n\nاختر:",
                    parse_mode="Markdown", reply_markup=kb)
            except: pass
        await update.message.reply_text("⏳ طلبك قيد المراجعة.\n🛡️ BLACK WEB © 2026")
        return
    
    await update.message.reply_text(
        "🛡️ *BLACK WEB* 🛡️\n\n"
        "بوت البريد المؤقت - إيميلات غير محدودة!\n"
        "مدعوم من GuerrillaMail\n\n"
        "⚠️ للاستخدام الشخصي فقط\n\n"
        "🛡️ BLACK WEB © 2026",
        parse_mode="Markdown", reply_markup=main_menu())

async def btn(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = str(q.from_user.id)
    d = q.data
    
    if d == "gen":
        gm = gm_new_email()
        if not gm:
            await q.edit_message_text("❌ فشل إنشاء البريد. حاول مرة أخرى.", reply_markup=main_menu())
            return
        inbox = load_json("inbox.json", {})
        inbox[uid] = gm
        inbox[uid]["msgs"] = []
        inbox[uid]["seq"] = 0
        save_json("inbox.json", inbox)
        await q.edit_message_text(
            f"✅ *تم إنشاء بريدك!*\n\n"
            f"📧 `{gm['email']}`\n\n"
            f"انسخ الإيميل واستخدمه في أي موقع.\n"
            f"ثم اضغط 📥 تحديث الوارد لاستقبال الرسائل.",
            parse_mode="Markdown", reply_markup=email_menu())
    
    elif d == "new_email":
        inbox = load_json("inbox.json", {})
        if uid in inbox:
            gm_forget_email(inbox[uid].get("email", ""))
            del inbox[uid]
            save_json("inbox.json", inbox)
        await q.edit_message_text("🔄 اضغط إنشاء بريد للحصول على عنوان جديد.", reply_markup=main_menu())
    
    elif d == "inbox":
        inbox = load_json("inbox.json", {})
        if uid not in inbox or not inbox[uid].get("email"):
            await q.edit_message_text("❌ لا يوجد بريد نشط. أنشئ واحداً أولاً.", reply_markup=main_menu())
            return
        
        result = gm_check_inbox(inbox[uid]["sid"], inbox[uid].get("seq", 0))
        if not result:
            await q.edit_message_text(
                f"📧 `{inbox[uid]['email']}`\n\n📭 الصندوق فارغ.",
                parse_mode="Markdown", reply_markup=email_menu())
            return
        
        new_msgs = result.get("list", [])
        if new_msgs:
            inbox[uid]["msgs"].extend(new_msgs)
            inbox[uid]["seq"] = result.get("seq", inbox[uid].get("seq", 0))
            save_json("inbox.json", inbox)
        
        all_msgs = inbox[uid].get("msgs", [])
        if not all_msgs:
            await q.edit_message_text(
                f"📧 `{inbox[uid]['email']}`\n\n📭 لا توجد رسائل.",
                parse_mode="Markdown", reply_markup=email_menu())
            return
        
        txt = f"📧 `{inbox[uid]['email']}`\n📥 *الوارد ({len(all_msgs)})*:\n\n"
        for i, m in enumerate(all_msgs[-10:], 1):
            subj = m.get("mail_subject", "بدون عنوان")[:30]
            fro = m.get("mail_from", "?")[:25]
            mail_id = m.get("mail_id", "")
            txt += f"{i}. *{subj}*\n   👤 {fro}\n   🔍 /read_{i}\n\n"
        
        # Save msg mapping for /read command
        msg_map = load_json("msg_map.json", {})
        msg_map[uid] = {str(i): m.get("mail_id") for i, m in enumerate(all_msgs[-10:], 1)}
        save_json("msg_map.json", msg_map)
        
        await q.edit_message_text(txt, parse_mode="Markdown", reply_markup=email_menu())
    
    elif d == "delete_email":
        inbox = load_json("inbox.json", {})
        if uid in inbox:
            gm_forget_email(inbox[uid].get("email", ""))
            del inbox[uid]
            save_json("inbox.json", inbox)
        await q.edit_message_text("🗑️ تم حذف البريد.", reply_markup=main_menu())
    
    elif d == "info":
        inbox = load_json("inbox.json", {})
        e = inbox.get(uid, {}).get("email", "لا يوجد")
        msgs = len(inbox.get(uid, {}).get("msgs", []))
        approved = load_json("approved.json", [])
        await q.edit_message_text(
            f"👤 *المعلومات*\n\n"
            f"📧 `{e}`\n"
            f"📥 رسائل: {msgs}\n"
            f"👥 مستخدمين: {len(approved)}\n"
            f"🔌 GuerrillaMail API\n\n"
            f"🛡️ BLACK WEB © 2026",
            parse_mode="Markdown", reply_markup=main_menu())
    
    elif d == "brand":
        await q.edit_message_text(
            "🛡️ *BLACK WEB* 🛡️\n\n"
            "بوت بريد مؤقت - إيميلات غير محدودة\n"
            "مدعوم من GuerrillaMail\n\n"
            "👨‍💻 يوسف\n"
            "🛡️ BLACK WEB © 2026",
            parse_mode="Markdown", reply_markup=main_menu())
    
    elif d == "menu":
        await q.edit_message_text("🛡️ *BLACK WEB*\nاختر من القائمة:", parse_mode="Markdown", reply_markup=main_menu())
    
    elif d.startswith("ap_"):
        if uid != str(ADMIN_ID):
            await q.answer("⛔ غير مصرح", show_alert=True)
            return
        target = d[3:]
        approved = load_json("approved.json", [])
        pending = load_json("pending.json", {})
        if target not in approved:
            approved.append(target)
            save_json("approved.json", approved)
        if target in pending: del pending[target]; save_json("pending.json", pending)
        try: await ctx.bot.send_message(int(target), "✅ تم قبولك! /start")
        except: pass
        await q.edit_message_text(f"✅ تمت الموافقة على `{target}`", parse_mode="Markdown")
    
    elif d.startswith("rj_"):
        if uid != str(ADMIN_ID):
            await q.answer("⛔ غير مصرح", show_alert=True)
            return
        target = d[3:]
        pending = load_json("pending.json", {})
        blocked = load_json("blocked.json", [])
        if target in pending: del pending[target]; save_json("pending.json", pending)
        if target not in blocked: blocked.append(target); save_json("blocked.json", blocked)
        try: await ctx.bot.send_message(int(target), "❌ تم رفضك.")
        except: pass
        await q.edit_message_text(f"❌ رفض `{target}`", parse_mode="Markdown")

async def cmd_approve(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try: uid = str(ctx.args[0])
    except: await update.message.reply_text("/approve <id>"); return
    approved = load_json("approved.json", [])
    pending = load_json("pending.json", {})
    if uid not in approved: approved.append(uid); save_json("approved.json", approved)
    if uid in pending: del pending[uid]; save_json("pending.json", pending)
    try: await ctx.bot.send_message(int(uid), "✅ تم قبولك! /start")
    except: pass
    await update.message.reply_text(f"✅ {uid}")

async def cmd_reject(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try: uid = str(ctx.args[0])
    except: await update.message.reply_text("/reject <id>"); return
    pending = load_json("pending.json", {})
    blocked = load_json("blocked.json", [])
    if uid in pending: del pending[uid]; save_json("pending.json", pending)
    if uid not in blocked: blocked.append(uid); save_json("blocked.json", blocked)
    await update.message.reply_text(f"❌ {uid}")

async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    approved = load_json("approved.json", [])
    pending = load_json("pending.json", {})
    blocked = load_json("blocked.json", [])
    await update.message.reply_text(
        f"📊 *BLACK WEB*\n\n"
        f"👥 مستخدمين: {len(approved)}\n"
        f"⏳ انتظار: {len(pending)}\n"
        f"🚫 محظورين: {len(blocked)}\n\n"
        f"🛡️ BLACK WEB © 2026",
        parse_mode="Markdown")

async def cmd_read(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    try: idx = int(ctx.args[0])
    except: await update.message.reply_text("استخدم: /read <رقم>"); return
    
    msg_map = load_json("msg_map.json", {})
    inbox = load_json("inbox.json", {})
    mail_id = msg_map.get(uid, {}).get(str(idx))
    
    if not mail_id or uid not in inbox:
        await update.message.reply_text("❌ غير موجود. استخدم البريد الوارد أولاً.")
        return
    
    sid = inbox[uid]["sid"]
    full = gm_fetch_email(sid, mail_id)
    if not full:
        await update.message.reply_text("❌ تعذر جلب الرسالة.")
        return
    
    body = full.get("mail_body", "بدون محتوى")[:1000]
    # Strip HTML
    body = re.sub(r'<[^>]+>', '', body)[:800]
    await update.message.reply_text(
        f"📧 *{full.get('mail_subject','?')}*\n"
        f"👤 {full.get('mail_from','?')}\n"
        f"📅 {full.get('mail_date','?')}\n\n"
        f"{body[:700]}",
        parse_mode="Markdown")

async def cmd_broadcast(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    msg = " ".join(ctx.args)
    if not msg: await update.message.reply_text("/broadcast <نص>"); return
    approved = load_json("approved.json", [])
    sent = 0
    for u in approved:
        try: await ctx.bot.send_message(int(u), f"📢 {msg}", parse_mode="Markdown"); sent += 1
        except: pass
    await update.message.reply_text(f"✅ أرسلت لـ {sent}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("approve", cmd_approve))
    app.add_handler(CommandHandler("reject", cmd_reject))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("read", cmd_read))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    app.add_handler(CallbackQueryHandler(btn))
    logger.info("🛡️ BLACK WEB Bot v4.0 — GuerrillaMail")
    app.run_polling()

if __name__ == "__main__":
    main()
