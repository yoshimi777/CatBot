from __future__ import print_function
import os
import sys
import subprocess
try:                                        
    import urllib.request                   
    from importlib.util import find_spec    
except ImportError:
    pass
import platform
import webbrowser
import hashlib
import argparse
import shutil
import stat
import time
try:
    import pip
except ImportError:
    pip = None



INTRO = ("~~~~~~~~~~~~~~~~~~~~~~~~~~\n"
         "          CatBot          \n"
         "~~~~~~~~~~~~~~~~~~~~~~~~~~\n")

IS_WINDOWS = os.name == "nt"
IS_MAC = sys.platform == "darwin"
IS_64BIT = platform.machine().endswith("64")
INTERACTIVE_MODE = not len(sys.argv) > 1  # CLI flags = non-interactive
PYTHON_OK = sys.version_info >= (3, 5)

FFMPEG_FILES = {#TODO recheck these
    "ffmpeg.exe"  : "e0d60f7c0d27ad9d7472ddf13e78dc89",
    "ffplay.exe"  : "d100abe8281cbcc3e6aebe550c675e09",
    "ffprobe.exe" : "0e84b782c0346a98434ed476e937764f"
}

def parse_cli_arguments():
    parser = argparse.ArgumentParser(description="CatBot - catapault")
    parser.add_argument("--start", "-s",
                        help="Starts CatBot",
                        action="store_true")
    parser.add_argument("--auto-restart",
                        help="Autorestarts CatBot in case of issues",
                        action="store_true")
    parser.add_argument("--update-reqs",
                        help="Updates requirements (w/ audio)",
                        action="store_true")

    return parser.parse_args()

def run_catbot(autorestart):
    interpreter = sys.executable

    if interpreter is None: # This should never happen
        raise RuntimeError("Couldn't find Python's interpreter")

    cmd = (interpreter, "bot.py")

    while True:
        try:
            code = subprocess.call(cmd)
        except KeyboardInterrupt:
            code = 0
            break
        else:
            if code == 0:
                break
            elif code == 26:
                print("Restarting CatBot...")
                continue
            else:
                if not autorestart:
                    break

    print("CatBot has been terminated. Exit code: %d" % code)

def clear_screen():
    if IS_WINDOWS:
        os.system("cls")
    else:
        os.system("clear")

def write_kys():
    if not os.path.isfile("cogs/utils/keys.py"):
        keys = "## These keys may change and become deactivated.  Currency only has 1000/mo, please be kind.  They're all free and you're encouraged to get your own, which is why this file exists.\n"
        keys += "yt = 'AIzaSyCcJqSmUFboDasqYnmKCtbiU0PPEaFuCN0' #https://developers.google.com/apis-explorer/#p/\n" 
        keys += "giphy = '5Qpya49BCDLcJ1X0OgMe31xMWbrGZnx7' #https://developers.giphy.com/\n"
        keys += "maps = 'AIzaSyBzaO21hTYu4uTA_9p6MZigxx4JWJBz5kA' #https://google-developers.appspot.com/maps/documentation/static-maps/\n"
        keys += "currency = '95264b8a08f2259b35db7fd8002b6634' #https://currencylayer.com/\n"
        filename = "cogs/utils/keys.py"
        print("Creating {}...".format(filename))
        with open(filename, 'w') as f:
            f.write(keys)
        print('Key file written!  Contents:\n'+keys)
        print('You can edit this file in cogs/utils.')

def reqs():
    subprocess.run("pip install -r requirements.txt")
    
def write_settings():
    if not os.path.isfile("cogs/utils/config.py"):
        print('This is the setup for config file.\nMake a bot and enter its token, your user ID as owner, a volume, prefix, and chat channel.\nDo not use quotes.')
        token = input('Enter your bot\'s token: ').strip()
        owner_id = int(input('Enter your user ID: ').strip())
        chat = input('Enter a text chat channel for chatterbot: ').strip()
        vol = int(input('Enter a default volume (1-9, but 5 is recommended): ').strip())
        prefix = input('Enter a prefix for bot commands (ex: + or =): ')
        config = "token = '{}'\n".format(token) 
        config += "cogs = ['cogs.audio', 'cogs.translate', 'cogs.general', 'cogs.chatterbot', 'cogs.catbot']\n" 
        config += "prefix = '{}'\n".format(prefix) 
        config += "owner = '{}'\n".format(owner_id)
        config += "volume = .{}\n".format(vol) 
        config += "chatChannels = ['{}']\n".format(chat)
    
        filename = "cogs/utils/config.py"  
        print("Creating {}... ".format(filename))
        with open(filename, "w") as f:
            f.write(config)
        print('Config file written!  Contents:\n'+config)
        print('You can edit this file in cogs/utils.')

def create_fast_start_scripts():
    """Creates scripts for fast boot of CatBot without going
    through the launcher"""
    interpreter = sys.executable
    if not interpreter:
        return

    call = "\"{}\" run.py".format(interpreter)
    catbot = "{} --start --auto-restart".format(call)
    virtenv = "{} -m venv virtenv".format(interpreter)
    virtenv += "\nstart virtenv\\scripts\\activate.bat"
    modified = False

    if IS_WINDOWS:
        ccd = "pushd %~dp0\n"
        pause = "\npause"
        ext = ".bat"
    else:
        ccd = 'cd "$(dirname "$0")"\n'
        pause = "\nread -rsp $'Press enter to continue...\\n'"
        if not IS_MAC:
            ext = ".sh"
        else:
            ext = ".command"

    
    catbot = ccd + catbot + pause
    virtenv = ccd + virtenv + pause
    files = {
        "catbot" + ext : catbot,
        "virtenv" + ext : virtenv
    }

    if not IS_WINDOWS:
        files["start_launcher" + ext] = ccd + call

    for filename, content in files.items():
        if not os.path.isfile(filename):
            print("Creating {}... ".format(filename))
            modified = True
            with open(filename, "w") as f:
                f.write(content)

    if not IS_WINDOWS and modified: # Let's make them executable on Unix
        for script in files:
            st = os.stat(script)
            os.chmod(script, st.st_mode | stat.S_IEXEC)
def main():
    if IS_WINDOWS:
        os.system("TITLE CatBot")
    clear_screen()
    write_settings()
    write_kys()
    create_fast_start_scripts()
    reqs()
    clear_screen()
    
    print(INTRO)


main()
if __name__ == '__main__':
    abspath = os.path.abspath(__file__)
    dirname = os.path.dirname(abspath)
    # Sets current directory to the script's
    os.chdir(dirname)
        
    print("Starting CatBot...")
    run_catbot(autorestart=True)
        
