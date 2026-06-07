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
    
    # Core Espresso Variations
    'espresso': "☕ *Espresso (Standart)*\n\n*Ölçüler:* 18-20g kahve, 36-40g çıktı (1:2 oran).\n*Süre:* 25-30 sn.\n*Adımlar:*\n1. Portafiltreyi temizle ve kurula.\n2. Kahveyi öğüt ve düzle.\n3. Eşit kuvvetle tamp yap.\n4. Grup başlığını akıt, portafiltreyi tak ve hemen başlat.",
    'ristretto': "☕ *Ristretto*\n\n*Ölçüler:* 18-20g kahve, 20-25g çıktı (1:1.2 oran).\n*Süre:* 15-20 sn.\n*Not:* Daha gövdeli ve tatlı, daha az asidiktir.",
    'lungo': "☕ *Lungo*\n\n*Ölçüler:* 18-20g kahve, 60-80g çıktı (1:3 veya 1:4 oran).\n*Süre:* 35-45 sn.\n*Not:* Daha acı ve yüksek kafeinlidir.",
    
    # Milk Based
    'macchiato': "☕ *Espresso Macchiato*\n\n*Ölçüler:* Double espresso + 1-2 kaşık yoğun süt köpüğü.\n*Adım:* Espressoyu hazırla, üzerine sadece sütün en yoğun köpüğünden bir dokunuş ekle.",
    'cortado': "🥃 *Cortado*\n\n*Ölçüler:* Double espresso + 60ml süt (1:1 oran).\n*Süre:* 25-30 sn.\n*Süt:* 55-60°C, az havalandırılmış (ipeksi).",
    'flat_white': "🥛 *Flat White*\n\n*Ölçüler:* Double espresso + 120-150ml süt.\n*Süt:* 60-65°C, çok ince mikro-köpük (0.5cm).\n*Adım:* Espresso üzerine sütü ince bir akışla, krema ile bütünleşecek şekilde dök.",
    'cappuccino': "☁️ *Cappuccino*\n\n*Ölçüler:* Double espresso + 150ml süt.\n*Süt:* 60-65°C, yoğun ve kalın köpük (1.5-2cm).\n*Adım:* Sütü merkeze dökerek köpüğün üstte kalmasını sağla.",
    'latte': "🥛 *Caffè Latte*\n\n*Ölçüler:* Double espresso + 200-250ml süt.\n*Süt:* 60-65°C, ince mikro-köpük (1cm).\n*Adım:* Geniş bir bardağa sütü dökerek krema tabakası oluştur.",
    'latte_macchiato': "🥛 *Latte Macchiato*\n\n*Ölçüler:* 200ml süt + Double espresso.\n*Adım:*\n1. Sütü köpürtüp bardağa al.\n2. 30 sn bekle (süt ve köpük ayrılsın).\n3. Espressoyu yavaşça sütün ortasından dök (katmanlı görünüm).",
    
    # Specialty & Dessert
    'cafe_mocha': "🍫 *Caffè Mocha*\n\n*Ölçüler:* Double espresso + 20-30ml çikolata sosu + 200ml süt.\n*Adım:*\n1. Çikolatayı espresso ile karıştır.\n2. Üzerine köpürtülmüş sütü ekle.\n3. İsteğe bağlı çırpılmış krema ekle.",
    'espresso_romano': "🍋 *Espresso Romano*\n\n*Ölçüler:* Single/Double espresso + Limon dilimi/kabuğu.\n*Adım:* Espressoyu hazırla, bardağın kenarına limon sür ve kabuğu içine at.",
    'affogato': "🍨 *Affogato*\n\n*Ölçüler:* 1 top vanilyalı dondurma + Double espresso.\n*Adım:* Dondurmayı kaseye al, üzerine sıcak espressoyu hemen servis etmeden dök.",
    'cafe_breve': "🥛 *Caffè Breve*\n\n*Ölçüler:* Double espresso + Half-and-half (yarı süt yarı krema).\n*Adım:* Süt ve krema karışımını latte gibi köpürtüp espresso üzerine ekle.",
    'vienna_coffee': "🍦 *Vienna Coffee*\n\n*Ölçüler:* Double espresso + Sıcak su (opsiyonel) + Çırpılmış krema.\n*Adım:* Uzun bir kahve hazırlayıp üzerine bolca soğuk çırpılmış krema ekle.",
    
    # High Caffeine
    'americano': "🥤 *Americano*\n\n*Ölçüler:* Double espresso + 150ml sıcak su (90°C).\n*Adım:* Önce suyu bardağa al, üzerine espressoyu ekle (kremayı korumak için).",
    'red_eye': "👁️ *Red Eye*\n\n*Ölçüler:* 250ml Filtre kahve + Single espresso.\n*Adım:* Demlenmiş filtre kahvenin içine bir shot espresso ekle.",
    'black_eye': "👁️👁️ *Black Eye*\n\n*Ölçüler:* 250ml Filtre kahve + Double espresso.\n*Adım:* Demlenmiş filtre kahvenin içine double shot espresso ekle.",
    'dead_eye': "💀 *Dead Eye*\n\n*Ölçüler:* 250ml Filtre kahve + Triple espresso.\n*Adım:* Demlenmiş filtre kahvenin içine üç shot espresso ekle.",
    
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
        [InlineKeyboardButton("Espresso", callback_data='espresso'), InlineKeyboardButton("Ristretto", callback_data='ristretto')],
        [InlineKeyboardButton("Lungo", callback_data='lungo'), InlineKeyboardButton("Americano", callback_data='americano')],
        [InlineKeyboardButton("Macchiato", callback_data='macchiato'), InlineKeyboardButton("Cortado", callback_data='cortado')],
        [InlineKeyboardButton("Flat White", callback_data='flat_white'), InlineKeyboardButton("Latte", callback_data='latte')],
        [InlineKeyboardButton("Cappuccino", callback_data='cappuccino'), InlineKeyboardButton("Latte Macchiato", callback_data='latte_macchiato')],
        [InlineKeyboardButton("Mocha 🍫", callback_data='cafe_mocha'), InlineKeyboardButton("Affogato 🍨", callback_data='affogato')],
        [InlineKeyboardButton("Breve / Vienna", callback_data='cafe_breve'), InlineKeyboardButton("Romano 🍋", callback_data='espresso_romano')],
        [InlineKeyboardButton("Red/Black/Dead Eye 👁️", callback_data='red_eye')],
        [InlineKeyboardButton("Iced Menu 🧊", callback_data='iced_latte')],
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
    elif query.data == 'red_eye':
         # Sub-menu for X-Eye drinks
         keyboard = [
             [InlineKeyboardButton("Red Eye (1 shot)", callback_data='red_eye_recipe')],
             [InlineKeyboardButton("Black Eye (2 shots)", callback_data='black_eye')],
             [InlineKeyboardButton("Dead Eye (3 shots)", callback_data='dead_eye')],
             [InlineKeyboardButton("⬅️ Espresso Menüsü", callback_data='espresso_menu')]
         ]
         await query.edit_message_text("Filtre kahve + Espresso sertliği seçin:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif query.data == 'red_eye_recipe':
        text = RECIPES['red_eye']
        keyboard = [[InlineKeyboardButton("⬅️ Geri", callback_data='red_eye')], [InlineKeyboardButton("⬅️ Ana Menü", callback_data='menu')]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    elif query.data == 'cafe_breve':
         keyboard = [
             [InlineKeyboardButton("Caffè Breve", callback_data='cafe_breve_recipe')],
             [InlineKeyboardButton("Vienna Coffee", callback_data='vienna_coffee')],
             [InlineKeyboardButton("⬅️ Espresso Menüsü", callback_data='espresso_menu')]
         ]
         await query.edit_message_text("Kremalı tarifler seçin:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif query.data == 'cafe_breve_recipe':
        text = RECIPES['cafe_breve']
        keyboard = [[InlineKeyboardButton("⬅️ Geri", callback_data='cafe_breve')], [InlineKeyboardButton("⬅️ Ana Menü", callback_data='menu')]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    else:
        text = RECIPES.get(query.data, "Tarif bulunamadı.")
        keyboard = [[InlineKeyboardButton("⬅️ Menüye Dön", callback_data='menu')]]
        if query.data in RECIPES and query.data not in ['v60', 'chemex', 'aeropress', 'espresso_menu']:
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
