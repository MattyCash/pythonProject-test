import executor
from aiogram import *
from config import *
from pytube import YouTube
import os
import logging
import sqlite3
import socket
import threading

logging.basicConfig(level=logging.INFO)


class VideoBot:
    def __init__(self, token, host, port):
        self.bot = Bot(token)
        self.dp = Dispatcher(self.bot)
        self.conn = sqlite3.connect('download_status.db')
        self.cursor = self.conn.cursor()

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS download_status (
                url TEXT PRIMARY KEY,
                status TEXT
            )
        ''')
        self.conn.commit()

        # Dictionary to store download status for each link
        self.download_status = {}

        # Socket server configuration
        self.HOST = host
        self.PORT = port

    def start_socket_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.bind((self.HOST, self.PORT))
            server_socket.listen()
            logging.info(f"Socket server listening on {self.HOST}:{self.PORT}")
            while True:
                conn, addr = server_socket.accept()
                with conn:
                    logging.info(f"Connected by {addr}")
                    conn.sendall(b'Hello, client!')

    def start_polling(self):
        socket_thread = threading.Thread(target=self.start_socket_server)
        socket_thread.start()
        executor.start_polling(self.dp)

    async def start_message(self, message: types.Message):
        chat_id = message.chat.id
        await self.bot.send_message(chat_id,
                                    "Привет! Я бот по загрузке видео с YouTube. Отправь мне ссылку на видео, которое ты хочешь скачать.")

    async def text_message(self, message: types.Message):
        chat_id = message.chat.id
        url = message.text
        try:
            yt = YouTube(url)
            if message.text.startswith(('https://www.youtu.be/', 'https://www.youtube.com/')):
                # Update download status
                self.download_status[url] = "Downloading"

                await self.bot.send_message(chat_id, f"*Начинаю загрузку видео* : {yt.title}\n"
                                                     f"*С канала* : [{yt.author}]({yt.channel_url})",
                                            parse_mode="Markdown")
                await self.download_youtube_video(url, message)
                # If download_youtube_video completes successfully, update download status
                self.download_status[url] = "Downloaded"
                # Save the links and their status to the database
                self.save_download_status_to_database()
                # Save the links and their status to a file
                self.save_download_status_to_file()
        except Exception as e:
            logging.error(f"An error occurred: {e}")
            # Update download status in case of an error
            self.download_status[url] = "Error"
            await self.bot.send_message(chat_id,
                                        "Произошла ошибка при обработке вашего запроса. Убедитесь, что вы отправили "
                                        "правильную ссылку на видео и попробуйте еще раз.")
            # Save the links and their status to the database
            self.save_download_status_to_database()
            # Save the links and their status to a file
            self.save_download_status_to_file()

    async def download_youtube_video(self, url, message):
        try:
            yt = YouTube(url)
            stream = yt.streams.filter(progressive=True, file_extension='mp4')
            video_path = f"{message.chat.id}/{message.chat.id}_{yt.title}"
            stream.get_highest_resolution().download(f'{message.chat.id}', f'{message.chat.id}_{yt.title}')

            # Check if the file was downloaded successfully
            if os.path.exists(video_path):
                with open(video_path, 'rb') as Video:
                    await self.bot.send_video(message.chat.id, Video, caption="*Ваше видео загружено *",
                                              parse_mode="Markdown")
                    os.remove(video_path)
            else:
                logging.error(f"Failed to download video from URL: {url}")
                raise Exception("Failed to download video")
        except Exception as e:
            logging.error(
                f"An error occurred during video download: {e}")
            raise  # Override the exception so it can be handled at the top

    def save_download_status_to_database(self):
        for url, status in self.download_status.items():
            self.cursor.execute('''
                INSERT OR REPLACE INTO download_status (url, status) VALUES (?, ?)
            ''', (url, status))
            self.conn.commit()

    def save_download_status_to_file(self):
        self.cursor.execute('SELECT * FROM download_status')
        data = self.cursor.fetchall()
        with open('download_status.txt', 'w') as file:
            for row in data:
                file.write(f"{row[0]}:{row[1]}\n")
