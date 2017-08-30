import os
import pickle
import threading
import time

import asyncio
import youtube_dl
from concurrent.futures import ProcessPoolExecutor


# Song model
class Song:
    def __init__(self, id, title, thumbnail, description, duration, views, likes, dislikes, playlist, uploader, url, source, requester=None,
                 file=None):
        self.id = id
        self.title = title
        self.thumbnail = thumbnail
        self.description = description
        self.duration = duration
        # Create duration string
        m, s = divmod(duration, 60)
        h, m = divmod(m, 60)
        duration_string = ("%d:%02d:%02d" % (h, m, s)) if h else ("%02d:%02d" % (m, s))
        self.duration_string = duration_string
        # -----------
        self.views = views
        self.likes = likes
        self.dislikes = dislikes
        self.playlist = playlist
        self.requester = requester
        self.uploader = uploader
        self.url = url
        self.source = source
        self.file = file


# Some file functions
def remove_file(file):
    if file:
        if os.path.exists(file):
            tries = 0
            while tries < 5:
                time.sleep(2)
                tries += 1
                try:
                    os.remove(file)
                    return 1
                except OSError as e:
                    print("Could not delete, retrying... " + e.strerror)


def load_queue_file():
    # check for queue file
    if os.path.isfile("queue.dat"):
        try:
            with open("queue.dat", "rb") as f:
                return pickle.load(f)
        except EOFError:
            print("EOFError: File seems to be empty...")
            return []
    else:
        print('No old queue data found, starting with new queue.')
        return update_queue_file([])


def update_queue_file(playlist):
    with open("queue.dat", "wb") as f:
        pickle.dump(playlist, f)
        return playlist


# The music player
class Player(object):
    def __init__(self, bot, voice_client):
        self.voice_client = voice_client
        self.media_player = None
        self.is_playing = False
        self.timeout = 0
        self.bot = bot
        self.playlist = load_queue_file()

        # start this player class as a new thread
        thread = threading.Thread(target=self.run, args=())
        thread.daemon = True  # Daemonize thread
        thread.start()  # Start the execution

    def play(self):
        self.playlist = self.get_playlist()
        if self.playlist:
            if self.voice_client:
                if self.playlist[0].file:
                    if not self.is_playing:
                        self.media_player = self.voice_client.create_ffmpeg_player(self.playlist[0].file, after=self.on_song_finished)
                        self.media_player.volume = 0.3
                        self.timeout = 0
                        self.is_playing = True
                        self.media_player.start()
                else:
                    # Wait max 30sec for the download, then skip it
                    if self.timeout >= 30:
                        print("Skipping song, took too long to download...")
                        self.timeout = 0
                        self.on_song_finished()
                    else:
                        if self.timeout == 0:
                            print('\nWaiting for song to download... ')
                        self.timeout += 1
            else:
                print("Voice client not ready yet")

    def on_song_finished(self):
        print('Song finished')
        self.playlist = self.get_playlist()
        if not self.file_needed(self.playlist[0].file):
            executor = ProcessPoolExecutor(1)
            del_future = self.bot.loop.run_in_executor(executor, remove_file, self.playlist[0].file)
            del_task = asyncio.ensure_future(del_future)
            asyncio.ensure_future(del_task)
        del self.playlist[0]
        self.is_playing = False
        update_queue_file(self.playlist)
        self.play()

    def skip(self):
        print('Skipping song')
        self.media_player.stop()
        # on_song_finished() will be automatically called which will start the next song

    def queue(self, song):
        self.playlist = self.get_playlist()
        self.playlist.append(song)
        update_queue_file(self.playlist)

    def clear_queue(self):
        self.playlist = self.get_playlist()
        del self.playlist[1:]
        update_queue_file(self.playlist)

    def remove(self, index):
        self.playlist = self.get_playlist()
        to_delete = self.playlist[index].file
        del self.playlist[index]
        update_queue_file(self.playlist)

        executor = ProcessPoolExecutor(1)
        del_future = self.bot.loop.run_in_executor(executor, remove_file, to_delete)
        del_task = asyncio.ensure_future(del_future)
        asyncio.ensure_future(del_task)

    def file_needed(self, file):
        self.playlist = self.get_playlist()
        found = False
        for index, song in enumerate(self.playlist):
            if not index == 0:
                if self.playlist[index].file == file:
                    found = True
        return found

    def get_playlist(self):
        return load_queue_file()

    def run(self):
        while True:
            self.play()
            time.sleep(1)


# YT downloader stuff
# ---------------------------------
class YTDLogger(object):
    def debug(self, msg):
        print(msg)

    def warning(self, msg):
        print(msg)

    def error(self, msg):
        print(msg)


def my_hook(d):
    if d['status'] == 'finished':
        print('Finished downloading, converting ...')


ydl_opts = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'audioformat': "mp3",
    'outtmpl': '%(id)s',
    'logger': YTDLogger(),
    'progress_hooks': [my_hook],
}


def fetch_song(url):
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, False)
        if info_dict:
            song = Song(
                id=info_dict.get('display_id', None),
                title=info_dict.get('title', None),
                thumbnail=info_dict.get('thumbnail', None),
                description=info_dict.get('description', None),
                duration=info_dict.get('duration', None),
                views=info_dict.get('view_count', None),
                likes=info_dict.get('like_count', None),
                dislikes=info_dict.get('dislike_count', None),
                playlist=info_dict.get('playlist', None),
                uploader=info_dict.get('uploader', None),
                url=info_dict.get('webpage_url', None),
                source="youtube.com",
            )
            return song
        else:
            return None


def downloadSong(url):
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
