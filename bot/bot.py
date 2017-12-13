import asyncio
import datetime
import json
from datetime import datetime
import os
import discord
from discord.ext import commands
from cogs.utils.dataIO import DataIO 
from cogs.utils import config, exceptions, keys

DESCRIPTION = "CatBot - You've cat to be kitten me."

bot = commands.Bot(command_prefix=config.prefix, formatter=None, description=DESCRIPTION, pm_help=True, path=os.getcwd(), pypath='py')

@bot.event
async def on_ready():
    print('Logged in as %s!' % bot.user.name)
    botowner = discord.utils.find(lambda m: m.id == config.owner, bot.get_all_members())
    print('Owner: %s'% botowner)
    print(datetime.now())
    print('Use this link to invite bot to server:\n"https://discordapp.com/oauth2/authorize?client_id=%s&scope=bot&permissions=66321471"'% bot.user.id)

@bot.event
async def on_message(message):
    if message.content.startswith(config.prefix):
        message.content = message.content.lower()
        await bot.process_commands(message)
        
@bot.event
async def on_command(command, ctx):
    message = ctx.message
    destination = None
    if message.channel.is_private:
        destination = 'Private Message'
    else:
        destination = '#{0.channel.name} ({0.server.name})'.format(message)

    print('{0.timestamp}: {0.author.name} in {1}: {0.content}'.format(message, destination))

@bot.event
async def on_command_error(error, ctx):
    print('error: {}'.format(error))

@bot.command()
async def cogs():
    """Lists currently running cogs"""
    await bot.say("```py\n"+', '.join(list(bot.cogs.keys()))+"```")

@bot.command()
async def load(ctx, extension_name : str):
    """Loads an extension."""
    try:
        bot.load_extension('cogs.'+extension_name)
    except (AttributeError, ImportError) as e:
        await bot.say("```py\n{}: {}\n```".format(type(e).__name__, str(e)))
        return
    await bot.say("{} loaded.".format(extension_name))
    
@bot.command(pass_context=True)
async def unload(ctx, extension_name : str):
    """Unloads an extension."""
    if ctx.message.author.id != config.owner:
        return
    bot.unload_extension('cogs.'+ extension_name)
    await bot.say("{} unloaded.".format(extension_name))

@bot.command(pass_context=True, aliases=['re'])
async def refresh(ctx, extension_name : str):
    """Reloads an extension."""
    if ctx.message.author.id != config.owner:
        return
    bot.unload_extension('cogs.'+ extension_name)
    asyncio.sleep(.2)
    try:
        bot.load_extension('cogs.' + extension_name)
        await bot.say("{} refreshed.".format(extension_name))
    except (AttributeError, ImportError) as e:
        await bot.say("```py\n{}: {}\n```".format(type(e).__name__, str(e)))
        return
            

@bot.command(aliases=['ripkitty'], pass_context=True)
async def bye(ctx):
    """buh-bye now"""
    try:
        if ctx.message.author.id == config.owner:
            await bot.say('See ya.')
            await bot.logout()
            print("Cleaning up... ", end='')
            pending = asyncio.Task.all_tasks()
            gathered = asyncio.gather(*pending)
            try:
                gathered.cancel()
                bot.loop.run_until_complete(gathered)
                gathered.exception()
            except:  # Can be ignored
                pass
            print("Done.")
    
    except exceptions.PermissionsError:
        await bot.say('You lack permission to use this command.')
@bot.command()
async def restart():
    """Restarts a bitchy bot"""
    await bot.logout()
    print("Cleaning up... ", end='')
    pending = asyncio.Task.all_tasks()
    gathered = asyncio.gather(*pending)
    try:
        gathered.cancel()
        bot.loop.run_until_complete(gathered)
        gathered.exception()
    except:  # Can be ignored
        pass
    print("Done.")
    os.system('cmd /k run.py --start --restart')
    
@bot.command(pass_context=True, hidden=True)
async def nuke(ctx, limit: int = None):
    """Purge (bulk delete) msgs from channel.
    Doesn't nuke pinned msgs."""
    if ctx.message.author.id == config.owner:
        pinned = await bot.pins_from(ctx.message.channel)
        def checkdel(m):
            return(m.pinned == False)
        if limit is None:
            limit = 1000
        else:
            limit = limit
        deleted = await bot.purge_from(ctx.message.channel, limit=limit, check=checkdel)

        await bot.say("Nuked {} messages".format(len(deleted)), delete_after=5)
    else:
        raise exceptions.PermissionsError('You lack permission to use this command')
        
@bot.command(pass_context=True)
async def savejson(ctx):
    """write or update settings to data/settings.json"""
    if ctx.message.author.id != config.owner:
        return
    servers = []
    dataIO = DataIO()
    file = 'data/settings.json'
    data = {"token": config.token, "cogs": ['cogs.audio', 'cogs.translate', 'cogs.general', 'cogs.chatterbot', 'cogs.catbot'],
            "prefix": config.prefix, "owner": config.owner, "volume": config.volume, "chatChannels": config.chatChannels, "servers": {}}    
    if not os.path.isfile(file):
        dataIO.save_json(file, data)

    settings = dataIO.load_json(file)
    def serverset():
        for server in bot.servers:
            roles = len(server.roles)
            servrs = {'name':server.name, 'owner':server.owner.name, 'member_count':server.member_count, 'role_count':roles, 'region':server.region.name, 'created':datetime.ctime(server.created_at)}
            if server.id not in settings['servers']:
                settings['servers'][server.id] = servrs
    
    dataIO.save_json(filename=file, data=data)
    serverset()
    dataIO.save_json(filename=file, data=settings)

if __name__ == '__main__':
    for extension in config.cogs:
        try:
            bot.load_extension(extension)
        except Exception as e:
            exc = '{}: {}'.format(type(e).__name__, e)
            print('Failed to load extension {}\n{}'.format(extension, exc))
        
    bot.run(config.token)
