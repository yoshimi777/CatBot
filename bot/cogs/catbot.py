import asyncio
import json
import textwrap
import subprocess
import os
import io
from datetime import datetime
from functools import wraps
from random import choice, shuffle
from subprocess import Popen

import urllib
from urllib.parse import urlparse
import aiohttp
import discord
import pytz
import wikipedia
import youtube_dl
import requests
from bs4 import BeautifulSoup
from colorthief import ColorThief
from google import lucky, search, search_apps, search_books, search_images, \
search_news, search_shop, search_videos
from cogs.utils import exceptions, config, helpers, checks, keys, dataIO
from cogs.utils.dataIO import DataIO, set_value
from discord.embeds import Embed
from discord.ext import commands
from discord.ext.commands import *
from discord.ext.commands.bot import _get_variable
from discord.ext.commands.core import Command
from youtube_dl import utils

DESCRIPTION = "CatBot - You've cat to be kitten me."



class Response:
    def __init__(self, content, reply=False, delete_after=0):
        self.content = content
        self.reply = reply
        self.delete_after = delete_after

def load_file(filename, skip_commented_lines=True, comment_char='#'):
    with open(filename, encoding='utf8') as f:
        results = []
        for line in f:
            line = line.strip()

            if line and not (skip_commented_lines and line.startswith(comment_char)):
                results.append(line)

        return results
  
class CatBot():
    def __init__(self, bot):
        self.bot = bot
        self.bird = load_file('cat/bird.txt')
        self.hammer = load_file('cat/hammer.txt')
        self.simpspons = load_file('cat/simpsons.txt')
        self.day = load_file('cat/badday.txt')
        self.settingsDict = {}
        
    def avatar_url(self):
        """Returns a friendly URL version of the avatar variable the user has. An empty string if
        the user has no avatar."""
        if self.avatar is None:
            return ''

        url = 'https://images.discordapp.net/avatars/{0.id}/{0.avatar}.{1}'
        if self.avatar.startswith('a_'):
            return url.format(self, 'gif')
        else:
            return url.format(self, 'webp')

    @commands.command(pass_context=True)
    async def spin(self, ctx):
        """Slots of fun."""
        ITEMS = ["🥜", "💣", "🍌",
                        "🍆", "💰", "💎"]
        PLAYER = ctx.message.author.id
        INIT_SCORE = 20
        folder = ctx.message.server.id
        file = f"{PLAYER}.txt"
        if not os.path.isfile(f"data/{folder}/{file}"):
            score = INIT_SCORE
        else:
            with open(f"data/{folder}/{file}", "r") as f:
                line = f.readline().strip()
                score = int(line)
                await self.bot.say(f"Hullo, {ctx.message.author.name}. Your score is {score}")
        firstWheel = None
        secondWheel = None
        thirdWheel = None

        def spinWheel():
            randomNumber = random.randint(0, 5)
            return ITEMS[randomNumber]

        def chkagain(m):
            return(m.content.lower() in 'yn' and m.author.id == PLAYER)

        async def printScore(PLAYER, score):
            firstWheel = choice(ITEMS)
            secondWheel = choice(ITEMS)
            thirdWheel = choice(ITEMS)
            spun = [firstWheel, secondWheel, thirdWheel]
            spin = await self.bot.say(' '.join(spun))
            await asyncio.sleep(0.6)

            for x in range(3):
                shuffle(spun)
                await self.bot.edit_message(spin, ' '.join(spun))
                await asyncio.sleep(0.6)
                        
                        
            if firstWheel == "🥜" and secondWheel != "🥜":
                win = 2
            elif firstWheel == "🥜" and secondWheel == "🥜" and thirdWheel != "🥜":
                win = 5
            elif firstWheel == "🥜" and secondWheel == "🥜" and thirdWheel == "🥜":
                win = 7
            elif firstWheel == "🍌" and secondWheel == "🍌" and thirdWheel == "🍌" or thirdWheel == "💰":
                win = 10
            elif firstWheel == "🍆" and secondWheel == "🍆" and thirdWheel == "🍆" or thirdWheel == "💰":
                win = 14
            elif firstWheel == "💰" and secondWheel == "💰" and thirdWheel == "💰" or thirdWheel == "💎":
                win = 20
            elif firstWheel == "💎" and secondWheel == "💎" and thirdWheel == "💎":
                win = 250
            else:
                win = -2
            score += win
            if win > 0:
                await self.bot.say(f'You won ${win}. You have ${score}.')
            else:
                await self.bot.say(f'You lose ${str(win).strip("-")}. You have ${score}.')
            if score > 0:
                msg = await self.bot.say('Spin again? (y/n)')
            while score > 0:
                again = await self.bot.wait_for_message(30, check=chkagain)
                if again.content.lower().startswith('y'):
                    await self.bot.delete_message(again)
                    await self.bot.delete_message(msg)
                    await printScore(PLAYER, score)
                if again.content.lower().startswith('n'):
                    filename = PLAYER + ".txt"
                    sid = ctx.message.channel.server.id
                    foldername = f"data/{sid}"
                    if not os.path.isdir(foldername):
                        os.makedirs(foldername)
                    with open(f"{foldername}/{filename}", "w+", encoding="utf-8") as scores:
                        scores.write(f"{score}")
                    break

        await printScore(PLAYER, score)

    @commands.command(pass_context=True)
    async def avatar(self, ctx, *, user: discord.Member = None ):
        """Returns a user's avatar. 
        
        If not user mention, returns the invoker's avatar."""
        embed = discord.Embed(title='Purty', color=ctx.message.author.color)
        author = ctx.message.author
        server = ctx.message.server

        if not user:
            user = author
            embed.set_image(url=user.avatar_url)
            await self.bot.say(embed=embed)
        else:
            embed.set_image(url=user.avatar_url)
            await self.bot.say(embed=embed)

    @commands.command(pass_context=True)
    async def dog(self, ctx):
        """Random Frickin dog. 🐕"""
        async with aiohttp.get('https://random.dog/woof.json') as r:
            if r.status == 200:
                js = await r.json()
        embed = discord.Embed(title="Yo dog.", color=discord.Color(0xeee8cd))
        embed.set_image(url=js['url'])
        await self.bot.say(embed=embed)
        if js['url'].endswith('.mp4'):
            await self.bot.say(js['url'])    

    @commands.command(pass_context=True)
    async def giftag(self, ctx, tag):
        """<tag> Random giphy by tag."""
        channel = ctx.message.channel
        key = keys.giphy
        tag = ctx.message.content.replace(config.prefix+'giftag ','').strip().replace(' ','%20')
        async with aiohttp.get('https://api.giphy.com/v1/gifs/random?api_key=%s&tag=%s&rating=R'% (key, tag)) as r:
             if r.status == 200:
                 js = await r.json()
        if js['data'] == []:
            return Response('```Nothing found for tag %s. Try spaces between words.```'%tag, delete_after=20)
        else:
            url = js['data']['image_url']
            embed = discord.Embed(title="Random %s"%tag.replace('%20',' '),
                               color=discord.Color(0xffd700))
            embed.set_image(url=url)
            await self.bot.say(embed=embed)
            await self.bot.delete_message(ctx.message)

    @commands.command(name='map', pass_context=True)
    async def staticmap(self, ctx, query):
        """<location> ["zoom level"] 
        
        zoom level, if present, must be 1-20 and in "quotes"."""
        this = ctx.message.content.replace(config.prefix+'map ', '').replace(' ','+').replace(',','').split('"')
        query = this[0]
        key = keys.maps
        if len(this) == 1:
            zoom = 16
        elif len(this) == 3:
            zoom = this[1]
        url = "https://maps.googleapis.com/maps/api/staticmap?maptype=hybrid&center=%s&zoom=%s&size=640x640&key=%s"%(query.upper(),zoom,key)
        colour = ''.join([choice('0123456789ABCDEF') for x in range(6)])
        colour = int(colour, 16)
        embed = discord.Embed(title=query.replace("+"," ").upper(), description="Hybrid Static Map", color=discord.Color(value=colour))
        embed.set_image(url=url)
        embed.set_footer(text="Zoom %s"%zoom)
        await self.bot.say(embed=embed)
        await self.bot.delete_message(ctx.message)

    @commands.command(pass_context=True)
    async def serverstuff(self, ctx):
        """some server info"""
        author = ctx.message.author
        for server in self.bot.servers:
            server = ctx.message.channel.server
            guild_id = server.id
            count = server.member_count
            for r in server.roles:
                if r.name == "@everyone":
                    r.name = "everyone"

            roles = ["%s: %s" % (r.name, r.id) for r in server.roles]
            region = server.region
            drole = server.default_role
        server = ctx.message.channel.server
        colour = ''.join([choice('0123456789ABCDEF') for x in range(6)])
        colour = int(colour, 16)
        embed = discord.Embed(title="Server Info", colour=discord.Colour(
                value=colour), description='Just some server shit.', timestamp=datetime.now(pytz.utc))
        embed.set_image(
                url='https://cdn.discordapp.com/icons/%s/%s.jpg' % (guild_id, server.icon))
        embed.set_author(name=author.name, icon_url=author.avatar_url)
        embed.set_footer(text=self.bot.user.name, icon_url='https://images.discordapp.net/avatars/%s/%s.jpg' %
                             (self.bot.user.id, self.bot.user.avatar))
        embed.add_field(name='Server Name:', value=server.name)
        embed.add_field(name="Server ID:", value=server.id)
        embed.add_field(name="Created At:", value=server.created_at, inline=False)
        embed.add_field(name="Owner:", value=server.owner.name)
        embed.add_field(name="Region:", value=region)
        embed.add_field(name="Member Count:", value=count)
        embed.add_field(name="Server Role Count:", value=len(server.roles))
        embed.add_field(name='Server Roles', value =','.join(roles))
        await self.bot.say(embed=embed)

    @commands.command(pass_context=True)
    async def user(self, ctx):
        """Returns an embed of user info.  
        
        If blank, returns the invoker's user info."""
        server = ctx.message.channel.server
        message = ctx.message
        user_mentions = list(map(message.server.get_member, message.raw_mentions))
        author = ctx.message.author
        channel = ctx.message.channel
        for s in self.bot.servers:
            guild_id = s.id
        for user in user_mentions:
            user = user_mentions[0]
        if not user_mentions:
            user = author
        for Member in server.members:
            Member = user
            names = Member.nick
            trole = Member.top_role
            joined = Member.joined_at
            if trole == server.default_role:
                trole = "everyone"
        colour = ''.join([choice('0123456789ABCDEF') for x in range(6)])
        colour = int(colour, 16)
        embed = discord.Embed(title='User Info', colour=discord.Colour(
            value=colour), description='Just some shit.', timestamp=datetime.now(pytz.utc))
        embed.set_image(
            url='https://images.discordapp.net/avatars/%s/%s.jpg' % (user.id, user.avatar))
        embed.set_thumbnail(
            url='https://cdn.discordapp.com/icons/%s/%s.png' % (guild_id, s.icon))
        embed.set_author(name=author.name, icon_url=author.avatar_url)
        embed.set_footer(text=self.bot.user.name, icon_url='https://images.discordapp.net/avatars/%s/%s.jpg' %
                         (self.bot.user.id, self.bot.user.avatar))

        embed.add_field(name='User Name:', value=user.name)
        embed.add_field(name='User ID:', value=user.id)
        embed.add_field(name='Account Created:', value=user.created_at)
        embed.add_field(name="Server Nickname:", value=names)
        embed.add_field(name="Joined at", value=joined)
        embed.add_field(name="Top Role:", value=trole)
        embed.add_field(name="Is a bitch?:",
                        value=choice(["yes", "no", "i dunno"]))

        await self.bot.say(embed=embed)

    @commands.command(pass_context=True)
    async def trump(self, ctx): 
        """Trump quotes 
        
        from WhatDoesTrumpThinkAPI."""
        async with aiohttp.get('https://api.whatdoestrumpthink.com/api/v1/quotes/random') as r:
            if r.status == 200:
                js = await r.json()
            mesg = js['message']
            
        embed = discord.Embed(title="**What Does Trump Think?**", color=discord.Color(0xa6a6a6))
        embed.add_field(name= '😕', value='```%s```' % mesg)
        await self.bot.say(embed=embed)

    @commands.command(pass_context=True)
    async def trumpet(self, ctx):
        """Personalized Trump Insults
        
        [user_mentions] [user_id] ["a name"] Pick 1 or none.""" 
        message = ctx.message  
        user_mentions = list(map(message.server.get_member, message.raw_mentions))
        author = ctx.message.author
        query = message.content.lstrip(config.prefix + 'trumpet ')
        
        if not user_mentions:
            user = author
        else:
            name = '<@%s>' % user_mentions[0].id
        if query.isdigit() == True:
            name = '<@%s>' % query
        elif query.isalpha() == True and len(user_mentions) == 0:
            name = query
        elif query.isdigit() == False and len(user_mentions) == 0:
            name = '<@%s>' % message.author.id
        
        async with aiohttp.get('https://api.whatdoestrumpthink.com/api/v1/quotes/personalized?q=name') as r:
            if r.status == 200:
                js = await r.json()
            mesg = js['message'].replace('name', '%s' % name)
            
            await self.bot.delete_message(message)
        embed = discord.Embed(title="Trump says: ", color=discord.Color(0xa6a6a6))
        embed.add_field(name='😕', value=mesg)
        await self.bot.say(embed=embed)
        await self.bot.delete_message(ctx.message)

    @commands.command(pass_context=True)
    async def hammy(self, ctx):
        """Random Frickin Hamster. 🐹"""
        resp = urllib.request.urlopen(
            "http://crystal.x10host.com/rand/img/hamster/")
        soup = BeautifulSoup(
            resp, 'html.parser')
        ham = []
        for link in soup.find_all('a', href=True):
            if link['href'] != '/rand/img/':
                ham.append(link['href'])
        pick = choice(ham)  
        base = 'http://crystal.x10host.com/rand/img/hamster/'
        url =  base + pick
        embed = discord.Embed(title="Random Hamster 🐹",
                               color=discord.Color(0xeee9bf))
        embed.set_image(url=url)
        await self.bot.say(embed=embed)
  
    @commands.command(pass_context=True)
    async def hammer(self, ctx):
        """Random Frickin hammer. 🔨"""
        
        url = choice(self.hammer)
        embed = discord.Embed(title="Random Hammer 🔨",
                              color=discord.Color(0x663300))
        embed.set_image(url=url)
        await self.bot.say(embed=embed)

    @commands.command(pass_context=True, hidden=True)
    async def zoey(self, channel):
        """Zoey!"""
        async with aiohttp.get('http://crystal.x10host.com/meh/zoey.json') as r:
            if r.status == 200:
                js = await r.json()
        base = 'http://crystal.x10host.com/'
        pick = js['zoey'][choice(range(len(js['zoey'])))]['url']
        embed = discord.Embed(title="Random Zoey 💔 💖 💔",
                              color=discord.Color(0x040101))
        embed.set_image(url=pick)
        await self.bot.say(embed=embed)

    @commands.command(pass_context=True)
    async def fails(self, ctx):
        """Random Fails 🙃"""
        url = choice(self.day)
        colour = ''.join([choice('0123456789ABCDEF') for x in range(6)])
        colour = int(colour, 16)
        embed = discord.Embed(title="Bad Day 🙃", color=discord.Color(value=colour))
        embed.set_image(url=url)
        await self.bot.say(embed=embed)

    @commands.command(pass_context=True)
    async def birb(self, ctx):
        """Random Frickin bird. 🐦"""
        url = choice(self.bird)
        embed = discord.Embed(title="Random Birb 🐦",
                              color=discord.Color(0xffd700))
        embed.set_image(url=url)
        await self.bot.say(embed=embed)
    
    @commands.command(pass_context=True)
    async def simpsons(self, ctx):
        """Assorted Simpsons whatever."""
        url = choice(self.simsons)
        embed = discord.Embed(title="☁️ the Simpsons ☁️",
                              color=discord.Color(0xffff00))
        embed.set_image(url=url)
        await self.bot.say(embed=embed)

    @commands.command(pass_context=True)
    async def turtle(self, ctx):
        """Random Frickin Turtle. 🐢"""
        async with aiohttp.get('http://crystal.x10host.com/meh/turtle.json') as r:
             if r.status == 200:
                 js = await r.json()
        base = 'http://crystal.x10host.com/'
        pick = js['turtle'][choice(range(len(js['turtle'])))]['url']
        embed = discord.Embed(title="Random Turtle 🐢",
                              color=discord.Color(0x2ecc71))
        embed.set_image(url=pick)
        await self.bot.say(embed=embed)

    @commands.command(pass_context=True)
    async def mouse(self, ctx):
        """Blurry pics of my cat."""
        async with aiohttp.get('http://crystal.x10host.com/meh/mouselinks.json') as r:
             if r.status == 200:
                 js = await r.json()
        index = choice(range(len(js['images'])))
        url = js['images'][index]['url']
        embed = discord.Embed(title="Random 🐁 the 🐈",
                              colour=discord.Colour(0x8B7355))
        embed.set_image(url=url)
        await self.bot.say(embed=embed)

    @commands.command(pass_context=True)
    async def cat(self, ctx):
        """Random Frickin cat. 🐱‍👤"""
        async with aiohttp.get('http://random.cat/meow') as r:
            if r.status == 200:
                js = await r.json()
        embed = discord.Embed(
                title="Cool cat.", color=discord.Color(0xcae1ff))
        embed.set_image(url=js['file'])
        await self.bot.say(embed=embed)

    @commands.command(pass_context=True)
    async def invite(self, ctx):
        """bot's invite url"""
        await self.bot.say('https://discordapp.com/oauth2/authorize?client_id=%s&scope=bot&permissions=66321471'%self.bot.user.id)
    
    @commands.command(pass_context=True)
    async def wiki(self, ctx, *, search : str = None):
        """Search Wikipedia"""
        if search == None:
            await self.bot.say("Usage: `{}wiki [search terms]`".format(ctx.prefix))
            return
        results = wikipedia.search(search)
        if not len(results):
            await self.bot.say("No results")
            return
        newSearch = results[0]
        try:
            wik = wikipedia.page(newSearch)
        except wikipedia.DisambiguationError:
            await self.bot.say("That search wasn't specific enough - try again with more detail.")
            return
        wiki_embed = discord.Embed(color=ctx.message.author.color)
        wiki_embed.title = wik.title
        wiki_embed.url = wik.url
        textList = textwrap.wrap(wik.content, 500, break_long_words=True, replace_whitespace=False)
        wiki_embed.add_field(name="Wikipedia Results", value=textList[0]+"...")
        wiki_embed.set_footer(text=', '.join(results[1:]))
        await self.bot.say(embed=wiki_embed)

    @commands.command(pass_context=True)
    async def tictac(self, ctx):
        """tic-tac-toe"""
        channel = ctx.message.channel
        ROWS = 3
        COLMS = 3
        O = '⭕️'
        X = '❌'
        brd = [
            ['⏹️', '🔳', '⏹️'],
            ['🔳', '🆓', '🔳'],
            ['⏹️', '🔳', '⏹️']
        ]

        numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9]
        embed = discord.Embed(title="Tic-tac-toe")
        done = False
        await self.bot.say("``"+"Tic-Tac-Toe!\n"+" 1 | 2 | 3 \n"+"-----------\n"+" 4 | 5 | 6 \n"+"-----------\n"+" 7 | 8 | 9 \n"+"``")
        for i in range(ROWS):
                await self.bot.say('|'.join(brd[i]))
        while not done:
            await self.bot.say("Player 1, you are ❌, make your move. (Enter a # 1-9)")
            def checknumb(m):
                return(m.author.id != self.bot.user.id and m.content.strip().isnumeric() is True)
            pick = await self.bot.wait_for_message(60, channel=channel, check=checknumb)
            userInput = int(pick.content[0])
            if userInput in numbers:
                if userInput == 1:
                    numbers.remove(1)
                    brd[0][0] = '❌'
                if userInput == 2:
                    numbers.remove(2)
                    brd[0][1] = '❌'
                if userInput == 3:
                    numbers.remove(3)
                    brd[0][2] = '❌'
                if userInput == 4:
                    numbers.remove(4)
                    brd[1][0] = '❌'
                if userInput == 5:
                    numbers.remove(5)
                    brd[1][1] = '❌'
                if userInput == 6:
                    numbers.remove(6)
                    brd[1][2] = '❌'
                if userInput == 7:
                    numbers.remove(7)
                    brd[2][0] = '❌'
                if userInput == 8:
                    numbers.remove(8)
                    brd[2][1] = '❌'
                if userInput == 9:
                    numbers.remove(9)
                    brd[2][2] = '❌'
            else:
                await self.bot.say("Invalid input, <@%s>.  Lose a turn." % pick.author.id)
            for i in range(ROWS):
                await self.bot.say('|'.join(brd[i]))
            if numbers == [] or numbers == 0:
                await self.bot.say("Game over. No winner.")
                done = True
                if done == True:
                    break
            if brd[0][0] == brd[0][1] == brd[0][2] or brd[1][0] == brd[1][1] == brd[1][2] or brd[2][0] == brd[2][1] == brd[2][2] or brd[0][0] == brd[1][0] == brd[2][0] or brd[0][1] == brd[1][1] == brd[2][1] or brd[0][2] == brd[1][2] == brd[2][2] or brd[0][0] == brd[1][1] == brd[2][2] or brd[0][2] == brd[1][1] == brd[2][0]:
                winner = "<@%s>" % pick.author.id
                await self.bot.say("Game Over, You win, %s!" % winner)
                done = True
                if done == True:
                    break
            await self.bot.say("Player 2, you are ⭕️, make your move. (Enter a # 1-9)")
            def checknumb(m):
                return(m.author.id != self.bot.user.id and m.content.strip().isnumeric() is True)
            pick2 = await self.bot.wait_for_message(60, channel=channel, check=checknumb)
            userInput = int(pick2.content[0])
            if userInput in numbers:
                if userInput == 1:
                    numbers.remove(1)
                    brd[0][0] = '⭕️'
                if userInput == 2:
                    numbers.remove(2)
                    brd[0][1] = '⭕️'
                if userInput == 3:
                    numbers.remove(3)
                    brd[0][2] = '⭕️'
                if userInput == 4:
                    numbers.remove(4)
                    brd[1][0] = '⭕️'
                if userInput == 5:
                    numbers.remove(5)
                    brd[1][1] = '⭕️'
                if userInput == 6:
                    numbers.remove(6)
                    brd[1][2] = '⭕️'
                if userInput == 7:
                    numbers.remove(7)
                    brd[2][0] = '⭕️'
                if userInput == 8:
                    numbers.remove(8)
                    brd[2][1] = '⭕️'
                if userInput == 9:
                    numbers.remove(9)
                    brd[2][2] = '⭕️'
            else:
                await self.bot.say("Invalid input, <@%s>.  Lose a turn." % pick2.author.id)
            for i in range(ROWS):
                await self.bot.say('|'.join(brd[i]))
            if numbers == [] or numbers == 0:
                await self.bot.say("Game over. No winner.")
                done = True
                if done == True:
                    break
            if brd[0][0] == brd[0][1] == brd[0][2] or brd[1][0] == brd[1][1] == brd[1][2] or brd[2][0] == brd[2][1] == brd[2][2] or brd[0][0] == brd[1][0] == brd[2][0] or brd[0][1] == brd[1][1] == brd[2][1] or brd[0][2] == brd[1][2] == brd[2][2] or brd[0][0] == brd[1][1] == brd[2][2] or brd[0][2] == brd[1][1] == brd[2][0]:
                winner = "<@%s>" % pick2.author.id
                await self.bot.say("Game Over, You win, %s!" % winner)
                done = True
                if done == True:
                    break

    @commands.command(pass_context=True)
    async def meowd(self, ctx, phrase: str):
        """<text> Make CatBot meow someshit"""
        message = ctx.message
        channel = ctx.message.channel
        phrase = message.content.replace(config.prefix +'meowd ','')
        await self.bot.say(phrase)
        await self.bot.delete_message(message)

    @commands.command(name='google', pass_context=True)
    async def googl(self, ctx, query: str):
        """<search query> Googles."""
        query = ctx.message.content.lower().replace(config.prefix+'google ','').strip()
        queery = query.replace(' ', '+').strip()
        links = []
        for url in search(queery, num=1, start=0, stop=2, pause=2.0):
            links.append(url)
        await self.bot.say('\n'.join(links[:5]))
            
    @commands.command(pass_context=True)
    async def mews(self, ctx, query: str):
        """<news query> Fresh mews (news)."""
        query = ctx.message.content.lower().replace(config.prefix+'mews ','').strip()
        queery = query.replace(' ', '+')
        links = []
        for url in search_news(queery, num=1, start=0, stop=2, pause=2.0):
            links.append(url)
        await self.bot.say('\n'.join(links[:4]))
            
            
    @commands.command(pass_context=True)
    async def vids(self, ctx, query: str):
        """<video query> Search Google for videos."""
        query = ctx.message.content.lower().replace(config.prefix+'vids ','').strip()
        queery = query.replace(' ', '+')
        for url in search_videos(queery, num=1, start=0, stop=2, pause=2.0):
            await asyncio.sleep(0.5)
            await self.bot.say(url)
    
    @commands.command(pass_context=True)
    async def imgs(self, ctx, query: str):
        """shitty implementation, does not return image links"""
        query = ctx.message.content.lower().replace(config.prefix+'imgs ','').strip()
        queery = query.replace(' ', '+')
        for url in search_images(queery, num=3, start=0, stop=3, pause=2.0):
            await asyncio.sleep(0.5)
            print(url)
            await self.bot.say(url)

    @commands.command(pass_context=True, no_pm=False, aliases=['lyrics'])        
    async def genius(self, ctx, query: str):
        """Lyric search from Genius.com"""
        message = ctx.message.content.lower()
        query = message.replace(config.prefix,'').replace(' ', '+').replace('lyrics', 'genius')
        for url in search(query, lang='en', tbs='0', safe='off', num=1, start=0,
           stop=1, pause=2.0, only_standard=False, tpe='', user_agent=None):
            url = url.replace('genius.com/', 'genius.com/amp/')
        try:
            page = requests.get(url)
            html = BeautifulSoup(page.text, "html.parser")
            [h.extract() for h in html('script')]
            lyrics = html.find('div', class_='lyrics').get_text()
            title = html.find('title').get_text()
            ugh = html.select('div.header_with_cover_art-primary_image amp-img[src]')
            for img in ugh:
                image = img['src']
            embed = discord.Embed(title=title, description=lyrics, color=ctx.message.author.color)
            embed.set_thumbnail(url=image)
            await self.bot.say(embed=embed)
        except Exception as e:
            print(e)

    @commands.command(pass_context=True, hidden=True)
    async def sendthis(self, ctx, file : str):
        """upload a file"""
        if ctx.message.author.id != config.owner:
            return
        img = '%s'%file
        message = ctx.message
        await self.bot.delete_message(message)
        await self.bot.send_file(ctx.message.channel, img)      				
                            				
    @commands.command(pass_context=True)
    async def halp(self, ctx, command:str = None):
        if command is None:
            audio = []
            general = []
            catbot = []
            main = []
            hidden = []
            commands = []
            msg = "```"
            for command in self.bot.commands:
                cmd = self.bot.get_command(command)
                if cmd.hidden is True:
                    hidden.append('{} in {}'.format(command, cmd.cog_name))
                if cmd.cog_name is None and cmd.hidden is False:
                    main.append(command)
                if cmd.cog_name == "Translate" and cmd.hidden is False:
                    general.append(command)
                if cmd.cog_name == "General" and cmd.hidden is False:
                    general.append(command)
                if cmd.cog_name == "ChatterBot" and cmd.hidden is False:
                    general.append(command)
                if cmd.cog_name == "CatBot" and cmd.hidden is False:	
                    catbot.append(command)
                if cmd.cog_name == "Google"	and cmd.hidden is False:
                    catbot.append(command)
                if cmd.cog_name == 'Audio' and cmd.hidden is False:
                    audio.append(command)
                else:
                    if cmd.hidden is False:
                        commands.append(command)
                    
            embed = discord.Embed(title="Halp! {}'s Commands...".format(self.bot.user.name), description="Type {}halp [command] for more help.\n\n".format(config.prefix), color=discord.Color(0xff80aa))
            embed.set_thumbnail(url=ctx.message.server.icon_url)
            embed.set_footer(text=self.bot.user.name, icon_url='https://images.discordapp.net/avatars/%s/%s.jpg' %
                             (self.bot.user.id, self.bot.user.avatar))
            embed.add_field(name='Main Commands:', value=', '.join(main))
            embed.add_field(name="Music Related Commands:", value=', '.join(audio))
            embed.add_field(name='General Commands:', value=', '.join(general))
            embed.add_field(name="CatBot Commands:", value=', '.join(catbot))
            msg +="Halp! CatBot+'s Commands...\n\nType {}command name for more help.\n\n".format(config.prefix)
            msg +='Main Commands:\n'+', '.join(main)+'\n\n'
            msg +='Music Related Commands:\n'+', '.join(audio)+'\n\n'
            msg +='General Commands:\n'+', '.join(general)+'\n\n'
            msg +='CatBot Commands:\n'+', '.join(catbot)+'\n\n'
            msg +="```"
            await self.bot.say(embed=embed)
            print('Hidden Commands:\n'+', '.join(hidden))
        else:
            cmd = self.bot.get_command(command)
            if cmd is None:
                msg = "```"
                msg += "Command does not exist"+"```"
                await self.bot.say(msg)
            else:
                msg = "```"
                msg += '{}{}\n{}\n\n'.format(config.prefix, cmd.name, cmd.help)
                if len(cmd.aliases) > 0:
                    msg += 'Aliases: {}\n'.format(', '.join(cmd.aliases)) + "```"
                else:
                    msg += "```"
                await self.bot.say(msg)

    @commands.command(aliases=['font'])
    async def fonts(self, ctx, num:str=None, words:str=None):
        """<index # of font> <words> Write in a font. 
        
        If no arguments called, returns font list"""
        fonts = []
        txt = []
        with open('cat/fonts.txt', encoding='utf-8') as file:
            js = json.load(file)
        if num is None and words is None:
            for i in range(len(js['fonts'])):
                name = js['fonts'][i]['name']
                number = js['fonts'][i]['num']
                fonts.append('%d: %s'%(number, name))
            await self.bot.say('\n'.join(fonts))
        else:
            words = ctx.message.content.replace('{}fonts '.format(config.prefix), '').replace('{}font '.format(config.prefix), '').strip(num).strip()
            indx = int(num) - 1
            mapp = js['fonts'][indx]['font']
            charArray = list(words)
            txt = []
            for i in range(len(charArray)):
                txt.append(mapp[charArray[i]])
            text = "".join(txt)
            await self.bot.say(text)
            await self.bot.delete_message(ctx.message)

    @checks.is_owner()
    @commands.command(hidden=True)
    async def shit(self, ctx):
        words = 'What the fuck?'
        lower = []
        
        char = list("ZYXWVUTSRQPONMLKJIHGFEDCBAzyxwvutsrqponmlkjihgfedcba9876543210~/?.>,<;:|][}{=-+_)(*&^%$#@!")
        
        tran = list("zʎxʍ𐌡nʇsɹbdouɯןʞɾıɥƃɟǝpɔqɐzʎxʍʌnʇsɹbdouɯןʞɾıɥƃɟǝpɔqɐ9876543210~/¿.>‘<;:\|][}{=-+_)(*⅋^%$#@¡")
        
        for i in range(len(char)):
             lower.append('"%s":"%s"'%(char[i], tran[i]))
        
        this = ', '.join(lower)
        await self.bot.say(this)

def setup(bot):
    n = CatBot(bot)
    bot.add_cog(n)

