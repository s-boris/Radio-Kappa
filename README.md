# Radio Kappa

A simple music bot for your Discord server.


### Requirements:

Bot was tested only on Windows 10 x64 and Windows 8 Server x64.

- Python 3.4 or above

### Installation

1. Download and unpackage or clone the repository in a desired folder.
2. Install Python 3.4 and add the Python directory and the "scripts" subdirectory to the path variable.
3. Install pip for Python
4. Download required libraries by entering: pip install requirements.txt
5. Set your bot token and the desired channel id's in the settings.ini
6. To start the bot: `python kappabot.py`


## Configuration

## Usage

__**For everyone available commands:**__

**!play** <youtube link or song name>     -    Adds your song to the playlist
**!song**                                 -    Shows information about the currently playing song
**!queue**                                -    Shows a list with all queued songs
**!skip**                                 -    Skips the current song (You can only use this command if the song currently playing was requested by you)*(Mods have full acccess to this command)*
**!remove**                               -    Removes the last added song by you. (You can execute this multiple times)
**!removeall**                            -    Removes all your songs in the queue.

__**Commands only available to mods:**__

**!remove** <user mention>                -    Removes the last song that was requested by the mentioned user. (You can execute this multiple times)
**!removeall** <user mention>             -    Removes all songs that were requested by the mentioned user
**!autoremove** <true or false>           -    Enables/Disables the auto removing of the bots messages after some time
**!clearqueue**                           -    Removes all songs from the queue


__**Known issues:**__
- Queue does not show when too many songs are queued
- Bot won't reconnect after losing connection to discord



## Contributing

1. Fork it!
2. Create your feature branch: `git checkout -b my-new-feature`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin my-new-feature`
5. Submit a pull request :D


## License

TODO: Write license