import os
import tempfile
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, CommandHandler, filters
import openai
import subprocess

# Load environment variables
load_dotenv()

# Configure OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')
client = openai.Client()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    await update.message.reply_text(
        "👋 Hi! Send me a voice message and I'll convert it to text in a copyable format."
    )

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle voice messages."""
    try:
        # Send a processing message
        processing_msg = await update.message.reply_text("🎧 Processing your voice message...")

        # Get the voice message file
        voice_file = await context.bot.get_file(update.message.voice.file_id)

        # Create a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Download the voice message
            ogg_path = Path(temp_dir) / "voice.ogg"
            mp3_path = Path(temp_dir) / "voice.mp3"

            # Download the voice file
            await voice_file.download_to_drive(str(ogg_path))

            # Convert OGG to MP3 using ffmpeg
            try:
                command = [
                    'ffmpeg',
                    '-i', str(ogg_path),
                    '-y',  # Overwrite output file if it exists
                    str(mp3_path)
                ]
                process = subprocess.run(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True
                )
            except subprocess.CalledProcessError as e:
                await update.message.reply_text(f"❌ Error converting audio: {e.stderr.decode()}")
                return

            # Transcribe using OpenAI's Whisper
            with open(mp3_path, "rb") as audio_file:
                transcript = await asyncio.to_thread(
                    client.audio.transcriptions.create,
                    model="whisper-1",
                    file=audio_file
                )

            # Escape special characters for MarkdownV2
            escaped_text = transcript.text.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)').replace('~', '\\~').replace('`', '\\`').replace('>', '\\>').replace('#', '\\#').replace('+', '\\+').replace('-', '\\-').replace('=', '\\=').replace('|', '\\|').replace('{', '\\{').replace('}', '\\}').replace('.', '\\.').replace('!', '\\!')

            # Delete the processing message
            await processing_msg.delete()

            # Send only the code block message for one-click copying
            await update.message.reply_text(
                f"``````",
                parse_mode='MarkdownV2'
            )

    except Exception as e:
        await update.message.reply_text(f"❌ Sorry, an error occurred: {str(e)}")

def main() -> None:
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))

    # Start the Bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
