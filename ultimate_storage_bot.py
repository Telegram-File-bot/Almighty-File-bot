#!/usr/bin/env python3
import os
import sqlite3
import uuid
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
DB_FILE = os.environ.get("DB_FILE", "files.db")

if not BOT_TOKEN:
    logger.error("BOT_TOKEN not set. Set it in Render environment variables.")
    raise SystemExit("Missing BOT_TOKEN")

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id TEXT PRIMARY KEY,
            file_id TEXT,
            file_name TEXT,
            file_type TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_file(unique_id, file_id, file_name, file_type):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO files (id, file_id, file_name, file_type, created_at) VALUES (?, ?, ?, ?, ?)",
              (unique_id, file_id, file_name, file_type, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def get_file(unique_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT file_id, file_name, file_type FROM files WHERE id=?", (unique_id,))
    r = c.fetchone()
    conn.close()
    return r

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if args:
        uid = args[0]
        data = get_file(uid)
        if not data:
            await update.message.reply_text("Link invalid ya file delete ho gayi.")
            return
        file_id, file_name, file_type = data
        chat_id = update.effective_chat.id
        if file_type == "photo":
            await context.bot.send_photo(chat_id=chat_id, photo=file_id, caption=file_name)
        elif file_type == "video":
            await context.bot.send_video(chat_id=chat_id, video=file_id, caption=file_name)
        elif file_type == "audio":
            await context.bot.send_audio(chat_id=chat_id, audio=file_id, caption=file_name)
        else:
            await context.bot.send_document(chat_id=chat_id, document=file_id, filename=file_name)
    else:
        await update.message.reply_text("Welcome! Agar aapke paas file link hai to /start <id> ya us link se kholen.")

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Sirf admin file upload kar sakta hai.")
        return

    msg = update.message
    file_id = None
    file_name = None
    file_type = "document"

    if msg.document:
        file_id = msg.document.file_id
        file_name = msg.document.file_name or "document"
        file_type = "document"
    elif msg.photo:
        file_id = msg.photo[-1].file_id
        file_name = msg.caption or "photo"
        file_type = "photo"
    elif msg.video:
        file_id = msg.video.file_id
        file_name = getattr(msg.video, 'file_name', None) or (msg.caption or "video")
        file_type = "video"
    elif msg.audio:
        file_id = msg.audio.file_id
        file_name = getattr(msg.audio, 'file_name', None) or "audio"
        file_type = "audio"
    elif msg.voice:
        file_id = msg.voice.file_id
        file_name = "voice"
        file_type = "voice"
    elif msg.animation:
        file_id = msg.animation.file_id
        file_name = "animation"
        file_type = "animation"
    elif msg.sticker:
        file_id = msg.sticker.file_id
        file_name = "sticker"
        file_type = "sticker"

    if not file_id:
        await update.message.reply_text("Koi supported file bheje (document/photo/video/audio).")
        return

    unique_id = uuid.uuid4().hex[:8]
    save_file(unique_id, file_id, file_name, file_type)
    link = f"https://t.me/{context.bot.username}?start={unique_id}"
    await update.message.reply_text(f"File saved ✅\nLink: {link}")

def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ALL, handle_file))
    logger.info("Bot starting (cloud mode).")
    app.run_polling()

if __name__ == "__main__":
    main()
