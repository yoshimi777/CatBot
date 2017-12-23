from __future__ import print_function
import os
import sys
import subprocess
import urllib.request                   
from importlib.util import find_spec
import requests
import zipfile
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
FFMPEG_64_URL = "https://ffmpeg.zeranoe.com/builds/win64/static/ffmpeg-20171223-d02289c-win64-static.zip"
FFMPEG_32_URL = "https://ffmpeg.zeranoe.com/builds/win32/static/ffmpeg-20171223-d02289c-win32-static.zip"
FFMPEG_64_MAC_URL = "https://ffmpeg.zeranoe.com/builds/macos64/static/ffmpeg-20171223-d02289c-macos64-static.zip"
FILES = {
    "ffmpeg.exe"  : "09e5595997969ad60d81b261d1a2e176",
    "ffplay.exe"  : "5bc5d563453e0566f2bf1d8bcf435f5c",
    "ffprobe.exe" : "6bfcb66a5304ec5d4bec710bdd54a89c"
}
THIS_DIR = os.path.dirname(os.path.abspath(__file__))

def download():
    this_dir = os.path.dirname(os.path.abspath(__file__))
    if not os.path.isfile(f"{THIS_DIR}\\ffmpeg.exe"):
        if IS_WINDOWS:
            if IS_64BIT:
                r = requests.get(FFMPEG_64_URL)
            else:
                r = requests.get(FFMPEG_32_URL)
        if IS_MAC:
            r = requests.get(FFMPEG_64_MAC_URL)
        with open(f'{THIS_DIR}/ffmpeg.zip', 'wb+') as z:
            z.write(r.content)
        with zipfile.ZipFile(f'{THIS_DIR}/ffmpeg.zip') as myzip:
            contents = myzip.namelist()
            files = [contents[2], contents[3], contents[4]]
            myzip.extractall(path=f'{THIS_DIR}', members=files)
            for file in files:
                file = f'{THIS_DIR}\\{file}'
                shutil.move(file, f'{this_dir}')
            shutil.rmtree(f'{THIS_DIR}/{contents[0]}')

def verify(filename):
    if IS_WINDOWS:
        if IS_64BIT:
            verified = []

            for filename in FILES:
                if os.path.isfile(filename):
                    print(f"{filename} already present. Verifying integrity... ", end="")
                    _hash = calculate_md5(filename)
                    if _hash == FILES[filename]:
                        verified.append(filename)
                        print("OK")
                        continue
                    else:
                        print("Hash mismatch.")

            for filename, _hash in FILES.items():
                if filename in verified:
                    continue
                print(f"Verifying {filename}... ", end="")
                if not calculate_md5(filename) != _hash:
                    print("Passed.")
                else:
                    print("Hash mismatch. Please redownload.")
                    download()

            print("\nAll files a-ok.")

def calculate_md5(filename):
    hash_md5 = hashlib.md5()
    with open(f"{THIS_DIR}\\{filename}", "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


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
    if not os.path.isfile(f"{THIS_DIR}\\cogs\\utils\\keys.py"):
        keys = "## These keys may change and become deactivated.  Currency only has 1000/mo, please be kind.  They're all free and you're encouraged to get your own, which is why this file exists.\n"
        keys += "yt = 'AIzaSyCcJqSmUFboDasqYnmKCtbiU0PPEaFuCN0' #https://developers.google.com/apis-explorer/#p/\n" 
        keys += "giphy = '5Qpya49BCDLcJ1X0OgMe31xMWbrGZnx7' #https://developers.giphy.com/\n"
        keys += "maps = 'AIzaSyBzaO21hTYu4uTA_9p6MZigxx4JWJBz5kA' #https://google-developers.appspot.com/maps/documentation/static-maps/\n"
        keys += "currency = '95264b8a08f2259b35db7fd8002b6634' #https://currencylayer.com/\n"
        filename = f"{THIS_DIR}\\cogs\\utils\\keys.py"
        print(f"Creating {filename}...")
        with open(filename, 'w') as f:
            f.write(keys)
        print('Key file written!  Contents:\n'+keys)
        print('You can edit this file in cogs/utils.')

def reqs():
    subprocess.run("pip install -r requirements.txt")
    
def write_settings():
    if not os.path.isfile(f"{THIS_DIR}\\cogs\\utils\\config.py"):
        print('This is the setup for config file.\nMake a bot and enter its token, your user ID as owner, a volume, prefix, and chat channel.\nDo not use quotes.')
        token = input('Enter your bot\'s token: ').strip()
        owner_id = int(input('Enter your user ID: ').strip())
        chat = input('Enter a text chat channel for chatterbot: ').strip()
        vol = int(input('Enter a default volume (1-9, but 5 is recommended): ').strip())
        prefix = input('Enter a prefix for bot commands (ex: + or =): ')
        config = f"token = '{token}'\n"
        config += "cogs = ['cogs.audio', 'cogs.translate', 'cogs.general', 'cogs.chatterbot', 'cogs.catbot']\n" 
        config += f"prefix = '{prefix}'\n" 
        config += f"owner = '{owner_id}'\n"
        config += f"volume = .{vol}\n"
        config += f"chatChannels = ['{chat}']\n"
    
        filename = "cogs\\utils\\config.py"  
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

    call = f"\"{interpreter}\" run.py"
    catbot = f"{call} --start --auto-restart"
    virtenv = f"{interpreter} -m venv virtenv"
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
            print(f"Creating {filename}... ")
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
        download()
        verify(filename=None)
        if os.path.isfile(f'{THIS_DIR}\\ffmpeg.zip'):
            os.remove(f'{THIS_DIR}\\ffmpeg.zip')
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
        
