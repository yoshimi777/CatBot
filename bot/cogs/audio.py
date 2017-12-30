import asyncio
import aiohttp
import collections
import copy
import inspect
import logging
import math
import os
import re
import subprocess
import sys
import threading
import time
from json import JSONDecodeError
from random import choice, shuffle
from urllib.parse import urlparse, quote_plus

import discord
import youtube_dl
from cogs.utils import checks, config, exceptions, keys
from cogs.utils.chat_formatting import pagify
from cogs.utils.dataIO import dataIO
from discord.ext import commands
from youtube_dl import utils

__author__ = "tekulvw" #code borrowed and modified from https://github.com/Cog-Creators/Red-DiscordBot

log = logging.getLogger(__name__)

try:
   import youtube_dl
except:
   youtube_dl = None

try:
    if not discord.opus.is_loaded():
        discord.opus.load_opus('libopus-0.dll')
except OSError:  # Incorrect bitness
    opus = False
except:  # Missing opus
    opus = None
else:
    opus = True

youtube_dl_options = {
    'source_address': '0.0.0.0',
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': "mp3",
    'outtmpl': '%(id)s',
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'quiet': True,
    'no_warnings': True,
    'outtmpl': "data/audio/cache/%(id)s",
    'default_search': 'auto'
}




class MaximumLength(Exception):
    def __init__(self, m):
        self.message = m

    def __str__(self):
        return self.message


class NotConnected(Exception):
    pass


class AuthorNotConnected(NotConnected):
    pass


class VoiceNotConnected(NotConnected):
    pass


class UnauthorizedConnect(Exception):
    pass


class UnauthorizedSpeak(Exception):
    pass


class ChannelUserLimit(Exception):
    pass


class UnauthorizedSave(Exception):
    pass


class ConnectTimeout(NotConnected):
    pass


class InvalidURL(Exception):
    pass


class InvalidSong(InvalidURL):
    pass


class InvalidPlaylist(InvalidSong):
    pass


class deque(collections.deque):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def peek(self):
        ret = self.pop()
        self.append(ret)
        return copy.deepcopy(ret)

    def peekleft(self):
        ret = self.popleft()
        self.appendleft(ret)
        return copy.deepcopy(ret)


class Song:
    def __init__(self, **kwargs):
        self.__dict__ = kwargs
        self.title = kwargs.pop('title', None)
        self.id = kwargs.pop('id', None)
        self.url = kwargs.pop('url', None)
        self.webpage_url = kwargs.pop('webpage_url', "")
        self.duration = kwargs.pop('duration', "")


class Playlist:
    def __init__(self, server=None, sid=None, name=None, author=None, url=None,
                 playlist=None, path=None, main_class=None, **kwargs):

        self.server = server
        self._sid = sid
        self.name = name
        # this is an id......
        self.author = author
        self.url = url
        self.main_class = main_class  
        self.path = path

        if url is None and "link" in kwargs:
            self.url = kwargs.get('link')
        self.playlist = playlist

    @property
    def filename(self):
        f = "data/audio/playlists"
        f = os.path.join(f, self.sid, self.name + ".txt")
        return f

    def to_json(self):
        ret = {"author": self.author, "playlist": self.playlist,
               "link": self.url}
        return ret

    def is_author(self, user):
        """checks if the user is the author of this playlist
        Returns True/False"""
        return user.id == self.author

    def can_edit(self, user):
        """right now checks if user is mod or higher including server owner
        global playlists are uneditable atm"""


        if self.main_class._playlist_exists_global(self.name):
            return False

        is_playlist_author = self.is_author(user)
        is_bot_owner = user.id == config.owner
        is_server_owner = self.server.owner.id == self.author

        return any((is_playlist_author,
                    is_bot_owner,
                    is_server_owner))

    def append_song(self, author, url):
        if not self.can_edit(author):
            raise UnauthorizedSave
        elif not self.main_class._valid_playable_url(url):
            raise InvalidURL
        else:
            self.playlist.append(url)
            self.save()

    def save(self):
        dataIO.save_json(self.path, self.to_json())

    @property
    def sid(self):
        if self._sid:
            return self._sid
        elif self.server:
            return self.server.id
        else:
            return None


class Downloader(threading.Thread):
    def __init__(self, url, max_duration=None, download=False,
                 cache_path="data/audio/cache", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url = url
        self.max_duration = max_duration
        self.done = threading.Event()
        self.song = None
        self.failed = False
        self._download = download
        self.hit_max_length = threading.Event()
        self._yt = None
        self.cache_path = cache_path

    def run(self):
        try:
            self.get_info()
            if self._download:
                self.download()
        except MaximumLength:
            self.hit_max_length.set()
        except:
            self.failed = True
        self.done.set()

    def download(self):
        self.duration_check()

        if not os.path.isfile('data/audio/cache' + self.song.id):
            video = self._yt.extract_info(self.url)
            self.song = Song(**video)

    def duration_check(self):
        if self.max_duration and self.song.duration > self.max_duration:
            log.debug("songid {} too long".format(self.song.id))
            raise MaximumLength("songid {} has duration {} > {}".format(
                self.song.id, self.song.duration, self.max_duration))

    def get_info(self):
        if self._yt is None:
            self._yt = youtube_dl.YoutubeDL(youtube_dl_options)
        if "[SEARCH:]" not in self.url:
            video = self._yt.extract_info(self.url, download=False,
                                          process=False)
        else:
            self.url = self.url[9:]
            yt_id = self._yt.extract_info(
                self.url, download=False)["entries"][0]["id"]
            # Should handle errors here ^
            self.url = "https://youtube.com/watch?v={}".format(yt_id)
            video = self._yt.extract_info(self.url, download=False,
                                          process=False)

        self.song = Song(**video)


class Audio:
    """Music Streaming."""

    def __init__(self, bot, player):
        self.bot = bot
        self.queue = {}  # add deque's, repeat
        self.downloaders = {}  # sid: object
        self.settings = dataIO.load_json("data/audio/settings.json")
        self.server_specific_setting_keys = ["VOLUME"]
        self.cache_path = "data/audio/cache"
        self.local_playlist_path = "data/audio/localtracks"
        self._old_game = False
        self.connect_timers = {}
        self.is_paused = threading.Event()
        self.is_paused.clear()
        if player == "ffmpeg":
            self.settings["AVCONV"] = False
        elif player == "avconv":
            self.settings["AVCONV"] = True
        self.save_settings()

    async def send_cmd_help(self, ctx):
        if ctx.invoked_subcommand:
            pages = self.bot.formatter.format_help_for(ctx, ctx.invoked_subcommand)
            for page in pages:
                await self.bot.send_message(ctx.message.channel, page)
        else:
            pages = self.bot.formatter.format_help_for(ctx, ctx.command)
            for page in pages:
                await self.bot.send_message(ctx.message.channel, page)
    
    async def _add_song_status(self, song):
        if self._old_game is False:
            self._old_game = list(self.bot.servers)[0].me.game
        status = list(self.bot.servers)[0].me.status
        prefix = u'\u275A\u275A ' if self.is_paused.is_set() else ''
        name = u'{}{}'.format(prefix, song.title)[:128]
        game = discord.Game(name=name)
        await self.bot.change_presence(status=status, game=game)

    def _add_to_queue(self, server, url):
        if server.id not in self.queue:
            self._setup_queue(server)
        self.queue[server.id]["QUEUE"].append(url)

    def _add_to_temp_queue(self, server, url):
        if server.id not in self.queue:
            self._setup_queue(server)
        self.queue[server.id]["TEMP_QUEUE"].append(url)

    def _addleft_to_queue(self, server, url):
        if server.id not in self.queue:
            self._setup_queue(server)
        self.queue[server.id]["QUEUE"].appendleft(url)

    def _cache_desired_files(self):
        filelist = []
        for server in self.downloaders:
            song = self.downloaders[server].song
            try:
                filelist.append(song.id)
            except AttributeError:
                pass
        shuffle(filelist)
        return filelist

    def _cache_max(self):
        setting_max = self.settings["MAX_CACHE"]
        return max([setting_max, self._cache_min()])  # enforcing hard limit

    def _cache_min(self):
        x = self._server_count()
        return max([60, 48 * math.log(x) * x**0.3])  # log is not log10

    def _cache_required_files(self):
        queue = copy.deepcopy(self.queue)
        filelist = []
        for server in queue:
            now_playing = queue[server].get("NOW_PLAYING")
            try:
                filelist.append(now_playing.id)
            except AttributeError:
                pass
        return filelist

    def _cache_size(self):
        songs = os.listdir(self.cache_path)
        size = sum(map(lambda s: os.path.getsize(
            os.path.join(self.cache_path, s)) / 10**6, songs))
        return size

    def _cache_too_large(self):
        if self._cache_size() > self._cache_max():
            return True
        return False

    def _clear_queue(self, server):
        if server.id not in self.queue:
            return
        self.queue[server.id]["QUEUE"] = deque()
        self.queue[server.id]["TEMP_QUEUE"] = deque()

    async def _create_ffmpeg_player(self, server, filename, local=False):
        """This function will guarantee we have a valid voice client,
            even if one doesn't exist previously."""
        voice_channel_id = self.queue[server.id]["VOICE_CHANNEL_ID"]
        voice_client = self.voice_client(server)

        if voice_client is None:
            log.debug("not connected when we should be in sid {}".format(
                server.id))
            to_connect = self.bot.get_channel(voice_channel_id)
            if to_connect is None:
                raise VoiceNotConnected("Okay somehow we're not connected and"
                                        " we have no valid channel to"
                                        " reconnect to. In other words...LOL"
                                        " REKT.")
            log.debug("valid reconnect channel for sid"
                      " {}, reconnecting...".format(server.id))
            await self._join_voice_channel(to_connect)  # SHIT
        elif voice_client.channel.id != voice_channel_id:
            # This was decided at 3:45 EST in #advanced-testing by 26
            self.queue[server.id]["VOICE_CHANNEL_ID"] = voice_client.channel.id

        # Okay if we reach here we definitively have a working voice_client

        if local:
            song_filename = os.path.join(self.local_playlist_path, filename)
        else:
            song_filename = os.path.join(self.cache_path, filename)

        use_avconv = self.settings["AVCONV"]
        options = '-b:a 256k -bufsize 256k'

        try:
            voice_client.audio_player.process.kill()
        except AttributeError:
            pass
        except ProcessLookupError:
            pass


        voice_client.audio_player = voice_client.create_ffmpeg_player(
            song_filename, use_avconv=use_avconv, options=options)

        # Set initial volume
        vol = self.get_server_settings(server)['VOLUME'] / 100
        voice_client.audio_player.volume = vol

        return voice_client  # Just for ease of use, it's modified in-place

    # TODO: _current_playlist

    # TODO: _current_song

    def _delete_playlist(self, server, name):
        if not name.endswith('.txt'):
            name = name + ".txt"
        try:
            os.remove(os.path.join('data/audio/playlists', server.id, name))
        except OSError:
            pass
        except WindowsError:
            pass


    async def _disconnect_voice_client(self, server):
        if not self.voice_connected(server):
            return

        voice_client = self.voice_client(server)

        await voice_client.disconnect()

    async def _download_all(self, url_list):
        """
        Doesn't actually download, just get's info for uses like queue_list
        """
        downloaders = []
        for url in url_list:
            d = Downloader(url)
            d.start()
            downloaders.append(d)

        while any([d.is_alive() for d in downloaders]):
            await asyncio.sleep(0.1)

        songs = [d.song for d in downloaders if d.song is not None]
        return songs

    async def _download_next(self, server, curr_dl, next_dl):
        """Checks to see if we need to download the next, and does.

        Both curr_dl and next_dl should already be started."""
        if curr_dl.song is None:
            return

        max_length = self.settings["MAX_LENGTH"]

        while next_dl.is_alive():
            await asyncio.sleep(0.5)

        if curr_dl.song.id != next_dl.song.id:
            try:
                next_dl.duration_check()
            except MaximumLength:
                return
            self.downloaders[server.id] = Downloader(next_dl.url, max_length,
                                                     download=True)
            self.downloaders[server.id].start()

    def _dump_cache(self, ignore_desired=False):
        reqd = self._cache_required_files()
        log.debug("required cache files:\n\t{}".format(reqd))

        opt = self._cache_desired_files()
        log.debug("desired cache files:\n\t{}".format(opt))

        prev_size = self._cache_size()

        for file in os.listdir(self.cache_path):
            if file not in reqd:
                if ignore_desired or file not in opt:
                    try:
                        os.remove(os.path.join(self.cache_path, file))
                    except OSError:
                        # A directory got in the cache?
                        pass
                    except WindowsError:
                        # Removing a file in use, reqd failed
                        pass

        post_size = self._cache_size()
        dumped = prev_size - post_size

        if not ignore_desired and self._cache_too_large():
            return dumped + self._dump_cache(ignore_desired=True)

        log.debug("dumped {} MB of audio files".format(dumped))

        return dumped

    # TODO: _enable_controls()

    # returns list of active voice channels
    # assuming list does not change during the execution of this function
    # if that happens, blame asyncio.
    def _get_active_voice_clients(self):
        avcs = []
        for vc in self.bot.voice_clients:
            if hasattr(vc, 'audio_player') and not vc.audio_player.is_done():
                avcs.append(vc)
        return avcs

    def _get_queue(self, server, limit):
        if server.id not in self.queue:
            return []

        ret = []
        for i in range(limit):
            try:
                ret.append(self.queue[server.id]["QUEUE"][i])
            except IndexError:
                pass

        return ret

    def _get_queue_nowplaying(self, server):
        if server.id not in self.queue:
            return None

        return self.queue[server.id]["NOW_PLAYING"]

    def _get_queue_playlist(self, server):
        if server.id not in self.queue:
            return None

        return self.queue[server.id]["PLAYLIST"]

    def _get_queue_repeat(self, server):
        if server.id not in self.queue:
            return None

        return self.queue[server.id]["REPEAT"]

    def _get_queue_tempqueue(self, server, limit):
        if server.id not in self.queue:
            return []

        ret = []
        for i in range(limit):
            try:
                ret.append(self.queue[server.id]["TEMP_QUEUE"][i])
            except IndexError:
                pass
        return ret

    async def _guarantee_downloaded(self, server, url):
        max_length = self.settings["MAX_LENGTH"]
        if server.id not in self.downloaders:  
            self.downloaders[server.id] = Downloader(url, max_length)

        if self.downloaders[server.id].url != url:  
            self.downloaders[server.id] = Downloader(url, max_length)

        try:
            # We're assuming we have the right thing in our downloader object
            self.downloaders[server.id].start()
        except RuntimeError:
            # Queue manager already started it for us, isn't that nice?
            pass

        # Getting info w/o download
        self.downloaders[server.id].done.wait()

        # This will throw a maxlength exception if required
        self.downloaders[server.id].duration_check()
        song = self.downloaders[server.id].song

        # Now we check to see if we have a cache hit
        cache_location = os.path.join(self.cache_path, song.id)
        if not os.path.exists(cache_location):
            self.downloaders[server.id] = Downloader(url, max_length,
                                                     download=True)
            self.downloaders[server.id].start()

            while self.downloaders[server.id].is_alive():
                await asyncio.sleep(0.5)

            song = self.downloaders[server.id].song
        else:
            log.debug("cache hit on song id {}".format(song.id))

        return song

    def _is_queue_playlist(self, server):
        if server.id not in self.queue:
            return False

        return self.queue[server.id]["PLAYLIST"]

    async def _join_voice_channel(self, channel):
        server = channel.server
        connect_time = self.connect_timers.get(server.id, 0)
        if time.time() < connect_time:
            diff = int(connect_time - time.time())
            raise ConnectTimeout("You are on connect cooldown for another {}"
                                 " seconds.".format(diff))
        if server.id in self.queue:
            self.queue[server.id]["VOICE_CHANNEL_ID"] = channel.id
        try:
            await asyncio.wait_for(self.bot.join_voice_channel(channel),
                                   timeout=5, loop=self.bot.loop)
        except asyncio.futures.TimeoutError as e:
            log.exception(e)
            self.connect_timers[server.id] = time.time() + 300
            raise ConnectTimeout("We timed out connecting to a voice channel,"
                                 " please try again in 10 minutes.")

    def _list_local_playlists(self):
        ret = []
        for thing in os.listdir(self.local_playlist_path):
            if os.path.isdir(os.path.join(self.local_playlist_path, thing)):
                ret.append(thing)
        log.debug("local playlists:\n\t{}".format(ret))
        return ret

    def _list_playlists(self, server):
        try:
            server = server.id
        except:
            pass
        path = "data/audio/playlists"
        old_playlists = [f[:-4] for f in os.listdir(path)
                         if f.endswith(".txt")]
        path = os.path.join(path, server)
        if os.path.exists(path):
            new_playlists = [f[:-4] for f in os.listdir(path)
                             if f.endswith(".txt")]
        else:
            new_playlists = []
        return list(set(old_playlists + new_playlists))

    def _load_playlist(self, server, name, local=True):
        try:
            server = server.id
        except:
            pass

        f = "data/audio/playlists"
        if local:
            f = os.path.join(f, server, name + ".txt")
        else:
            f = os.path.join(f, name + ".txt")
        kwargs = dataIO.load_json(f)

        kwargs['path'] = f
        kwargs['main_class'] = self
        kwargs['name'] = name
        kwargs['sid'] = server
        kwargs['server'] = self.bot.get_server(server)

        return Playlist(**kwargs)

    def _local_playlist_songlist(self, name):
        dirpath = os.path.join(self.local_playlist_path, name)
        return sorted(os.listdir(dirpath))

    def _make_local_song(self, filename):
        # filename should be playlist_folder/file_name
        folder, song = os.path.split(filename)
        return Song(name=song.replace('.mp3', ''), id=filename, title=song, url=filename,
                    webpage_url=filename.strip('<>'))

    def _make_playlist(self, author, url, songlist):
        try:
            author = author.id
        except:
            pass

        return Playlist(author=author, url=url, playlist=songlist)

    def _match_sc_playlist(self, url):
        return self._match_sc_url(url)

    def _match_yt_playlist(self, url):
        if not self._match_yt_url(url):
            return False
        yt_playlist = re.compile(
            r'^(https?\:\/\/)?(www\.)?(youtube\.com|youtu\.?be)'
            r'((\/playlist\?)|\/watch\?).*(list=)(.*)(&|$)')
        # Group 6 should be the list ID
        if yt_playlist.match(url):
            return True
        return False

    def _match_sc_url(self, url):
        sc_url = re.compile(
            r'^(https?\:\/\/)?(www\.)?(soundcloud\.com\/)')
        if sc_url.match(url):
            return True
        return False

    def _match_yt_url(self, url):
        yt_link = re.compile(
            r'^(https?\:\/\/)?(www\.|m\.)?(youtube\.com|youtu\.?be)\/.+$')
        if yt_link.match(url):
            return True
        return False

    def _match_any_url(self, url):
        url = urlparse(url)
        if url.scheme and url.netloc and url.path:
            return True
        return False

    # TODO: _next_songs_in_queue

    async def _parse_playlist(self, url):
        if self._match_sc_playlist(url):
            return await self._parse_sc_playlist(url)
        elif self._match_yt_playlist(url):
            return await self._parse_yt_playlist(url)
        raise InvalidPlaylist("The given URL is neither a Soundcloud or"
                              " YouTube playlist.")

    async def _parse_sc_playlist(self, url):
        playlist = []
        d = Downloader(url)
        d.start()

        while d.is_alive():
            await asyncio.sleep(0.5)

        for entry in d.song.entries:
            if entry["url"][4] != "s":
                song_url = "https{}".format(entry["url"][4:])
                playlist.append(song_url)
            else:
                playlist.append(entry.url)

        return playlist

    async def _parse_yt_playlist(self, url):
        d = Downloader(url)
        d.start()
        playlist = []

        while d.is_alive():
            await asyncio.sleep(0.5)

        for entry in d.song.entries:
            try:
                song_url = "https://www.youtube.com/watch?v={}".format(
                    entry['id'])
                playlist.append(song_url)
            except AttributeError:
                pass
            except TypeError:
                pass

        return playlist

    async def _play(self, sid, url):
        """Returns the song object of what's playing"""
        if type(sid) is not discord.Server:
            server = self.bot.get_server(sid)
        else:
            server = sid

        assert type(server) is discord.Server
        if self._match_sc_playlist(url):
            await self.bot.say('No SoundCloud') 
        elif self._match_yt_playlist(url):
            playlist = await self._parse_playlist(url)
            await self._play_playlist(server, playlist)
            
        else:
            if self._valid_playable_url(url) or "[SEARCH:]" in url:
                try:
                    song = await self._guarantee_downloaded(server, url)
                except MaximumLength:
                    raise
                local = False

            else:  # Assume local
                try:
                    song = self._make_local_song(url)
                    local = True
                except FileNotFoundError:
                    raise

        voice_client = await self._create_ffmpeg_player(server, song.id,
                                                        local=local)
        # That ^ creates the audio_player property

        voice_client.audio_player.start()

        return song

    def _play_playlist(self, server, playlist):
        try:
            songlist = playlist.playlist
            name = playlist.name
        except AttributeError:
            songlist = playlist
            name = True

        self._stop_player(server)
        self._stop_downloader(server)
        self._clear_queue(server)

        self._setup_queue(server)
        self._set_queue_playlist(server, name)
        self._set_queue_repeat(server, True)
        self._set_queue(server, songlist)
        

    def _play_local_playlist(self, server, name):
        songlist = self._local_playlist_songlist(name)

        ret = []
        for song in songlist:
            ret.append(os.path.join(name, song))

        ret_playlist = Playlist(server=server, name=name, playlist=ret)
        self._play_playlist(server, ret_playlist)

    def _player_count(self):
        count = 0
        queue = copy.deepcopy(self.queue)
        for sid in queue:
            server = self.bot.get_server(sid)
            try:
                vc = self.voice_client(server)
                if vc.audio_player.is_playing():
                    count += 1
            except:
                pass
        return count

    def _playlist_exists(self, server, name):
        return self._playlist_exists_local(server, name) or \
            self._playlist_exists_global(name)

    def _playlist_exists_global(self, name):
        f = "data/audio/playlists"
        f = os.path.join(f, name + ".txt")
        log.debug('checking for {}'.format(f))

        return dataIO.is_valid_json(f)

    def _playlist_exists_local(self, server, name):
        try:
            server = server.id
        except AttributeError:
            pass

        f = "data/audio/playlists"
        f = os.path.join(f, server, name + ".txt")
        log.debug('checking for {}'.format(f))

        return dataIO.is_valid_json(f)

    def _remove_queue(self, server):
        if server.id in self.queue:
            del self.queue[server.id]

    async def _remove_song_status(self):
        if self._old_game is not False:
            status = list(self.bot.servers)[0].me.status
            await self.bot.change_presence(game=self._old_game,
                                           status=status)
            log.debug('Bot status returned to ' + str(self._old_game))
            self._old_game = False

    def _save_playlist(self, server, name, playlist):
        sid = server.id
        try:
            f = playlist.filename
            playlist = playlist.to_json()
            log.debug("got playlist object")
        except AttributeError:
            f = os.path.join("data/audio/playlists", sid, name + ".txt")

        head, _ = os.path.split(f)
        if not os.path.exists(head):
            os.makedirs(head)

        log.debug("saving playlist '{}' to {}:\n\t{}".format(name, f,
                                                             playlist))
        dataIO.save_json(f, playlist)

    def _shuffle_queue(self, server):
        shuffle(self.queue[server.id]["QUEUE"])

    def _shuffle_temp_queue(self, server):
        shuffle(self.queue[server.id]["TEMP_QUEUE"])

    def _server_count(self):
        return max([1, len(self.bot.servers)])

    def _set_queue(self, server, songlist):
        if server.id in self.queue:
            self._clear_queue(server)
        else:
            self._setup_queue(server)
        self.queue[server.id]["QUEUE"].extend(songlist)

    def _set_queue_channel(self, server, channel):
        if server.id not in self.queue:
            return

        try:
            channel = channel.id
        except AttributeError:
            pass

        self.queue[server.id]["VOICE_CHANNEL_ID"] = channel

    def _set_queue_nowplaying(self, server, song):
        if server.id not in self.queue:
            return

        self.queue[server.id]["NOW_PLAYING"] = song

    def _set_queue_playlist(self, server, name=True):
        if server.id not in self.queue:
            self._setup_queue(server)

        self.queue[server.id]["PLAYLIST"] = name

    def _set_queue_repeat(self, server, value):
        if server.id not in self.queue:
            self._setup_queue(server)

        self.queue[server.id]["REPEAT"] = value

    def _setup_queue(self, server):
        self.queue[server.id] = {"REPEAT": True, "PLAYLIST": False,
                                 "VOICE_CHANNEL_ID": None,
                                 "QUEUE": deque(), "TEMP_QUEUE": deque(),
                                 "NOW_PLAYING": None}

    def _stop(self, server):
        self._setup_queue(server)
        self._stop_player(server)
        self._stop_downloader(server)
        self.bot.loop.create_task(self._update_bot_status())

    async def _stop_and_disconnect(self, server):
        self._stop(server)
        await self._disconnect_voice_client(server)

    def _stop_downloader(self, server):
        if server.id not in self.downloaders:
            return

        del self.downloaders[server.id]

    def _stop_player(self, server):
        if not self.voice_connected(server):
            return

        voice_client = self.voice_client(server)

        if hasattr(voice_client, 'audio_player'):
            voice_client.audio_player.stop()

    # no return. they can check themselves.
    async def _update_bot_status(self):
        if self.settings["TITLE_STATUS"]:
            song = None
            try:
                active_servers = self._get_active_voice_clients()
            except:
                log.debug("Voice client changed while trying to update bot's"
                          " song status")
                return
            if len(active_servers) == 1:
                server = active_servers[0].server
                song = self.queue[server.id]["NOW_PLAYING"]
            if song:
                await self._add_song_status(song)
            elif len(active_servers) > 1:
                    game = discord.Game(name='on {} servers'.format(len(active_servers)))
                    await self.bot.change_presence(game=game)
            else:
                await self._remove_song_status()

    def _valid_playlist_name(self, name):
        for char in name:
            if char.isdigit() or char.isalpha() or char == "_":
                pass
            else:
                return False
        return True

    def _valid_playable_url(self, url):
        yt = self._match_yt_url(url)
        sc = self._match_sc_url(url)
        if yt:  # TODO: Add sc check
            return True
        return False



    @commands.command(pass_context=True, name="vol", no_pm=True)
    async def volume(self, ctx, percent: int=None):
        """Sets the volume (0 - 100)
        Note: volume may be set up to 200 but you may experience clipping."""
        server = ctx.message.server
        if percent is None:
            vol = self.get_server_settings(server)['VOLUME']
            msg = "Volume is currently set to %d%% 🔊" % vol
        elif percent >= 0 and percent <= 200:
            self.set_server_setting(server, "VOLUME", percent)
            msg = "Volume is now set to %d. 🔊" % percent
            if percent > 100:
                msg += ("\nWarning: volume levels above 100 may result in"
                        " clipping")

            # Set volume of playing audio
            vc = self.voice_client(server)
            if vc:
                vc.audio_player.volume = percent / 100

            self.save_settings()
        else:
            msg = "Volume must be between 0 and 100."
        await self.bot.say(msg, delete_after=30)


    @commands.group(pass_context=True, aliases=['shutupkitty'], no_pm=True)
    async def disconnect(self, ctx):
        """Disconnects from voice channel"""
        if ctx.invoked_subcommand is None:
            server = ctx.message.server
            await self._stop_and_disconnect(server)
            await self.bot.say('🙊', delete_after=30)

    @disconnect.command(name="all", hidden=True, no_pm=True)
    async def disconnect_all(self):
        """Disconnects from all voice channels."""
        if ctx.message.author.id != config.owner.id:
            return
        while len(list(self.bot.voice_clients)) != 0:
            vc = list(self.bot.voice_clients)[0]
            await self._stop_and_disconnect(vc.server)
        await self.bot.say("done.", delete_after=30)

    @commands.command(aliases=['herekitty', 'join'], pass_context=True, no_pm=True)
    async def joinvoice(self, ctx):
        """Joins your voice channel"""
        author = ctx.message.author
        server = ctx.message.server
        voice_channel = author.voice_channel

        if voice_channel is not None:
            self._stop(server)

        await self._join_voice_channel(voice_channel)

    @commands.group(pass_context=True, no_pm=True)
    async def local(self, ctx):
        """Local playlists commands"""
        if ctx.invoked_subcommand is None:
            await self.send_cmd_help(ctx)
        
    @local.command(name="song")
    async def local_song(self, ctx, name:str=None):
        """Plays a local song file.  
        
        Name should be folder/filename"""
        server = ctx.message.server
        author = ctx.message.author
        voice_client = self.voice_client(server)
        if voice_client is None:
            await self.bot.say('Use {}herekitty to call the bot to your voice channel'.format(config.prefix))
        if name is not None:
            message = ctx.message.content.replace(config.prefix+'local song ', '').strip()
            name = message
            sid = ctx.message.channel.server.id
            await self._play(sid=sid, url=name)

    @local.command(name="start", pass_context=True, no_pm=True)
    async def play_local(self, ctx, *, name):
        """Plays a local playlist"""
        server = ctx.message.server
        author = ctx.message.author
        voice_channel = author.voice_channel

        # Checking already connected, will join if not

        if not self.voice_connected(server):
            try:
                self.has_connect_perm(author, server)
            except AuthorNotConnected:
                await self.bot.say("You must join a voice channel before I can"
                                   " play anything.", delete_after=30)
                return
            except UnauthorizedConnect:
                await self.bot.say("I don't have permissions to join your"
                                   " voice channel.", delete_after=30)
                return
            except UnauthorizedSpeak:
                await self.bot.say("I don't have permissions to speak in your"
                                   " voice channel.", delete_after=30)
                return
            except ChannelUserLimit:
                await self.bot.say("Your voice channel is full.", delete_after=30)
                return
            else:
                await self._join_voice_channel(voice_channel)
        else:  # We are connected but not to the right channel
            if self.voice_client(server).channel != voice_channel:
                pass  # TODO: Perms

        # Checking if playing in current server

        if self.is_playing(server):
            await self.bot.say("I'm already playing a song on this server!", delete_after=30)
            return  # TODO: Possibly execute queue?

        # If not playing, spawn a downloader if it doesn't exist and begin
        #   downloading the next song

        if self.currently_downloading(server):
            await self.bot.say("I'm already downloading a file!", delete_after=30)
            return

        lists = self._list_local_playlists()

        if not any(map(lambda l: os.path.split(l)[1] == name, lists)):
            await self.bot.say("Local playlist not found.", delete_after=30)
            return

        self._play_local_playlist(server, name)

    @local.command(name="list", no_pm=True)
    async def list_local(self):
        """Lists local playlists"""
        playlists = ", ".join(self._list_local_playlists())
        if playlists:
            playlists = "Available local playlists:\n\n" + playlists
            for page in pagify(playlists, delims=[" "]):
                await self.bot.say(page)
        else:
            await self.bot.say("There are no playlists.", delete_after=30)

    @commands.command(pass_context=True, aliases=["paws"], no_pm=True)
    async def pause(self, ctx):
        """Pauses audio"""
        server = ctx.message.server
        if not self.voice_connected(server):
            await self.bot.say("Not voice connected in this server.", delete_after=30)
            return

        voice_client = self.voice_client(server)

        if not hasattr(voice_client, 'audio_player'):
            await self.bot.say("Nothing playing, nothing to pause.", delete_after=30)
        elif voice_client.audio_player.is_playing():
            voice_client.audio_player.pause()
            self.is_paused.set()
            await self._update_bot_status()
            await self.bot.say(":feet:", delete_after=30)
        else:
            await self.bot.say("Nothing playing, nothing to pause.")
    
    async def ytsearch(self, query: str):
        base = 'https://www.youtube.com/watch?v='
        idName = 'videoId'
        query = query.replace(' ', '+').strip()
        url = f'https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=3&q={query}&type=video&key={keys.yt}' 
        async with aiohttp.get(url) as r:
            js = await r.json()
        id1= js['items'][0]['id']['{idName}']
        newurl = base+id1
        return newurl
                
    @commands.command(pass_context=True, no_pm=True)
    async def play(self, ctx, *, url_or_search_terms):
        """Plays a link/searches - Youtube only"""
        url = url_or_search_terms
        server = ctx.message.server
        author = ctx.message.author
        voice_channel = author.voice_channel

        # Checking if playing in current server

        if self.is_playing(server):
            await ctx.invoke(self._queue, url=url)
            return  # Default to queue

        # Checking already connected, will join if not

        try:
            self.has_connect_perm(author, server)
        except AuthorNotConnected:
            await self.bot.say("You must join a voice channel before I can"
                               " play anything.")
            return
        except UnauthorizedConnect:
            await self.bot.say("I don't have permissions to join your"
                               " voice channel.")
            return
        except UnauthorizedSpeak:
            await self.bot.say("I don't have permissions to speak in your"
                               " voice channel.")
            return
        except ChannelUserLimit:
            await self.bot.say("Your voice channel is full.")
            return

        if not self.voice_connected(server):
            await self._join_voice_channel(voice_channel)
        else:  # We are connected but not to the right channel
            if self.voice_client(server).channel != voice_channel:
                await self._stop_and_disconnect(server)
                await self._join_voice_channel(voice_channel)

        # If not playing, spawn a downloader if it doesn't exist and begin
        #   downloading the next song

        if self.currently_downloading(server):
            await self.bot.say("I'm already downloading a file!", delete_after=30)
            return

        url = url.strip("<>")

        if self._match_any_url(url):
            if not self._valid_playable_url(url):
                await self.bot.say("That's not a valid URL.", delete_after=30)
                return
        else:
             
            url = url.replace("/", "&#47")
            url = await self.ytsearch(query=url)
            

        if "[SEARCH:]" not in url and "youtube" in url:
            url = url.split("&")[0]  # Temp fix for the &list issue

        self._stop_player(server)
        self._clear_queue(server)
        self._add_to_queue(server, url)

    @commands.command(pass_context=True, no_pm=True)
    async def prev(self, ctx):
        """Goes back to the last song."""
        # Current song is in NOW_PLAYING
        server = ctx.message.server

        if self.is_playing(server):
            curr_url = self._get_queue_nowplaying(server).webpage_url
            last_url = None
            if self._is_queue_playlist(server):
                # need to reorder queue
                try:
                    last_url = self.queue[server.id]["QUEUE"].pop()
                except IndexError:
                    pass

            self._addleft_to_queue(server, curr_url)
            if last_url:
                self._addleft_to_queue(server, last_url)
            self._set_queue_nowplaying(server, None)

            self.voice_client(server).audio_player.stop()

            await self.bot.say("Going back 1 song. ⏪", delete_after=30)
        else:
            await self.bot.say("Not playing anything on this server.", delete_after=30)

    @commands.group(pass_context=True, no_pm=True)
    async def playlist(self, ctx):
        """Playlist management/control."""
        if ctx.invoked_subcommand is None:
            await self.send_cmd_help(ctx)

    @playlist.command(pass_context=True, no_pm=True, name="create")
    async def playlist_create(self, ctx, name):
        """Creates an empty playlist"""
        server = ctx.message.server
        author = ctx.message.author
        if not self._valid_playlist_name(name) or len(name) > 25:
            await self.bot.say("That playlist name is invalid. It must only"
                               " contain alpha-numeric characters or _.", delete_after=30)
            return

        # Returns a Playlist object
        url = None
        songlist = []
        playlist = self._make_playlist(author, url, songlist)

        playlist.name = name
        playlist.server = server

        self._save_playlist(server, name, playlist)
        await self.bot.say("Empty playlist '{}' saved.".format(name), delete_after=30)

    @playlist.command(pass_context=True, no_pm=True, name="add")
    async def playlist_add(self, ctx, name, url):
        """[name of playlist] [yt url] Add a YouTube playlist."""
        server = ctx.message.server
        author = ctx.message.author
        if not self._valid_playlist_name(name) or len(name) > 25:
            await self.bot.say("That playlist name is invalid. It must only"
                               " contain alpha-numeric characters or _.", delete_after=30)
            return

        if self._valid_playable_url(url):
            try:
                await self.bot.say("Enumerating song list... This could take"
                                   " a few moments.", delete_after=30)
                songlist = await self._parse_playlist(url)
            except InvalidPlaylist:
                await self.bot.say("That playlist URL is invalid.", delete_after=30)
                return

            playlist = self._make_playlist(author, url, songlist)
            # Returns a Playlist object

            playlist.name = name
            playlist.server = server

            self._save_playlist(server, name, playlist)
            await self.bot.say("Playlist '{}' saved. Tracks: {}".format(
                name, len(songlist)), delete_after=30)
        else:
            await self.bot.say("That URL is not a valid Soundcloud or YouTube"
                               " playlist link.", delete_after=30)

    @playlist.command(pass_context=True, no_pm=True, name="append")
    async def playlist_append(self, ctx, name, url):
        """Appends to a playlist."""
        author = ctx.message.author
        server = ctx.message.server
        if name not in self._list_playlists(server):
            await self.bot.say("There is no playlist with that name.", delete_after=30)
            return
        playlist = self._load_playlist(
            server, name, local=self._playlist_exists_local(server, name))
        try:
            playlist.append_song(author, url)
        except UnauthorizedSave:
            await self.bot.say("You're not the author of that playlist.", delete_after=30)
        except InvalidURL:
            await self.bot.say("Invalid link.", delete_after=30)
        else:
            await self.bot.say("Done.", delete_after=30)

   

    @playlist.command(pass_context=True, no_pm=True, name="list")
    async def playlist_list(self, ctx):
        """Lists all available playlists"""
        server = ctx.message.server
        playlists = ", ".join(self._list_playlists(server))
        if playlists:
            playlists = "Available playlists:\n\n" + playlists
            for page in pagify(playlists, delims=[" "]):
                await self.bot.say(page, delete_after=30)
        else:
            await self.bot.say("There are no playlists.", delete_after=30)

    @playlist.command(pass_context=True, no_pm=True, name="queue")
    async def playlist_queue(self, ctx, url):
        """Adds a song to the playlist loop.

        Does NOT write to disk."""
        server = ctx.message.server
        if not self.voice_connected(server):
            await self.bot.say("Not voice connected in this server.", delete_after=30)
            return

        # We are connected somewhere
        if server.id not in self.queue:
            raise VoiceNotConnected("Something went wrong, we have no internal"
                                    " queue to modify. This should never"
                                    " happen.")

        # We have a queue to modify
        self._add_to_queue(server, url)

        await self.bot.say("Queued.", delete_after=30)

    @playlist.command(pass_context=True, no_pm=True, name="remove")
    async def playlist_remove(self, ctx, name):
        """Deletes a saved playlist."""
        author = ctx.message.author
        server = ctx.message.server

        if not self._valid_playlist_name(name):
            await self.bot.say("The playlist's name contains invalid "
                               "characters.", delete_after=30)
            return

        if not self._playlist_exists(server, name):
            await self.bot.say("Playlist not found.", delete_after=30)
            return

        playlist = self._load_playlist(
            server, name, local=self._playlist_exists_local(server, name))

        if not playlist.can_edit(author):
            await self.bot.say("You do not have permissions to delete that playlist.", delete_after=30)
            return

        self._delete_playlist(server, name)
        await self.bot.say("Playlist deleted.", delete_after=30)


    @playlist.command(pass_context=True, no_pm=True, name="start")
    async def playlist_start(self, ctx, name):
        """Plays a playlist."""
        server = ctx.message.server
        author = ctx.message.author
        voice_channel = ctx.message.author.voice_channel

        caller = inspect.currentframe().f_back.f_code.co_name

        if voice_channel is None:
            await self.bot.say("You must be in a voice channel to start a"
                               " playlist.", delete_after=30)
            return

        if self._playlist_exists(server, name):
            if not self.voice_connected(server):
                try:
                    self.has_connect_perm(author, server)
                except AuthorNotConnected:
                    await self.bot.say("You must join a voice channel before"
                                       " I can play anything.", delete_after=30)
                    return
                except UnauthorizedConnect:
                    await self.bot.say("I don't have permissions to join your"
                                       " voice channel.", delete_after=30)
                    return
                except UnauthorizedSpeak:
                    await self.bot.say("I don't have permissions to speak in"
                                       " your voice channel.", delete_after=30)
                    return
                except ChannelUserLimit:
                    await self.bot.say("Your voice channel is full.", delete_after=30)
                    return
                else:
                    await self._join_voice_channel(voice_channel)
            self._clear_queue(server)
            playlist = self._load_playlist(server, name,
                                           local=self._playlist_exists_local(
                                               server, name))
            if caller == "playlist_start_mix":
                shuffle(playlist.playlist)

            self._play_playlist(server, playlist)
            await self.bot.say("Playlist queued.", delete_after=30)
        else:
            await self.bot.say("That playlist does not exist.", delete_after=30)

    @playlist.command(pass_context=True, no_pm=True, name="mix")
    async def playlist_start_mix(self, ctx, name):
        """Plays and mixes a playlist."""
        await self.playlist_start.callback(self, ctx, name)

    @commands.command(pass_context=True, no_pm=True, name="queue")
    async def _queue(self, ctx, *, url=None):
        """Queues a song to play next.

        If you use `queue` when one song is playing, your new song will get
            added to the song loop (if running). If you use `queue` when a
            playlist is running, it will temporarily be played next and will
            NOT stay in the playlist loop."""
        if url is None:
            return await self._queue_list(ctx)
        server = ctx.message.server
        if not self.voice_connected(server):
            await ctx.invoke(self.play, url_or_search_terms=url)
            return

        # We are connected somewhere
        if server.id not in self.queue:
            raise VoiceNotConnected("Something went wrong, we have no internal"
                                    " queue to modify. This should never"
                                    " happen.")

        url = url.strip("<>")

        if self._match_any_url(url):
            if not self._valid_playable_url(url):
                await self.bot.say("That's not a valid URL.")
                return
        
        if not self._match_sc_playlist(url) or self._match_yt_playlist(url):
            url = await self.ytsearch(query=url)
            if "[SEARCH:]" not in url and "youtube" in url:
                url = url.split("&")[0]  # Temp fix for the &list issue

            # We have a queue to modify
            if self.queue[server.id]["PLAYLIST"]:
                self._add_to_temp_queue(server, url)
            else:
                self._add_to_queue(server, url)
        else:
            if self._match_sc_playlist(url) or self._match_yt_playlist:
                playlist = await self._parse_playlist(url)
                if self.queue[server.id]["PLAYLIST"]:
                    self._add_to_temp_queue(server, playlist)
                else:
                    self._add_to_queue(server, playlist)
        
        await self.bot.say("Queued.", delete_after=30)

    async def _queue_list(self, ctx):
        """Not a command, use `queue` with no args to call this."""
        server = ctx.message.server
        if server.id not in self.queue:
            await self.bot.say("Nothing playing on this server!")
            return
        elif len(self.queue[server.id]["QUEUE"]) == 0:
            await self.bot.say("Nothing queued on this server.", delete_after=30)
            return

        msg = ""

        now_playing = self._get_queue_nowplaying(server)

        if now_playing is not None:
            msg += "\n***Now playing:***\n{}\n".format(now_playing.title)

        queue_url_list = self._get_queue(server, 7)
        tempqueue_url_list = self._get_queue_tempqueue(server, 7)

        await self.bot.say("Gathering information...")

        queue_song_list = await self._download_all(queue_url_list)
        tempqueue_song_list = await self._download_all(tempqueue_url_list)

        song_info = []
        for num, song in enumerate(tempqueue_song_list, 1):
            if song.title is None:
                for num, item in enumerate(tempqueue_url_list, 1):
                    song = self._make_local_song(item)
                    song_info.append("{}. {.title}".format(num, song))
            else:
                try:
                    song_info.append("{}. {.title}".format(num, song))
                except AttributeError:
                    song_info.append("{}. {.webpage_url}".format(num, song))

        for num, song in enumerate(queue_song_list, len(song_info) + 1):
            
            if num > 7:
                break
            if song.title is None:
                for num, item in enumerate(queue_url_list, len(song_info) + 1):
                    if num > 7:
                        break
                    song = self._make_local_song(item)
                    try:
                        song_info.append("{}. {.title}".format(num, song))
                    except AttributeError:
                        song_info.append("{}. {.webpage_url}".format(num, song))
            else:
                try:
                    song_info.append("{}. {.title}".format(num, song))
                except AttributeError:
                    song_info.append("{}. {.webpage_url}".format(num, song))
        msg += "\n***Next up:***\n" + "\n".join(song_info)

        await self.bot.say(msg)

    @commands.group(pass_context=True, no_pm=True)
    async def repeat(self, ctx):
        """Toggles REPEAT"""
        server = ctx.message.server
        if ctx.invoked_subcommand is None:
            if self.is_playing(server):
                if self.queue[server.id]["REPEAT"]:
                    msg = "The queue is currently looping."
                else:
                    msg = "The queue is currently not looping."
                await self.bot.say(msg, delete_after=30)
                await self.bot.say(
                    "Do `{}repeat toggle` to change this.".format(ctx.prefix), delete_after=30)
            else:
                await self.bot.say("Play something to see this setting.", delete_after=30)

    @repeat.command(pass_context=True, no_pm=True, name="toggle")
    async def repeat_toggle(self, ctx):
        """Flips repeat setting."""
        server = ctx.message.server
        if not self.is_playing(server):
            await self.bot.say("I don't have a repeat setting to flip."
                               " Try playing something first.", delete_after=30)
            return

        self._set_queue_repeat(server, not self.queue[server.id]["REPEAT"])
        repeat = self.queue[server.id]["REPEAT"]
        if repeat:
            await self.bot.say("Repeat toggled on.", delete_after=30)
        else:
            await self.bot.say("Repeat toggled off.", delete_after=30)

    @commands.command(pass_context=True, aliases=["ok"], no_pm=True)
    async def resume(self, ctx):
        """Resumes paused audio"""
        server = ctx.message.server
        if not self.voice_connected(server):
            await self.bot.say("Not voice connected in this server.", delete_after=30)
            return

        # We are connected somewhere
        voice_client = self.voice_client(server)

        if not hasattr(voice_client, 'audio_player'):
            await self.bot.say("Nothing paused, nothing to resume.", delete_after=30)
        elif not voice_client.audio_player.is_done() and \
                not voice_client.audio_player.is_playing():
            voice_client.audio_player.resume()
            self.is_paused.clear()
            await self._update_bot_status()
            await self.bot.say("Resuming.", delete_after=30)
        else:
            await self.bot.say("Nothing paused, nothing to resume.", delete_after=30)

    @commands.command(pass_context=True, no_pm=True, name="shuffle")
    async def _shuffle(self, ctx):
        """Shuffles the current queue"""
        server = ctx.message.server
        if server.id not in self.queue:
            await self.bot.say("I have nothing in queue to shuffle.", delete_after=30)
            return

        self._shuffle_queue(server)
        self._shuffle_temp_queue(server)
        cards = ['\N{BLACK SPADE SUIT}', '\N{BLACK CLUB SUIT}', '\N{BLACK HEART SUIT}', '\N{BLACK DIAMOND SUIT}']
        shuffle(cards)

        hand = await self.bot.say(' '.join(cards))
        await asyncio.sleep(0.6)

        for x in range(4):
            shuffle(cards)
            await self.bot.edit_message(hand, ' '.join(cards))
            await asyncio.sleep(0.6)
        await self.bot.say("🔀", delete_after=20)

    @commands.command(pass_context=True, aliases=["next"], no_pm=True)
    async def skip(self, ctx):
        """Skips a song"""
        msg = ctx.message
        server = ctx.message.server
        if self.is_playing(server):
            vchan = server.me.voice_channel
            vc = self.voice_client(server)
            if msg.author.voice_channel == vchan:
                vc.audio_player.stop()
                if self._get_queue_repeat(server) is False:
                    self._set_queue_nowplaying(server, None)
                    await self.bot.say(':fast_forward:', delete_after=20)
            else:
                await self.bot.say("You need to be in the voice channel to skip the music.", delete_after=30)
        else:
            await self.bot.say("Can't skip if I'm not playing.", delete_after=30)

   

    @commands.command(aliases=['nowplaying'], pass_context=True, no_pm=True)
    async def song(self, ctx):
        """Info about the current song."""
        server = ctx.message.server
        if not self.is_playing(server):
            await self.bot.say("I'm not playing on this server.", delete_after=30)
            return

        song = self._get_queue_nowplaying(server)
        if song:
            if not hasattr(song, 'creator'):
                song.creator = None
            if not hasattr(song, 'view_count'):
                song.view_count = None
            if not hasattr(song, 'uploader'):
                song.uploader = None
            if hasattr(song, 'duration'):
                m, s = divmod(song.duration, 60)
                h, m = divmod(m, 60)
                if h:
                    dur = "{0}:{1:0>2}:{2:0>2}".format(h, m, s)
                else:
                    dur = "{0}:{1:0>2}".format(m, s)
            else:
                dur = None
            msg = ("\n**Title:** {}\n**Author:** {}\n**Uploader:** {}\n"
                   "**Views:** {}\n**Duration:** {}\n\n<{}>".format(
                       song.title, song.creator, song.uploader,
                       song.view_count, dur, song.webpage_url))
            await self.bot.say(msg.replace("**Author:** None\n", "")
                                  .replace("**Views:** None\n", "")
                                  .replace("**Uploader:** None\n", "")
                                  .replace("**Duration:** None\n", ""), delete_after=30)
        else:
            await self.bot.say("Darude - Sandstorm.")


    @commands.command(pass_context=True, no_pm=True)
    async def stop(self, ctx):
        """Stops audio; CLEARS QUEUE"""
        server = ctx.message.server
        if self.is_playing(server):
            if ctx.message.author.voice_channel == server.me.voice_channel:
                await self.bot.say("🛑'ed", delete_after=20)
                self._stop(server)
            else:
                await self.bot.say("You need to be in the voice channel to stop the music.", delete_after=30)
        else:
            await self.bot.say("Can't stop if I'm not playing.", delete_after=30)

    @commands.command(name="yt", pass_context=True, no_pm=True)
    async def yt_search(self, ctx, *, query: str):
        """Searches and plays a video from YouTube"""
        channel = ctx.message.channel
        author = ctx.message.author
        print(query)
        if query.startswith('pl '):
            opt = 'playlist'
            base = "https://www.youtube.com/playlist?list="
            idName = 'playlistId'
            query = query.lstrip('pl ')
        else:
            opt = 'video'
            base = 'https://www.youtube.com/watch?v='
            idName = 'videoId'

        query = quote_plus(query)
        url = f'https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=3&q={query}&type={opt}&key={keys.yt}' 
        async with aiohttp.get(url) as r:
            js = await r.json()
        key = keys.yt
        for i in range(len(js['items'])):
            id1 = js['items'][i]['id'][f'{idName}']
            title1 = js['items'][i]['snippet']['title']
            index = i+1
            url1 = base + id1
            await self.bot.say('%d. %s:\n'%(index, title1)+url1+'\n', delete_after=45)
        await self.bot.say("pick 1-3", delete_after=45)
        def check(m):
            return(m.author.id != self.bot.user.id and m.content.isdigit())
        hmm = await self.bot.wait_for_message(30, channel=channel, check=check)
        if not hmm:
            print('nope')
            return
        userchoice = hmm.content[0]
        if userchoice == '1':
            await ctx.invoke(self.play, url_or_search_terms=base+js['items'][0]['id'][f'{idName}'])
        elif userchoice == '2':
            await ctx.invoke(self.play, url_or_search_terms=base+js['items'][1]['id'][f'{idName}'])
        elif userchoice == '3':
            await ctx.invoke(self.play, url_or_search_terms=base+js['items'][2]['id'][f'{idName}'])
        else:
            return

    def is_playing(self, server):
        if not self.voice_connected(server):
            return False
        if self.voice_client(server) is None:
            return False
        if not hasattr(self.voice_client(server), 'audio_player'):
            return False
        if self.voice_client(server).audio_player.is_done():
            return False
        return True 
        
        
    async def cache_manager(self):
        while self == self.bot.get_cog("Audio"):
            if self._cache_too_large():
                # Our cache is too big, dumping
                log.debug("cache too large ({} > {}), dumping".format(
                    self._cache_size(), self._cache_max()))
                self._dump_cache()
            await asyncio.sleep(5)  # No need to run this every half second

    async def cache_scheduler(self):
        await asyncio.sleep(30)  # Extra careful

        self.bot.loop.create_task(self.cache_manager())

    def currently_downloading(self, server):
        if server.id in self.downloaders:
            if self.downloaders[server.id].is_alive():
                return True
        return False

    async def disconnect_timer(self):
        stop_times = {}
        while self == self.bot.get_cog('Audio'):
            for vc in self.bot.voice_clients:
                server = vc.server
                if not hasattr(vc, 'audio_player') and \
                        (server not in stop_times or
                         stop_times[server] is None):
                    stop_times[server] = int(time.time())

                if hasattr(vc, 'audio_player'):
                    if vc.audio_player.is_done():
                        if server not in stop_times or stop_times[server] is None:
                            stop_times[server] = int(time.time())

                    if len(vc.channel.voice_members) == 1:
                        if server not in stop_times or stop_times[server] is None:
                            stop_times[server] = int(time.time())
                    elif not vc.audio_player.is_done():
                        stop_times[server] = None

            for server in stop_times:
                if stop_times[server] and \
                        int(time.time()) - stop_times[server] > 300:
                    self._clear_queue(server)
                    await self._stop_and_disconnect(server)
                    stop_times[server] = None
            await asyncio.sleep(5)

    def get_server_settings(self, server):
        try:
            sid = server.id
        except:
            sid = server

        if sid not in self.settings["SERVERS"]:
            self.settings["SERVERS"][sid] = {}
        ret = self.settings["SERVERS"][sid]

        for setting in self.server_specific_setting_keys:
            if setting not in ret:
                # Add the default
                ret[setting] = self.settings[setting]
                if setting.lower() == "volume" and ret[setting] <= 1:
                    ret[setting] *= 100
        # ^This will make it so that only users with an outdated config will
        # have their volume set * 100. In theory.
        self.save_settings()

        return ret

    def has_connect_perm(self, author, server):
        channel = author.voice_channel

        if channel:
            is_admin = channel.permissions_for(server.me).administrator
            if channel.user_limit == 0:
                is_full = False
            else:
                is_full = len(channel.voice_members) >= channel.user_limit

        if channel is None:
            raise AuthorNotConnected
        elif channel.permissions_for(server.me).connect is False:
            raise UnauthorizedConnect
        elif channel.permissions_for(server.me).speak is False:
            raise UnauthorizedSpeak
        elif is_full and not is_admin:
            raise ChannelUserLimit
        else:
            return True
        return False
    
    @commands.command(pass_context=True)
    async def testtube(self, ctx, url : str):
        """yt url to mp3"""
        print(url)
        if not ctx.message.author.id == config.owner:
            return
        
        ydl_opts = {
                'format': 'bestaudio/best',
                'extractaudio': True,
                'audioformat': 'mp3',
                'outtmpl': 'data/audio/localtracks/%(playlist_title)s/%(title)s.%(ext)s',
                'restrictfilenames': False,
                'noplaylist': False,
                'nooverwrites': True,
                'nocheckcertificate': True,
                'ignoreerrors': False,
                'logtostderr': False,
                'quiet': True,
                'no_warnings': True,
                'default_search': 'auto',
                'source_address': '0.0.0.0',
                'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                
            }]
        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            print(info)
            await asyncio.sleep(3)
            if '_type' in info.keys():
                if info['_type'] == 'playlist':
                    subprocess.Popen('youtube-dl -x --audio-format "mp3" --audio-quality 0 --restrict-filenames --output data/audio/localtracks/%(playlist_title)s/%(title)s.%(ext)s '+ url)
                    # await self.bot.say('This is a playlist; run %sttbb <url> in a few min for whatever files I can send.  Expect that I\'ll be knocked offline if files are too large or numerous.'%config.prefix)
            else:
                url = url.split('&')[0]
                info = ydl.extract_info(url, download=True)
                folder = 'NA'
                title = info['title']
                await self.bot.send_file(ctx.message.channel, "data/audio/localtracks/%s/%s.mp3"%(folder, title))

 
    @commands.command(pass_context=True)
    async def ttbb(self, ctx, url : str):
        """sends 🎧 files from url"""
        
        if not ctx.message.author.id == config.owner:
            return
        class MyLogger(object):
            def debug(self, msg):
                pass

            def warning(self, msg):
                pass

            def error(self, msg):
                print(msg)
        
        def my_hook(d):
            if d['status'] == 'finished':
                if d['downloaded_bytes'] >= 8000000:
                    print('file too big!')

        ydl_opts = {
                'format': 'bestaudio/best',
                'extractaudio': True,
                'audioformat': 'mp3',
                'outtmpl': 'data/audio/localtracks/NA/%(title)s.%(ext)s',
                'restrictfilenames': False,
                'noplaylist': True,
                'nooverwrites': True,
                'nocheckcertificate': True,
                'ignoreerrors': False,
                'logtostderr': False,
                'quiet': True,
                'no_warnings': True,
                'default_search': 'auto',
                'source_address': '0.0.0.0',
                'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        }],
                'progress_hooks': [my_hook],
                'logger': MyLogger(),
                }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            try:
                for i in range(len(info['formats'])):
                    if info['formats'][i]['format_id'] == '140':
                        size = int(info['formats'][i]['filesize'])
            except:
                Exception
            if '_type' in info.keys():
                # await self.bot.say('This is a playlist; please run tracks one at a time to get em.')
                if info['_type'] == 'playlist':
                    print(size)
                    for i in range(len(info['entries'])):
                        url = info['entries'][i]['url']
                        folder = info['title']

                        title = info['entries'][i]['title']
                        index = info['entries'][i]['playlist_index']
                        await self.bot.send_file(ctx.message.channel, "data/audio/localtracks/%s/%s.mp3"%(folder, title), content='#%s of %s'%(index, len(info['entries'])))
            else:
                url = url.split('&')[0]
                info = ydl.extract_info(url, download=True)
                folder = 'NA'
                title = info['title']
                
                if size >= 8000000:
                    await self.bot.say('File is too big!  Limit 8MB')
                else:
                    await self.bot.send_file(ctx.message.channel, "data/audio/localtracks/%s/%s.mp3"%(folder, title))

    @commands.command(pass_context=True)
    async def qtest(self, ctx):
        server = ctx.message.channel.server
        temp_queue = self.queue[server.id]["TEMP_QUEUE"]
        queue = self.queue[server.id]["QUEUE"]
        repeat = self.queue[server.id]["REPEAT"]
        last_song = self.queue[server.id]["NOW_PLAYING"]
        print(queue)
        print(temp_queue)
        print(last_song)

    async def queue_manager(self, sid):
        """This function assumes that there's something in the queue for us to
            play"""
        server = self.bot.get_server(sid)
        max_length = self.settings["MAX_LENGTH"]

        # This is a reference, or should be at least
        temp_queue = self.queue[server.id]["TEMP_QUEUE"]
        queue = self.queue[server.id]["QUEUE"]
        repeat = self.queue[server.id]["REPEAT"]
        last_song = self.queue[server.id]["NOW_PLAYING"]

        assert temp_queue is self.queue[server.id]["TEMP_QUEUE"]
        assert queue is self.queue[server.id]["QUEUE"]

        # _play handles creating the voice_client and player for us

        if not self.is_playing(server):
            await self._update_bot_status()
            if len(temp_queue) > 0:
                try:
                    song = await self._play(sid, temp_queue.popleft())
                except MaximumLength:
                    return
            elif len(queue) > 0:  # We're in the normal queue
                url = queue.popleft()
                try:
                    song = await self._play(sid, url)
                except MaximumLength:
                    return
                if repeat and last_song:
                    queue.append(last_song.webpage_url)
            else:
                song = None
            self.queue[server.id]["NOW_PLAYING"] = song
            self.bot.loop.create_task(self._update_bot_status())

        elif server.id in self.downloaders:
            # We're playing but we might be able to download a new song
            curr_dl = self.downloaders.get(server.id)
            if len(temp_queue) > 0:
                next_dl = Downloader(temp_queue.peekleft(),
                                     max_length)
            elif len(queue) > 0:
                next_dl = Downloader(queue.peekleft(), max_length)
            else:
                next_dl = None

            if next_dl is not None:
                # Download next song
                next_dl.start()
                await self._download_next(server, curr_dl, next_dl)

    async def queue_scheduler(self):
        while self == self.bot.get_cog('Audio'):
            tasks = []
            queue = copy.deepcopy(self.queue)
            for sid in queue:
                if len(queue[sid]["QUEUE"]) == 0 and \
                        len(queue[sid]["TEMP_QUEUE"]) == 0:
                    continue
                tasks.append(
                    self.bot.loop.create_task(self.queue_manager(sid)))
            completed = [t.done() for t in tasks]
            while not all(completed):
                completed = [t.done() for t in tasks]
                await asyncio.sleep(0.5)
            await asyncio.sleep(1)

    async def reload_monitor(self):
        while self == self.bot.get_cog('Audio'):
            await asyncio.sleep(0.5)

        for vc in self.bot.voice_clients:
            try:
                vc.audio_player.stop()
            except:
                pass

    def save_settings(self):
        dataIO.save_json('data/audio/settings.json', self.settings)

    def set_server_setting(self, server, key, value):
        if server.id not in self.settings["SERVERS"]:
            self.settings["SERVERS"][server.id] = {}
        self.settings["SERVERS"][server.id][key] = value

    def voice_client(self, server):
        return self.bot.voice_client_in(server)

    def voice_connected(self, server):
        if self.bot.is_voice_connected(server):
            return True
        return False

    async def voice_state_update(self, before, after):
        server = after.server
        # Member objects
        if after.voice_channel != before.voice_channel:
            pass
        if after is None:
            return
        if server.id not in self.queue:
            return
        if after != server.me:
            return

        # Member is the bot

        if before.voice_channel != after.voice_channel:
            self._set_queue_channel(after.server, after.voice_channel)

        if before.mute != after.mute:
            vc = self.voice_client(server)
            if after.mute and vc.audio_player.is_playing():
                vc.audio_player.pause()
                return self.is_paused.set()
            elif not after.mute and \
                    (not vc.audio_player.is_playing() and
                     not vc.audio_player.is_done()):
                vc.audio_player.resume()
                return self.is_paused.clear()

    def __unload(self):
        for vc in self.bot.voice_clients:
            self.bot.loop.create_task(vc.disconnect())


def check_folders():
    folders = ("data/audio", "data/audio/cache", "data/audio/playlists",
               "data/audio/localtracks", "data/audio/localtracks/NA", "data/audio/sfx")
    for folder in folders:
        if not os.path.exists(folder):
            print("Creating " + folder + " folder...")
            os.makedirs(folder)


def check_files():
    default = {"VOLUME": 50, "MAX_LENGTH": 0,
               "MAX_CACHE": 0, 
               "TITLE_STATUS": True, "AVCONV": False, 
               "SERVERS": {}}
    settings_path = "data/audio/settings.json"

    if not os.path.isfile(settings_path):
        print("Creating default audio settings.json...")
        dataIO.save_json(settings_path, default)
    else:  # consistency check
        try:
            current = dataIO.load_json(settings_path)
        except JSONDecodeError:
            dataIO.save_json(settings_path, default)
            current = dataIO.load_json(settings_path)
        if current.keys() != default.keys():
            for key in default.keys():
                if key not in current.keys():
                    current[key] = default[key]
                    print(
                        "Adding " + str(key) + " field to audio settings.json")
            dataIO.save_json(settings_path, current)

def verify_ffmpeg_avconv():
    try:
        subprocess.call(["ffmpeg", "-version"], stdout=subprocess.DEVNULL)
    except FileNotFoundError:
        pass
    else:
        return "ffmpeg"

    try:
        subprocess.call(["avconv", "-version"], stdout=subprocess.DEVNULL)
    except FileNotFoundError:
        return False
    else:
        return "avconv"


def setup(bot):
    check_folders()
    check_files()

    if youtube_dl is None:
        raise RuntimeError("You need to run `pip install youtube_dl`")
    if opus is False:
        raise RuntimeError(
            "Your opus library's bitness must match your python installation's"
            " bitness. They both must be either 32bit or 64bit.")
    elif opus is None:
        raise RuntimeError(
            "You need to install ffmpeg and opus. See \"https://github.com/")

    player = verify_ffmpeg_avconv()

    if not player:
        if os.name == "nt":
            msg = "ffmpeg isn't installed"
        else:
            msg = "Neither ffmpeg nor avconv are installed"
        raise RuntimeError(
          "{}.\nConsult the guide for your operating system "
          "and do ALL the steps in order.\n"
          "".format(msg))

      
    n = Audio(bot, player=player)  # Praise 26
    bot.add_cog(n)
    bot.add_listener(n.voice_state_update, 'on_voice_state_update')
    bot.loop.create_task(n.queue_scheduler())
    bot.loop.create_task(n.disconnect_timer())
    bot.loop.create_task(n.reload_monitor())
    bot.loop.create_task(n.cache_scheduler())
