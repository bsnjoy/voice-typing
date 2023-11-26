#!/usr/bin/env python3

# In Mac OS Before run allow Settings-Microphone and Accessibility for iTerm and VSCode
# https://support.apple.com/en-us/102071
import os
import sys
import sounddevice as sd
import pyautogui
import requests
from pynput import keyboard
import threading
from datetime import datetime
import wave
import queue
import json
import pyclip
import time
import config
import subprocess
import re

app = 'voice-typing'
ver = '0.020'

# Disable the Fail-Safe, because we don't neet to stop a pyautogui script when mouse is moved to a corner of the screen
pyautogui.FAILSAFE = False

stop_update_mic_thread = False
keyboard_thread = None
mic_update_thread = None

transcribe_server_url = f"{config.transcribe_server}?token={config.token}&languages={config.languages}&app={app}-{ver}"

# Convert the list of lists to an AppleScript list of lists format
mac_menu_as = '{' + ', '.join(['{' + ', '.join(['"' + str(item[key]) + '"' for key in ['edit', 'paste']]) + '}' for item in config.mac_menu]) + '}'

def printt(text):
    current_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # Format current time
    thread_id = threading.get_ident()  # Get current thread id
    print(f"{current_time} [Thread-{thread_id}] {text}")

printt(f"{mac_menu_as}")
printt(f'{[sys.executable] + sys.argv}')
printt(f'Transcribe server: {transcribe_server_url}')

# Compile the regex case-insensitive patterns
substitutions_case_insensitive = {re.compile(pattern, re.IGNORECASE): replacement for pattern, replacement in config.substitutions_case_insensitive.items()}

audio_queue = queue.Queue()

lock = threading.Lock()

samplerate = 16000

keys_pressed = set()

recording_audio = False
processing_audio = False
record_start_time = None
# Global declaration
audio_stream = None

if sys.platform == 'darwin':  # This checks if the OS is MacOS
    key_to_hold = 'command'
else:
    key_to_hold = 'ctrl'

# The sounddevice library internally caches the list of devices for performance reasons. However, it does not provide an explicit way to reset or refresh this cache through its public API.
# One way to bypass the cached devices and force sounddevice to re-query the devices is to restart the Python process or script, but this may not be ideal in many scenarios.
def get_selected_mic():
    result = subprocess.run([sys.executable, "select_mic.py"], capture_output=True, text=True)
    if result.returncode != 0:
        printt(f'Error getting selected microphone. May be Ctrl+C pressed. Wait 5 seconds to finish all threads...')
        return {"index": config.fallback_mic_index, "name": "Default"}
    result_stdout = result.stdout.strip()
    json_data = json.loads(result_stdout)
    return json_data

selected_mic = None

def restart_program():
    global stop_update_mic_thread, keyboard_thread
    printt("Restarting app!!!!!")
    stop_update_mic_thread = True
    keyboard.Listener.stop(keyboard_thread)
    printt("keyboard_thread.stop() finish!!!!!")
    subprocess.Popen([sys.executable] + sys.argv)
    sys.exit()

def update_mic():
    global selected_mic, processing_audio, stop_update_mic_thread
    while not stop_update_mic_thread:
        if not processing_audio:  # Don't check microphone update while recording audio.
            new_mic = get_selected_mic()
            if selected_mic is None:
                selected_mic = new_mic
                printt(f"Microphone selected: {selected_mic}")
            elif new_mic["index"] != selected_mic["index"] or new_mic["name"] != selected_mic["name"]:
                printt(f"Microphone changed to index: {new_mic['index']}, name: {new_mic['name']}")
                selected_mic = new_mic
                # There's no other way to clear SoundDevice library cache
                restart_program()
        time.sleep(5)  # wait for 5 seconds before checking again
        #printt("update_mic loop")


def save_audio_to_file(data):
    # Store year/month/day in separate folders
    recordings_dir = f"{config.recordings_dir}/{datetime.now().strftime('%Y/%m/%d')}"
    if not os.path.exists(recordings_dir):
        os.makedirs(recordings_dir)
    filename = f"{recordings_dir}/record_{datetime.now().strftime('%Y%m%d-%H%M%S')}.wav"
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 2 bytes because format is int16
        wf.setframerate(samplerate)
        wf.writeframes(b''.join(data))
    return filename

def transcribe_audio_to_text(fname):
    printt(f"Transcribing {fname}...")
    with open(fname, 'rb') as f:
        response = requests.post(transcribe_server_url, files={'file': f})
    printt(f"Transcription response: {response.text}")
    try:
        data = json.loads(response.text)
    except json.JSONDecodeError as e:
        printt(f"Error decoding JSON response: {e}")
        data = {'text': '', 'language': ''}
    except Exception as e:
        printt(f"Error unexpected decoding  JSON: {e}")
        data = {'text': '', 'language': ''}

    return data


def check_keys_combination():
    return all(k in keys_pressed for k in config.hotkey_2)


def callback(indata, frames, time, status):
    """This is called (from a separate thread) for each audio block."""
    global audio_queue
    # printt('callback initiated')
    audio_queue.put(bytes(indata))

def paste(text):
    global key_to_hold

    saved_clipboard = None
    try:
        saved_clipboard = pyclip.paste()
    except:
        saved_clipboard = None
# Try to paste using AppleScript. If it fails, use pyautogui. AppleScript by clicking menu Edit->Paste is more reliable, then presing Cmd+V
    if sys.platform == 'darwin':  # This checks if the OS is MacOS
        applescript = f"""
set the clipboard to "{text}"
tell application "System Events"
    set frontmostApp to name of the first application process whose frontmost is true
    tell process frontmostApp
        set menuItems to {mac_menu_as}
        set success to false
        repeat with menuItem in menuItems
            try
                click menu item (item 2 of menuItem) of menu 1 of menu bar item (item 1 of menuItem) of menu bar 1
                set success to true
                exit repeat
            on error
                -- continue to next iteration
            end try
        end repeat
        if not success then
            return "fail"
        else
            return "success"
        end if
    end tell
end tell
"""
        result = subprocess.run(["osascript", "-e", applescript], capture_output=True, text=True)
        printt(f"AppleScript {result.stdout.strip()}")
        # We don't use AppleScript to Paste ```keystroke "v" using {{command down}}``` because it's only working in english layout
        if result.stdout.strip() == 'fail':
            printt('AppleScript failed to click menu Paste. Trying pyautogui Cmd+V')
            pyclip.copy(text)
            if config.v_delay > 0:
                time.sleep(config.v_delay)
            with pyautogui.hold(['command']):
                time.sleep(1)
                pyautogui.press('v')
        time.sleep(config.restore_clipborad_delay)
    else:
        pyclip.copy(text)
        if config.v_delay > 0:
            time.sleep(config.v_delay)
        pyautogui.hotkey('ctrl', 'v')

    if saved_clipboard is not None:
        pyclip.copy(saved_clipboard)


def stop_audio_stream():
    global audio_stream, audio_queue, processing_audio, record_start_time
    record_duration = (datetime.now() - record_start_time).total_seconds() * 1000
    audio_stream.stop()
    audio_stream.close()
    audio_data = []
    while not audio_queue.empty():
        audio_data.append(audio_queue.get())

    audio_duration_ms = len(audio_data)* 1000000 / samplerate
    printt(f'Finished recording audio. Got {len(audio_data)} frames. Audio duration: {audio_duration_ms} ms. Record duration: {record_duration} ms.')
    filename = save_audio_to_file(audio_data)

    if audio_duration_ms < config.min_audio_duration_ms:
        printt('Audio duration is too short. Exiting...')
        processing_audio = False
        return

    data = transcribe_audio_to_text(filename)
    text = data['text']
    language = data['language']
    printt(f"Language: {language} Got result: {text}")

    if len(text) < 2:
        printt('No text detected. Exiting...')
        processing_audio = False
        return

    # Apply case-sensitive substitutions
    for old, new in config.substitutions_case_sensitive.items():
        text = text.replace(old, new)

    # Apply case-insensitive substitutions
    for pattern, replacement in substitutions_case_insensitive.items():
        text = pattern.sub(replacement, text)

    # Apply regular expression substitutions
    for pattern, replacement in config.substitutions_regex.items():
        text = re.sub(pattern, replacement, text)

    printt(f"After substitutionst: {text}")
    paste(text)
    printt('Finished processing audio...')
    processing_audio = False

def start_audio_stream():
    global recording_audio, audio_stream, selected_mic, record_start_time
    recording_audio = True
    record_start_time = datetime.now()
    printt('Started recording audio...')
    audio_stream = sd.RawInputStream(samplerate=samplerate, blocksize=1000, device=selected_mic["index"],
                                    dtype="int16", channels=1, callback=callback)
    audio_stream.start()
    while recording_audio:
        time.sleep(0.1)
    stop_audio_stream()


def on_press(key):
    global keys_pressed, processing_audio, lock
    if key in config.hotkey_2:
        keys_pressed.add(key)

    if check_keys_combination() or key == config.hotkey_1:
        if lock.acquire(blocking=False): # This will prevent multiple threads from starting at the same time.
            if not processing_audio:
                processing_audio = True
                threading.Thread(target=start_audio_stream).start()
            lock.release()



def on_release(key):
    global recording_audio, keys_pressed

    if key in keys_pressed:
        keys_pressed.remove(key)

    if recording_audio and (not check_keys_combination() or key == config.hotkey_1):
        recording_audio = False  # This will terminate the process_audio_thread.

if __name__ == '__main__':
    printt("Started main. Press Ctrl+C to exit.")
    mic_update_thread = threading.Thread(target=update_mic, daemon=None)
    mic_update_thread.start()

    keyboard_thread = keyboard.Listener(on_press=on_press, on_release=on_release)
    keyboard_thread.start()
    try:
        keyboard_thread.join()
    except KeyboardInterrupt:
        print("Program was interrupted by the user. Wait 5 seconds to finish all threads...")
    printt("main - keyboard_thread.join() finish!!!!!")

    stop_update_mic_thread = True
    mic_update_thread.join()
    printt("main - mic_update_thread.join() finish!!!!!")
