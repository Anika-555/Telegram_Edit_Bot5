import os
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from PIL import Image, ImageDraw, ImageFont
import pytesseract
import io

# Load token securely from environment variable
BOT_TOKEN = os.getenv("BOT_TOKEN")

# In-memory store for OCR results per user
user_text_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Send me an image with text, and I’ll make the text editable!")

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = await update.message.photo[-1].get_file()
    image_bytes = await photo.download_as_bytearray()
    image = Image.open(io.BytesIO(image_bytes))

    text_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    user_text_data[update.effective_chat.id] = text_data

    texts = [text_data["text"][i] for i in range(len(text_data["text"])) if text_data["text"][i].strip() != ""]
    await update.message.reply_text("📝 Detected Text:\n" + "\n".join(texts))
    await update.message.reply_text("✏️ Now send me the new text in this format:\n\n`OLD TEXT -> NEW TEXT`", parse_mode="Markdown")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in user_text_data:
        await update.message.reply_text("❗ Please send an image first.")
        return

    content = update.message.text
    if "->" not in content:
        await update.message.reply_text("❌ Invalid format. Use `OLD TEXT -> NEW TEXT`")
        return

    old_text, new_text = [x.strip() for x in content.split("->", 1)]
    data = user_text_data[chat_id]
    image = Image.new("RGB", (800, 800), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()

    for i in range(len(data["text"])):
        word = data["text"][i]
        if word.strip() == "":
            continue
        x, y = int(data["left"][i]), int(data["top"][i])
        word_to_draw = new_text if word == old_text else word
        draw.text((x, y), word_to_draw, fill=(0, 0, 0), font=font)

    bio = io.BytesIO()
    bio.name = "edited.png"
    image.save(bio, "PNG")
    bio.seek(0)
    await update.message.reply_photo(photo=InputFile(bio))

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.PHOTO, handle_image))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

app.run_polling()