class BotManager:
    def __init__(self, bot_instance):
        self.bot_instance = bot_instance

    def run_bot(self):
        self.bot_instance.dp.message_handler(commands=['start'])(self.bot_instance.start_message)
        self.bot_instance.dp.message_handler()(self.bot_instance.text_message)
        self.bot_instance.start_polling()
