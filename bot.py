import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from dotenv import load_dotenv
from database import save_highlight

load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to Readvibe! 🌿\n\n"
        "Send me any text, highlight, or quote you want to save.\n\n"
        "Tip: You can use the format:\n"
        "Title | Author\n"
        "Your highlight content here..."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    # Extract hashtags
    import re
    tags = re.findall(r'#(\w+)', text)
    # Remove hashtags from the content if you want it clean, 
    # but for now we'll keep the text as is and just save the tags separately.
    
    lines = text.split('\n')
    
    title = "Untitled"
    author = "Unknown"
    content = text

    # Simple heuristic parser
    if len(lines) > 1 and '|' in lines[0]:
        parts = lines[0].split('|')
        title = parts[0].strip()
        if len(parts) > 1:
            author = parts[1].strip()
        content = '\n'.join(lines[1:]).strip()
    
    try:
        save_highlight(content, title, author, tags)
        await update.message.reply_text("Saved to Readvibe! ✨")
    except Exception as e:
        logging.error(f"Error saving highlight: {e}")
        await update.message.reply_text("Oops! Something went wrong while saving. 🌿")

if __name__ == '__main__':
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN not found in .env")
    else:
        application = ApplicationBuilder().token(token).build()
        
        start_handler = CommandHandler('start', start)
        msg_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
        
        application.add_handler(start_handler)
        application.add_handler(msg_handler)
        
        print("Readvibe Bot is running...")
        application.run_polling()
