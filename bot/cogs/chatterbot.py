import asyncio
import os
from os import listdir
import discord
import logging
from discord.ext import commands
from cogs.utils import config, helpers
from cogs.utils.json2yaml import Json2yaml
from cogs.utils.dataIO import DataIO

from chatterbot.chatterbot import ChatBot
from chatterbot import corpus
import json
from textblob import TextBlob
from random import choice

DESCRIPTION = "CatBot - You've cat to be kitten me."

logging.basicConfig(level=logging.ERROR)

GREETING_KWDS = ['bonjour',
'buenas noches',
'buenos dias',
'good day',
'good morning',
'greetings',
'hey',
'hi',
'hiya',
'how are you?',
'how goes it?',
'howdy',
'howdy-do',
'shalom',
'welcome',
"what's happening?",
"what's up?",
'good morning',
'hello',
'bonjour']

class ChatterBot:

    # Init with the bot reference, and a reference to the settings var
    def __init__(self, bot, chatChannels=config.chatChannels, prefix=config.prefix):
        self.bot = bot
        self.chatChannels = chatChannels
        self.prefix = prefix
        self.waitTime = 4  # Wait time in seconds
        self.botDir = 'botdata'
        self.botBrain = 'data.db'
        self.botList = []
        self.ownerName = discord.utils.find(lambda m: m.id == config.owner, self.bot.get_all_members())
        self.ownerGender = "Female"
        self.timeout = 3
        self.chatBot = ChatBot("Catbot", storage_adapter="chatterbot.storage.SQLStorageAdapter",
            logic_adapters=[
            # "chatterbot.logic.MathematicalEvaluation",
            # "chatterbot.logic.TimeLogicAdapter",
            "chatterbot.logic.BestMatch"
            ],
            database="data.db",
            trainer='chatterbot.trainers.ChatterBotCorpusTrainer')

        
    async def onmessage(self, message):
        if message.channel.id not in self.chatChannels:
            return
        channel = message.channel

        if message.author.id != self.bot.user.id and not message.content.startswith(self.prefix):
            await self._chat(message.channel, message.channel.server, message.content, message.author)
   
    @commands.command()
    async def export(self, ctx):
        if ctx.message.author.id != config.owner:
            return
        data = {'conversations': self.chatBot.trainer._generate_export_data()}
        ymlfile = 'this_data.yml'
        jsonfile = 'this_data.json'
        with open(jsonfile, 'w+', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False)
        with Json2yaml.safeopen(jsonfile, 'r') as json_file:
            with Json2yaml.safeopen(ymlfile, 'w+') as yaml_file:
                Json2yaml.convert(json_file, yaml_file)

    @commands.command(hidden = True, pass_context=True)
    async def train(self, ctx, data_file_or_path:str):
        if ctx.message.author.id != config.owner:
            return
        self.chatBot.train(data_file_or_path)

    @commands.command(name='channel')
    async def add_chat_channel(self, ctx, channelID:int=None):
        if ctx.message.author.id != config.owner:
            return
        def chkedit(m):
            return(m.author.id != self.bot.user.id and m.content.isdigit())
        if channelID is None:
            chanq = await self.bot.say('Enter a channel ID for Chatterbot...')
            channelID = await self.bot.wait_for_message(60, check=chkedit)
        if not channelID:
            return
        chans = self.chatChannels
        chans.append('%d'%channelID)
        configfile = helpers.load_file('cogs/utils/config.py')
        configfile.remove(configfile[5])
        configfile.append('chatChannels = {}'.format(chans))
        helpers.write_file('cogs/utils/config.py', configfile)
        dataIO = DataIO()
        file = 'data/settings.json'

        data = {"token": config.token, "cogs": config.cogs,
            "prefix": config.prefix, "owner": config.owner, "volume": config.volume, "chatChannels": config.chatChannels, "servers": {}}    
        dataIO.save_json(filename=file, data=data)


    async def onready(self): #that won't happen. Train it with cogs/utils/blob.py in terminal.
        if not os.path.isfile(self.botBrain):
            self.chatBot.train('botdata.data')
 
       

    @commands.command(pass_context=True)
    async def chat(self, ctx, *, message=None):
        """Chats with the bot."""
        await self._chat(ctx.message.channel, ctx.message.channel.server, message, ctx.message.author)

    async def _chat(self, channel, server, message, author):
        if message == None:
            return
        blob = TextBlob(message)
        if author.nick is None:
            author = author.name
        else:
            author = author.nick
        for word in blob.words:
            if word.lower() in GREETING_KWDS:
                mess = choice(GREETING_KWDS) +', {}!'.format(author)
                msg = self.chatBot.input.process_input_statement(mess)
            else:
                msg = self.chatBot.get_response(message)    
        if not msg:
            return
        await self.bot.send_message(channel, msg)


def setup(bot):
    n = ChatterBot(bot)
    bot.add_listener(n.onready, 'on_ready')
    bot.add_listener(n.onmessage, 'on_message')
    bot.add_cog(n)
