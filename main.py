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
import pyperclip
import time
import config
import subprocess

# Disable the Fail-Safe, because we don't neet to stop a pyautogui script when mouse is moved to a corner of the screen
pyautogui.FAILSAFE = False

audio_queue = queue.Queue()

samplerate = 16000

keys_pressed = set()
processing_audio = False

# Global declaration
audio_stream = None

if sys.platform == 'darwin':  # This checks if the OS is MacOS
    key_to_hold = 'command'
else:
    key_to_hold = 'ctrl'


def select_mic():
    """
    Returns the index of the desired microphone based on availability.
    Prioritize config.primary_mic_name, if not available, then use config.backup_mic_name if available.
    If both not available, fallback to config.fallback_mic_index
    """
    devices = sd.query_devices()

    # return index, not name because on windows can be multiple devices with same name
    mic_index = config.fallback_mic_index
    for device in devices:
        print(device)
        if device['name'] == config.primary_mic_name:
            mic_index = device["index"]
            break

        if device['name'] == config.backup_mic_name:
            mic_index = device["index"]

    return mic_index


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
    print(f"Transcribing {fname}...")
    with open(fname, 'rb') as f:
        response = requests.post(config.transcribe_server, files={'file': f})
    return json.loads(response.text)


def check_keys_combination():
    return all(k in keys_pressed for k in config.hotkey_2)


def callback(indata, frames, time, status):
    """This is called (from a separate thread) for each audio block."""
    global audio_queue
    print('callback initiated')
    audio_queue.put(bytes(indata))

def paste(text):
    if sys.platform == 'darwin':  # This checks if the OS is MacOS 
        applescript = f"""
    set saved_clipboard to the clipboard
    set the clipboard to "{text}"
    tell application "System Events"
        set frontmostApp to name of the first application process whose frontmost is true
        tell process frontmostApp
            -- keystroke "v" using command down
            click menu item "Paste" of menu 1 of menu bar item "Edit" of menu bar 1
        end tell
    end tell
    delay 1
    set the clipboard to saved_clipboard
    """
        subprocess.run(["osascript", "-e", applescript])
    else:
        saved_clipboard = pyperclip.paste()
        pyperclip.copy(text)
        with pyautogui.hold([key_to_hold]):
            if config.v_delay > 0:
                time.sleep(config.v_delay)
            pyautogui.press('v')
        if saved_clipboard is not None:
            pyperclip.copy(saved_clipboard)


def stop_audio_stream():
    global audio_stream, key_to_hold, processing_audio, audio_queue
    audio_stream.stop()
    audio_stream.close()
    processing_audio = False
    audio_data = []
    while not audio_queue.empty():
        audio_data.append(audio_queue.get())
    filename = save_audio_to_file(audio_data)

    data = transcribe_audio_to_text(filename)
    text = data['text']
    language = data['language']
    print(f"Language: {language} Got result: {text}")

    paste(text)

def start_audio_stream():
    global processing_audio, audio_stream
    print('Started recording audio...')
    processing_audio = True
    selected_mic = select_mic()
    audio_stream = sd.RawInputStream(samplerate=samplerate, blocksize=1000, device=selected_mic,
                                     dtype="int16", channels=1, callback=callback)
    audio_stream.start()

def process_audio_thread():
    global processing_audio
    while processing_audio:
        # Keep the thread alive while processing audio. This can be enhanced to process other tasks if needed.
        time.sleep(0.1)
    stop_audio_stream()

def on_press(key):
    global processing_audio

    if key in config.hotkey_2:
        keys_pressed.add(key)

    if not processing_audio and (check_keys_combination() or key == config.hotkey_1):
        start_audio_stream()
        threading.Thread(target=process_audio_thread, daemon=True).start()


def on_release(key):
    global processing_audio, keys_pressed

    if key in keys_pressed:
        keys_pressed.remove(key)

    if processing_audio and (not check_keys_combination() or key == config.hotkey_1):
        processing_audio = False  # This will terminate the process_audio_thread.


def listen_keyboard():
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()


if __name__ == '__main__':
    print("started")
    keyboard_thread = threading.Thread(target=listen_keyboard, daemon=True)
    keyboard_thread.start()
    keyboard_thread.join()  # This will keep the main thread alive until keyboard_thread terminates.