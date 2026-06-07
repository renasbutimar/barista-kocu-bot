import logging
import json
import asyncio
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, PreCheckoutQueryHandler

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- RECIPES DATABASE ---
RECIPES = {
    'v60': "☕ *Hario V60 Tarifi*\n\n15g kahve, 250ml su (92-94°C). 30g blooming (30sn), 1:15'e kadar 150ml, kalan suyu dairesel dök.",
    'chemex': "🧪 *Chemex Tarifi*\n\n30g kahve, 500ml su (94°C). 60g blooming (45sn), yavaşça merkeze dökerek 500ml'ye tamamla.",
    'aeropress': "🚀 *AeroPress Tarifi*\n\n18g kahve, 200ml su (85-88°C). Ters yöntem: Suyu ekle, 30sn bekle, 1:30'da presle.",
    'espresso': "☕ *Espresso*\n18-20g kahve (İnce öğütüm)\n36-40g çıktı (1:2 oran)\n25-30 saniye süre\n1. Portafiltreyi kurula.\n2. Kahveyi tart ve düzle.\n3. Eşit kuvvetle tampla.\n4. Grupu durula ve hemen demle.",
    'ristretto': "☕ *Ristretto*\n18-20g kahve, 22-25g çıktı (1:1.2 oran). Daha yoğun ve tatlı.",
    'lungo': "☕ *Lungo*\n18-20g kahve, 60g+ çıktı (1:3 oran). Daha hafif ama daha acı.",
    'latte': "🥛 *Latte*\nDouble espresso + 200ml ipeksi süt köpüğü (60-65°C).",
    'cappuccino': "☁️ *Cappuccino*\nDouble espresso + 150ml yoğun süt köpüğü (1.5-2cm foam).",
    'flat_white': "🥛 *Flat White*\nDouble espresso + 120ml çok ince süt köpüğü (0.5cm foam).",
    'cortado': "🥃 *Cortado*\nDouble espresso + 60ml süt (1:1 oran). 55-60°C sıcaklık.",
    'mocha': "🍫 *Caffè Mocha*\nEspresso + Çikolata sosu + Buharlanmış süt + Opsiyonel krema.",
    'turkish': "☕ *Türk Kahvesi*\n7g kahve (Çok ince), 65ml su. Kısık ateşte köpürene kadar pişir.",
    'vietnamese': "🇻🇳 *Vietnam Kahvesi*\nPhin filtre, 20g kahve, 20g yoğunlaştırılmış süt. Damla damla demlenir.",
    'de_olla': "🇲🇽 *Café de Olla*\nToprak kapta kahve, tarçın ve piloncillo (esmer şeker) ile kaynatılır.",
    'irish': "🇮🇪 *Irish Coffee*\nSıcak filtre kahve + Irish Whiskey + Üzerine soğuk çırpılmış krema.",
    'cold_brew': "🧊 *Cold Brew*\n1:8 oranında kalın öğütülmüş kahve ve soğuk su. 12-18 saat demlenir."
}

# --- SIMPLE DATABASE (IN-MEMORY MOCK) ---
# NOTE: In serverless, this resets. For production, connect this to Supabase.
USER_DATA = {}

def get_user_state(user_id):
    if user_id not in USER_DATA:
        USER_DATA[user_id] = {'lookups': 0, 'premium': False}
    return USER_DATA[user_id]

# --- MENU HELPERS ---
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("Demleme Yöntemleri ☕", callback_data='brew_menu')],
        [InlineKeyboardButton("Dünya Kahveleri 🌍", callback_data='world_menu')],
        [InlineKeyboardButton("Espresso Bazlı 🥛", callback_data='espresso_menu')]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- TELEGRAM STARS PAYMENT ---
async def send_stars_invoice(update, context):
    chat_id = update.effective_chat.id
    title = "Sınırsız Tarif Paket"
    description = "Limitleri kaldırın ve tüm barista sırlarına sınırsızca erişin! ☕✨"
    payload = "premium_upgrade"
    currency = "XTR"  # Telegram Stars
    price = 50  # 50 Stars
    prices = [LabeledPrice("Sınırsız Erişim", price)]

    await context.bot.send_invoice(
        chat_id, title, description, payload, "", currency, prices
    )

async def precheckout_callback(update, context):
    query = update.pre_checkout_query
    if query.invoice_payload != 'premium_upgrade':
        await query.answer(ok=False, error_message="Bir şeyler ters gitti...")
    else:
        await query.answer(ok=True)

async def successful_payment_callback(update, context):
    user_id = update.effective_user.id
    state = get_user_state(user_id)
    state['premium'] = True
    await update.message.reply_text("🎉 Tebrikler! Artık gerçek bir baristasınız. Tüm tarifler sınırsızca emrinizde! ☕💪")

# --- HANDLERS ---
async def start(update, context):
    await update.message.reply_text(
        "👋 Merhaba! Ben Barista Koçu.\n\nSizin için en güzel kahve tariflerini hazırladım. Menüden seçebilir veya merak ettiğiniz bir kahveyi yazabilirsiniz!",
        reply_markup=get_main_menu()
    )

async def handle_request(update, context, recipe_id):
    user_id = update.effective_user.id
    state = get_user_state(user_id)
    
    if not state['premium'] and state['lookups'] >= 3:
        await update.effective_message.reply_text(
            "🛑 Limit doldu! 3 ücretsiz tarif hakkınızı kullandınız.\nDevam etmek için Telegram Stars ile sınırsız erişim alabilirsiniz: :)",
        )
        await send_stars_invoice(update, context)
        return

    text = RECIPES.get(recipe_id, "Tarif bulunamadı.")
    if not state['premium']:
        state['lookups'] += 1
        remaining = 3 - state['lookups']
        counter_text = f"\n\n*(Ücretsiz hakkınız: {remaining}/3)*"
    else:
        counter_text = "\n\n✨ Sınırsız Erişim Aktif"

    await update.effective_message.reply_text(text + counter_text, parse_mode='Markdown')

async def handle_callback(update, context):
    query = update.callback_query
    await query.answer()
    
    if query.data in RECIPES:
        await handle_request(update, context, query.data)
    elif query.data == 'espresso_menu':
        keyboard = [
            [InlineKeyboardButton("Espresso", callback_data='espresso'), InlineKeyboardButton("Latte", callback_data='latte')],
            [InlineKeyboardButton("Cortado", callback_data='cortado'), InlineKeyboardButton("Flat White", callback_data='flat_white')]
        ]
        await query.edit_message_text("Espresso'nun büyülü dünyası:", reply_markup=InlineKeyboardMarkup(keyboard))
    # ... more menus ...

TOKEN = '8640816185:AAH3vQsZl9TtNF5lFmZQJxHdxlV0-LPCa2w'
telegram_app = ApplicationBuilder().token(TOKEN).build()
telegram_app.add_handler(CommandHandler('start', start))
telegram_app.add_handler(CallbackQueryHandler(handle_callback))
telegram_app.add_handler(PreCheckoutQueryHandler(precheckout_callback))
telegram_app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))

app = Flask(__name__)

@app.route('/api/webhook', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET': return "OK"
    update_json = request.get_json()
    async def process():
        async with telegram_app:
            update = Update.de_json(update_json, telegram_app.bot)
            await telegram_app.process_update(update)
    asyncio.run(process())
    return "OK", 200

application = app
