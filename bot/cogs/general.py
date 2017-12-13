import asyncio
import datetime
import fnmatch
import inspect
import json
import os
import platform
import subprocess
import sys
import time
import urllib
from enum import Enum
from functools import wraps
from random import choice, randint
from urllib.parse import quote, quote_plus

import aiohttp
import discord
import psutil
import pyspeedtest
import requests
from pyquery.ajax import PyQuery as pq
from bs4 import BeautifulSoup
from discord import Client
from discord.ext import commands
from discord.ext.commands.bot import Bot, _default_help_command, _get_variable
from PIL import Image

from cogs.utils import config, exceptions, helpers, DisplayName, checks, keys
from cogs.utils.chat_formatting import escape_mass_mentions, italics, pagify

settings = {"POLL_DURATION" : 60}


class RPS(Enum):
    rock     = "\N{MOYAI}"
    paper    = "\N{PAGE FACING UP}"
    scissors = "\N{BLACK SCISSORS}"


class RPSParser:
    def __init__(self, argument):
        argument = argument.lower()
        if argument == "rock":
            self.choice = RPS.rock
        elif argument == "paper":
            self.choice = RPS.paper
        elif argument == "scissors":
            self.choice = RPS.scissors
        else:
            raise


class General:
    """General commands."""

    def __init__(self, bot, path=os.getcwd(), pypath='py'):
        self.bot = bot
        self.path = path
        self.pypath = pypath
        self.startTime = int(time.time())
        self.stopwatches = {}
        self.ball = ["As I see it, yes", "It is certain", "It is decidedly so", "Most likely", "Outlook good",
                     "Signs point to yes", "Without a doubt", "Yes", "Yes – definitely", "You may rely on it", "Reply hazy, try again",
                     "Ask again later", "Better not tell you now", "Cannot predict now", "Concentrate and ask again",
                     "Don't count on it", "My reply is no", "My sources say no", "Outlook not so good", "Very doubtful"]
        self.poll_sessions = []

 
    @commands.command(pass_context=True)
    async def ping(self, ctx):
        """Timed ping"""
        before_typing = time.monotonic()
        await self.bot.send_typing(ctx.message.channel)
        after_typing = time.monotonic()
        ms = int((after_typing - before_typing) * 1000)
        msg = '*{}*, ***PONG!*** (~{}ms)'.format(ctx.message.author.mention, ms)
        await self.bot.say(msg)

        
    @commands.command(pass_context=True, hidden=True)
    async def nickname(self, ctx, *, name : str = None):
        """Set the bot's nickname (admin-only)."""
        
        isAdmin = ctx.message.author.permissions_in(ctx.message.channel).administrator
        # Only allow admins to change server stats
        if not isAdmin:
            await self.bot.say('You do not have sufficient privileges to access this command.')
            return
        
        # Let's get the bot's member in the current server
        botName = "{}#{}".format(self.bot.user.name, self.bot.user.discriminator)
        botMember = ctx.message.server.get_member_named(botName)
        await botMember.edit(nick=name)

    @checks.is_owner()
    @commands.command(pass_context=True)
    async def hostinfo(self, ctx):
        """List info about the bot's host environment."""
        cpuThred      = os.cpu_count()
        cpuUsage      = psutil.cpu_percent(interval=1)
        memStats      = psutil.virtual_memory()
        memPerc       = memStats.percent
        memUsed       = memStats.used
        memTotal      = memStats.total
        memUsedGB     = "{0:.1f}".format(((memUsed / 1024) / 1024) / 1024)
        memTotalGB    = "{0:.1f}".format(((memTotal/1024)/1024)/1024)
        currentOS     = platform.platform()
        system        = platform.system()
        release       = platform.release()
        version       = platform.version()
        processor     = platform.processor()
        botMember     = DisplayName.memberForID(self.bot.user.id, ctx.message.server)
        botName       = DisplayName.name(botMember)
        currentTime   = int(time.time())
        timeString    = helpers.getReadableTimeBetween(self.startTime, currentTime)
        pythonMajor   = sys.version_info.major
        pythonMinor   = sys.version_info.minor
        pythonMicro   = sys.version_info.micro
        pythonRelease = sys.version_info.releaselevel
        process       = subprocess.Popen(['git', 'rev-parse', '--short', 'HEAD'], shell=False, stdout=subprocess.PIPE)

        threadString = 'thread'
        if not cpuThred == 1:
            threadString += 's'
        message = await self.bot.say('Gathering info...')
        msg = '***{}\'s*** **Home:**\n'.format(botName)
        msg += '```\n'
        msg += 'OS       : {}\n'.format(currentOS)
        msg += 'Hostname : {}\n'.format(platform.node())
        msg += 'Language : Python {}.{}.{} {}\n'.format(pythonMajor, pythonMinor, pythonMicro, pythonRelease)
        
        msg += helpers.center('{}% of {} {}'.format(cpuUsage, cpuThred, threadString), 'CPU') + '\n'
        msg += helpers.makeBar(int(round(cpuUsage))) + "\n\n"
        msg += helpers.center('{} ({}%) of {}GB used'.format(memUsedGB, memPerc, memTotalGB), 'RAM') + '\n'
        msg += helpers.makeBar(int(round(memPerc))) + "\n\n"
        msg += '{} uptime```'.format(timeString)

        await self.bot.edit_message(message, new_content=msg)

    @checks.is_owner()
    @commands.command(pass_context=True)
    async def speedtest(self, ctx):
        """Run a network speed test"""

        channel = ctx.message.channel
        author  = ctx.message.author
        server  = ctx.message.server

        message = await self.bot.say('Running speed test...')
        st = pyspeedtest.SpeedTest()
        msg = '**Speed Test Results:**\n'
        msg += '```\n'
        msg += '    Ping: {}\n'.format(round(st.ping(), 2))
        msg += 'Download: {}MB/s\n'.format(round(st.download()/1024/1024, 2))
        msg += '  Upload: {}MB/s```'.format(round(st.upload()/1024/1024, 2))
        await self.bot.edit_message(message, new_content=msg)
        
    @commands.command(pass_context=True)
    async def servers(self, ctx):
        """Lists # of connected servers"""

        channel = ctx.message.channel
        author  = ctx.message.author
        server  = ctx.message.server
        
        total = 0
        for server in self.bot.servers:
            total += 1
        if total == 1:
            msg = 'I am a part of *1* server!'
        else:
            msg = 'I am a part of *{}* servers!'.format(total)
        await self.bot.say(msg)
        
    @commands.command(pass_context=True)
    async def cloc(self, ctx):
        """Outputs the total count of lines of code."""
        # Script pulled and edited from https://github.com/kyco/python-count-lines-of-code/blob/python3/cloc.py
        
        # Get our current working directory - should be the bot's home
        path = os.getcwd()
        
        # Set up some lists
        extensions = []
        code_count = []
        include = ['py','bat','sh']
        
        # Get the extensions - include our include list
        extensions = self.get_extensions(path, include)
        for run in extensions:
            extension = "*."+run
            temp = 0
            for root, dir, files in os.walk(path):
                for items in fnmatch.filter(files, extension):
                    value = root + "/" + items
                    temp += sum(+1 for line in open(value, 'rb'))
            code_count.append(temp)
            pass
        
        # Set up our output
        msg = 'Whoa:\n```\n'
        padTo = 0
        for idx, val in enumerate(code_count):
            # Find out which has the longest
            tempLen = len(str('{:,}'.format(code_count[idx])))
            if tempLen > padTo:
                padTo = tempLen
        for idx, val in enumerate(code_count):
            lineWord = 'lines'
            if code_count[idx] == 1:
                lineWord = 'line'
            # Setup a right-justified string padded with spaces
            numString = str('{:,}'.format(code_count[idx])).rjust(padTo, ' ')
            msg += numString + " " + lineWord + " of " + extensions[idx] + "\n"
            pass
        msg += '```'
        await self.bot.say(msg)
        
    @cloc.error
    async def cloc_error(self, ctx, error):
        # do stuff
        msg = 'cloc Error: {}'.format(ctx)
        await self.bot.say(msg)

    # Helper function to get extensions
    def get_extensions(self, path, excl):
        extensions = []
        for root, dir, files in os.walk(path):
            for items in fnmatch.filter(files, "*"):
                temp_extensions = items.rfind(".")
                ext = items[temp_extensions+1:]
                if ext not in extensions:
                    if ext in excl:
                        extensions.append(ext)
                        pass
        return extensions

    @commands.command()
    async def choose(self, *choices):
        """Chooses between choices.

        To denote multiple choices, you should use double quotes.
        """
        choices = [escape_mass_mentions(c) for c in choices]
        if len(choices) < 2:
            await self.bot.say('Not enough choices to pick from.')
        else:
            await self.bot.say(choice(choices))

    @commands.command(pass_context=True)
    async def roll(self, ctx, number : int = 100):
        """Rolls random number (between 1 and choice)
        """
        author = ctx.message.author
        if number > 1:
            n = randint(1, number)
            await self.bot.say("{} :game_die: {} :game_die:".format(author.mention, n))
        else:
            await self.bot.say("{} Maybe higher than 1? ;P".format(author.mention))

    @commands.command(pass_context=True)
    async def flip(self, ctx, user : discord.Member=None):
        """Flips a coin... or a user.

        Defaults to coin.
        """
        if user != None:
            msg = ""
            if user.id == self.bot.user.id:
                user = ctx.message.author
                msg = "Nice try. You think this is funny? How about *this* instead:\n\n"
            char = "abcdefghijklmnopqrstuvwxyz"
            tran = "ɐqɔpǝɟƃɥᴉɾʞlɯuodbɹsʇnʌʍxʎz"
            table = str.maketrans(char, tran)
            name = user.display_name.translate(table)
            char = char.upper()
            tran = "∀qƆpƎℲפHIſʞ˥WNOԀQᴚS┴∩ΛMX⅄Z"
            table = str.maketrans(char, tran)
            name = name.translate(table)
            await self.bot.say(msg + "(╯°□°）╯︵ " + name[::-1])
        else:
            botcall = choice(["HEADS!", "TAILS!"])
            await self.bot.say('*Flips a coin and...* **{}** Loser.'.format(botcall))
                    

    @commands.command(pass_context=True)
    async def rps(self, ctx, your_choice : RPSParser):
        """Play rock paper scissors"""
        author = ctx.message.author
        player_choice = your_choice.choice
        catbot_choice = choice((RPS.rock, RPS.paper, RPS.scissors))
        cond = {
                (RPS.rock,     RPS.paper)    : False,
                (RPS.rock,     RPS.scissors) : True,
                (RPS.paper,    RPS.rock)     : True,
                (RPS.paper,    RPS.scissors) : False,
                (RPS.scissors, RPS.rock)     : False,
                (RPS.scissors, RPS.paper)    : True
               }

        if catbot_choice == player_choice:
            outcome = None # Tie
        else:
            outcome = cond[(player_choice, catbot_choice)]

        if outcome is True:
            await self.bot.say("{} You win {}!"
                               "".format(catbot_choice.value, author.mention))
        elif outcome is False:
            await self.bot.say("{} You lose {}!"
                               "".format(catbot_choice.value, author.mention))
        else:
            await self.bot.say("{} We're square {}!"
                               "".format(catbot_choice.value, author.mention))

    @commands.command(name="8", aliases=["8ball"])
    async def _8ball(self, *, question : str):
        """Ask 8 ball a question

        Question must end with a question mark.
        """
        if question.endswith("?") and question != "?":
            await self.bot.say("`" + choice(self.ball) + "`")
        else:
            await self.bot.say("That doesn't look like a question.")

    @commands.command(aliases=["sw"], pass_context=True)
    async def stopwatch(self, ctx):
        """Starts/stops stopwatch"""
        author = ctx.message.author
        if not author.id in self.stopwatches:
            self.stopwatches[author.id] = int(time.perf_counter())
            await self.bot.say(author.mention + " Stopwatch started!")
        else:
            tmp = abs(self.stopwatches[author.id] - int(time.perf_counter()))
            tmp = str(datetime.timedelta(seconds=tmp))
            await self.bot.say(author.mention + " Stopwatch stopped! Time: **" + tmp + "**")
            self.stopwatches.pop(author.id, None)

    @commands.command(pass_context=True)
    async def convert(self, ctx, amount = None, to = None):
        """<amount> <currency 1, currency 2...> Convert currencies to USD

        convert without amount or currency returns currency list"""
        hasError = False
        key = keys.currency
        msg = ctx.message.content.replace('%sconvert '%config.prefix, '').upper().strip()
        curr = msg.replace(amount, '').strip()
        ugh = curr.split(' ')
        if len(ugh) > 1:
            to = ',%20'.join(ugh)
        try:
            amount = float(amount)
        except:
            hasError = True
        if to == None or amount <= 0:
            hasError = True
        if hasError == True:
            errorMsg = 'Usage: `convert <amount> <fromCurrency> <toCurrency>`\n *Here are the list of currencies* ```Markdown\n<AED = United Arab Emirates Dirham (AED)>\n<AFN = Afghan Afghani (AFN)>\n<ALL = Albanian Lek (ALL)>\n<AMD = Armenian Dram (AMD)>\n<ANG = Netherlands Antillean Guilder (ANG)>\n<AOA = Angolan Kwanza (AOA)>\n<ARS = Argentine Peso (ARS)>\n<AUD = Australian Dollar (A$)>\n<AWG = Aruban Florin (AWG)>\n<AZN = Azerbaijani Manat (AZN)>\n<BAM = Bosnia-Herzegovina Convertible Mark (BAM)>\n<BBD = Barbadian Dollar (BBD)>\n<BDT = Bangladeshi Taka (BDT)>\n<BGN = Bulgarian Lev (BGN)>\n<BHD = Bahraini Dinar (BHD)>\n<BIF = Burundian Franc (BIF)>\n<BMD = Bermudan Dollar (BMD)>\n<BND = Brunei Dollar (BND)>\n<BOB = Bolivian Boliviano (BOB)>\n<BRL = Brazilian Real (R$)>\n<BSD = Bahamian Dollar (BSD)>\n<BTC = Bitcoin (฿)>\n<BTN = Bhutanese Ngultrum (BTN)>\n<BWP = Botswanan Pula (BWP)>\n<BYN = Belarusian Ruble (BYN)>\n<BYR = Belarusian Ruble (2000-2016) (BYR)>\n<BZD = Belize Dollar (BZD)>\n<CAD = Canadian Dollar (CA$)>\n<CDF = Congolese Franc (CDF)>\n<CHF = Swiss Franc (CHF)>\n<CLF = Chilean Unit of Account (UF) (CLF)>\n<CLP = Chilean Peso (CLP)>\n```';
            await self.bot.say(errorMsg)
            errorMsg = '```Markdown\n<CNH = CNH (CNH)>\n<CNY = Chinese Yuan (CN¥)>\n<COP = Colombian Peso (COP)>\n<CRC = Costa Rican Colón (CRC)>\n<CUP = Cuban Peso (CUP)>\n<CVE = Cape Verdean Escudo (CVE)>\n<CZK = Czech Republic Koruna (CZK)>\n<DEM = German Mark (DEM)>\n<DJF = Djiboutian Franc (DJF)>\n<DKK = Danish Krone (DKK)>\n<DOP = Dominican Peso (DOP)>\n<DZD = Algerian Dinar (DZD)>\n<EGP = Egyptian Pound (EGP)>\n<ERN = Eritrean Nakfa (ERN)>\n<ETB = Ethiopian Birr (ETB)>\n<EUR = Euro (€)>\n<FIM = Finnish Markka (FIM)>\n<FJD = Fijian Dollar (FJD)>\n<FKP = Falkland Islands Pound (FKP)>\n<FRF = French Franc (FRF)>\n<GBP = British Pound (£)>\n<GEL = Georgian Lari (GEL)>\n<GHS = Ghanaian Cedi (GHS)>\n<GIP = Gibraltar Pound (GIP)>\n<GMD = Gambian Dalasi (GMD)>\n<GNF = Guinean Franc (GNF)>\n<GTQ = Guatemalan Quetzal (GTQ)>\n<GYD = Guyanaese Dollar (GYD)>\n<HKD = Hong Kong Dollar (HK$)>\n<HNL = Honduran Lempira (HNL)>\n<HRK = Croatian Kuna (HRK)>\n<HTG = Haitian Gourde (HTG)>\n<HUF = Hungarian Forint (HUF)>\n<IDR = Indonesian Rupiah (IDR)>\n<IEP = Irish Pound (IEP)>\n<ILS = Israeli New Sheqel (₪)>\n<INR = Indian Rupee (₹)>\n<IQD = Iraqi Dinar (IQD)>\n<IRR = Iranian Rial (IRR)>\n<ISK = Icelandic Króna (ISK)>\n<ITL = Italian Lira (ITL)>\n<JMD = Jamaican Dollar (JMD)>\n<JOD = Jordanian Dinar (JOD)>\n<JPY = Japanese Yen (¥)>\n<KES = Kenyan Shilling (KES)>\n<KGS = Kyrgystani Som (KGS)>\n<KHR = Cambodian Riel (KHR)>\n<KMF = Comorian Franc (KMF)>\n```';
            await self.bot.say(errorMsg)
            errorMsg = '```Markdown\n<KPW = North Korean Won (KPW)>\n<KRW = South Korean Won (₩)>\n<KWD = Kuwaiti Dinar (KWD)>\n<KYD = Cayman Islands Dollar (KYD)>\n<KZT = Kazakhstani Tenge (KZT)>\n<LAK = Laotian Kip (LAK)>\n<LBP = Lebanese Pound (LBP)>\n<LKR = Sri Lankan Rupee (LKR)>\n<LRD = Liberian Dollar (LRD)>\n<LSL = Lesotho Loti (LSL)>\n<LTL = Lithuanian Litas (LTL)>\n<LVL = Latvian Lats (LVL)>\n<LYD = Libyan Dinar (LYD)>\n<MAD = Moroccan Dirham (MAD)>\n<MDL = Moldovan Leu (MDL)>\n<MGA = Malagasy Ariary (MGA)>\n<MKD = Macedonian Denar (MKD)>\n<MMK = Myanmar Kyat (MMK)>\n<MNT = Mongolian Tugrik (MNT)>\n<MOP = Macanese Pataca (MOP)>\n<MRO = Mauritanian Ouguiya (MRO)>\n<MUR = Mauritian Rupee (MUR)>\n<MVR = Maldivian Rufiyaa (MVR)>\n<MWK = Malawian Kwacha (MWK)>\n<MXN = Mexican Peso (MX$)>\n<MYR = Malaysian Ringgit (MYR)>\n<MZN = Mozambican Metical (MZN)>\n<NAD = Namibian Dollar (NAD)>\n<NGN = Nigerian Naira (NGN)>\n<NIO = Nicaraguan Córdoba (NIO)>\n<NOK = Norwegian Krone (NOK)>\n<NPR = Nepalese Rupee (NPR)>\n<NZD = New Zealand Dollar (NZ$)>\n<OMR = Omani Rial (OMR)>\n<PAB = Panamanian Balboa (PAB)>\n<PEN = Peruvian Nuevo Sol (PEN)>\n<PGK = Papua New Guinean Kina (PGK)>\n```';
            await self.bot.say(errorMsg)
            errorMsg = '```Markdown\n<PHP = Philippine Peso (PHP)>\n<PKG = PKG (PKG)>\n<PKR = Pakistani Rupee (PKR)>\n<PLN = Polish Zloty (PLN)>\n<PYG = Paraguayan Guarani (PYG)>\n<QAR = Qatari Rial (QAR)>\n<RON = Romanian Leu (RON)>\n<RSD = Serbian Dinar (RSD)>\n<RUB = Russian Ruble (RUB)>\n<RWF = Rwandan Franc (RWF)>\n<SAR = Saudi Riyal (SAR)>\n<SBD = Solomon Islands Dollar (SBD)>\n<SCR = Seychellois Rupee (SCR)>\n<SDG = Sudanese Pound (SDG)>\n<SEK = Swedish Krona (SEK)>\n<SGD = Singapore Dollar (SGD)>\n<SHP = St. Helena Pound (SHP)>\n<SKK = Slovak Koruna (SKK)>\n<SLL = Sierra Leonean Leone (SLL)>\n<SOS = Somali Shilling (SOS)>\n<SRD = Surinamese Dollar (SRD)>\n<STD = São Tomé & Príncipe Dobra (STD)>\n<SVC = Salvadoran Colón (SVC)>\n<SYP = Syrian Pound (SYP)>\n<SZL = Swazi Lilangeni (SZL)>\n<THB = Thai Baht (THB)>\n<TJS = Tajikistani Somoni (TJS)>\n<TMT = Turkmenistani Manat (TMT)>\n<TND = Tunisian Dinar (TND)>\n<TOP = Tongan Paʻanga (TOP)>\n<TRY = Turkish Lira (TRY)>\n<TTD = Trinidad & Tobago Dollar (TTD)>\n<TWD = New Taiwan Dollar (NT$)>\n<TZS = Tanzanian Shilling (TZS)>\n<UAH = Ukrainian Hryvnia (UAH)>\n<UGX = Ugandan Shilling (UGX)>\n<USD = US Dollar ($)>\n<UYU = Uruguayan Peso (UYU)>\n<UZS = Uzbekistani Som (UZS)>\n<VEF = Venezuelan Bolívar (VEF)>\n<VND = Vietnamese Dong (₫)>\n<VUV = Vanuatu Vatu (VUV)>\n<WST = Samoan Tala (WST)>\n<XAF = Central African CFA Franc (FCFA)>\n<XCD = East Caribbean Dollar (EC$)>\n<XDR = Special Drawing Rights (XDR)>\n<XOF = West African CFA Franc (CFA)>\n<XPF = CFP Franc (CFPF)>\n<YER = Yemeni Rial (YER)>\n<ZAR = South African Rand (ZAR)>\n<ZMK = Zambian Kwacha (1968–2012) (ZMK)>\n<ZMW = Zambian Kwacha (ZMW)>\n<ZWL = Zimbabwean Dollar (2009) (ZWL)>\n```';
            await self.bot.say(errorMsg)
            return;
        
        convert_url = "http://apilayer.net/api/live?access_key=%s&currencies=%s&source=USD&format=1"%(key,to)
        r = requests.get(convert_url)
        js = r.json()
        result = "```py\n%d USD:\n"%amount
        for i in ugh:
            result += "%r %s\n"%(js['quotes']['USD%s'%i] * amount, i)
            
        result += "```"
        # result = '\n'.join("{!s} = {!r}".format(key,val) for (key,val) in res.items())
        
        if result:
            await self.bot.say(result)
        else:
            await self.bot.say("Whoops!  I couldn't make that conversion.")

    @commands.command(pass_context=True, no_pm=True)
    async def userinfo(self, ctx, *, user: discord.Member=None):
        """Shows users's info"""
        author = ctx.message.author
        server = ctx.message.server
        if not user:
            user = author
        roles = [x.name for x in user.roles if x.name != "@everyone"]
        joined_at = user.joined_at
        since_created = (ctx.message.timestamp - user.created_at).days
        since_joined = (ctx.message.timestamp - joined_at).days
        user_joined = joined_at.strftime("%d %b %Y %H:%M")
        user_created = user.created_at.strftime("%d %b %Y %H:%M")
        member_number = sorted(server.members,
                               key=lambda m: m.joined_at).index(user) + 1
        created_on = "{}\n({} days ago)".format(user_created, since_created)
        joined_on = "{}\n({} days ago)".format(user_joined, since_joined)
        game = "Chilling in {} status".format(user.status)
        if user.game is None:
            pass
        elif user.game.url is None:
            game = "Playing {}".format(user.game)
        else:
            game = "Streaming: [{}]({})".format(user.game, user.game.url)
        if roles:
            roles = sorted(roles, key=[x.name for x in server.role_hierarchy
                                       if x.name != "@everyone"].index)
            roles = ", ".join(roles)
        else:
            roles = "None"

        data = discord.Embed(description=game, colour=user.colour)
        data.add_field(name="Joined Discord on", value=created_on)
        data.add_field(name="Joined this server on", value=joined_on)
        data.add_field(name="Roles", value=roles, inline=False)
        data.set_footer(text="Member #{} | User ID:{}"
                             "".format(member_number, user.id))
        name = str(user)
        name = " ~ ".join((name, user.nick)) if user.nick else name

        if user.avatar_url:
            data.set_author(name=name, url=user.avatar_url)
            data.set_thumbnail(url=user.avatar_url)
        else:
            data.set_author(name=name)

        try:
            await self.bot.say(embed=data)
        except discord.HTTPException:
            await self.bot.say("I need the `Embed links` permission "
                               "to send this")

    @commands.command(pass_context=True, no_pm=True)
    async def serverinfo(self, ctx):
        """Shows server's info"""
        server = ctx.message.server
        online = len([m.status for m in server.members
                      if m.status == discord.Status.online or
                      m.status == discord.Status.idle])
        total_users = len(server.members)
        text_channels = len([x for x in server.channels
                             if x.type == discord.ChannelType.text])
        voice_channels = len(server.channels) - text_channels
        passed = (ctx.message.timestamp - server.created_at).days
        created_at = ("Since {}. That's over {} days ago!"
                      "".format(server.created_at.strftime("%d %b %Y %H:%M"),
                                passed))

        colour = ''.join([choice('0123456789ABCDEF') for x in range(6)])
        colour = int(colour, 16)

        data = discord.Embed(
            description=created_at,
            colour=discord.Colour(value=colour))
        data.add_field(name="Region", value=str(server.region))
        data.add_field(name="Users", value="{}/{}".format(online, total_users))
        data.add_field(name="Text Channels", value=text_channels)
        data.add_field(name="Voice Channels", value=voice_channels)
        data.add_field(name="Roles", value=len(server.roles))
        data.add_field(name="Owner", value=str(server.owner))
        data.set_footer(text="Server ID: " + server.id)

        if server.icon_url:
            data.set_author(name=server.name, url=server.icon_url)
            data.set_thumbnail(url=server.icon_url)
        else:
            data.set_author(name=server.name)

        try:
            await self.bot.say(embed=data)
        except discord.HTTPException:
            await self.bot.say("I need the `Embed links` permission "
                               "to send this")

    @commands.command()
    async def urban(self, ctx, *, search_terms:str, definition_number:int=1):
        """Urban Dictionary search

        Definition number must be between 1 and 10"""
        def encode(s):
            return quote_plus(s, encoding='utf-8', errors='replace')

        # definition_number is just there to show up in the help
        # all this mess is to avoid forcing double quotes on the user

        search_terms = search_terms.split(" ")
        try:
            if len(search_terms) > 1:
                pos = int(search_terms[-1]) - 1
                search_terms = search_terms[:-1]
            else:
                pos = 0
            if pos not in range(0, 11): # API only provides the
                pos = 0                 # top 10 definitions
        except ValueError:
            pos = 0

        search_terms = "+".join([encode(s) for s in search_terms])
        url = "http://api.urbandictionary.com/v0/define?term=" + search_terms
        try:
            async with aiohttp.get(url) as r:
                result = await r.json()
            if result["list"]:
                definition = result['list'][pos]['definition']
                example = result['list'][pos]['example']
                defs = len(result['list'])
                msg = ("**Definition #{} out of {}:\n**{}\n\n"
                       "**Example:\n**{}".format(pos+1, defs, definition,
                                                 example))
                msg = pagify(msg, ["\n"])
                for page in msg:
                    await self.bot.say(page)
            else:
                await self.bot.say("Your search terms gave no results.")
        except IndexError:
            await self.bot.say("There is no definition #{}".format(pos+1))
        except:
            await self.bot.say("Error.")

    @commands.command(pass_context=True, no_pm=True)
    async def poll(self, ctx, *text):
        """Starts/stops a poll

        Usage example:
        poll Is this a poll?;Yes;No;Maybe
        poll stop"""
        message = ctx.message
        if len(text) == 1:
            if text[0].lower() == "stop":
                await self.endpoll(message)
                return
        if not self.getPollByChannel(message):
            check = " ".join(text).lower()
            if "@everyone" in check or "@here" in check:
                await self.bot.say("Nice try.")
                return
            p = NewPoll(message, " ".join(text), self)
            if p.valid:
                self.poll_sessions.append(p)
                await p.start()
            else:
                await self.bot.say("poll question;option1;option2 (...)")
        else:
            await self.bot.say("A poll is already ongoing in this channel.")

    async def endpoll(self, message):
        if self.getPollByChannel(message):
            p = self.getPollByChannel(message)
            if p.author == message.author.id: # or isMemberAdmin(message)
                await self.getPollByChannel(message).endPoll()
            else:
                await self.bot.say("Only admins and the author can stop the poll.")
        else:
            await self.bot.say("There's no poll ongoing in this channel.")

    def getPollByChannel(self, message):
        for poll in self.poll_sessions:
            if poll.channel == message.channel:
                return poll
        return False

    async def check_poll_votes(self, message):
        if message.author.id != self.bot.user.id:
            if self.getPollByChannel(message):
                    self.getPollByChannel(message).checkAnswer(message)


class NewPoll():
    def __init__(self, message, text, main):
        self.channel = message.channel
        self.author = message.author.id
        self.client = main.bot
        self.poll_sessions = main.poll_sessions
        msg = [ans.strip() for ans in text.split(";")]
        if len(msg) < 2: # Needs at least one question and 2 choices
            self.valid = False
            return None
        else:
            self.valid = True
        self.already_voted = []
        self.question = msg[0]
        msg.remove(self.question)
        self.answers = {}
        i = 1
        for answer in msg: # {id : {answer, votes}}
            self.answers[i] = {"ANSWER" : answer, "VOTES" : 0}
            i += 1

    async def start(self):
        msg = "**POLL STARTED!**\n\n{}\n\n".format(self.question)
        for id, data in self.answers.items():
            msg += "{}. *{}*\n".format(id, data["ANSWER"])
        msg += "\nType the number to vote!"
        await self.client.send_message(self.channel, msg)
        await asyncio.sleep(settings["POLL_DURATION"])
        if self.valid:
            await self.endPoll()

    async def endPoll(self):
        self.valid = False
        msg = "**POLL ENDED!**\n\n{}\n\n".format(self.question)
        for data in self.answers.values():
            msg += "*{}* - {} votes\n".format(data["ANSWER"], str(data["VOTES"]))
        await self.client.send_message(self.channel, msg)
        self.poll_sessions.remove(self)

    def checkAnswer(self, message):
        try:
            i = int(message.content)
            if i in self.answers.keys():
                if message.author.id not in self.already_voted:
                    data = self.answers[i]
                    data["VOTES"] += 1
                    self.answers[i] = data
                    self.already_voted.append(message.author.id)
        except ValueError:
            pass

def setup(bot):
    n = General(bot)
    bot.add_listener(n.check_poll_votes, "on_message")
    bot.add_cog(n)
