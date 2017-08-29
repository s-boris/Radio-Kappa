import time
import os

from utils import load_queue_file, update_queue_file
from utils import downloadSong


class Downloader(object):
    def __init__(self):
        self.is_downloading = False
        self.is_running = True
        print("Downloader waiting...")

    def run(self):
        while self.is_running:
            playlist = load_queue_file()
            for index, song in enumerate(playlist):
                if not song.file:
                    if os.path.isfile("cache/audio/" + song.id + ".mp3"):
                        print(song.id + " is already cached cached.")
                        playlist[index].file = os.path.dirname(os.path.abspath(__file__)) + "\\cache\\audio\\" + song.id + ".mp3"
                    else:
                        print('Downloading ' + song.url)
                        downloadSong(song.url)
                        if os.path.isfile(song.id):
                            os.rename(song.id, 'cache/audio/' + song.id + '.mp3')
                            playlist[index].file = os.path.dirname(os.path.abspath(__file__)) + "\\cache\\audio\\" + song.id + ".mp3"
                        else:
                            print("Downloaded file not found!")
                    update_queue_file(playlist)
            time.sleep(1)


Downloader().run()
