import logging
import json
import asyncio
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Recipes
RECIPES = {
    'v60': "☕ *Hario V60 Tarifi*\n\n15g kahve, 250ml su (92-94°C). 30g blooming (30sn), 1:15'e kadar 150ml, kalan suyu dairesel dök.",
    'chemex': "🧪 *Chemex Tarifi*\n\n30g kahve, 500ml su (94°C). 60g blooming (45sn), yavaşça merkeze dökerek 500ml'ye tamamla.",
    'aeropress': "🚀 *AeroPress Tarifi*\n\n18g kahve, 200ml su (85-88°C). Ters yöntem: Suyu ekle, 30sn bekle, 1:30'da presle.",
    'espresso_menu': "☕ *Espresso Bazlı Kahveler*\n\nHangi içeceği hazırlıyoruz?",
    'espresso': "☕ *Espresso*\n\n*   *Kahve:* 18-20g (İnce öğütülmüş)\n*   *Oran:* 1:2 (36-40g çıktı)\n*   *Süre:* 25-30 saniye\n*   *Sıcaklık:* 92-94°C\n\n*Hazırlanışı:*\n1. Sepeti temizle ve kurula.\n2. Kahveyi tart ve homojen dağıt.\n3. Düzgünce tampla.\n4. Grup başlığını temizle (flush).\n5. Portafiltreyi tak ve hemen başlat.",
    'americano': "🥤 *Americano*\n\nDouble espresso + 150ml sıcak su.",
    'latte': "🥛 *Latte*\n\n*   *Baz:* Double Espresso (36-40g)\n*   *Süt:* 200-250ml taze süt\n*   *Köpük:* İnce, ipeksi mikro köpük (~1cm)\n*   *Sıcaklık:* 60-65°C\n\n*Hazırlanışı:*\n1. Espressoyu hazırla.\n2. Sütü 2-3 sn havalandırıp (pıtırtı sesi) girdap oluştur.\n3. Sütü dairesel hareketlerle espressoya ekle.\n4. Yüzeyde desen oluşturarak tamamla.",
    'cappuccino': "☁️ *Cappuccino*\n\n*   *Baz:* Double Espresso (36-40g)\n*   *Süt:* 150ml taze süt\n*   *Köpük:* Yoğun ve kremsi mikro köpük (1.5-2cm)\n*   *Sıcaklık:* 60-65°C\n\n*Hazırlanışı:*\n1. Espressoyu hazırla.\n2. Sütü 5-6 sn havalandırarak yoğun köpük oluştur.\n3. Sütü merkezden dökerek beyaz bir köpük katmanı oluştur.",
    'flat_white': "🥛 *Flat White*\n\n*   *Baz:* Double Espresso (36-40g)\n*   *Süt:* 120-150ml taze süt\n*   *Köpük:* Çok ince mikro köpük (~0.5cm)\n*   *Sıcaklık:* 60-65°C\n\n*Hazırlanışı:*\n1. Espressoyu hazırla.\n2. Sütü çok kısa süre havalandırıp ipeksi doku ver.\n3. Sütü yavaşça dökerek pürüzsüzce karıştır.",
    'cortado': "🥃 *Cortado*\n\n*   *Baz:* Double Espresso (36-40g)\n*   *Süt:* 40-60ml taze süt (1:1 oran)\n*   *Köpük:* Çok az mikro köpük\n*   *Sıcaklık:* 55-60°C\n\n*Hazırlanışı:*\n1. Espressoyu hazırla.\n2. Sütü hafifçe ısıt ve çok az havalandır.\n3. Espresso ile sütü eşit miktarda karıştır.",
    'iced_latte': "🧊 *Iced Latte*\n\nBuz + 180ml soğuk süt + Double espresso.",
    'iced_americano': "🧊 *Iced Americano*\n\nBuz + 150ml soğuk su + Double espresso."
}

def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("V60 ☕", callback_data='v60')],
        [InlineKeyboardButton("Chemex 🧪", callback_data='chemex')],
        [InlineKeyboardButton("AeroPress 🚀", callback_data='aeropress')],
        [InlineKeyboardButton("Espresso Bazlı ☕🥛", callback_data='espresso_menu')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_espresso_menu():
    keyboard = [
        [InlineKeyboardButton("Espresso", callback_data='espresso'), InlineKeyboardButton("Americano", callback_data='americano')],
        [InlineKeyboardButton("Latte", callback_data='latte'), InlineKeyboardButton("Cappuccino", callback_data='cappuccino')],
        [InlineKeyboardButton("Flat White", callback_data='flat_white'), InlineKeyboardButton("Cortado", callback_data='cortado')],
        [InlineKeyboardButton("Iced Latte 🧊", callback_data='iced_latte'), InlineKeyboardButton("Iced Americano 🧊", callback_data='iced_americano')],
        [InlineKeyboardButton("⬅️ Ana Menü", callback_data='menu')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update, context):
    await update.message.reply_text("👋 Selam! Ben Barista Koçu.\nBugün ne demlemek istersin?", reply_markup=get_main_menu())

async def handle_callback(update, context):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'menu':
        await query.edit_message_text("Hangi demleme yöntemini seçiyoruz?", reply_markup=get_main_menu())
    elif query.data == 'espresso_menu':
        await query.edit_message_text(RECIPES['espresso_menu'], reply_markup=get_espresso_menu())
    else:
        text = RECIPES.get(query.data, "Tarif bulunamadı.")
        keyboard = [[InlineKeyboardButton("⬅️ Menüye Dön", callback_data='menu')]]
        if query.data in ['espresso', 'americano', 'latte', 'cappuccino', 'flat_white', 'cortado', 'iced_latte', 'iced_americano']:
            keyboard = [[InlineKeyboardButton("⬅️ Espresso Menüsü", callback_data='espresso_menu')], [InlineKeyboardButton("⬅️ Ana Menü", callback_data='menu')]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def handle_text(update, context):
    text = update.message.text.lower()
    if any(word in text for word in ["menü", "geri", "dön", "ana"]):
        await update.message.reply_text("Ana Menü:", reply_markup=get_main_menu())

TOKEN = '8640816185:AAH3vQsZl9TtNF5lFmZQJxHdxlV0-LPCa2w'

# Setup telegram application
telegram_app = ApplicationBuilder().token(TOKEN).build()
telegram_app.add_handler(CommandHandler('start', start))
telegram_app.add_handler(CallbackQueryHandler(handle_callback))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    return "Barista Koçu Bot is running! Send POST to /api/webhook"

@app.route('/api/webhook', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET':
        return "Webhook endpoint is active."
    
    update_json = request.get_json()
    
    # Process update asynchronously
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        async with telegram_app:
            update = Update.de_json(update_json, telegram_app.bot)
            loop.run_until_complete(telegram_app.process_update(update))
    finally:
        loop.close()
    
    return "OK", 200

# Vercel's Python runtime entry point
def application(environ, start_response):
    return app(environ, start_response)
