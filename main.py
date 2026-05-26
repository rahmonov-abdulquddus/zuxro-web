import logging
import re
import pandas as pd
import io
import json
import requests
import base64
import os
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# --- LOGGING ---
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- SOZLAMALAR ---
TOKEN = "8727582359:AAGwul94F9VcteJFxZgqYuOiD2ukoHqNBlU"
ADMIN_ID = 5545483477
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
REPO_OWNER = "rahmonov-abdulquddus"
REPO_NAME = "zuxro-web"
WEB_APP_URL = ""

DATA_FILE = "local_database.json"
STATS_FILE = "search_stats.json"

# --- MA'LUMOTLARNI YUKLASH ---
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return pd.DataFrame(json.load(f))
        except Exception as e:
            logger.error(f"Lokal bazani o'qishda xato: {e}")
    return None

def load_stats():
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {"searches": {}, "total_searches": 0, "last_update": None}

def save_stats(stats):
    with open(STATS_FILE, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

cached_df = load_data()
search_stats = load_stats()

# --- MATN NORMALIZATSIYA ---
def normalize_text(text):
    if not text: return ""
    text = str(text).lower().strip()
    trans = {
        'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'yo','ж':'j','з':'z',
        'и':'i','й':'y','к':'k','л':'l','м':'m','н':'n','о':'o','п':'p','р':'r',
        'с':'s','т':'t','у':'u','ф':'f','х':'h','ц':'s','ч':'ch','ш':'sh','ъ':'',
        'э':'e','ю':'yu','я':'ya','қ':'q','ғ':'g','ҳ':'h','ў':'o'
    }
    for k, v in trans.items():
        text = text.replace(k, v)
    return re.sub(r'[^a-z0-9]', ' ', text)

# --- GITHUB-GA YUKLASH ---
async def upload_to_github(json_data: str) -> bool:
    try:
        url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/data.json"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }

        res = requests.get(url, headers=headers)
        sha = None
        if res.status_code == 200:
            sha = res.json().get('sha')
        elif res.status_code != 404:
            logger.error(f"GitHub xato: {res.status_code}")
            return False

        payload = {
            "message": f"💊 Baza yangilandi — {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            "content": base64.b64encode(json_data.encode('utf-8')).decode('utf-8'),
            "branch": "main"
        }
        if sha:
            payload["sha"] = sha

        put_res = requests.put(url, headers=headers, json=payload)
        if put_res.status_code in [200, 201]:
            logger.info("✅ GitHub-ga yuklandi!")
            return True
        else:
            logger.error(f"GitHub xato: {put_res.status_code} — {put_res.text}")
            return False
    except Exception as e:
        logger.error(f"GitHub funksiya xato: {e}")
        return False

# --- ASOSIY MENYU ---
def main_menu():
    return ReplyKeyboardMarkup([
        [KeyboardButton("💊 Katalog", web_app=WebAppInfo(url=WEB_APP_URL))],
        [KeyboardButton("🔍 Dori qidirish")],
        [KeyboardButton("📍 Manzil"), KeyboardButton("ℹ️ Yordam")]
    ], resize_keyboard=True)

# --- /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = user.first_name or "Do'stim"

    text = (
        f"👋 Xush kelibsiz, *{name}*!\n\n"
        f"🏥 *Zuxro Farm 2020* — Quva tumani\n"
        f"📍 G'alaba MFY A.Yassaviy 133\n"
        f"   Mo'ljal: Diamond klinikasi yonida\n"
        f"🕐 Ish vaqti: 08:00 – 20:00\n\n"
        f"💊 Dori qidirish yoki katalogni ko'rish uchun tugmalardan foydalaning:"
    )

    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_menu())

# --- /help ---
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "ℹ️ *Yordam*\n\n"
        "🔍 *Dori qidirish* — dori nomini yozing\n"
        "💊 *Katalog* — barcha dorilarni ko'ring\n"
        "📍 *Manzil* — dorixona joylashuvi\n\n"
        "💡 Qidirish uchun dori nomini to'g'ridan-to'g'ri yozing!\n"
        "Masalan: `paracetamol` yoki `amoksitsillin`"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# --- MANZIL ---
async def location_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📍 *Zuxro Farm 2020*\n\n"
        "🏠 Quva tumani, A.Yassaviy 133\n"
        "📞 +998 88 205 25 20\n"
        "🕐 Har kuni: 08:00 – 20:00\n\n"
        "🗺️ Saytdagi xaritadan ham topishingiz mumkin!"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🗺️ Google Xarita", url="https://maps.google.com/?q=Quva+tumani,+Fergana,+Uzbekistan")],
        [InlineKeyboardButton("📞 Qo'ng'iroq", callback_data="call:+998882052520")]
    ])
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)

# --- STATISTIKA BOTDAN OLIB TASHLANDI ---
# Statistika endi faqat sayt admin panelida mavjud

# --- CALLBACK QUERY HANDLER ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("call:"):
        phone_number = query.data.replace("call:", "")
        
        # Kontakt kartasi yaratish
        contact = {
            'phone_number': phone_number,
            'first_name': 'Zuxro Farm',
            'last_name': 'Dorixona',
            'vcard': f"""BEGIN:VCARD
VERSION:3.0
FN:Zuxro Farm Dorixona
TEL:{phone_number}
ADR:;;Quva tumani, A.Yassaviy 133;Quva;;Fergona;Uzbekistan
EMAIL:info@zuxrofarm.uz
ORG:Zuxro Farm 2020
END:VCARD"""
        }
        
        await query.message.reply_contact(
            phone_number=contact['phone_number'],
            first_name=contact['first_name'],
            last_name=contact['last_name'],
            vcard=contact['vcard']
        )

# --- XABAR HANDLER ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global cached_df, search_stats
    text = update.message.text

    # Tugmalar
    if text == "🔍 Dori qidirish":
        await update.message.reply_text(
            "🔍 *Qidiruv rejimi*\n\nDori nomini yozing:",
            parse_mode="Markdown"
        )
        context.user_data['searching'] = True
        return

    if text == "📊 Statistika":
        await statistics(update, context)
        return

    if text == "📍 Manzil":
        await location_info(update, context)
        return

    if text == "ℹ️ Yordam":
        await help_cmd(update, context)
        return

    # Qidiruv
    if cached_df is not None and not cached_df.empty and len(text) >= 2:
        search_terms = normalize_text(text).split()
        if not search_terms:
            return

        results = []
        for _, row in cached_df.iterrows():
            if row['Pachka'] > 0 or row['Dona'] > 0:
                # Ikkala tomondan qidirish: lotin va kirill
                product_name = str(row['Nomi']).lower()
                normalized_product = normalize_text(product_name)
                
                # Qidiruv so'zini ikki xil shaklda tekshirish
                found = False
                for term in search_terms:
                    if term in normalized_product or term in product_name:
                        found = True
                    else:
                        # Lotin harflarini kirillga o'tkazib tekshirish
                        latin_to_cyrillic = {
                            'a':'а','b':'б','v':'в','g':'г','d':'д','e':'е','yo':'ё','j':'ж','z':'з',
                            'i':'и','y':'й','k':'к','l':'л','m':'м','n':'н','o':'о','p':'п','r':'р',
                            's':'с','t':'т','u':'у','f':'ф','h':'х','c':'ц','ch':'ч','sh':'ш',
                            'e':'э','yu':'ю','ya':'я','q':'қ'
                        }
                        cyrillic_term = term
                        for latin, cyrillic in latin_to_cyrillic.items():
                            cyrillic_term = cyrillic_term.replace(latin, cyrillic)
                        
                        if cyrillic_term in product_name:
                            found = True
                
                if found:
                    results.append(row)

        # Statistika saqlash
        key = text.lower().strip()
        search_stats['searches'][key] = search_stats['searches'].get(key, 0) + 1
        search_stats['total_searches'] = search_stats.get('total_searches', 0) + 1
        search_stats['last_update'] = datetime.now().strftime('%d.%m.%Y %H:%M')
        save_stats(search_stats)

        if results:
            msg = f"✅ *Topildi: {len(results)} ta dori*\n\n"
            for r in results[:8]:
                narx = "{:,.0f}".format(float(r['Sotish_narxi'])).replace(',', ' ')
                status = "✅" if (r['Pachka'] > 0 or r['Dona'] > 0) else "❌"
                msg += (
                    f"{status} *{r['Nomi']}*\n"
                    f"  💰 `{narx}` so'm\n"
                    f"  📦 {int(r['Pachka'])} pachka · {int(r['Dona'])} dona\n"
                    f"  ⏳ {r['Srok']} | 🏭 {r['Zavod']}\n\n"
                )
            if len(results) > 8:
                msg += f"_...va yana {len(results) - 8} ta dori. To'liq ro'yxat uchun Katalogga o'ting._"

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("💊 Katalogni ochish", web_app=WebAppInfo(url=WEB_APP_URL))]
            ])
            await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=keyboard)
        else:
            await update.message.reply_text(
                f"😔 *'{text}'* topilmadi yoki omborda yo'q.\n\n"
                "💡 Boshqa nom bilan qidiring yoki katalogni oching.",
                parse_mode="Markdown"
            )
    elif cached_df is None:
        await update.message.reply_text(
            "⚠️ Baza hali yuklanmagan.\n\n"
            "🔧 Admin Excel fayl yuklashini kuting.",
            parse_mode="Markdown"
        )

# --- EXCEL YUKLASH (faqat admin) ---
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global cached_df, search_stats

    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Fayl yuklash faqat admin uchun!")
        return

    status = await update.message.reply_text("⏳ Excel qayta ishlanmoqda...")

    try:
        file = await update.message.document.get_file()
        f_bytes = await file.download_as_bytearray()

        df = pd.read_excel(io.BytesIO(f_bytes), header=1)

        # Ustunlar: 2:Nomi, 3:Pachka, 4:Dona, 6:Narxi, 9:Srok, 10:Zavod
        new_df = df.iloc[:, [2, 3, 4, 6, 9, 10]].copy()
        new_df.columns = ['Nomi', 'Pachka', 'Dona', 'Sotish_narxi', 'Srok', 'Zavod']
        new_df = new_df.dropna(subset=['Nomi'])
        new_df = new_df[new_df['Nomi'].astype(str).str.strip() != '']

        for col in ['Pachka', 'Dona', 'Sotish_narxi']:
            new_df[col] = pd.to_numeric(new_df[col], errors='coerce').fillna(0)

        new_df['Srok'] = new_df['Srok'].astype(str).str.strip()
        new_df['Zavod'] = new_df['Zavod'].astype(str).str.strip()

        cached_df = new_df.copy()

        # Lokal saqlash
        cached_df.to_json(DATA_FILE, orient='records', force_ascii=False)

        # GitHub-ga yuklash (faqat mavjudlarni)
        web_data = cached_df[
            (cached_df['Pachka'] > 0) | (cached_df['Dona'] > 0)
        ].to_dict(orient='records')

        github_ok = await upload_to_github(json.dumps(web_data, ensure_ascii=False, indent=2))

        # Statistika yangilash
        search_stats['last_update'] = datetime.now().strftime('%d.%m.%Y %H:%M')
        save_stats(search_stats)

        total = len(cached_df)
        available = len(cached_df[(cached_df['Pachka'] > 0) | (cached_df['Dona'] > 0)])
        factories = cached_df['Zavod'].nunique()

        msg = (
            f"✅ *Bot bazasi yangilandi!*\n\n"
            f"💊 Jami: *{total}* ta dori\n"
            f"✅ Mavjud: *{available}* ta\n"
            f"🏭 Ishlab chiqaruvchi: *{factories}* ta\n\n"
        )

        if github_ok:
            msg += "🌐 *Sayt ham yangilandi!* ✅\n"
            msg += f"🔗 [Saytni ochish]({WEB_APP_URL})"
        else:
            msg += "⚠️ Sayt yangilanmadi. GitHub sozlamalarini tekshiring."

        await status.edit_text(msg, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Excel xato: {e}")
        await status.edit_text(
            f"❌ *Xatolik yuz berdi!*\n\n"
            f"`{str(e)}`\n\n"
            f"Excel faylning formatini tekshiring.",
            parse_mode="Markdown"
        )
# --- WEB APP'DAN KELGAN CHEKNI TUTIB OLISH ---
async def web_app_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Web App'dan yuborilgan buyurtma ma'lumotlarini qabul qilish"""
    # Web App'dan kelgan tekst
    order_text = update.effective_message.web_app_data.data
    
    # 1. Mijozga tasdiqlash xabari
    await update.message.reply_text(
        f"✅ Buyurtmangiz qabul qilindi!\n\n{order_text}",
        parse_mode="Markdown"
    )
    
    # 2. Adminga (Senga) bildirishnoma yuborish
    await context.bot.send_message(
        chat_id=ADMIN_ID, 
        text=f"🔔 **YANGI BUYURTMA KELDI!**\n\nKimdan: @{update.effective_user.username}\n\n{order_text}",
        parse_mode="Markdown"
    )

# --- ASOSIY MAIN QISMI ---
def main():
    app = Application.builder().token(TOKEN).build()

    # Buyruqlar
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    # stats buyrug'i olib tashlandi
    
    # Ma'lumotlarni qabul qilish (Web App Data) - SHU QATORNI QO'SHTIK!
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data_handler))
    
    # Callback query handler
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # Fayllar va tekstlar
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("🤖 Zuxro Farm boti ishga tushdi!")
    app.run_polling()

if __name__ == '__main__':
    main()