#!/usr/bin/env python3

from pynput import keyboard
from datetime import datetime

def printt(text):
    current_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # Format current time
    print(f"{current_time}	{text}")


def on_press(key):
    try:
        # If the key has a printable representation, display that
        printt('alphanumeric key {0} pressed'.format(key.char))
    except AttributeError:
        # If the key doesn't have a printable representation (like 'ctrl' or 'alt'), display its name
        printt('special key {0} pressed'.format(key))
        print(key)

def on_release(key):
    printt('{0} released'.format(key))
    # Exit the listener when the 'esc' key is pressed
#    if key == keyboard.Key.esc:
#        return False

# Set up the listener to monitor key presses and releases
listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.start()
listener.join()

