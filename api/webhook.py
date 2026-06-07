import logging
import json
import asyncio
import re
import difflib
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Sarcastic Barista Recipes Database
RECIPES = {
    'v60': "☕ *Hario V60 (Filtre meraklılarına)*\n\n15g kahve, 250ml su. Sabırla dök, dairesel hareketlerle... Vaktin çok galiba?",
    'chemex': "🧪 *Chemex (Laboratuvar faresi misin?)*\n\n30g kahve, 500ml su. O kalın filtreyi ıslatmayı unutma, kağıt tadı içme sonra.",
    'aeropress': "🚀 *AeroPress (Basınç tutkusu)*\n\n18g kahve, 200ml su. Ters yöntem yap da bari bir şeye benzesin. 1:30'da presle, koluna kuvvet.",
    'espresso_menu': "☕ *Espresso Bazlılar (Süt banyosu sevenler)*\n\nHangi 'kahvemsi' içecekle vaktimi çalacaksın?",
    'espresso': "☕ *Gerçek Kahve (Espresso)*\n\nBak evlat, kahve budur. Sütle, şekerle kirletme şunu.\n18-20g kahve, 36-40g çıktı. 25-30 saniyede bitir, tadını al.",
    'ristretto': "☕ *Ristretto (Kısa ve öz)*\n\nTatlı ve yoğun. Kahvenin özü bu. 1:1.2 oran, 15 saniyede çek bitir.",
    'lungo': "☕ *Lungo (Acı sevenlere)*\n\nKahveyi sömürmek istiyorsun herhalde. 1:3 oran, 40 saniye. Biraz acı olur ama senin tercihin...",
    'macchiato': "🥛 *Macchiato*\n\nEspressoyu bir kaşık sütle 'lekeledin'. Korktun mu acılığından?",
    'latte_macchiato': "🥛 *Latte Macchiato*\n\nBolca süt, üzerine biraz espresso. Katman katman süt içiyorsun resmen.",
    'americano': "🥤 *Americano (Seyreltilmiş mutluluk)*\n\nEspressoyu suyla boğmak... II. Dünya Savaşı'ndan kalma bir alışkanlık işte.",
    'latte': "🥛 *Latte (Yani Sütlü Su)*\n\n200ml sütü bastın, kahvenin canını okudun. İpeksi köpükmüş... Peh.",
    'cappuccino': "☁️ *Cappuccino*\n\nO yoğun köpüğü bıyığına bulaştırmak için mi istiyorsun bunu? 1.5-2cm köpük yap bari.",
    'flat_white': "🥛 *Flat White*\n\nLatte'den farkı ne sanıyorsun? Sadece daha az süt. Havalı görünmek için mi seçtin bunu?",
    'cortado': "🥃 *Cortado*\n\nNe tam kahve, ne tam süt. Kararsızların içeceği. 1:1 oran.",
    'mocha': "🍫 *Caffè Mocha*\n\nKahve mi içiyorsun sıcak çikolata mı belli değil. Şeker komasına girmesen bari.",
    'romano': "🍋 *Espresso Romano*\n\nKahveye limon kabuğu mu? İlginç bir damak zevki, ne diyeyim...",
    'affogato': "🍨 *Affogato*\n\nTatlıcıya gitsene sen? Kahveyi dondurmaya sos yaptın resmen.",
    'breve': "🥛 *Caffè Breve*\n\nKrema ve süt... Kalp damarlarına selam söyle.",
    'vienna': "🍦 *Vienna Coffee*\n\nÜzerine bir dağ kadar krema. Kahveyi görebiliyor musun ordan?",
    'red_eye': "👁️ *Red Eye*\n\nUyumak mı istemiyorsun yoksa kalbinle derdin mi var? Filtre kahve + 1 shot espresso.",
    'black_eye': "👁️👁️ *Black Eye*\n\n2 shot espresso... Bugün yerinde duramayacaksın belli ki.",
    'dead_eye': "💀 *Dead Eye*\n\nVasiyetini yazdın mı? 3 shot espresso... Ölmek için daha zahmetsiz yollar var.",
    'iced_latte': "🧊 *Iced Latte*\n\nBuzlu sütlü kahve. Serinle bakalım, kahve tadı arama ama.",
    'iced_americano': "🧊 *Iced Americano*\n\nBuzlu su ve espresso. Yazın kurtarıcısı diyorlar, ben 'su' diyorum."
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
    'dead eye': 'dead_eye',
    'iced latte': 'iced_latte', 'buzlu latte': 'iced_latte',
    'iced americano': 'iced_americano', 'buzlu americano': 'iced_americano'
}

def find_best_recipe(text):
    text = text.lower().strip()
    words = text.split()
    
    # 1. Exact or keyword matches
    for keyword, recipe_id in KEYWORD_MAP.items():
        if keyword in text:
            return recipe_id, None
            
    # 2. Fuzzy matching using difflib
    all_keywords = list(KEYWORD_MAP.keys())
    for word in words:
        matches = difflib.get_close_matches(word, all_keywords, n=1, cutoff=0.7)
        if matches:
            return KEYWORD_MAP[matches[0]], matches[0]
            
    # 3. Recommendation logic
    if any(word in text for word in ['sert', 'güçlü', 'uyandır', 'kafein']):
        if any(word in text for word in ['ölü', 'çok', 'max']): return 'dead_eye', None
        return 'ristretto', None
    if any(word in text for word in ['sütlü', 'yumuşak', 'hafif']):
        return 'latte', None
    if any(word in text for word in ['soğuk', 'buzlu', 'ferah']):
        return 'iced_latte', None
        
    return None, None

def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("V60 (Vaktim çok) ☕", callback_data='v60')],
        [InlineKeyboardButton("Chemex (Laboratuvar) 🧪", callback_data='chemex')],
        [InlineKeyboardButton("AeroPress (Presle) 🚀", callback_data='aeropress')],
        [InlineKeyboardButton("Espresso & Süt Banyosu ☕🥛", callback_data='espresso_menu')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_espresso_menu():
    keyboard = [
        [InlineKeyboardButton("Gerçek Kahve (Espresso)", callback_data='espresso'), InlineKeyboardButton("Ristretto", callback_data='ristretto')],
        [InlineKeyboardButton("Sütlü Su (Latte)", callback_data='latte'), InlineKeyboardButton("Bıyık Köpüğü (Cappuccino)", callback_data='cappuccino')],
        [InlineKeyboardButton("Havalı (Flat White)", callback_data='flat_white'), InlineKeyboardButton("Kararsız (Cortado)", callback_data='cortado')],
        [InlineKeyboardButton("⬅️ Ana Menü", callback_data='menu')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update, context):
    await update.message.reply_text(
        "👋 Yine mi geldin? Ben Barista Koçu.\n\nNe istiyorsun, yine o sütlü kahvelerinden mi? Yaz bir şeyler ya da menüden seç de işimize bakalım.", 
        reply_markup=get_main_menu()
    )

async def handle_callback(update, context):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'menu':
        await query.edit_message_text("Hangi demleme yöntemiyle vaktimi harcayacaksın?", reply_markup=get_main_menu())
    elif query.data == 'espresso_menu':
        await query.edit_message_text(RECIPES['espresso_menu'], reply_markup=get_espresso_menu())
    else:
        text = RECIPES.get(query.data, "Bunu bulamadım, herhalde menüden kaldırdık.")
        keyboard = [[InlineKeyboardButton("⬅️ Menüye Dön", callback_data='menu')]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def handle_text(update, context):
    user_text = update.message.text
    recipe_id, matched_word = find_best_recipe(user_text)
    
    if recipe_id:
        text = RECIPES[recipe_id]
        response_prefix = ""
        if matched_word:
            response_prefix = f"Hah, '{matched_word}' demek istedin herhalde. Yazmayı bile bilmiyorsun ama kahve içmek istiyorsun, ilginç...\n\n"
        else:
            response_prefix = "Hah, sonunda bir şey buldum. Al bakalım, çok bir şey bekleme ama:\n\n"
            
        keyboard = [[InlineKeyboardButton("⬅️ Ana Menü", callback_data='menu')]]
        await update.message.reply_text(text=f"{response_prefix}{text}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    else:
        await update.message.reply_text(
            "Ne diyorsun? Düzgünce yaz şunu ya da menüden seç, vaktimi çalma.", 
            reply_markup=get_main_menu()
        )

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
    try:
        asyncio.run(process())
    except Exception as e:
        logger.error(f"Error: {e}")
        return "Error", 500
    return "OK", 200

application = app
