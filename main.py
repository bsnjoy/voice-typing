#!/usr/bin/env python3

# Before run allow Settings-Microphone and Accessibility for iTerm and VSCode
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

audio_queue = queue.Queue()

samplerate = 16000

keys_pressed = set()
processing_audio = False
last_chunk = False
audio_stream_stoped = False

# Global declaration
audio_stream = None

if sys.platform == 'darwin':  # This checks if the OS is MacOS
    key_to_hold = 'command'
else:
    key_to_hold = 'ctrl'


def select_mic():
    """
    Returns the index of the desired microphone based on availability.
    Prioritize config.preffered_mic, if not available, fallback to config.fallback_mic
    """
    devices = sd.query_devices()

    mic = config.fallback_mic
    for device in devices:
        print(device)
        if device['name'] == config.preffered_mic:
            mic = config.preffered_mic
            break
    return mic

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
    global audio_queue, processing_audio, last_chunk, audio_stream_stoped
    print('callback initiated')

    if not audio_stream_stoped:
        audio_queue.put(bytes(indata))

    if not processing_audio:
        last_chunk = True

def stop_audio_stream():
    global audio_stream, audio_stream_stoped, key_to_hold
    audio_stream_stoped = True
    audio_data = []
    while not audio_queue.empty():
        audio_data.append(audio_queue.get())
    filename = save_audio_to_file(audio_data)
    data = transcribe_audio_to_text(filename)
    text = data['text']
    language = data['language']
    print(f"Language: {language} Got result: {text}")
    saved_clipboard = pyperclip.paste()
    pyperclip.copy(text)
    
    with pyautogui.hold([key_to_hold]):
        time.sleep(config.v_delay)
        pyautogui.press('v')

    pyperclip.copy(saved_clipboard)

    audio_stream.stop()
    audio_stream.close()


def start_audio_stream():
    global processing_audio, audio_stream, last_chunk, audio_stream_stoped
    print('Started recording audio...')
    processing_audio = True
    audio_stream_stoped = False
    last_chunk = False
    selected_mic = select_mic()
    audio_stream = sd.RawInputStream(samplerate=samplerate, blocksize=4000, device=selected_mic,
                                     dtype="int16", channels=1, callback=callback)
    audio_stream.start()

def on_press(key):
    global processing_audio

    if key in config.hotkey_2:
        keys_pressed.add(key)

    if not processing_audio and (check_keys_combination() or key == config.hotkey_1):
        start_audio_stream()

def receive_last_audio_chunk_and_stop():
    global processing_audio
    print('Stopped recording audio...')
    # We don't stop immediately, we wait for the last chunk to be processed
    processing_audio = False

def on_release(key):
    global processing_audio, keys_pressed
    if key in keys_pressed:
        keys_pressed.remove(key)

    if processing_audio and (not check_keys_combination() or key == config.hotkey_1):
        receive_last_audio_chunk_and_stop()

def listen_keyboard():
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()
    
print("#" * 80)
print("Press Ctrl+C twice to stop the service")
print("#" * 80)
keyboard_thread = threading.Thread(target=listen_keyboard)
keyboard_thread.start()
while True:
    if last_chunk and not audio_stream_stoped and not processing_audio:
        stop_audio_stream()
    pass  # Keep the script running