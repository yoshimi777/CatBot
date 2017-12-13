import asyncio
import json
import os

import discord
import mtranslate
from discord.ext import commands

# Requires the mtranslate module be installed
# Borrowed from https://github.com/corpnewt/CorpBot.py

class Translate:
            
    def __init__(self, bot, language_file = "Languages.json"):
        self.bot = bot
        

        if os.path.exists(language_file):
            f = open(language_file,'r')
            filedata = f.read()
            f.close()
            self.languages = json.loads(filedata)
        else:
            self.languages = []
            print("No {}!".format(language_file))

    @commands.command(pass_context=True)
    async def langlist(self, ctx):
        """Lists available languages."""
        if not len(self.languages):
            await self.bot.say("I can't seem to find any languages :(")
            return

        # Pm languages to author
        # await ctx.send("I'll pm them to you.")
        msg = "Languages:\n\n"
        for lang in self.languages:
            msg += lang["Name"] + ", "
        await self.bot.whisper(msg)

    @commands.command(pass_context=True)
    async def tr(self, ctx, *, translate = None):
        """Translate"""
        usage = "Usage: `{}tr [words] [language]`".format(ctx.prefix)
        if translate == None:
            await self.bot.say(usage)
            return

        word_list = translate.split(" ")

        if len(word_list) < 2:
            await self.bot.say(usage)
            return

        lang = word_list[len(word_list)-1]
        trans = " ".join(word_list[:-1])

        lang_code = None

        for item in self.languages:
            if item["Name"].lower() == lang.lower():
                lang_code = item["Code"]
                break
        if not lang_code and len(word_list) > 2:
            # Maybe simplified/traditional chinese or other 2 word lang
            lang = " ".join(word_list[len(word_list)-2:])
            trans = " ".join(word_list[:-2])
            for item in self.languages:
                if item["Name"].lower() == lang.lower():
                    lang_code = item["Code"]
                    break
        
        if not lang_code:
            await self.bot.say("I couldn't find that language!")
            return

        result = mtranslate.translate(trans, lang_code, "auto")
        if not result:
            await self.bot.say("I wasn't able to translate that!")
            return

        await self.bot.say('**{}** is {} for\n"*{}*"'.format(result, lang.capitalize(), trans))
        await self.bot.delete_message(ctx.message)
        
def setup(bot):
    n = Translate(bot, language_file = "Languages.json")
    bot.add_cog(n)        
