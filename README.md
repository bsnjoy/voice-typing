# voice-typing

Dictation app for voice typing using private whisper or any other transcription server

  

## Installation

```
# In Mac OS install HomeBrew and git and python3:
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install git
brew install python3

# In linux needed to Pyperclip module works:
sudo apt-get install -y xclip python3 python3-pip

# copy project
git clone https://github.com/bsnjoy/voice-typing.git

cd voice-typing
python3 -m pip install -r requirements.txt
cp config.py.sample config.py

# Print devices with microphone and their names to use in config file:
python3 -c "import sounddevice as sd; devices = sd.query_devices(); print('\n'.join(f'{idx}: {device[\"name\"]}' for idx, device in enumerate(devices)))"
# or 
python3 list_devices.py

# edit config using your preferred editor:
vim config.py

# Start application
python3 main.py
```

