# Radio Kappa

A simple music bot for your Discord server.


### Requirements:

Bot was tested only on Windows 10 x64 and Windows 8 Server x64.

- Python 3.4 or above

## Installation

1. Download and unpackage or clone the repository in a desired folder.
2. Install Python 3.4 and add the Python directory and the "scripts" subdirectory to the path environment variable.
3. Install pip for Python if not already included.
4. Download required libraries with `pip install -r requirements.txt`
5. Download the latest [ffmpeg codec](https://ffmpeg.zeranoe.com/builds/) and place the three files (ffmpeg.exe, ffplay.exe and ffprobe.exe) in the directory with with the other Radio Kappa files.
6. Set your bot token and the desired channel id's in the `settings.ini`
7. To start the bot, double click `run.bat`


## Configuration

Adjust the values in `settings.ini` to your needs. (To see discord channel and user id's you need to enable the developer mode on discord)

## Usage

__**For everyone available commands:**__

**!play** \<youtube link or song name>      -    Adds your song to the playlist

**!song**                                                            -    Shows information about the currently playing song

**!queue**                                                         -    Shows a list with all queued songs

**!skip**                                                             -    Skips the current song (You can only use this command if the song currently playing was requested by you)*(Mods have full acccess to this command)*

**!remove**                                                      -    Removes the last added song by you. (You can execute this multiple times)

**!removeall**                                                  -    Removes all your songs in the queue.                      



__**Commands only available to mods:**__

**!remove** \<user mention>                        -    Removes the last song that was requested by the mentioned user. (You can execute this multiple times)

**!removeall** \<user mention>                    -    Removes all songs that were requested by the mentioned user

**!autoremove** \<true or false>                  -    Enables/Disables the auto removing of the bots messages after some time

**!clearqueue**                                                -    Removes all songs from the queue

**!restart**                                                        -    Restart the bot



## Contributing

1. Fork it!
2. Create your feature branch: `git checkout -b my-new-feature`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin my-new-feature`
5. Submit a pull request :D
