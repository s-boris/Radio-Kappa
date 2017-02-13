import asyncio
import configparser
import re
import sys
import urllib.parse
import urllib.request

import discord
from discord.ext import commands

from utils import *

##Read settings
config = configparser.ConfigParser()
config.read('settings.ini')

login_token = config['Login']['Token']
voice_channel_id = config['Autojoin']['Voice_Channel_ID']
text_channel_id = config['Autojoin']['Text_Channel_ID']
moderator_roles = config['Roles']['Moderator_Rolenames'].split(',')
owner_id = config['Roles']['Owner_ID']
max_duration = int(config['Settings']['Max_Song_Duration'])

##Initialize opus and discord
if not discord.opus.is_loaded():
    discord.opus.load_opus('opus')

##Initialize global variables
voice_client = None
text_channel = None
player = None
downloader = None
q_file = "queue.dat"
yt_url_pattern = re.compile("^http(s)?:/\/(?:www\.)?youtube.com\/watch\?(?=.*v=\w+)(?:\S+)?$")
yt_color = 0xc4302b
yt_icon = "https://www.youtube.com/yt/brand/media/image/YouTube-icon-full_color.png"

##Configure the bot
description = '''Just a music bot.'''
bot = commands.Bot(command_prefix='!', description=description)


@bot.event
async def on_ready():
    global voice_client
    global player
    global downloader
    global text_channel

    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

    ##get channels
    v_channel = bot.get_channel(voice_channel_id)
    text_channel = bot.get_channel(text_channel_id)
    if not v_channel:
        print("No voice channel with that ID found!")
    if not text_channel:
        print("No text channel with that ID found!")
    voice_client = await bot.join_voice_channel(v_channel)

    ##create a new downloader and player
    player = Player(voice_client=voice_client)
    player.load_queue_file()
    downloader = Downloader(player=player)


@bot.command(pass_context=True, no_pm=True, help="Add a song to the queue. Either the song name or the youtube link.")
async def play(ctx, *, search_term: str):
    if ctx.message.channel.id == text_channel_id:
        song_url = None

        ##Send typing status for max 10s, which should be enough to fetch the song data
        await bot.send_typing(ctx.message.channel)

        ##If its a youtube link, search in youtube and get the link of the best match
        if yt_url_pattern.match(search_term):
            song_url = search_term
        else:
            query_string = urllib.parse.urlencode({"search_query": search_term})
            html_content = urllib.request.urlopen("http://www.youtube.com/results?" + query_string)
            search_results = re.findall(r'href=\"\/watch\?v=(.{11})', html_content.read().decode())
            if search_results:
                song_url = "http://www.youtube.com/watch?v=" + search_results[0]
            else:
                await bot.say(ctx.message.author.mention + " sorry, couldn't find this song on youtube :( Try to give me the link.")

        if song_url:
            ##Get all needed information from the song url
            try:
                song = fetch_song(song_url)
            except:
                await bot.say(ctx.message.author.mention + " couldn't find a video with this link :(")
                return
            song.set_requester(ctx.message.author)

            ##Create song embed
            em = get_song_embed(song)

            ##Reject song if it's too long
            if song.duration > max_duration:
                await bot.say(
                    ctx.message.author.mention + ' I can\'t add this song to the queue. The maximum duration of a song is 15:00. Please try to add a shorter video.',
                    embed=em)
                return
            else:
                player.queue(song)
                await bot.say(ctx.message.author.mention + ' your song was added to the queue!', embed=em)
        else:
            await bot.say(ctx.message.author.mention + " sorry, couldn't find a matching song.\nTry to call !play with your desired youtube link.")
    else:
        return


@bot.command(pass_context=True, no_pm=True, help="Shows the current queue.")
async def queue(ctx):
    if ctx.message.channel.id == text_channel_id:
        ##Send typing status for max 10s
        await bot.send_typing(ctx.message.channel)

        if player and player.get_playlist():
            em = get_queue_embed(player.get_playlist())
            await bot.say("Here's the current queue: ", embed=em)
        else:
            await bot.say(ctx.message.author.mention + " Nothing is playing right now.")


@bot.command(pass_context=True, no_pm=True, help="Skip the current song.")
async def skip(ctx):
    if ctx.message.channel.id == text_channel_id:
        ##Send typing status for max 10s
        await bot.send_typing(ctx.message.channel)

        if player.get_playlist() and len(player.get_playlist()) > 0:
            if ctx.message.author.id == player.get_playlist()[0].requester.id or has_mod_access(ctx.message.author):
                player.skip()
                await bot.say("Song was skipped by " + ctx.message.author.mention)
            else:
                await bot.say(ctx.message.author.mention + " only the requester can skip this song.")
        else:
            await bot.say(ctx.message.author.mention + " nothing is playing right now.")


@bot.command(pass_context=True, no_pm=True, help="Remove all queued songs (mod only).")
async def clearqueue(ctx):
    if ctx.message.channel.id == text_channel_id:
        ##Send typing status for max 10s
        await bot.send_typing(ctx.message.channel)

        if has_mod_access(ctx.message.author):
            player.clear_queue()
            player.update_queue_file()

            await bot.say(ctx.message.author.mention + " the queue was wiped!")


@bot.command(pass_context=True, no_pm=True, help="Show the currently playing song.")
async def song(ctx):
    if ctx.message.channel.id == text_channel_id:
        ##Send typing status for max 10s
        await bot.send_typing(ctx.message.channel)

        if player.get_playlist() and len(player.get_playlist()) > 0:
            playlist = player.get_playlist()
            em = get_song_embed(playlist[0])
            await bot.say(
                ctx.message.author.mention + " this song was requested by " + playlist[0].requester.display_name + " and is playing right now",
                embed=em)
        else:
            await bot.say(ctx.message.author.mention + " nothing is playing right now")


@bot.command(pass_context=True, no_pm=True, help="Restart the music bot (mod only).")
async def restart(ctx):
    if ctx.message.channel.id == text_channel_id:
        if has_mod_access(ctx.message.message.author):
            await bot.say("Restarting, please wait...")
            await voice_client.disconnect()
            await bot.close()
            sys.exit()


@bot.command(pass_context=True, no_pm=True, help="Remove all queued songs from the mentioned user/yourself.")
async def removeall(ctx):
    if ctx.message.channel.id == text_channel_id:
        ##Send typing status for max 10s
        await bot.send_typing(ctx.message.channel)

        msg = ""
        if len(ctx.message.mentions) == 1:
            user_mention = ctx.message.mentions[0]
            if ctx.message.author.id == user_mention.id or has_mod_access(ctx.message.author):
                if player.get_playlist() and len(player.get_playlist()) > 1:
                    for index, song in enumerate(player.get_playlist()):
                        if song.requester.id == user_mention.id:
                            if not index == 0:
                                player.remove(index)
                                msg = 'Removed all songs requested by ' + user_mention.mention + ' from the queue.'
                    if not msg:
                        msg = ctx.message.author.mention + ' there are no songs from ' + user_mention.mention + ' in the queue.'
                else:
                    msg = ctx.message.author.mention + "the queue is empty, nothing to remove."
            else:
                msg = ctx.message.author.mention + " you can't remove songs requested by other people."
        ##If command is without mention
        else:
            msg = ctx.message.author.mention + " please mention one person to execute this command."
        await bot.say(msg)


@bot.command(pass_context=True, no_pm=True, help="Remove the last added song from the mentioned user/yourself.")
async def remove(ctx):
    if ctx.message.channel.id == text_channel_id:
        ##Send typing status for max 10s
        await bot.send_typing(ctx.message.channel)

        msg = ""
        ##If command is !remove <mention>
        if len(ctx.message.mentions) > 0:
            user_mention = ctx.message.mentions[0]
            if ctx.message.author.id == user_mention.id or has_mod_access(ctx.message.author):
                if player.get_playlist() and len(player.get_playlist()) > 1:
                    removed_one = False
                    r_playlist = list(reversed(player.get_playlist()))
                    for index, song in enumerate(r_playlist):
                        ##the last song is the first, so the one currently playing
                        if not index == len(r_playlist) - 1:
                            if song.requester.id == user_mention.id:
                                if not removed_one:
                                    player.remove(len(player.get_playlist())-index)
                                    removed_one = True
                                    msg = 'Removed "' + song.title + '" requested by: ' + song.requester.mention + ' from the queue.'
                    if not msg:
                        msg = ctx.message.author.mention + " Could not find any songs from " + user_mention.mention + " in the queue."
                else:
                    msg = ctx.message.author.mention + " Queue is empty, nothing to remove."
            else:
                msg = ctx.message.author.mention + " You are not allowed to use this command."
        ##If command is without mention
        else:
            if player.get_playlist() and len(player.get_playlist()) > 1:
                removed_one = False
                r_playlist = list(reversed(player.get_playlist()))
                for index, song in enumerate(r_playlist):
                    if not index == len(r_playlist) - 1:
                        if song.requester.id == ctx.message.author.id:
                            if not removed_one:
                                player.remove(len(player.get_playlist()) - (index+1))
                                removed_one = True
                                msg = 'Removed "' + song.title + '" requested by ' + song.requester.mention + ' from the queue.'
                if not msg:
                    msg = ctx.message.author.mention + " Could not find any song that was requested by you in queue."
            else:
                msg = ctx.message.author.mention + " Queue is empty, nothing to remove."
        await bot.say(msg)


def get_song_embed(song):
    if len(song.description) > 200:
        em = discord.Embed(title=" ", description=song.description[:200] + "...", colour=yt_color, url=song.url)
    else:
        em = discord.Embed(title=" ", description=song.description, colour=yt_color, url=song.url)
    em.set_author(name=song.title, url=song.url)
    em.add_field(name="Duration", value=song.duration_string, inline=True)
    em.set_thumbnail(url=song.thumbnail)
    em.add_field(name="Views", value=song.views, inline=True)
    em.add_field(name="Likes", value=song.likes, inline=True)
    em.add_field(name="Dislikes", value=song.dislikes, inline=True)
    em.set_footer(text=song.source, icon_url=yt_icon)
    return em


def get_queue_embed(playlist):
    em = discord.Embed(title=playlist[0].title,
                       description="*Duration: " + playlist[0].duration_string + " | Requested by " + playlist[0].requester.display_name + "*",
                       colour=0x87CEEB,
                       url=playlist[0].url)
    em.set_thumbnail(url=playlist[0].thumbnail)
    em.set_author(name="Playing now:")

    if len(playlist) > 1:
        q_list = ""
        for index, song in enumerate(playlist):
            if index > 0:
                q_list += str(index) + ". " + song.title + " *[" + song.duration_string + " | " + song.requester.display_name + "]*\n\n"
            if index >= 10:
                if len(playlist) > 10:
                    q_list += "*[" + str(len(playlist) - 10) + " more songs...]*"
                break
        em.add_field(name="Queued:", value=q_list, inline=False)
    else:
        em.add_field(name="Queued:", value=" - ", inline=False)
    return em


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


bot.run(login_token)
