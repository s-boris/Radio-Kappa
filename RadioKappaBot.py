import discord
import asyncio
import urllib.request
import urllib.parse
import re
import YT_Downloader
import threading
import time
import os
import pickle
import configparser

autoDelMsg = False
client = discord.Client()
playlist = []
voiceClient = None
nowPlaying = None
ytPlayer = None
ytUrlPattern = re.compile("^http(s)?:\/\/(?:www\.)?youtube.com\/watch\?(?=.*v=\w+)(?:\S+)?$")
PIK = "queue.dat"
skipping = False
finishingSing = False

config = configparser.ConfigParser()
config.read('settings.ini')
loginToken = config['Login']['Token']
voiceChannelID = config['Autojoin']['Voice_Channel_ID']

with open('FILE.INI', 'w') as configfile:    # save
    config.write(configfile)


if not discord.opus.is_loaded():
    discord.opus.load_opus('opus')



class Song:
    def __init__(self, title, id, url, duration, location, requester):
        self.title = title
        self.id = id
        self.url = url
        self.duration = duration
        self.location = location
        self.requester = requester


class YTPlayer(object):
    """ Threading example class
    The run() method will be started and it will run in the background
    until the application exits.
    """

    mediaPlayer = None

    def __init__(self, interval=1):
        """ Constructor
        :type interval: int
        :param interval: Check interval, in seconds
        """
        self.interval = interval

        thread = threading.Thread(target=self.run, args=())
        thread.daemon = True  # Daemonize thread
        thread.start()  # Start the execution

    def song_finished(self):
        global nowPlaying
        global skipping
        global finishingSing
        if not finishingSing:
            finishingSing = True
            if not skipping:
                YTPlayer.mediaPlayer.stop()
                print('song finished')
                if not self.file_needed(playlist[0].location):
                    if os.path.exists(playlist[0].location):
                        fileDeleted = False
                        while not fileDeleted:
                            fileDeleted = self.remove_file(playlist[0].location)
                            time.sleep(3)
                del playlist[0]
                nowPlaying = None
                self.storeQueueFile()
            finishingSing = False

    def skip(self):
        global nowPlaying
        global skipping
        skipping = True
        YTPlayer.mediaPlayer.stop()
        print('skipping song')
        if not self.file_needed(playlist[0].location):
            if os.path.exists(playlist[0].location):
                fileDeleted = False
                while not fileDeleted:
                    fileDeleted = self.remove_file(playlist[0].location)
                    time.sleep(3)

        del playlist[0]
        nowPlaying = None
        self.storeQueueFile()
        skipping = False

    def file_needed(self, lookingFor):
        found = False
        for index, song in enumerate(playlist):
            if not index == 0:
                if playlist[index].location == lookingFor:
                    found = True
        return found

    def remove_file(self, location):
        try:
            os.remove(location)
            return True
        except OSError:
            print("Could not delete, retrying...")
            return False

    def storeQueueFile(self):
        with open(PIK, "wb") as f:
            pickle.dump(playlist, f)

    def run(self):
        global nowPlaying
        """ Method that runs forever """
        while True:
            if playlist:
                if playlist[0]:
                    if playlist[0].location:
                        if voiceClient:
                            if not nowPlaying:
                                YTPlayer.mediaPlayer = voiceClient.create_ffmpeg_player(playlist[0].location,
                                                                                        after=self.song_finished)
                                YTPlayer.mediaPlayer.volume = 0.2
                                YTPlayer.mediaPlayer.start()
                                nowPlaying = playlist[0].id
                                self.storeQueueFile()

                        else:
                            print('Ready to play, but voice client not ready')
                    else:
                        print('Downloading song, please wait...')
                else:
                    print('Playlist is not empty but there is no position 1 song - you fucked up.')
            time.sleep(self.interval)


class PlaylistDownloader(object):
    """ Threading example class
    The run() method will be started and it will run in the background
    until the application exits.
    """

    def __init__(self, interval=1):
        """ Constructor
        :type interval: int
        :param interval: Check interval, in seconds
        """
        self.interval = interval

        thread = threading.Thread(target=self.run, args=())
        thread.daemon = True  # Daemonize thread
        thread.start()  # Start the execution

    def run(self):
        global playlist
        """ Method that runs forever """
        while True:
            for index, song in enumerate(playlist):
                if not song.location:
                    if song.url:
                        if os.path.isfile("cache/audio/" + song.id + ".mp3"):
                            print(song.id + " is already downloaded")
                        else:
                            print('Started download of: ' + song.url)
                            YT_Downloader.downloadSong(song.url)
                            os.rename(song.id, 'cache/audio/' + song.id + '.mp3')
                        playlist[index].location = os.path.dirname(
                            os.path.abspath(__file__)) + "\\cache\\audio\\" + song.id + ".mp3"
            time.sleep(self.interval)


def getNowPlayingMessage():
    sMsg = "Playing Now:\n\n```No song playing right now.```"
    if playlist:
        m, s = divmod(playlist[0].duration, 60)
        h, m = divmod(m, 60)
        durationString = ("\nDuration: %d:%02d:%02d" % (h, m, s)) if h else ("\nDuration: %02d:%02d" % (m, s))
        sMsg = "Playing Now:\n\n```" + playlist[0].title + durationString + "\nRequested by: " + \
               playlist[0].requester.display_name + "\n```\n" + \
               playlist[0].url + "\n\n"
    return sMsg


def getQueueMessage():
    qMsg = "\n\nUpcoming Songs:\n\n```Queue is empty.```"
    if playlist:
        if len(playlist) > 1:
            qMsg = "\n\nUpcoming Songs:\n\n```"
            for index, song in enumerate(playlist):
                if not index == 0:
                    m, s = divmod(playlist[index].duration, 60)
                    h, m = divmod(m, 60)
                    durationString = ("%d:%02d:%02d" % (h, m, s)) if h else ("%02d:%02d" % (m, s))
                    qMsg += str(index) + ". " + song.title + " (" + durationString + ")     Requested by: " + song.requester.display_name + "\n"
            qMsg += "\n```"
    return qMsg


@client.event
async def on_ready():
    global voiceClient
    global ytPlayer
    global playlist
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')
    vChannel = client.get_channel(voiceChannelID)
    voiceClient = await client.join_voice_channel(vChannel)
    if os.path.isfile(PIK):
        with open(PIK, "rb") as f:
            playlist = pickle.load(f)
            print('Restored old queue')
    else:
        print('No old queue data found')
    ytPlayer = YTPlayer()
    PlaylistDownloader()


@client.event
async def on_message(message):
    global playlist
    global ytPlayer
    global ytUrlPattern
    global autoDelMsg

    if message.content.startswith('!play'):
        songSearch = message.content.split("!play ", 1)[1]
        songUrl = None

        if not ytUrlPattern.match(songSearch):
            query_string = urllib.parse.urlencode({"search_query": songSearch})
            html_content = urllib.request.urlopen("http://www.youtube.com/results?" + query_string)
            search_results = re.findall(r'href=\"\/watch\?v=(.{11})', html_content.read().decode())
            if search_results:
                songUrl = "http://www.youtube.com/watch?v=" + search_results[0]
        else:
            songUrl = songSearch

        if songUrl:
            video_id, video_title, video_duration = YT_Downloader.getSongInformation(songUrl)
            foundSong = Song(video_title, video_id, songUrl, video_duration, "", message.author)
            playlist.append(foundSong)

            m, s = divmod(video_duration, 60)
            h, m = divmod(m, 60)
            durationString = ("\nDuration: %d:%02d:%02d" % (h, m, s)) if h else (
                "\nDuration: %02d:%02d" % (m, s))
            tmp = await client.send_message(message.channel,
                                            message.author.mention + ' The following song was added to the queue:\n\n```"' +
                                            video_title + '"' + durationString + "\n```\n" + songUrl + "\n\n")
            if autoDelMsg:
                await asyncio.sleep(10)
                await client.delete_message(tmp)
        else:
            tmp = await client.send_message(message.channel, message.author.mention + " Sorry, song not found")
            if autoDelMsg:
                await asyncio.sleep(5)
                await client.delete_message(tmp)


    elif message.content.startswith('!queue'):
        if playlist:
            sMsg = getNowPlayingMessage()
            qMsg = getQueueMessage()
            tmp = await client.send_message(message.channel, sMsg + qMsg)
        else:
            tmp = await client.send_message(message.channel, "Queue is empty.")
        if autoDelMsg:
            await asyncio.sleep(15)
            await client.delete_message(tmp)


    elif message.content.startswith('!skip'):
        if playlist:
            if playlist[0].requester.id == message.author.id or any(r.id == '117296318052958214' for r in message.author.roles) or message.author.id == '95174017710821376':
                ytPlayer.skip()
                tmp = await client.send_message(message.channel, "Skipping...")
            else:
                tmp = await client.send_message(message.channel,
                                                message.author.mention + " You are not allowed to skip the current song.")
        else:
            tmp = await client.send_message(message.channel, "No song playing.")
        if autoDelMsg:
            await asyncio.sleep(3)
            await client.delete_message(tmp)

    elif message.content.startswith('!clearqueue'):
        if playlist:
            if any(r.name.lower() == "mods" for r in message.author.roles) or message.author.id == '95174017710821376':
                del playlist[1:]
                YTPlayer.storeQueueFile(ytPlayer)
                tmp = await client.send_message(message.channel, "Queue cleared!")
            else:
                tmp = await client.send_message(message.channel,
                                                message.author.mention + " You are not allowed to use this command.")
        else:
            tmp = await client.send_message(message.channel, "Queue is already empty")
        if autoDelMsg:
            await asyncio.sleep(3)
            await client.delete_message(tmp)


    elif message.content.startswith('!song'):
        sMsg = getNowPlayingMessage()
        tmp = await client.send_message(message.channel, sMsg)
        if autoDelMsg:
            await asyncio.sleep(15)
            await client.delete_message(tmp)

    elif message.content.startswith('!remove'):
        msg = ""
        if len(message.content.split("!remove ", 1)) > 1:
            if message.content.split("!remove ", 1)[1]:
                if any(r.name.lower() == "mods" for r in message.author.roles) or message.author.id == '95174017710821376':
                    userMention = message.content.split("!remove ", 1)[1]
                    if playlist:
                        for index, song in enumerate(playlist):
                            if song.requester.mention == userMention:
                                if not index == 0:
                                    del playlist[index]
                                    msg = 'Removed all songs from ' + userMention + ' in queue.'
                else:
                    msg = "You are not allowed to use this command."
        else:
            if playlist:
                removedOne = False
                rPlaylist = list(reversed(playlist))
                for index, song in enumerate(rPlaylist):
                    if not index == len(rPlaylist) - 1:
                        if song.requester.id == message.author.id:
                            if not removedOne:
                                del playlist[index]
                                removedOne = True
                                msg = 'Removed "' + song.title + '" from queue.'

        if msg:
            tmp = await client.send_message(message.channel, msg)
        else:
            tmp = await client.send_message(message.channel,
                                            message.author.mention + "You have no songs in queue right now.")
        if autoDelMsg:
            await asyncio.sleep(15)
            await client.delete_message(tmp)

    elif message.content.startswith('!autoremove'):
        msg = ''
        if len(message.content.split("!autoremove ", 1)) > 1:
            if message.content.split("!autoremove ", 1)[1]:
                if any(r.name.lower() == "mods" for r in message.author.roles) or message.author.id == '95174017710821376':
                    request = message.content.split("!autoremove ", 1)[1]
                    if request.lower() == 'true':
                        autoDelMsg = True
                        msg = 'Enabled bot to automatically remove his own messages after some time'
                    elif request.lower() == 'false':
                        autoDelMsg = False
                        msg = 'Disabled bot to automatically remove his own messages after some time'
                    else:
                        msg = message.author.mention + ' Use either "true" or "false" as option for this command.'
                else:
                    msg = message.author.mention+ " You are not allowed to use this command."

        if msg:
            tmp = await client.send_message(message.channel, msg)
        else:
            tmp = await client.send_message(message.channel,
                                                    message.author.mention + ' Please add a parameter (true or false) for this command.')
            if autoDelMsg:
                await asyncio.sleep(15)
                await client.delete_message(tmp)

client.run(loginToken)
