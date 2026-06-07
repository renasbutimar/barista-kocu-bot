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

# Recipes Database - Expanded with Global and Traditional Recipes
RECIPES = {
    # Existing / Espresso Based
    'espresso': "☕ *Espresso: Zarafetin Özü*\n\n18-20g kahve, 1:2 oranında (36-40g) çıktı. 25-30 saniye demleme. Kahve dünyasının kalbine giden en kısa yol! :)",
    'ristretto': "☕ *Ristretto: Yoğun Bir Öpücük*\n\n18-20g kahve, 1:1.2 oranında (22-25g) çıktı. 15-20 saniye. Kısa, öz ve inanılmaz tatlı bir deneyim.",
    'lungo': "☕ *Lungo: Uzun ve Karakterli*\n\n18-20g kahve, 1:3 oranında (60g+) çıktı. 35-40 saniye. Daha fazla su, daha farklı aromalar!",
    'macchiato': "🥛 *Espresso Macchiato: Sütün Dokunuşu*\n\nEspresso üzerine sadece bir kaşık ipeksi süt köpüğü. Sütün kahveyle ilk flörtü...",
    'latte_macchiato': "🥛 *Latte Macchiato: Katmanlı Rüya*\n\n250ml sıcak sütün içine nazikçe süzülen espresso. Görsel bir şölen ve yumuşacık bir içim.",
    'americano': "🥤 *Americano: Klasik Ferahlık*\n\nDouble espresso ve 150ml sıcak su. Günün her saati size eşlik edecek sadık bir dost.",
    'latte': "🥛 *Caffè Latte: İpeksi Bir Kucaklama*\n\nDouble espresso ve 200ml buharlanmış süt. Yumuşacık bir günaydın demek için birebir! :)",
    'cappuccino': "☁️ *Cappuccino: Köpük Bulutu*\n\nDouble espresso, eşit miktarda sıcak süt ve yoğun süt köpüğü. Klasiklerin en romantiği.",
    'flat_white': "🥛 *Flat White: Kadife Dokusu*\n\nDouble espresso ve 120ml mikro-köpüklü süt. Sütün ve kahvenin mükemmel dengesi.",
    'cortado': "🥃 *Cortado: İspanyol Esintisi*\n\nDouble espresso ve 60ml süt (1:1 oran). Sertlik ve yumuşaklığın dansı.",
    'mocha': "🍫 *Caffè Mocha: Çikolata Aşkı*\n\nEspresso, çikolata sosu ve sıcak süt. Tatlı bir kaçamak yapmak isteyenlere...",
    
    # Filter / Alternative
    'v60': "☕ *Hario V60: Aromaların Dansı*\n\n15g kahve, 250ml su (92°C). 30g ön demleme (30sn), ardından dairesel hareketlerle su ekle. Berrak ve asidik bir fincan!",
    'chemex': "🧪 *Chemex: Saf ve Berrak*\n\n30g orta-kalın kahve, 500ml su. Kalın filtresi sayesinde en saf aromaları fincanınıza taşır. Sanat eseri gibi bir demleme.",
    'aeropress': "🚀 *AeroPress: Pratik Macera*\n\n18g kahve, 200ml su. Ters yöntemle demleyip 1:30'da presle. Her seferinde şaşırtıcı sonuçlar!",
    'cold_brew': "🧊 *Cold Brew: Sabrın Ödülü*\n\n1:10 oranında kahve ve soğuk su. 12-18 saat oda sıcaklığında beklet. Düşük asidite, yüksek enerji!",

    # Traditional & Regional World Recipes
    'turkish_coffee': "🇹🇷 *Türk Kahvesi: 500 Yıllık Hatır*\n\n7-8g incecik çekilmiş kahve, 65ml su. Kısık ateşte köpürene kadar pişir. Dost sohbetlerinin vazgeçilmezi. Afiyet olsun! :)",
    'vietnamese_iced': "🇻🇳 *Cà Phê Sữa Đá: Vietnam'ın Enerjisi*\n\nPhin filtresinde demlenmiş koyu kahve, üzerine 2-3 kaşık yoğunlaştırılmış süt (condensed milk) ve bol buz. Tatlı ve çok sert!",
    'greek_frappe': "🇬🇷 *Greek Frappe: Ege Serinliği*\n\n2 tatlı kaşığı granül kahve, şeker ve az su ile çırpılarak yoğun bir köpük elde edilir. Üzerine buz ve soğuk su/süt eklenir. Yazın favorisi!",
    'cafe_de_olla': "🇲🇽 *Café de Olla: Meksika Sıcaklığı*\n\nToprak kapta demlenmiş filtre kahve, tarçın çubuğu ve piloncillo (esmer şeker). Baharatlı ve mistik bir lezzet.",
    'irish_coffee': "🇮🇪 *Irish Coffee: Sıcak Bir Kaçamak*\n\nSıcak filtre kahve, İrlanda viskisi, esmer şeker ve üzerine çırpılmış soğuk krema. Karıştırmadan kremanın içinden yudumla!",
    'miel': "🍯 *Café Miel: Bal ve Tarçın*\n\nEspresso, sıcak süt, bir tatlı kaşığı bal ve bir tutam tarçın. Isıtıcı ve doğal bir tatlılık.",
    'mazagran': "🇩🇿 *Mazagran: Kahvenin Limonata Hali*\n\nCezayir asıllı. Güçlü bir kahve üzerine buz, şeker ve taze limon suyu. Şaşırtıcı derecede ferahlatıcı!",
    'dirty_chai': "☕ *Dirty Chai Latte: Baharat Yolu*\n\nChai Tea Latte'nin içine eklenen bir shot espresso. Hem baharatlı hem de kafeinli bir rüya.",
    'cafe_bombon': "🇪🇸 *Café Bombón: İspanyol Tatlısı*\n\n1:1 oranında espresso ve yoğunlaştırılmış süt. Katmanlı görünümüyle tam bir görsel şölen!",
    'yuenyeung': "🇭🇰 *Yuenyeung: Doğu ile Batı*\n\nHong Kong klasiği. 3 ölçü kahve ve 7 ölçü sütlü çayın karışımı. İnanılmaz bir denge!",

    # High Caffeine
    'red_eye': "👁️ *Red Eye: Uyanış*\n\nStandart bir fincan filtre kahve içine eklenen 1 shot espresso. Güne hızlı başlamak isteyenlere.",
    'black_eye': "👁️👁️ *Black Eye: Çift Etki*\n\nFiltre kahve içine 2 shot espresso. Gerçek bir kafein bombası!",
    'dead_eye': "💀 *Dead Eye: Uykusuzlara Son*\n\nFiltre kahve içine tam 3 shot espresso. Dikkatli yudumla, yerinde duramayabilirsin! :)"
}

# Mapping keywords to recipe IDs
KEYWORD_MAP = {
    'v60': 'v60', 'hario': 'v60', 'chemex': 'chemex', 'aeropress': 'aeropress',
    'espresso': 'espresso', 'ristretto': 'ristretto', 'lungo': 'lungo',
    'macchiato': 'macchiato', 'latte macchiato': 'latte_macchiato',
    'americano': 'americano', 'latte': 'latte', 'cappuccino': 'cappuccino',
    'flat white': 'flat_white', 'cortado': 'cortado', 'mocha': 'mocha',
    'turkish': 'turkish_coffee', 'türk': 'turkish_coffee',
    'vietnamese': 'vietnamese_iced', 'vietnam': 'vietnamese_iced',
    'frappe': 'greek_frappe', 'greek': 'greek_frappe',
    'olla': 'cafe_de_olla', 'mexican': 'cafe_de_olla',
    'irish': 'irish_coffee', 'irlanda': 'irish_coffee',
    'miel': 'miel', 'ballı': 'miel',
    'mazagran': 'mazagran', 'limonlu': 'mazagran',
    'dirty chai': 'dirty_chai', 'bombon': 'cafe_bombon',
    'yuenyeung': 'yuenyeung', 'çaylı': 'yuenyeung',
    'cold brew': 'cold_brew', 'soğuk demleme': 'cold_brew',
    'red eye': 'red_eye', 'black eye': 'black_eye', 'dead eye': 'dead_eye'
}

def find_best_recipe(text):
    text = text.lower()
    # Direct keyword search
    for keyword, recipe_id in KEYWORD_MAP.items():
        if keyword in text:
            return recipe_id
    
    # Fuzzy matching for typos
    all_keywords = list(KEYWORD_MAP.keys())
    # Split text into words to check each one
    words = text.split()
    for word in words:
        matches = difflib.get_close_matches(word, all_keywords, n=1, cutoff=0.7)
        if matches:
            return KEYWORD_MAP[matches[0]]
            
    return None

def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("Dünya Kahveleri 🌍", callback_data='world_menu')],
        [InlineKeyboardButton("Espresso Bazlılar ☕", callback_data='espresso_menu')],
        [InlineKeyboardButton("Demleme Yöntemleri 🧪", callback_data='brew_menu')],
        [InlineKeyboardButton("Kafein Bombaları 💀", callback_data='high_caffeine')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update, context):
    await update.message.reply_text(
        "Merhaba! Ben Barista Koçun. 😊\n\nKahve dünyasının gizemli tariflerini keşfetmeye hazır mısın? "
        "Bana merak ettiğin bir kahveyi sorabilirsin (örneğin: 'V60 nasıl yapılır?' veya 'Türk kahvesi tarifi') "
        "ya da menüden seçim yapabilirsin.", 
        reply_markup=get_main_menu()
    )

async def handle_callback(update, context):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    keyboard = [[InlineKeyboardButton("⬅️ Ana Menü", callback_data='menu')]]
    
    if data == 'menu':
        await query.edit_message_text("Hangi serüvene atılmak istersin?", reply_markup=get_main_menu())
    elif data == 'world_menu':
        text = "🌍 *Geleneksel Dünya Kahveleri*\nFarklı kültürlerin en özel lezzetleri..."
        sub_kb = [
            [InlineKeyboardButton("Türk Kahvesi 🇹🇷", callback_data='turkish_coffee')],
            [InlineKeyboardButton("Vietnamese Iced 🇻🇳", callback_data='vietnamese_iced')],
            [InlineKeyboardButton("Greek Frappe 🇬🇷", callback_data='greek_frappe')],
            [InlineKeyboardButton("Café de Olla 🇲🇽", callback_data='cafe_de_olla')],
            [InlineKeyboardButton("İrlanda / Mazagran 🇮🇪🇩🇿", callback_data='more_world')],
            [InlineKeyboardButton("⬅️ Geri", callback_data='menu')]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(sub_kb), parse_mode='Markdown')
    elif data == 'espresso_menu':
        text = "☕ *Espresso Sanatı*\nKlasik İtalyan dokunuşları..."
        sub_kb = [
            [InlineKeyboardButton("Espresso / Ristretto", callback_data='espresso')],
            [InlineKeyboardButton("Latte / Cappuccino", callback_data='latte')],
            [InlineKeyboardButton("Flat White / Cortado", callback_data='flat_white')],
            [InlineKeyboardButton("⬅️ Geri", callback_data='menu')]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(sub_kb), parse_mode='Markdown')
    elif data in RECIPES:
        await query.edit_message_text(RECIPES[data], reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    else:
        await query.edit_message_text("Bu tarif henüz gizli... Yakında gelecek! :)", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_text(update, context):
    user_text = update.message.text
    recipe_id = find_best_recipe(user_text)
    
    if recipe_id:
        # Finding which keyword matched for the "Did you mean X?" effect
        all_keywords = list(KEYWORD_MAP.keys())
        words = user_text.lower().split()
        match_found = None
        for word in words:
            m = difflib.get_close_matches(word, all_keywords, n=1, cutoff=0.7)
            if m:
                match_found = m[0]
                break
        
        reply_prefix = ""
        if match_found and match_found not in user_text.lower():
            reply_prefix = f"*{match_found.capitalize()}* demek istedin galiba? Harika seçim! :) \n\n"
        
        await update.message.reply_text(f"{reply_prefix}{RECIPES[recipe_id]}", parse_mode='Markdown')
    else:
        await update.message.reply_text(
            "Bunu tam olarak anlayamadım ama kahve aşkına, menüden her şeyi bulabilirsin! 👇", 
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
    return "OK", 200

application = app
if __name__ == '__main__':
    app.run()
