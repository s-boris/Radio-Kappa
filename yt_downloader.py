import youtube_dl

class MyLogger(object):
    def debug(self, msg):
        print(msg)

    def warning(self, msg):
        print(msg)

    def error(self, msg):
        print(msg)


def my_hook(d):
    if d['status'] == 'finished':
        print('Done downloading, converting ...')

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


def getSongInformation(url):
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, False)
        video_title = info_dict.get('title', None)
        video_duration = info_dict.get('duration', None)
        video_id = info_dict.get('display_id', None)
        return video_id, video_title, video_duration


def downloadSong(url):
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
