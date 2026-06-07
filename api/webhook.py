import logging
import os
import json
import asyncio
from http.server import BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler

# Logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Coffee Recipes
RECIPES = {
    'v60': (
        "☕ *Hario V60 Tarifi*\n\n"
        "🔸 *Kahve:* 15g (Orta-İnce)\n"
        "🔸 *Su:* 250ml (92-94°C)\n"
        "🔸 *Süre:* 2:30 - 3:00 dk\n\n"
        "1. 30g su ile blooming yap (30 sn).\n"
        "2. 1:15'e kadar 150ml'ye tamamla.\n"
        "3. Kalan suyu nazikçe ekle."
    ),
    'chemex': (
        "🧪 *Chemex Tarifi*\n\n"
        "🔸 *Kahve:* 30g (Orta-Kalın)\n"
        "🔸 *Su:* 500ml (94°C)\n"
        "🔸 *Süre:* 3:30 - 4:30 dk\n\n"
        "1. 60g su ile blooming yap (45 sn).\n"
        "2. Suyu yavaşça merkeze dökerek 500ml'ye ulaş."
    ),
    'aeropress': (
        "🚀 *AeroPress Tarifi (Ters)*\n\n"
        "🔸 *Kahve:* 18g (İnce-Orta)\n"
        "🔸 *Su:* 200ml (85-88°C)\n"
        "🔸 *Süre:* 2:00 dk\n\n"
        "1. Suyu ekle, 30 sn bekle, karıştır.\n"
        "2. 1:30'da kapağı kapat ve 30 sn boyunca presle."
    ),
    'espresso_base': (
        "☕ *Espresso Bazlı Kahveler*\n\n"
        "Hangi içeceği hazırlamak istersin?"
    ),
    'espresso': (
        "☕ *Espresso (Double Shot)*\n\n"
        "🔸 *Kahve:* 18-20g\n"
        "🔸 *Çıktı:* 36-40g (1:2 oran)\n"
        "🔸 *Süre:* 25-30 saniye\n"
        "🔸 *Sıcaklık:* 93°C\n\n"
        "1. Portafiltreyi kurula ve kahveyi tartarak ekle.\n"
        "2. Düzgünce dağıt (WDT) ve tamp yap.\n"
        "3. Akışın dengeli ve kremsi olduğundan emin ol."
    ),
    'latte': (
        "🥛 *Caffè Latte*\n\n"
        "🔸 *Espresso:* 1 shot (veya double)\n"
        "🔸 *Süt:* 200-250ml\n"
        "🔸 *Süt Sıcaklığı:* 60-65°C\n"
        "🔸 *Köpük:* 0.5-1 cm (İnce mikro-köpük)\n\n"
        "1. Espressoyu hazırla.\n"
        "2. Sütü ipeksi bir doku için az havalandırarak ısıt.\n"
        "3. Kremsi sütü yavaşça espressoya dökerek birleştir."
    ),
    'cappuccino': (
        "☁️ *Cappuccino*\n\n"
        "🔸 *Espresso:* 1 shot\n"
        "🔸 *Süt:* 150ml\n"
        "🔸 *Süt Sıcaklığı:* 60-65°C\n"
        "🔸 *Köpük:* 1.5-2 cm (Yoğun köpük)\n\n"
        "1. Espressoyu fincana al.\n"
        "2. Sütü daha fazla havalandırarak yoğun bir köpük oluştur.\n"
        "3. Köpüğü ve sütü espresso ile buluştur."
    ),
    'flat_white': (
        "🇦🇺 *Flat White*\n\n"
        "🔸 *Espresso:* Double Shot (Ristretto tercih edilebilir)\n"
        "🔸 *Süt:* 150ml\n"
        "🔸 *Süt Sıcaklığı:* 60-62°C\n"
        "🔸 *Köpük:* Çok ince (Micro-foam)\n\n"
        "1. Güçlü bir double espresso hazırla.\n"
        "2. Sütü minimum hava ile pürüzsüzce ısıt.\n"
        "3. İnce bir tabaka oluşturacak şekilde dök."
    ),
    'cortado': (
        "🇪🇸 *Cortado*\n\n"
        "🔸 *Espresso:* Double Shot\n"
        "🔸 *Süt:* 60ml (1:1 oran)\n"
        "🔸 *Süt Sıcaklığı:* 55-60°C\n\n"
        "1. Espressoyu küçük cam bardağa (gibraltar) al.\n"
        "2. Sütü hafifçe ısıt.\n"
        "3. Kahvenin sertliğini kırmadan sütü ekle."
    ),
    'americano': (
        "💧 *Caffè Americano*\n\n"
        "🔸 *Espresso:* Double Shot\n"
        "🔸 *Sıcak Su:* 150-200ml\n\n"
        "1. Fincana önce sıcak suyu al.\n"
        "2. Üzerine taze espressoyu dökerek kremayı koru."
    ),
    'iced_latte': (
        "🧊 *Iced Latte*\n\n"
        "🔸 *Espresso:* Double Shot\n"
        "🔸 *Soğuk Süt:* 180ml\n"
        "🔸 *Buz:* 4-5 adet küp\n\n"
        "1. Bardağa buzları doldur.\n"
        "2. Üzerine soğuk sütü ekle.\n"
        "3. En son taze espressoyu dökerek katmanlı bir görüntü oluştur."
    ),
    'iced_americano': (
        "🧊 *Iced Americano*\n\n"
        "🔸 *Espresso:* Double Shot\n"
        "🔸 *Soğuk Süt:* 150ml\n"
        "🔸 *Buz:* Bolca\n\n"
        "1. Bardağa buz ve soğuk suyu al.\n"
        "2. Üzerine espressoyu ekle ve karıştır."
    )
}

TOKEN = '8640816185:AAH3vQsZl9TtNF5lFmZQJxHdxlV0-LPCa2w'
app = ApplicationBuilder().token(TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Pour Over (V60, Chemex...)", callback_data='pour_over_menu')],
        [InlineKeyboardButton("Espresso Bazlı Kahveler", callback_data='espresso_menu')],
        [InlineKeyboardButton("AeroPress 🚀", callback_data='aeropress')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 Selam Şef! Ben senin kişisel Barista asistanınım.\n\n"
        "Bugün hangi demleme yöntemiyle harikalar yaratmak istersin?",
        reply_markup=reply_markup
    )

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'menu':
        keyboard = [
            [InlineKeyboardButton("Pour Over (V60, Chemex...)", callback_data='pour_over_menu')],
            [InlineKeyboardButton("Espresso Bazlı Kahveler", callback_data='espresso_menu')],
            [InlineKeyboardButton("AeroPress 🚀", callback_data='aeropress')]
        ]
        await query.edit_message_text("Hangi demleme yöntemini seçiyoruz?", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif query.data == 'pour_over_menu':
        keyboard = [
            [InlineKeyboardButton("V60 ☕", callback_data='v60')],
            [InlineKeyboardButton("Chemex 🧪", callback_data='chemex')],
            [InlineKeyboardButton("⬅️ Ana Menü", callback_data='menu')]
        ]
        await query.edit_message_text("Bir Pour Over yöntemi seç:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == 'espresso_menu':
        keyboard = [
            [InlineKeyboardButton("Espresso", callback_data='espresso'), InlineKeyboardButton("Americano", callback_data='americano')],
            [InlineKeyboardButton("Latte", callback_data='latte'), InlineKeyboardButton("Cappuccino", callback_data='cappuccino')],
            [InlineKeyboardButton("Flat White", callback_data='flat_white'), InlineKeyboardButton("Cortado", callback_data='cortado')],
            [InlineKeyboardButton("Iced Latte 🧊", callback_data='iced_latte'), InlineKeyboardButton("Iced Americano 🧊", callback_data='iced_americano')],
            [InlineKeyboardButton("⬅️ Ana Menü", callback_data='menu')]
        ]
        await query.edit_message_text("Espresso bazlı bir içecek seç:", reply_markup=InlineKeyboardMarkup(keyboard))
        
    else:
        recipe_text = RECIPES.get(query.data, "Maalesef tarif bulunamadı.")
        back_target = 'espresso_menu' if query.data in ['espresso', 'americano', 'latte', 'cappuccino', 'flat_white', 'cortado', 'iced_latte', 'iced_americano'] else 'menu'
        keyboard = [[InlineKeyboardButton("⬅️ Geri Dön", callback_data=back_target)]]
        await query.edit_message_text(text=recipe_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

app.add_handler(CommandHandler('start', start))
app.add_handler(CallbackQueryHandler(button_click))

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        self.send_response(200)
        self.end_headers()
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        update_json = json.loads(post_data.decode('utf-8'))
        
        async def process_update():
            update = Update.de_json(update_json, app.bot)
            await app.initialize()
            await app.process_update(update)
            
        asyncio.run(process_update())
        return

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write("Barista Koçu is running!".encode('utf-8'))
        return
