from video_bot import VideoBot
from bot_manager import BotManager
from config import TOKEN

if __name__ == '__main__':
    bot_instance = VideoBot(TOKEN, '127.0.0.1', 12345)
    bot_manager = BotManager(bot_instance)
    bot_manager.run_bot()
