import logging
import json
import asyncio
import re
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Recipes Database
RECIPES = {
    'v60': "☕ *Hario V60 Tarifi*\n\n15g kahve, 250ml su (92-94°C). 30g blooming (30sn), 1:15'e kadar 150ml, kalan suyu dairesel dök.",
    'chemex': "🧪 *Chemex Tarifi*\n\n30g kahve, 500ml su (94°C). 60g blooming (45sn), yavaşça merkeze dökerek 500ml'ye tamamla.",
    'aeropress': "🚀 *AeroPress Tarifi*\n\n18g kahve, 200ml su (85-88°C). Ters yöntem: Suyu ekle, 30sn bekle, 1:30'da presle.",
    'espresso_menu': "☕ *Espresso Bazlı Kahveler*\n\nHangi içeceği hazırlıyoruz?",
    'espresso': "☕ *Espresso*\n18-20g kahve (İnce öğütüm)\n36-40g çıktı (1:2 oran)\n25-30 saniye süre\n1. Portafiltreyi kurula.\n2. Kahveyi tart ve düzle.\n3. Eşit kuvvetle tampla.\n4. Grupu durula ve hemen demle.",
    'ristretto': "☕ *Ristretto*\n18-20g kahve\n22-25g çıktı (1:1.2 oran)\n15-20 saniye süre\nDaha yoğun ve tatlı bir kısa çekim.",
    'lungo': "☕ *Lungo*\n18-20g kahve\n60g+ çıktı (1:3 oran)\n35-40 saniye süre\nDaha hafif ama daha acı bir uzun çekim.",
    'macchiato': "🥛 *Espresso Macchiato*\nSingle/Double Espresso + Bir kaşık süt köpüğü.",
    'latte_macchiato': "🥛 *Latte Macchiato*\n250ml sıcak süt üzerine yavaşça dökülen espresso (Katmanlı).",
    'americano': "🥤 *Americano*\nDouble espresso + 150ml sıcak su.",
    'latte': "🥛 *Latte*\nDouble espresso + 200ml ipeksi süt köpüğü (60-65°C).",
    'cappuccino': "☁️ *Cappuccino*\nDouble espresso + 150ml yoğun süt köpüğü (1.5-2cm foam).",
    'flat_white': "🥛 *Flat White*\nDouble espresso + 120ml çok ince süt köpüğü (0.5cm foam).",
    'cortado': "🥃 *Cortado*\nDouble espresso + 60ml süt (1:1 oran). 55-60°C sıcaklık.",
    'mocha': "🍫 *Caffè Mocha*\nEspresso + Çikolata sosu + Buharlanmış süt + Opsiyonel krema.",
    'romano': "🍋 *Espresso Romano*\nEspresso + Bir dilim limon kabuğu.",
    'affogato': "🍨 *Affogato*\nBir top vanilyalı dondurma + Üzerine dökülmüş Double Espresso.",
    'breve': "🥛 *Caffè Breve*\nEspresso + Buharlanmış yarı süt yarı krema karışımı.",
    'vienna': "🍦 *Vienna Coffee*\nDouble Espresso + Üzerine soğuk çırpılmış krema.",
    'red_eye': "👁️ *Red Eye*\nFiltre kahve + 1 shot Espresso.",
    'black_eye': "👁️👁️ *Black Eye*\nFiltre kahve + 2 shot Espresso.",
    'dead_eye': "💀 *Dead Eye*\nFiltre kahve + 3 shot Espresso.",
    'iced_latte': "🧊 *Iced Latte*\nBuz + 180ml soğuk süt + Double espresso.",
    'iced_americano': "🧊 *Iced Americano*\nBuz + 150ml soğuk su + Double espresso."
}

# Mapping keywords to recipe IDs
KEYWORD_MAP = {
    'v60': 'v60', 'hario': 'v60',
    'chemex': 'chemex',
    'aeropress': 'aeropress',
    'espresso': 'espresso',
    'ristretto': 'ristretto',
    'lungo': 'lungo',
    'macchiato': 'macchiato',
    'latte macchiato': 'latte_macchiato',
    'americano': 'americano',
    'latte': 'latte',
    'cappuccino': 'cappuccino',
    'flat white': 'flat_white',
    'cortado': 'cortado',
    'mocha': 'mocha', 'moka': 'mocha',
    'romano': 'romano',
    'affogato': 'affogato',
    'breve': 'breve',
    'vienna': 'vienna',
    'red eye': 'red_eye',
    'black eye': 'black_eye',
    'dead_eye': 'dead_eye',
    'buzlu latte': 'iced_latte', 'iced latte': 'iced_latte',
    'buzlu americano': 'iced_americano', 'iced americano': 'iced_americano'
}

def find_best_recipe(text):
    text = text.lower()
    for keyword, recipe_id in KEYWORD_MAP.items():
        if keyword in text:
            return recipe_id
    if any(word in text for word in ['sert', 'güçlü', 'uyandır', 'kafein']):
        if 'ölü' in text or 'çok' in text: return 'dead_eye'
        return 'ristretto'
    if any(word in text for word in ['sütlü', 'yumuşak', 'hafif']):
        return 'latte'
    if any(word in text for word in ['soğuk', 'buzlu', 'ferah']):
        return 'iced_latte'
    return None

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
        [InlineKeyboardButton("Latte", callback_data='latte'), InlineKeyboardButton("Cappuccino", callback_data='cappuccino')],
        [InlineKeyboardButton("Flat White", callback_data='flat_white'), InlineKeyboardButton("Cortado", callback_data='cortado')],
        [InlineKeyboardButton("⬅️ Ana Menü", callback_data='menu')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update, context):
    await update.message.reply_text("👋 Selam! Ben Barista Koçu.\nBana bir kahve adı yazabilir veya menüyü kullanabilirsin.", reply_markup=get_main_menu())

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
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def handle_text(update, context):
    user_text = update.message.text
    recipe_id = find_best_recipe(user_text)
    if recipe_id:
        text = RECIPES[recipe_id]
        await update.message.reply_text(text=f"İstediğin tarifi buldum:\n\n{text}", parse_mode='Markdown')
    else:
        await update.message.reply_text("Bunu anlayamadım. Menüden seçebilirsin:", reply_markup=get_main_menu())

TOKEN = '8640816185:AAH3vQsZl9TtNF5lFmZQJxHdxlV0-LPCa2w'
telegram_app = ApplicationBuilder().token(TOKEN).build()
telegram_app.add_handler(CommandHandler('start', start))
telegram_app.add_handler(CallbackQueryHandler(handle_callback))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

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
if __name__ == '__main__':
    app.run()
