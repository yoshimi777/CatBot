# CatBot
		
You've Cat to be Kitten me.

    

## Getting Started



Do you have a bot account you'd like to use? If yes, get its token and skip ahead.  Otherwise:        
>Go to https://discordapp.com/developers/applications/me and create an app.  Give it a name (CatBot?) and on the next page, click "Create a Bot User".  Click to  reveal the **Token**, copying it to clipboard.  



Is Developer mode on in your Discord account?  If yes, skip ahead, otherwise:
>In Discord, go to your user settings (on bottom left by mute and deafen, looks like a gear or cog) and under "appearance" menu, turn on Developer Mode.  It's on the bottom.


       

### Prerequisites


Must have Python 3.5 or 3.6 (3.7 not supported yet), pip, and a discordapp bot.  
		
Requirements are taken care of via pip, on startup.  You must have write permissions in the bot's directory.  Your configuration file is written on first-run, so have your bot's token and your Discord user ID handy.  

        

### Installing

        

Download or clone repo into a directory you'll have easy access to (your desktop or documents).  

Everything needed for the bot is in the aptly named "bot" folder.
      

Double click ``run.py`` and be prepared to enter your bot's token and your user ID for Discord.  This sets you up as the bot's owner.  Easiest way to get your user ID is right-clicking your name in Discord and clicking "Copy ID".  If you don't see it, you don't have Developer Mode enabled.  Go back to Getting Started.  
		
Same technique for a chat channel, if you choose to add one (this would be a designated channel in a server for A.I.).  You can add more channels later, for different servers.

Your config file, once written, can be modified in bot/cogs/utils, but keep to the format and modify values only.  This file is in .gitignore, and must stay there unless you want to publish your bot's token.

After the initial run, with ``run.py``, you'll be able to start or restart the bot with just a click of a script (catbot.bat).  Or type "catbot" in command prompt.
		
That's it!


### Acknowledgements 


Special thanks to https://github.com/corpnewt/CorpBot.py, https://github.com/Cog-Creators/Red-DiscordBot and https://github.com/Rapptz/discord.py


