import executor
from aiogram import *
from config import *
from pytube import YouTube
import os
import logging
import sqlite3

# Настроим логирование
logging.basicConfig(level=logging.INFO)  # Устанавливаем уровень логирования

bot = Bot(TOKEN)
dp = Dispatcher(bot)

# Подключение к базе данных SQLite
conn = sqlite3.connect('download_status.db')
cursor = conn.cursor()

# Создание таблицы для хранения статусов загрузки, если ее нет
cursor.execute('''
    CREATE TABLE IF NOT EXISTS download_status (
        url TEXT PRIMARY KEY,
        status TEXT
    )
''')
conn.commit()

# Dictionary to store download status for each link
download_status = {}


@dp.message_handler(commands=['start'])
async def start_message(message: types.Message):
    chat_id = message.chat.id
    await bot.send_message(chat_id,
                           "Привет! Я бот по загрузке видео с YouTube. Отправь мне ссылку на видео, которое ты хочешь скачать.")


@dp.message_handler()
async def text_message(message: types.Message):
    chat_id = message.chat.id
    url = message.text
    try:
        yt = YouTube(url)
        if message.text.startswith(('https://www.youtu.be/', 'https://www.youtube.com/')):
            # Update download status
            download_status[url] = "Downloading"

            await bot.send_message(chat_id, f"*Начинаю загрузку видео* : {yt.title}\n"
                                            f"*С канала* : [{yt.author}]({yt.channel_url})", parse_mode="Markdown")
            await download_youtube_video(url, message, bot)
            # Update download status
            download_status[url] = "Downloaded"
            # Save the links and their status to the database
            save_download_status_to_database()
            # Save the links and their status to a file
            save_download_status_to_file()
    except Exception as e:
        logging.error(f"An error occurred: {e}")  # Используем logging.error для записи ошибки в лог
        # Update download status in case of an error
        download_status[url] = "Error"
        await bot.send_message(chat_id, "Произошла ошибка при обработке вашего запроса. Убедитесь, что вы отправили "
                                        "правильную ссылку на видео и попробуйте еще раз.")
        # Save the links and their status to the database
        save_download_status_to_database()
        # Save the links and their status to a file
        save_download_status_to_file()


async def download_youtube_video(url, message, bot):
    try:
        yt = YouTube(url)
        stream = yt.streams.filter(progressive=True, file_extension='mp4')
        stream.get_highest_resolution().download(f'{message.chat.id}', f'{message.chat.id}_{yt.title}')
        with open(f"{message.chat.id}/{message.chat.id}_{yt.title}", 'rb') as Video:
            await bot.send_video(message.chat.id, Video, caption="*Ваше видео загружено *", parse_mode="Markdown")
            os.remove(f"{message.chat.id}/{message.chat.id}_{yt.title}")
    except Exception as e:
        logging.error(f"An error occurred during video download: {e}")  # Используем logging.error для записи ошибки в лог
        await bot.send_message(message.chat.id, "Произошла ошибка при загрузке видео. Пожалуйста, попробуйте еще раз.")


def save_download_status_to_database():
    for url, status in download_status.items():
        cursor.execute('''
            INSERT OR REPLACE INTO download_status (url, status) VALUES (?, ?)
        ''', (url, status))
        conn.commit()


def save_download_status_to_file():
    cursor.execute('SELECT * FROM download_status')
    data = cursor.fetchall()
    with open('download_status.txt', 'w') as file:
        for row in data:
            file.write(f"{row[0]}:{row[1]}\n")


if __name__ == '__main__':
    executor.start_polling(dp)
