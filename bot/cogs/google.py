import discord
from discord.ext import commands
import json
import aiohttp
import urllib.parse
from urllib.parse import quote as uriquote
import os
import aiohttp
from lxml import etree
from bs4 import BeautifulSoup
from urllib.parse import parse_qs, quote_plus
from random import choice
from .utils import keys, config, DisplayName, helpers

'''Module for google web and image search.'''

def embed_perms(message):
    try:
        check = message.author.permissions_in(message.channel).embed_links
    except:
        check = True

    return check

async def get_google_entries(query):
    url = 'https://www.google.com/search?q={}'.format(uriquote(query))
    params = {
        'safe': 'off',
        'lr': 'lang_en',
        'h1': 'en'
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; Win64; x64)'
    }
    entries = []
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, headers=headers) as resp:
            if resp.status != 200:
                async with session.get("https://www.googleapis.com/customsearch/v1?q=" + quote_plus(query) + "&start=" + '1' + "&key=" + keys.maps + "&cx=" + keys.engine) as resp:
                    result = json.loads(await resp.text())
                return None, result['items'][0]['link']

            try:
                root = etree.fromstring(await resp.text(), etree.HTMLParser())
                search_nodes = root.findall(".//div[@class='g']")
                for node in search_nodes:
                    url_node = node.find('.//h3/a')
                    if url_node is None:
                        continue
                    url = url_node.attrib['href']
                    if not url.startswith('/url?'):
                        continue
                    url = parse_qs(url[5:])['q'][0]
                    entries.append(url)
            except NameError:
                root = BeautifulSoup(await resp.text(), 'html.parser')
                for result in root.find_all("div", class_='g'):
                    url_node = result.find('h3')
                    if url_node:
                        for link in url_node.find_all('a', href=True):
                            url = link['href']
                            if not url.startswith('/url?'):
                                continue
                            url = parse_qs(url[5:])['q'][0]
                            entries.append(url)
    return entries, root


class Google:

    def __init__(self, bot):
        self.bot = bot

    async def sendprompt(self):
        botowner = discord.utils.find(lambda m: m.id == config.owner, self.bot.get_all_members())
        if keys.engine is None and keys.img is None:
            message = "To use the google cog, you MUST get a Google API key, and enable the custom-search API\n\n\
        start at https://console.developers.google.com/apis/library/customsearch.googleapis.com/\n\n\
        then follow directions at https://console.developers.google.com/apis/library/customsearch.googleapis.com/\n\n\
        You'll make two engines, one can just have https://www.google.com as the site to search.\n\n\
        The search engine ID for that goes into 'engine' in the cogs/utils/key.py file.\n\n\
        The 2nd, make sure you select 'Image Search' and enter whatever sites you please to search for images by keywords.\n\n\
        Using google won't work well, so pick something like http://www.picsearch.com/* or giphy or whatever the fuck.\n\n\
        That Search Engine ID goes in img in the keys.py file.\n\n\
        You only get 100 free searches a day, but the functionality is worth the effort. Good luck!"
            await self.bot.send_message(botowner, message)
        else:
            pass

    def parse_google_card(self, node):
        if node is None or type(node) is int:
            return None
        
        colour = ''.join([choice('0123456789ABCDEF') for x in range(6)])
        colour = int(colour, 16)
        e = discord.Embed(colour=discord.Colour(value=colour))

        # check if it's a calculator card:
        calculator = node.find(".//table/tr/td/span[@class='nobr']/h2[@class='r']")
        if calculator is not None:
            e.title = 'Calculator'
            e.description = ''.join(calculator.itertext())
            return e

        parent = node.getparent()

        # check for unit conversion card
        unit = parent.find(".//ol//div[@class='_Tsb']")
        if unit is not None:
            e.title = 'Unit Conversion'
            e.description = ''.join(''.join(n.itertext()) for n in unit)
            return e

        # check for currency conversion card
        currency = parent.find(".//ol/table[@class='std _tLi']/tr/td/h2")
        if currency is not None:
            e.title = 'Currency Conversion'
            e.description = ''.join(currency.itertext())
            return e

        # check for release date card
        release = parent.find(".//div[@id='_vBb']")
        if release is not None:
            try:
                e.description = ''.join(release[0].itertext()).strip()
                e.title = ''.join(release[1].itertext()).strip()
                return e
            except:
                return None

        # check for definition card
        words = parent.find(".//ol/div[@class='g']/div/h3[@class='r']/div")
        if words is not None:
            try:
                definition_info = words.getparent().getparent()[1]
            except:
                pass
            else:
                try:
                    e.title = words[0].text
                    e.description = words[1].text
                except:
                    return None
                for row in definition_info:
                    if len(row.attrib) != 0:
                        break
                    try:
                        data = row[0]
                        lexical_category = data[0].text
                        body = []
                        for index, definition in enumerate(data[1], 1):
                            body.append('%s. %s' % (index, definition.text))
                        e.add_field(name=lexical_category, value='\n'.join(body), inline=False)
                    except:
                        continue
                return e

        # check for translate card
        words = parent.find(".//ol/div[@class='g']/div/table/tr/td/h3[@class='r']")
        if words is not None:
            print(words)
            e.title = 'Google Translate'
            e.add_field(name='Input', value=words[0].text,  inline=True)
            e.add_field(name='Out', value=words[1].text,  inline=True)
            return e

        # check for "time in" card
        time_in = parent.find(".//ol//div[@class='_Tsb _HOb _Qeb']")
        if time_in is not None:
            try:
                time_place = ''.join(time_in.find("span[@class='_HOb _Qeb']").itertext()).strip()
                the_time = ''.join(time_in.find("div[@class='_rkc _Peb']").itertext()).strip()
                the_date = ''.join(time_in.find("div[@class='_HOb _Qeb']").itertext()).strip()
            except:
                return None
            else:
                e.title = time_place
                e.description = '%s\n%s' % (the_time, the_date)
                return e

        weather = parent.find(".//ol//div[@class='e']")
        if weather is None:
            return None

        location = weather.find('h3')
        if location is None:
            return None

        e.title = ''.join(location.itertext())

        table = weather.find('table')
        if table is None:
            return None

        try:
            tr = table[0]
            img = tr[0].find('img')
            category = img.get('alt')
            image = 'https:' + img.get('src')
            temperature = tr[1].xpath("./span[@class='wob_t']//text()")[0]
        except:
            return None
        else:
            e.set_thumbnail(url=image)
            e.description = '*%s*' % category
            e.add_field(name='Temperature', value=temperature)

        try:
            wind = ''.join(table[3].itertext()).replace('Wind: ', '')
        except:
            return None
        else:
            e.add_field(name='Wind', value=wind)

        try:
            humidity = ''.join(table[4][0].itertext()).replace('Humidity: ', '')
        except:
            return None
        else:
            e.add_field(name='Humidity', value=humidity)

        return e

    @commands.command(pass_context=True)
    async def g(self, ctx, *, query):
        """Google web search. Ex: [p]g define screw"""
        await self.sendprompt()
        if not embed_perms(ctx.message):
            async with aiohttp.ClientSession() as session:
                async with session.get("https://www.googleapis.com/customsearch/v1?q=" + urllib.parse.quote_plus(query) + "&start=" + '1' + "&key=" + keys.maps + "&cx=" + keys.engine) as resp:
                    result = json.loads(await resp.text())
            return await self.bot.say(result['items'][0]['link'])

        try:
            entries, root = await get_google_entries(query)
            card_node = root.find(".//div[@id='topstuff']")
            card = self.parse_google_card(card_node)
        except RuntimeError as e:
            await self.bot.say(str(e))
        else:
            if card:
                value = '\n'.join(entries[:2])
                if value:
                    card.add_field(name='Search Results', value=value, inline=False)
                return await self.bot.say(embed=card)
            if len(entries) == 0:
                return await self.bot.say('No results.')
            next_two = entries[1:3]
            if next_two:
                formatted = '\n'.join(map(lambda x: '<%s>' % x, next_two))
                msg = '{}\n\n**See also:**\n{}'.format(entries[0], formatted)
            else:
                msg = entries[0]
            await self.bot.say(msg)

    @commands.command(pass_context=True, aliases=['image', 'img'])
    async def i(self, ctx, *, query):
        """Google image search. [p]i Lillie pokemon sun and moon"""
        await self.sendprompt()
        await self.bot.delete_message(ctx.message)
        async with aiohttp.ClientSession() as session:
            async with session.get("https://www.googleapis.com/customsearch/v1?q=" + urllib.parse.quote_plus(query) + "&start=" + '1' + "&key=" + keys.maps + "&cx=" + keys.img + "&searchType=image") as resp:
                if resp.status != 200:
                    if not keys.maps or not keys.img:
                        return await self.bot.say("You don't seem to have image searching configured properly.")
                    return await self.bot.say('Google failed to respond.')
                else:
                    result = json.loads(await resp.text())
                    try:
                        result['items']
                    except:
                        return await self.bot.say('There were no results to your search. Use more common search query or make sure you have image search enabled for your custom search engine.')
                    if len(result['items']) < 1:
                        return await self.bot.say('There were no results to your search. Use more common search query or make sure you have image search enabled for your custom search engine.')
                    
                    colour = ''.join([choice('0123456789ABCDEF') for x in range(6)])
                    colour = int(colour, 16)
                    if len(result['items']) > 1:
                        item = choice(range(len(result['items'])))
                    else:
                        item = 0
                    em = discord.Embed(colour=discord.Colour(value=colour))
                    if embed_perms(ctx.message):
                        em.set_image(url=result['items'][item]['link'])
                        show_search = True
                        if show_search == "True":
                            em.set_footer(text="Search term: \"" + query + "\"")
                        await self.bot.say(content=None, embed=em)
                    else:
                        await self.bot.say(result['items'][item]['link'])
                        await self.bot.say("Search term: \"" + query + "\"")


def setup(bot):
    n = Google(bot)
    bot.add_cog(n)