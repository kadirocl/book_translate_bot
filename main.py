from keep_alive import keep_alive
keep_alive()

import os
import fitz  # PyMuPDF
from telegram import Update, Document, Message
from telegram.ext import ApplicationBuilder, MessageHandler, filters, CommandHandler, ContextTypes
from ebooklib import epub
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

BOT_TOKEN = "BOT_TOKENİNİ_BURAYA_YAPIŞTIR"

ADMINS = [
    7542599799,  # @Tomrisw
    6648442038,  # Sen
]

user_languages = {}

def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMINS:
            await update.message.reply_text("🚫 Bu komut sadece yöneticilere özel.")
            return
        return await func(update, context)
    return wrapper

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 Merhaba! Bu bot kitap ve metin çevirisi yapar.\n\n"
        "📝 Metin, 📄 PDF, 📘 EPUB ya da 📄 TXT dosyası gönder.\n"
        "🌍 Varsayılan dil: Türkçe\n"
        "💬 Dil ayarlamak için: /language en (veya fr, ar, de...)\n"
        "📌 Yanıtladığın mesajı çevirmek için: /translate"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 Yardım:\n"
        "/start - Karşılama\n"
        "/language <dil_kodu> - Hedef dili ayarla (örn: /language en)\n"
        "/translate <metin> - Metni çevir\n"
        "/translate (yanıtla) - Yanıtlanan mesajı çevir\n"
        "PDF, EPUB ya da TXT dosyası da gönderebilirsiniz.")

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        lang_code = context.args[0]
        user_languages[update.effective_user.id] = lang_code
        await update.message.reply_text(f"✅ Hedef dil ayarlandı: {lang_code}")
    else:
        await update.message.reply_text("❗ Dil kodu eksik. Örn: /language en")

@admin_only
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛠 Admin paneline hoş geldiniz.")

def translate_text(text, target_lang="tr"):
    try:
        return GoogleTranslator(source='auto', target=target_lang).translate(text)
    except Exception as e:
        return f"[❗ Çeviri hatası: {e}]"

def split_text(text, max_length=3000):
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]

def extract_text_from_pdf(file_path):
    try:
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        return f"[PDF okuma hatası: {e}]"

def extract_text_from_epub(file_path):
    try:
        book = epub.read_epub(file_path)
        text = ""
        for item in book.get_items():
            if item.get_type() == epub.EpubHtml:
                soup = BeautifulSoup(item.get_content(), 'html.parser')
                text += soup.get_text()
        return text
    except Exception as e:
        return f"[EPUB okuma hatası: {e}]"

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    target_lang = user_languages.get(user_id, "tr")
    text = update.message.text

    await update.message.reply_text("🌐 Çevriliyor...")
    translated = translate_text(text, target_lang)
    await update.message.reply_text(f"✅ Çeviri:\n\n{translated}")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        doc: Document = update.message.document
        file_name = doc.file_name.lower()

        if not file_name.endswith((".pdf", ".txt", ".epub")):
            await update.message.reply_text("❗ Sadece PDF, TXT veya EPUB gönderin.")
            return

        file = await context.bot.get_file(doc.file_id)
        os.makedirs("downloads", exist_ok=True)
        file_path = os.path.join("downloads", file_name)
        await file.download_to_drive(file_path)

        await update.message.reply_text("📥 Dosya alındı, metin çıkarılıyor...")

        if file_name.endswith(".pdf"):
            text = extract_text_from_pdf(file_path)
        elif file_name.endswith(".txt"):
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
        elif file_name.endswith(".epub"):
            text = extract_text_from_epub(file_path)

        if not text.strip():
            await update.message.reply_text("❌ Dosyada metin bulunamadı.")
            return

        await update.message.reply_text("🌐 Çeviri yapılıyor...")

        user_id = update.effective_user.id
        target_lang = user_languages.get(user_id, "tr")

        parts = split_text(text)
        translated_parts = [translate_text(part, target_lang) for part in parts]
        full_translation = "\n\n".join(translated_parts)

        output_path = os.path.join("downloads", f"translated_{file_name}.txt")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(full_translation)

        await update.message.reply_text("📄 Çeviri tamamlandı, dosya gönderiliyor...")
        await context.bot.send_document(chat_id=update.effective_chat.id, document=open(output_path, "rb"))

    except Exception as e:
        await update.message.reply_text(f"⚠️ Hata oluştu: {e}")

# ✅ /translate komutu: Yanıtlanan mesaj ya da direkt metni çevir
async def translate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    target_lang = user_languages.get(user_id, "tr")

    # Yanıt varsa onu çevir
    if update.message.reply_to_message and update.message.reply_to_message.text:
        text_to_translate = update.message.reply_to_message.text
    # Argüman varsa onu çevir
    elif context.args:
        text_to_translate = " ".join(context.args)
    else:
        await update.message.reply_text("❗ Çevirmek için ya bir mesaja yanıt verin ya da metin yazın.\n\nÖrn:\n/translate Merhaba")
        return

    await update.message.reply_text("🌐 Çevriliyor...")
    translated = translate_text(text_to_translate, target_lang)
    await update.message.reply_text(f"✅ Çeviri:\n\n{translated}")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("language", set_language))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("translate", translate_command))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))

    print("🚀 Bot çalışıyor...")
    app.run_polling()

if __name__ == "__main__":
    main()
