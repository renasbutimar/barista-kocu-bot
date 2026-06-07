import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler
from http.server import BaseHTTPRequestHandler
import json
import asyncio

# Bot loglarını yapılandırıyoruz
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Kahve tarifleri
RECIPES = {
    'v60': (
        "☕ *Hario V60 Tarifi (Barista Standartı)*\\n\\n"
        "Modern demlemenin zirvesi! İşte mükemmel asidite ve gövde dengesi için reçetemiz:\\n\\n"
        "🔸 *Kahve:* 15g (Orta-İnce öğütüm)\\n"
        "🔸 *Su:* 250ml (92-94°C)\\n"
        "🔸 *Süre:* 2:30 - 3:00 dakika\\n\\n"
        "1. *Blooming:* 30-45g su ile 30 saniye boyunca kahveyi uyandır.\\n"
        "2. *Birinci Döküş:* Süreyi 1:15'e kadar 150ml'ye tamamla.\\n"
        "3. *İkinci Döküş:* Kalan suyu nazik dairesel hareketlerle ekle.\\n\\n"
        "✨ *İpucu:* Filtre kağıdını önceden sıcak suyla durulamayı unutma!"
    ),
    'chemex': (
        "🧪 *Chemex Tarifi (Berrak ve Zarif)*\\n\\n"
        "Laboratuvar şıklığında tertemiz bir fincan:\\n\\n"
        "🔸 *Kahve:* 30g (Orta-Kalın öğütüm, deniz tuzu gibi)\\n"
        "🔸 *Su:* 500ml (94°C)\\n"
        "🔸 *Süre:* 3:30 - 4:30 dakika\\n\\n"
        "1. *Blooming:* 60g su ile 45 saniye bekle.\\n"
        "2. *Döküş:* Suyu yavaşça merkeze yakın dökerek 500ml'ye ulaş.\\n"
        "3. *Bitiş:* Kahve yatağının düz olduğundan emin ol.\\n\\n"
        "✨ *İpucu:* Chemex filtreleri kalındır, bu yüzden kahve çok daha parlak bir profil sunar."
    ),
    'aeropress': (
        "🚀 *AeroPress Tarifi (Pratik ve Yoğun)*\\n\\n"
        "Her yere taşınabilen bir efsane! (Ters Yöntem):\\n\\n"
        "🔸 *Kahve:* 18g (İnce-Orta öğütüm)\\n"
        "🔸 *Su:* 200ml (85-88°C)\\n"
        "🔸 *Süre:* 2:00 dakika\\n\\n"
        "1. *Hazırlık:* AeroPress'i ters çevir ve kahveyi ekle.\\n"
        "2. *Demleme:* Suyu ekle, 30 saniye bekledikten sonra 3-4 kez karıştır.\\n"
        "3. *Pres:* 1:30'da kapağı kapat ve yavaşça (30 sn) bardağa bastır.\\n\\n"
        "✨ *İpucu:* Daha yoğun bir tat için espressoya yakın bir öğütüm deneyebilirsin."
    )
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("V60 ☕", callback_data='v60')],
        [InlineKeyboardButton("Chemex 🧪", callback_data='chemex')],
        [InlineKeyboardButton("AeroPress 🚀", callback_data='aeropress')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 Selam Şef! Ben senin kişisel Barista asistanınım.\\n\\n"
        "Bugün hangi demleme yöntemiyle harikalar yaratmak istersin?",
        reply_markup=reply_markup
    )

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'menu':
        keyboard = [
            [InlineKeyboardButton("V60 ☕", callback_data='v60')],
            [InlineKeyboardButton("Chemex 🧪", callback_data='chemex')],
            [InlineKeyboardButton("AeroPress 🚀", callback_data='aeropress')]
        ]
        await query.edit_message_text(
            "Hangi demleme yöntemini seçiyoruz?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        recipe_text = RECIPES.get(query.data, "Maalesef tarif bulunamadı.")
        keyboard = [[InlineKeyboardButton("⬅️ Menüye Dön", callback_data='menu')]]
        await query.edit_message_text(text=recipe_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

TOKEN = '8640816185:AAH3vQsZl9TtNF5lFmZQJxHdxlV0-LPCa2w'
app = ApplicationBuilder().token(TOKEN).build()
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
        self.wfile.write("Bot is running!".encode('utf-8'))
        return