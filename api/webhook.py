import logging
import json
import asyncio
import re
from difflib import get_close_matches
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Recipes Database with a warm, passionate persona
RECIPES = {
    'v60': "✨ *Hario V60: Zarafetin Demlemesi*\n\nKahvenin en saf notalarını keşfetmeye hazır mısın? İşte benim favorim:\n\n📍 15g taze kahve (orta-ince öğütüm)\n💧 250ml yumuşak su (92-94°C)\n⏱️ 30 saniye blooming (30g su ile)\n☕ 1:15'e kadar 150ml'ye tamamla, sonra kalan suyu dairesel hareketlerle yavaşça dök. Toplam süre 2:30-3:00 civarı olmalı.",
    'chemex': "🧪 *Chemex: Saf Berraklık*\n\nO meşhur kalın filtresiyle pırıl pırıl bir fincan hazırlayalım:\n\n📍 30g kahve (orta öğütüm)\n💧 500ml su (94°C)\n⏱️ 60g su ile 45 sn ön demleme\n☕ Yavaşça merkeze dökerek 500ml'ye tamamla. Sabırlı ol, sonuç buna değecek!",
    'aeropress': "🚀 *AeroPress: Pratik ve Karakterli*\n\nEvdeki laboratuvarımıza hoş geldin! En sevdiğim ters yöntemi deneyelim:\n\n📍 18g kahve (ince-orta)\n💧 200ml su (85-88°C)\n⏱️ Suyu ekle, 30sn bekle, karıştır.\n☕ 1:30'da yavaşça presle. Yoğun ve lezzetli!",
    'espresso_menu': "☕ *Espresso Dünyası*\n\nHarika seçimler var! Bugün seni hangi lezzetle buluşturalım?",
    'espresso': "☕ *Klasik Espresso*\n\nSaf güç ve denge bir arada!\n\n📍 18-20g kahve\n⚖️ 1:2 oran (36-40g çıktı)\n⏱️ 25-30 saniye\n✨ İpucu: Portafiltren kuru olsun, eşit tampla ve o altın rengi kremayı izle!",
    'ristretto': "☕ *Ristretto*\n\nKısa, öz ve inanılmaz tatlı!\n\n📍 18-20g kahve\n⚖️ 1:1.2 oran (22-25g çıktı)\n⏱️ 15-20 saniye. Az su, çok lezzet!",
    'lungo': "☕ *Lungo*\n\nKahve keyfini biraz daha uzatmak isteyenlere...\n\n📍 18-20g kahve\n⚖️ 1:3 oran (60g+ çıktı)\n⏱️ 35-40 saniye. Hafif ama gövdeli.",
    'macchiato': "🥛 *Espresso Macchiato*\n\nEspresso'nun üzerine kondurulmuş bir bulut gibi bir kaşık kadifemsi süt köpüğü. Zarif bir dokunuş!",
    'latte_macchiato': "🥛 *Latte Macchiato*\n\nSüt, kahve ve köpüğün muhteşem katmanlı dansı. Önce 250ml sıcak süt, sonra üzerinden yavaşça akan espresso...",
    'americano': "🥤 *Americano*\n\nDouble espresso ve sıcak suyun ferahlatıcı uyumu. Dengeli bir içim arayanlara.",
    'latte': "🥛 *Caffè Latte*\n\nİpeksi bir kucaklama gibi...\n\n📍 Double espresso\n🥛 200ml pürüzsüz süt köpüğü (60-65°C). İç ısıtan bir yumuşaklık.",
    'cappuccino': "☁️ *Cappuccino*\n\nYoğun köpük severlerin vazgeçilmezi.\n\n📍 Double espresso\n☁️ 150ml bol ve kremsi süt köpüğü. Üzerine biraz kakao? Neden olmasın!",
    'flat_white': "🥛 *Flat White*\n\nAvustralya'dan gelen bu modern klasikte, sütün dokusu espresso ile tamamen bütünleşir.\n\n📍 Double espresso\n🥛 120ml çok ince mikro-foam.",
    'cortado': "🥃 *Cortado*\n\nSüt ve kahvenin eşitlikçi dostluğu.\n\n📍 Double espresso\n🥛 60ml tatlı süt (1:1). Sert ama yumuşak bir bitiş.",
    'mocha': "🍫 *Caffè Mocha*\n\nKahve ve çikolatanın o ayrılmaz aşkı... Espresso, bitter sos ve buharlanmış sütün tatlı buluşması.",
    'romano': "🍋 *Espresso Romano*\n\nEspresso'ya bir dilim taze limon kabuğu... İtalyanların o canlandırıcı sırrını denemelisin!",
    'affogato': "🍨 *Affogato*\n\nBir top vanilyalı dondurma ve üzerinde sıcak bir double espresso... Tatlı bir rüya gibi!",
    'breve': "🥛 *Caffè Breve*\n\nDaha zengin bir doku? Yarı süt yarı krema karışımıyla espressoyu taçlandırıyoruz.",
    'vienna': "🍦 *Vienna Coffee*\n\nDouble espresso üzerine eklenen soğuk çırpılmış krema. Klasik ve asil.",
    'red_eye': "👁️ *Red Eye*\n\nUyanmak için yardıma mı ihtiyacın var? Filtre kahvene eklenen 1 shot espresso seni canlandıracak!",
    'black_eye': "👁️👁️ *Black Eye*\n\nEnerjini ikiye katlıyoruz! Filtre kahve ve 2 shot espresso.",
    'dead_eye': "💀 *Dead Eye*\n\nGünün en zorlu anları için en güçlü müttefikin: Filtre kahve ve tam 3 shot espresso!",
    'iced_latte': "🧊 *Iced Latte*\n\nBuz, soğuk süt ve espresso... Sıcak günlerin en güzel serinliği.",
    'iced_americano': "🧊 *Iced Americano*\n\nFerahlatan, duru ve canlandırıcı bir soğuk kahve deneyimi."
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
    text = text.lower()
    # Direct keyword check
    for keyword, recipe_id in KEYWORD_MAP.items():
        if keyword in text:
            return recipe_id, None
    
    # Recommendation logic
    if any(word in text for word in ['sert', 'güçlü', 'uyandır', 'siyah', 'kafein']):
        if any(word in text for word in ['ölü', 'dead', 'çok']): return 'dead_eye', None
        return 'ristretto', None
    if any(word in text for word in ['sütlü', 'yumuşak', 'hafif', 'bol süt']):
        return 'latte', None
    if any(word in text for word in ['soğuk', 'buzlu', 'serin']):
        return 'iced_latte', None

    # Fuzzy matching for typos
    words = text.split()
    all_keywords = list(KEYWORD_MAP.keys())
    for word in words:
        matches = get_close_matches(word, all_keywords, n=1, cutoff=0.7)
        if matches:
            return KEYWORD_MAP[matches[0]], matches[0]
            
    return None, None

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
    await update.message.reply_text(
        "👋 Merhaba! Ben senin dijital Barista Koçun.\n\nSana en sevdiğin kahvenin tarifini verebilir, yeni lezzetler önerebilirim. "
        "İster menüden seç, istersen 'Bir Cortado tarifi verir misin?' gibi bana yaz. Bugün ne demlemek istersin? ✨",
        reply_markup=get_main_menu()
    )

async def handle_callback(update, context):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'menu':
        await query.edit_message_text("Hangi demleme yöntemini keşfedelim? ✨", reply_markup=get_main_menu())
    elif query.data == 'espresso_menu':
        await query.edit_message_text("Espresso dünyası çok geniştir! İşte bazı harika seçenekler:", reply_markup=get_espresso_menu())
    else:
        text = RECIPES.get(query.data, "Bu tarifi henüz defterime eklememişim ama hemen öğrenebilirim! 😊")
        keyboard = [[InlineKeyboardButton("⬅️ Menüye Dön", callback_data='menu')]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def handle_text(update, context):
    user_text = update.message.text
    recipe_id, correction = find_best_recipe(user_text)
    
    if recipe_id:
        text = RECIPES[recipe_id]
        keyboard = [[InlineKeyboardButton("⬅️ Ana Menü", callback_data='menu')]]
        
        response_prefix = ""
        if correction:
            response_prefix = f"✨ *{correction.capitalize()}* demek istedin galiba? Hemen hazırlayalım! :)\n\n"
        else:
            response_prefix = "Harika bir seçim! İşte tarifin:\n\n"
            
        await update.message.reply_text(text=f"{response_prefix}{text}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    else:
        await update.message.reply_text(
            "Bunu tam anlayamadım ama sana yardımcı olmayı çok isterim! 😊\n\nMenüyü kullanabilir veya başka bir kahve sorabilirsin. "
            "Örneğin: 'Lungo nasıl yapılır?'",
            reply_markup=get_main_menu()
        )

TOKEN = '8640816185:AAH3vQsZl9TtNF5lFmZQJxHdxlV0-LPCa2w'

# Setup telegram application
telegram_app = ApplicationBuilder().token(TOKEN).build()
telegram_app.add_handler(CommandHandler('start', start))
telegram_app.add_handler(CallbackQueryHandler(handle_callback))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    return "Barista Koçu Bot is running! ☕"

@app.route('/api/webhook', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET': return "Webhook endpoint is active. ☕"
    update_json = request.get_json()
    
    async def process():
        async with telegram_app:
            update = Update.de_json(update_json, telegram_app.bot)
            await telegram_app.process_update(update)

    try:
        asyncio.run(process())
    except Exception as e:
        logger.error(f"Error processing update: {e}")
        return "Internal Error", 500
    
    return "OK", 200

# Vercel entry point
application = app
