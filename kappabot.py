import discord
import configparser
import re
import threading
import time
import os
import sys
import pickle
import asyncio
import urllib.request
import urllib.parse
import yt_downloader

Xlate = {

    'a': 'ɐ', 'b': 'q', 'c': 'ɔ', 'd': 'p', 'e': 'ə',
    'f': 'ɟ', 'g': 'ɓ', 'h': 'ɥ', 'i': '!', 'j': 'ɾ',
    'k': 'ʞ', 'l': 'l', 'm': 'ɯ', 'n': 'u', 'o': 'o',
    'p': 'p', 'q': 'q', 'r': 'ɹ', 's': 's', 't': 'ʇ',
    'u': 'n', 'v': 'ʌ', 'w': 'ʍ', 'x': 'x', 'y': 'ʎ',
    'z': 'z',

    'A': '∀', 'B': 'B', 'C': 'Ↄ', 'D': '◖', 'E': 'Ǝ',
    'F': 'Ⅎ', 'G': '⅁', 'H': 'H', 'I': 'I', 'J': 'ſ',
    'K': 'K', 'L': '⅂', 'M': 'W', 'N': 'ᴎ', 'O': 'O',
    'P': 'Ԁ', 'Q': 'Ό', 'R': 'ᴚ', 'S': 'S', 'T': '⊥',
    'U': '∩', 'V': 'ᴧ', 'W': 'M', 'X': 'X', 'Y': '⅄',
    'Z': 'Z',

    '0': '0', '1': '1', '2': '0', '3': 'Ɛ', '4': 'ᔭ',
    '5': '5', '6': '9', '7': 'Ɫ', '8': '8', '9': '0',

    '_': '¯', "'": ',', ',': "'", '\\': '/', '/': '\\',
    '!': '¡', '?': '¿',
}

##Read settings
config = configparser.ConfigParser()
config.read('settings.ini')

login_token = config['Login']['Token']
main_voice_channel_id = config['Autojoin']['Main_Voice_Channel_ID']
main_text_channel_id = config['Autojoin']['Main_Text_Channel_ID']
moderator_roles = config['Roles']['Moderator_Rolenames'].split(',')
owner_id = config['Roles']['Owner_ID']

##Initialize Discord Client
client = discord.Client()
if not discord.opus.is_loaded():
    discord.opus.load_opus('opus')

##Initialize global variables
playlist = []
voice_client = None
main_text_channel = None
player = None
downloader = None
yt_url_pattern = re.compile("^http(s)?:/\/(?:www\.)?youtube.com\/watch\?(?=.*v=\w+)(?:\S+)?$")
q_file = "queue.dat"
auto_del_msg = False


##Song class
class Song:
    def __init__(self, title, id, url, duration, location, requester):
        self.title = title
        self.id = id
        self.url = url
        self.duration = duration
        self.location = location
        self.requester = requester


##Threaded Player
class Player(object):
    media_player = None
    is_playing = False
    timeout = 0

    def __init__(self):
        ##start this player class as a new thread
        thread = threading.Thread(target=self.run, args=())
        thread.daemon = True  # Daemonize thread
        thread.start()  # Start the execution

    def play_next_song(self):
        global playlist
        global voice_client
        global client

        if playlist:
            if voice_client:
                if playlist[0].location:
                    if not self.is_playing:
                        self.media_player = voice_client.create_ffmpeg_player(playlist[0].location,
                                                                              after=self.on_song_finished)
                        self.media_player.volume = 0.3
                        self.timeout = 0
                        self.is_playing = playlist[0]
                        self.media_player.start()
                else:
                    print('\nWaiting for song to download...')
                    self.timeout += 1
            else:
                print("Voice client not ready yet.")

    def on_song_finished(self):
        global playlist

        print('Song finished')
        if not self.file_needed(playlist[0].location):
            self.remove_file(playlist[0].location)
        del playlist[0]
        self.is_playing = False
        self.update_queue_file()
        self.play_next_song()

    def skip(self):
        print('skipping song')
        self.media_player.stop()
        ##on_song_finished() will be automatically called which will start the next song

    def file_needed(self, location):
        global playlist

        found = False
        for index, song in enumerate(playlist):
            if not index == 0:
                if playlist[index].location == location:
                    found = True
        return found

    def remove_file(self, location):
        if os.path.exists(location):
            retry = False
            tries = 0
            while not retry:
                time.sleep(2)
                try:
                    os.remove(location)
                    retry = True
                except OSError:
                    print("Could not delete, retrying...")
                    retry = False
                tries += 1
                if tries > 3:
                    retry = True
                    print('File: "' + location + '" could not be deleted. Another program is probably accessing it.')

    def update_queue_file(self):
        global playlist

        with open(q_file, "wb") as f:
            pickle.dump(playlist, f)

    def run(self):
        global client
        global main_text_channel
        while True:
            if self.timeout > 15:
                client.send_message(main_text_channel, 'Error: skipping "' + playlist[
                    0].title + '"')
                del playlist[0]
                self.is_playing = False
                self.update_queue_file()
                self.play_next_song()
                self.timeout = 0

            self.play_next_song()
            time.sleep(1)


##Threaded Downloader
class Downloader(object):
    def __init__(self):
        thread = threading.Thread(target=self.run, args=())
        thread.daemon = True  # Daemonize thread
        thread.start()  # Start the execution

    def run(self):
        global playlist

        while True:
            for index, song in enumerate(playlist):
                if not song.location:
                    if os.path.isfile("cache/audio/" + song.id + ".mp3"):
                        print(song.id + " is already cached.")
                    else:
                        print('Started download of: ' + song.url)
                        yt_downloader.downloadSong(song.url)
                        os.rename(song.id, 'cache/audio/' + song.id + '.mp3')
                    if len(playlist) > index:
                        playlist[index].location = os.path.dirname(
                            os.path.abspath(__file__)) + "\\cache\\audio\\" + song.id + ".mp3"
                    else:
                        print('Song index not found. Song deleted or skipped?')
            time.sleep(1)


##When discord client has connected, the rest
@client.event
async def on_ready():
    global voice_client
    global player
    global downloader
    global playlist
    global main_text_channel

    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')
    vChannel = client.get_channel(main_voice_channel_id)
    main_text_channel = client.get_channel(main_text_channel_id)
    voice_client = await client.join_voice_channel(vChannel)
    if os.path.isfile(q_file):
        with open(q_file, "rb") as f:
            playlist = pickle.load(f)
            print('Restored old queue from file.')
    else:
        print('No old queue data found, starting with new queue.')
    ##Start a new downloader and player
    downloader = Downloader()
    player = Player()
    await client.send_message(main_text_channel, 'HeyGuys')


@client.event
async def on_message(message):
    global playlist
    global player
    global auto_del_msg

    if message.content.startswith('!play '):
        search_term = message.content.split("!play ", 1)[1]
        song_url = None

        ##If its not a youtube link, search in youtube and get the link of the best match
        if not yt_url_pattern.match(search_term):
            query_string = urllib.parse.urlencode({"search_query": search_term})
            html_content = urllib.request.urlopen("http://www.youtube.com/results?" + query_string)
            search_results = re.findall(r'href=\"\/watch\?v=(.{11})', html_content.read().decode())
            if search_results:
                song_url = "http://www.youtube.com/watch?v=" + search_results[0]
        else:
            song_url = search_term

        if song_url:
            ##Get all needed information from the song url, create a Song object and add it to the queue
            video_id, video_title, video_duration = yt_downloader.getSongInformation(song_url)
            found_song = Song(video_title, video_id, song_url, video_duration, "", message.author)
            m, s = divmod(video_duration, 60)
            h, m = divmod(m, 60)
            duration_string = ("\nDuration: %d:%02d:%02d" % (h, m, s)) if h else (
                "\nDuration: %02d:%02d" % (m, s))
            if video_duration > 900:
                tmp = await client.send_message(message.channel,
                                                message.author.mention + ' I can not add this song to the queue. The maximum duration of a song is 15:00. Please try to add a shorter video.\n\n```"' +
                                                video_title + '"' + duration_string + "\n```\n" + song_url + "\n\n")
            else:
                playlist.append(found_song)
                player.update_queue_file()

                m, s = divmod(video_duration, 60)
                h, m = divmod(m, 60)
                duration_string = ("\nDuration: %d:%02d:%02d" % (h, m, s)) if h else (
                    "\nDuration: %02d:%02d" % (m, s))
                tmp = await client.send_message(message.channel,
                                                message.author.mention + ' The following song was added to the queue:\n\n```"' +
                                                video_title + '"' + duration_string + "\n```\n" + song_url + "\n\n")
            if auto_del_msg:
                await asyncio.sleep(10)
                await client.delete_message(tmp)
        else:
            tmp = await client.send_message(message.channel,
                                            message.author.mention + " Sorry, couldn't find a matching song. FeelsBadMan \nTry to call !play with your desired youtube link.")
            if auto_del_msg:
                await asyncio.sleep(5)
                await client.delete_message(tmp)

    elif message.content.startswith('!queue'):
        sMsg = get_now_playing_message()
        qMsg = get_queue_message()
        qMsg_lines = get_raw_queue_as_string().split('\n')
        qMsgs_list = []
        tmp_list = []

        if playlist:
            if len(qMsg_lines) > 15:
                last_index = 0
                for count, element in enumerate(qMsg_lines, 1):  # Start counting from 1
                    if count % 10 == 0:
                        qMsgs_list.append("```" + "\n".join(qMsg_lines[last_index:count - 1]) + "```")
                        last_index = count
                tmp_list.append(await client.send_message(message.channel, sMsg))
                for qPart in qMsgs_list:
                    tmp_list.append(await client.send_message(message.channel, qPart))

            else:
                tmp = await client.send_message(message.channel, sMsg + qMsg)
        else:
            tmp = await client.send_message(message.channel,
                                            "Queue is empty. And nothing is playing right now. FeelsWeirdMan")

        if auto_del_msg:
            await asyncio.sleep(15)
            if not tmp_list:
                await client.delete_message(tmp)
            else:
                for tPart in tmp_list:
                    await client.delete_message(tPart)

    elif message.content.startswith('!skip'):
        if playlist:
            if playlist[0].requester.id == message.author.id or has_mod_access(message.author):
                player.skip()
                tmp = await client.send_message(message.channel, "Skipping...")
            else:
                tmp = await client.send_message(message.channel,
                                                message.author.mention + " Sorry, you are not allowed to skip the current song.")
        else:
            tmp = await client.send_message(message.channel, "There is no song playing right now.")
        if auto_del_msg:
            await asyncio.sleep(3)
            await client.delete_message(tmp)

    elif message.content.startswith('!clearqueue'):
        if playlist:
            if has_mod_access(message.author):
                del playlist[1:]
                player.update_queue_file()
                tmp = await client.send_message(message.channel, "Queue cleared!")
            else:
                tmp = await client.send_message(message.channel,
                                                message.author.mention + " You are not allowed to use this command.")
        else:
            tmp = await client.send_message(message.channel, "Queue is already empty.")
        if auto_del_msg:
            await asyncio.sleep(3)
            await client.delete_message(tmp)

    elif message.content.startswith('!song'):
        tmp = await client.send_message(message.channel, get_now_playing_message())
        if auto_del_msg:
            await asyncio.sleep(10)
            await client.delete_message(tmp)

    elif message.content.startswith('!removeall'):
        msg = ""
        ##If command is !removeall <mention>
        if len(message.content.split("!removeall ", 1)) > 1:
            if message.content.split("!removeall ", 1)[1]:
                user_mention = message.content.split("!removeall ", 1)[1]
                if message.author.mention == user_mention or has_mod_access(message.author):
                    if playlist:
                        for index, song in enumerate(playlist):
                            if song.requester.mention == user_mention:
                                if not index == 0:
                                    del playlist[index]
                                    msg = 'Removed all songs requested by ' + user_mention + ' from the queue.'
                        if not msg:
                            msg = message.author.mention + ', ' + user_mention + ' has no songs in queue.'
                    else:
                        msg = message.author.mention + " Queue is empty, nothing to remove."
                else:
                    msg = message.author.mention + " You can not remove songs, requested by other people."
        ##If command is without mention
        else:
            if playlist:
                for index, song in enumerate(playlist):
                    if song.requester.mention == message.author.mention:
                        if not index == 0:
                            del playlist[index]
                            msg = message.author.mention + ' Removed all your songs from the queue.'
                if not msg:
                    msg = message.author.mention + ' You have no songs in queue.'
            else:
                msg = message.author.mention + " Queue is empty, nothing to remove."
        tmp = await client.send_message(message.channel, msg)
        if auto_del_msg:
            await asyncio.sleep(15)
            await client.delete_message(tmp)

    elif message.content.startswith('!remove'):
        msg = ""
        ##If command is !remove <mention>
        if len(message.content.split("!remove ", 1)) > 1:
            if message.content.split("!remove ", 1)[1]:
                user_mention = message.content.split("!remove ", 1)[1]
                if message.author.mention == user_mention or has_mod_access(message.author):
                    user_mention = message.content.split("!remove ", 1)[1]
                    if playlist:
                        removed_one = False
                        r_playlist = list(reversed(playlist))
                        for index, song in enumerate(r_playlist):
                            ##the last song is the first, so the one currently playing
                            if not index == len(r_playlist) - 1:
                                if song.requester.mention == user_mention:
                                    if not removed_one:
                                        del r_playlist[index]
                                        removed_one = True
                                        playlist = list(reversed(r_playlist))
                                        msg = 'Removed "' + song.title + '", requested by: ' + song.requester.mention + ' from queue.'
                        if not msg:
                            msg = message.author.mention + " Could not find any songs from " + user_mention + " in the queue."
                    else:
                        msg = message.author.mention + " Queue is empty, nothing to remove."
                else:
                    msg = message.author.mention + " You are not allowed to use this command."
        ##If command is without mention
        else:
            if playlist:
                removed_one = False
                r_playlist = list(reversed(playlist))
                for index, song in enumerate(r_playlist):
                    if not index == len(r_playlist) - 1:
                        if song.requester.id == message.author.id:
                            if not removed_one:
                                del r_playlist[index]
                                removed_one = True
                                playlist = list(reversed(r_playlist))
                                msg = 'Removed "' + song.title + '", requested by: ' + song.requester.mention + ' from queue.'
                if not msg:
                    msg = message.author.mention + " Could not find any song that was requested by you in queue."
            else:
                msg = message.author.mention + " Queue is empty, nothing to remove."
        tmp = await client.send_message(message.channel, msg)
        if auto_del_msg:
            await asyncio.sleep(15)
            await client.delete_message(tmp)

    elif message.content.startswith('!autoremove'):
        msg = ''
        if len(message.content.split("!autoremove ", 1)) > 1:
            if message.content.split("!autoremove ", 1)[1]:
                if has_mod_access(message.author):
                    request = message.content.split("!autoremove ", 1)[1]
                    if request.lower() == 'true':
                        auto_del_msg = True
                        msg = 'Enabled bot to automatically remove his own messages after some time.'
                    elif request.lower() == 'false':
                        auto_del_msg = False
                        msg = 'Disabled bot to automatically remove his own messages after some time.'
                    else:
                        msg = message.author.mention + ' Use either "true" or "false" as option for this command.'
                else:
                    msg = message.author.mention + " You are not allowed to use this command."

        if msg:
            tmp = await client.send_message(message.channel, msg)
        else:
            tmp = await client.send_message(message.channel,
                                            message.author.mention + ' Please add a parameter (true or false) for this command.')
        if auto_del_msg:
            await asyncio.sleep(15)
            await client.delete_message(tmp)

    elif message.content.startswith('!help'):

        tmp = await client.send_message(message.channel, get_help_message())

        if auto_del_msg:
            await asyncio.sleep(30)
            await client.delete_message(tmp)

    elif message.content.startswith('!flip '):

        user_to_flip = message.clean_content.split("!flip ", 1)[1]
        flipped_user = ''.join([Xlate[c] if c in Xlate else c for c in user_to_flip[::-1]])

        tmp = await client.send_message(message.channel, '(╯°□°）╯︵ ' + flipped_user)
        if auto_del_msg:
            await asyncio.sleep(10)
            await client.delete_message(tmp)

    elif message.content.startswith('!restart'):

        if has_mod_access(message.author):
            await client.send_message(message.channel, 'Restarting, please wait...')
            await voice_client.disconnect()
            await client.close()
            sys.exit()

def has_mod_access(user):
    has_access = False
    if user.id == owner_id:
        has_access = True
    else:
        for user_role in moderator_roles:
            for role in user.roles:
                if role.name.lower() == user_role.lower():
                    has_access = True
    return has_access


def get_now_playing_message():
    sMsg = "Playing Now:\n\n```No song playing right now.```"
    if playlist:
        m, s = divmod(playlist[0].duration, 60)
        h, m = divmod(m, 60)
        duration_string = ("\nDuration: %d:%02d:%02d" % (h, m, s)) if h else ("\nDuration: %02d:%02d" % (m, s))
        sMsg = "Playing Now:\n\n```" + playlist[0].title + duration_string + "\nRequested by: " + \
               playlist[0].requester.display_name + "\n```\n" + \
               playlist[0].url + "\n\n"
    return sMsg


def get_raw_queue_as_string():
    qMsg = ""
    if playlist:
        if len(playlist) > 1:
            for index, song in enumerate(playlist):
                if not index == 0:
                    m, s = divmod(playlist[index].duration, 60)
                    h, m = divmod(m, 60)
                    duration_string = ("%d:%02d:%02d" % (h, m, s)) if h else ("%02d:%02d" % (m, s))
                    qMsg += str(
                        index) + ". " + song.title + " (" + duration_string + ")     Requested by: " + song.requester.display_name + "\n"
    return qMsg


def get_queue_message():
    qMsg = "\n\nUpcoming Songs:\n\n```Queue is empty.```"
    if playlist:
        if len(playlist) > 1:
            qMsg = "\n\nUpcoming Songs:\n\n```"
            for index, song in enumerate(playlist):
                if not index == 0:
                    m, s = divmod(playlist[index].duration, 60)
                    h, m = divmod(m, 60)
                    duration_string = ("%d:%02d:%02d" % (h, m, s)) if h else ("%02d:%02d" % (m, s))
                    qMsg += str(
                        index) + ". " + song.title + " (" + duration_string + ")     Requested by: " + song.requester.display_name + "\n"
            qMsg += "\n```"
    return qMsg


def get_help_message():
    hMsg = '''__**For everyone available commands:**__

**!play** <youtube link or song name>      -    Adds your song to the playlist
**!song**                                                            -    Shows information about the currently playing song
**!queue**                                                         -    Shows a list with all queued songs
**!skip**                                                             -    Skips the current song (You can only use this command if the song currently playing was requested by you)*(Mods have full acccess to this command)*
**!remove**                                                      -    Removes the last added song by you. (You can execute this multiple times)
**!removeall**                                                  -    Removes all your songs in the queue.
**!flip <mention>**                                         -    Flip this cuck!

__**Commands only available to mods:**__

**!remove** <user mention>                        -    Removes the last song that was requested by the mentioned user. (You can execute this multiple times)
**!removeall** <user mention>                    -    Removes all songs that were requested by the mentioned user
**!autoremove** <true or false>                  -    Enables/Disables the auto removing of the bots messages after some time
**!clearqueue**                                                -    Removes all songs from the queue
**!clearqueue**                                                -    Removes all songs from the queue
**!restart**                                                        -    Restart the bot

For further information visit me on Github (https://github.com/Neolysion/Radio-Kappa)'''

    return hMsg


client.run(login_token)
