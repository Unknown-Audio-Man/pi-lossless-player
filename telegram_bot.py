#!/usr/bin/env python3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler
from telegram.ext import ContextTypes, filters
import asyncio
import re
from config import TELEGRAM_BOT_TOKEN, AUTHORIZED_USERS
from utils import logger, format_time, format_album_info

class TelegramBot:
    def __init__(self, music_library, audio_player):
        self.music_library = music_library
        self.audio_player = audio_player
        self.bot = None
        self.current_album = None
    
    async def start(self):
        """Start the Telegram bot."""
        try:
            # Create the Application instance
            self.bot = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
            
            # Add handlers
            self.bot.add_handler(CommandHandler("start", self.cmd_start))
            self.bot.add_handler(CommandHandler("help", self.cmd_help))
            self.bot.add_handler(CommandHandler("play", self.cmd_play))
            self.bot.add_handler(CommandHandler("pause", self.cmd_pause))
            self.bot.add_handler(CommandHandler("stop", self.cmd_stop))
            self.bot.add_handler(CommandHandler("next", self.cmd_next))
            self.bot.add_handler(CommandHandler("prev", self.cmd_prev))
            self.bot.add_handler(CommandHandler("volume", self.cmd_volume))
            self.bot.add_handler(CommandHandler("status", self.cmd_status))
            self.bot.add_handler(CommandHandler("scan", self.cmd_scan))
            
            # Handle regular messages for album search
            self.bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
            
            # Handle callback queries from inline keyboards
            self.bot.add_handler(CallbackQueryHandler(self.handle_callback))
            
            # Start the bot
            await self.bot.initialize()
            await self.bot.start_polling()
            logger.info("Telegram bot started successfully")
        except Exception as e:
            logger.error(f"Error starting Telegram bot: {e}")
    
    def stop(self):
        """Stop the Telegram bot."""
        if self.bot:
            asyncio.run(self.bot.stop())
            logger.info("Telegram bot stopped")
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /start command."""
        user_id = update.effective_user.id
        if not self._is_authorized(user_id):
            await self._unauthorized_response(update)
            return
            
        await update.message.reply_text(
            f"Hello, {update.effective_user.first_name}! I'm your Raspberry Pi Lossless Audio Player bot.\n\n"
            "You can control me by sending these commands:\n\n"
            "/help - Show this help message\n"
            "/play - Resume playback\n"
            "/pause - Pause playback\n"
            "/stop - Stop playback\n"
            "/next - Skip to next track\n"
            "/prev - Go to previous track\n"
            "/volume [level] - Set volume (0-100)\n"
            "/status - Show current playback status\n"
            "/scan - Scan music library (may take time)\n\n"
            "Or simply send me an album name to search for it!"
        )
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /help command."""
        user_id = update.effective_user.id
        if not self._is_authorized(user_id):
            await self._unauthorized_response(update)
            return
            
        await self.cmd_start(update, context)
    
    async def cmd_play(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /play command."""
        user_id = update.effective_user.id
        if not self._is_authorized(user_id):
            await self._unauthorized_response(update)
            return
            
        if self.audio_player.play():
            await update.message.reply_text("▶️ Playback resumed")
        else:
            await update.message.reply_text("❌ Failed to resume playback")
    
    async def cmd_pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /pause command."""
        user_id = update.effective_user.id
        if not self._is_authorized(user_id):
            await self._unauthorized_response(update)
            return
            
        if self.audio_player.pause():
            await update.message.reply_text("⏸ Playback paused")
        else:
            await update.message.reply_text("❌ Failed to pause playback")
    
    async def cmd_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /stop command."""
        user_id = update.effective_user.id
        if not self._is_authorized(user_id):
            await self._unauthorized_response(update)
            return
            
        if self.audio_player.stop():
            await update.message.reply_text("⏹ Playback stopped")
        else:
            await update.message.reply_text("❌ Failed to stop playback")
    
    async def cmd_next(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /next command."""
        user_id = update.effective_user.id
        if not self._is_authorized(user_id):
            await self._unauthorized_response(update)
            return
            
        if self.audio_player.next_track():
            await update.message.reply_text("⏭ Skipped to next track")
        else:
            await update.message.reply_text("❌ Failed to skip track")
    
    async def cmd_prev(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /prev command."""
        user_id = update.effective_user.id
        if not self._is_authorized(user_id):
            await self._unauthorized_response(update)
            return
            
        if self.audio_player.previous_track():
            await update.message.reply_text("⏮ Returned to previous track")
        else:
            await update.message.reply_text("❌ Failed to return to previous track")
    
    async def cmd_volume(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /volume command."""
        user_id = update.effective_user.id
        if not self._is_authorized(user_id):
            await self._unauthorized_response(update)
            return
            
        args = context.args
        if not args:
            status = self.audio_player.get_status()
            if status:
                await update.message.reply_text(f"🔊 Current volume: {status['volume']}%")
            else:
                await update.message.reply_text("❌ Failed to get volume")
            return
            
        try:
            volume = int(args[0])
            if volume < 0 or volume > 100:
                await update.message.reply_text("❌ Volume must be between 0 and 100")
                return
                
            if self.audio_player.set_volume(volume):
                await update.message.reply_text(f"🔊 Volume set to {volume}%")
            else:
                await update.message.reply_text("❌ Failed to set volume")
        except ValueError:
            await update.message.reply_text("❌ Invalid volume level. Please provide a number between 0 and 100.")
    
    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /status command."""
        user_id = update.effective_user.id
        if not self._is_authorized(user_id):
            await self._unauthorized_response(update)
            return
            
        status = self.audio_player.get_status()
        if not status:
            await update.message.reply_text("❌ Failed to get playback status")
            return
            
        state_emoji = {
            "play": "▶️",
            "pause": "⏸",
            "stop": "⏹"
        }.get(status['state'], "❓")
        
        message = f"{state_emoji} *Current Status*\n\n"
        if status['state'] == 'stop':
            message += "No playback in progress"
        else:
            message += f"*Title:* {status['title']}\n"
            message += f"*Artist:* {status['artist']}\n"
            message += f"*Album:* {status['album']}\n"
            message += f"*Position:* {format_time(status['elapsed'])}/{format_time(status['duration'])}\n"
            message += f"*Volume:* {status['volume']}%"
            
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def cmd_scan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /scan command."""
        user_id = update.effective_user.id
        if not self._is_authorized(user_id):
            await self._unauthorized_response(update)
            return
            
        await update.message.reply_text("🔍 Scanning music library. This may take a while...")
        
        # Run scanning in a separate task
        success = self.music_library.scan_library()
        
        if success:
            await update.message.reply_text("✅ Music library scan complete!")
        else:
            await update.message.reply_text("❌ Failed to scan music library")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages as album searches."""
        user_id = update.effective_user.id
        if not self._is_authorized(user_id):
            await self._unauthorized_response(update)
            return
            
        query = update.message.text.strip()
        if not query:
            return
            
        await update.message.reply_text(f"🔍 Searching for albums matching: *{query}*", parse_mode='Markdown')
        
        albums = self.music_library.search_albums(query)
        
        if not albums:
            await update.message.reply_text("❌ No albums found matching your query")
            return
            
        # If only one album found, show it with play button
        if len(albums) == 1:
            album = albums[0]
            keyboard = [
                [InlineKeyboardButton("▶️ Play Album", callback_data=f"play:{album['id']}")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                format_album_info(album),
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            # If multiple albums found, show a list
            message = "🎵 *Albums found:*\n\n"
            keyboard = []
            
            for i, album in enumerate(albums):
                # Add numbered list item
                message += f"{i+1}. *{album['title']}* by {album['artist']}\n"
                # Add button for this album
                keyboard.append([InlineKeyboardButton(
                    f"{i+1}. {album['title']} ({album['artist']})",
                    callback_data=f"album:{album['id']}"
                )])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                message, 
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline keyboards."""
        user_id = update.effective_user.id
        if not self._is_authorized(user_id):
            await update.callback_query.answer("Unauthorized")
            return
            
        query = update.callback_query
        data = query.data
        
        if data.startswith("album:"):
            # Show album details
            album_id = int(data.split(":")[1])
            album = self.music_library.get_album_by_id(album_id)
            
            if not album:
                await query.answer("Album not found")
                return
                
            keyboard = [
                [InlineKeyboardButton("▶️ Play Album", callback_data=f"play:{album_id}")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.edit_text(
                format_album_info(album),
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            await query.answer()
            
        elif data.startswith("play:"):
            # Play the selected album
            album_id = int(data.split(":")[1])
            album = self.music_library.get_album_by_id(album_id)
            
            if not album:
                await query.answer("Album not found")
                return
                
            success = self.audio_player.play_album(album)
            
            if success:
                self.current_album = album
                await query.answer(f"Playing: {album['title']}")
                await query.message.reply_text(f"▶️ Now playing: *{album['title']}* by *{album['artist']}*", parse_mode='Markdown')
            else:
                await query.answer("Failed to play album")
                await query.message.reply_text("❌ Failed to play album")
    
    def _is_authorized(self, user_id):
        """Check if user is authorized to use the bot."""
        # If no authorized users specified, allow everyone
        if not AUTHORIZED_USERS:
            return True
        return user_id in AUTHORIZED_USERS
    
    async def _unauthorized_response(self, update):
        """Send unauthorized response."""
        await update.message.reply_text("❌ You are not authorized to use this bot.")