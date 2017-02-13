import os
import pickle
import threading
import time
import youtube_dl


class Song:
    def __init__(self, id, title, thumbnail, description, duration, views ,likes, dislikes, playlist, uploader, url, source, requester=None, file=None):
        self.id = id
        self.title = title
        self.thumbnail = thumbnail
        self.description = description
        self.duration = duration
        ##Create duration string
        m, s = divmod(duration, 60)
        h, m = divmod(m, 60)
        duration_string = ("%d:%02d:%02d" % (h, m, s)) if h else ("%02d:%02d" % (m, s))
        self.duration_string = duration_string
        ##-----------
        self.views = views
        self.likes = likes
        self.dislikes = dislikes
        self.playlist = playlist
        self.requester = requester
        self.uploader = uploader
        self.url = url
        self.source = source
        self.file = file

    def set_requester(self, requester):
        self.requester = requester


##Threaded Player
class Player(object):
    def __init__(self, voice_client):
        self.voice_client = voice_client
        self.media_player = None
        self.is_playing = False
        self.playlist = []
        self.timeout = 0

        ##start this player class as a new thread
        thread = threading.Thread(target=self.run, args=())
        thread.daemon = True  # Daemonize thread
        thread.start()  # Start the execution

    def play(self):
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
                    ##Wait max 30sec for the download, then skip it
                    if self.timeout > 30:
                        print("Skipping song, took too long to download...")
                        self.timeout = 0
                        self.on_song_finished()
                    else:
                        print('\nWaiting for song to download... ' + str(self.timeout))
                        self.timeout += 1
            else:
                print("Voice client not ready yet")

    def on_song_finished(self):
        print('Song finished')
        if not self.file_needed(self.playlist[0].file):
            self.remove_file(self.playlist[0].file)
        del self.playlist[0]
        self.is_playing = False
        self.update_queue_file()
        self.play()

    def skip(self):
        print('Skipping song')
        self.media_player.stop()
        ##on_song_finished() will be automatically called which will start the next song

    def queue(self, song):
        self.playlist.append(song)
        self.update_queue_file()

    def clear_queue(self):
        del self.playlist[1:]
        self.update_queue_file()

    def remove(self, index):
        del self.playlist[index]

    def file_needed(self, file):
        found = False
        for index, song in enumerate(self.playlist):
            if not index == 0:
                if self.playlist[index].file == file:
                    found = True
        return found

    def remove_file(self, file):
        if file:
            if os.path.exists(file):
                retry = True
                tries = 0
                while retry:
                    time.sleep(2)
                    try:
                        os.remove(file)
                        retry = False
                    except OSError:
                        print("Could not delete, retrying...")
                        retry = True
                    tries += 1
                    if tries > 3:
                        retry = False
                        print('File: "' + file + '" could not be deleted. Another program is probably accessing it.')

    def update_queue_file(self):
        with open("queue.dat", "wb") as f:
            pickle.dump(self.playlist, f)

    def load_queue_file(self):
        ##check for queue file
        if os.path.isfile("queue.dat"):
            with open("queue.dat", "rb") as f:
                self.playlist = pickle.load(f)
                print('Restored old queue from file.')
        else:
            print('No old queue data found, starting with new queue.')

    def get_playlist(self):
        return self.playlist

    def run(self):
        while True:
            self.play()
            time.sleep(1)


##Threaded Downloader
class Downloader(object):
    def __init__(self, player):
        self.player = player

        thread = threading.Thread(target=self.run, args=())
        thread.daemon = True  # Daemonize thread
        thread.start()  # Start the execution

    def run(self):
        playlist = self.player.get_playlist()
        while True:
            for index, song in enumerate(playlist):
                if not song.file:
                    if os.path.isfile("cache/audio/" + song.id + ".mp3"):
                        print(song.id + " is already cached.")
                    else:
                        print('Started download of: ' + song.url)
                        downloadSong(song.url)
                        os.rename(song.id, 'cache/audio/' + song.id + '.mp3')
                    if len(playlist) > index:
                        playlist[index].file = os.path.dirname(
                            os.path.abspath(__file__)) + "\\cache\\audio\\" + song.id + ".mp3"
                    else:
                        print('Song index not found. Song deleted or skipped?')
            time.sleep(1)


##YT downloader stuff
##---------------------------------
class MyLogger(object):
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
    'logger': MyLogger(),
    'progress_hooks': [my_hook],
}


def fetch_song(url):
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, False)
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


def downloadSong(url):
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
