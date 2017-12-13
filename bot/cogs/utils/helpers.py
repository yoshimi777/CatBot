import asyncio
from urllib.request import urlopen

from functools import wraps
from discord.ext.commands import Command
from discord.ext.commands.bot import _get_variable
from . import exceptions, config

def clean(string):
    # A helper script to strip out @here and @everyone mentions
    zerospace = "​"
    return string.replace("@everyone", "@{}everyone".format(zerospace)).replace("@here", "@{}here".format(zerospace))


def makeBar(progress):
    return '[{0}{1}] {2}%'.format('#' * (int(round(progress / 2))), ' ' * (50 - (int(round(progress / 2)))), progress)


def center(string, header=None):
    leftPad = ' ' * (int(round((50 - len(string)) / 2)))
    leftPad += string
    if header:
        output = header + leftPad[len(header):]
    else:
        output = leftPad
    return output


def tiny_url(url):
    apiurl = "http://tinyurl.com/api-create.php?url="
    tinyurl = urlopen(apiurl + url).read().decode("utf-8")
    return tinyurl


def getReadableTimeBetween(first, last):
    # A helper function to make a readable string between two times
    timeBetween = int(last - first)
    weeks = int(timeBetween / 604800)
    days = int((timeBetween - (weeks * 604800)) / 86400)
    hours = int((timeBetween - (days * 86400 + weeks * 604800)) / 3600)
    minutes = int(
        (timeBetween - (hours * 3600 + days * 86400 + weeks * 604800)) / 60)
    seconds = int(timeBetween - (minutes * 60 + hours *
                  3600 + days * 86400 + weeks * 604800))
    msg = ""

    if weeks > 0:
        if weeks == 1:
            msg = '{}{} week, '.format(msg, str(weeks))
        else:
            msg = '{}{} weeks, '.format(msg, str(weeks))
    if days > 0:
        if days == 1:
            msg = '{}{} day, '.format(msg, str(days))
        else:
            msg = '{}{} days, '.format(msg, str(days))
    if hours > 0:
        if hours == 1:
            msg = '{}{} hour, '.format(msg, str(hours))
        else:
            msg = '{}{} hours, '.format(msg, str(hours))
    if minutes > 0:
        if minutes == 1:
            msg = '{}{} minute, '.format(msg, str(minutes))
        else:
            msg = '{}{} minutes, '.format(msg, str(minutes))
    if seconds > 0:
        if seconds == 1:
            msg = '{}{} second, '.format(msg, str(seconds))
        else:
            msg = '{}{} seconds, '.format(msg, str(seconds))

    if not msg:
        return "0 seconds"
    else:
        return msg[:-2]


def load_file(filename, skip_commented_lines=True, comment_char='#'):
    try:
        with open(filename, encoding='utf8') as f:
            results = []
            for line in f:
                line = line.strip()

                if line and not (skip_commented_lines and line.startswith(comment_char)):
                    results.append(line)

            return results

    except IOError as e:
        print("Error loading", filename, e)
        return []


def write_file(filename, contents):
    with open(filename, 'w', encoding='utf8') as f:
        for item in contents:
            f.write(str(item))
            f.write('\n')

