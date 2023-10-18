#!/usr/bin/env python3

from pynput import keyboard

def on_press(key):
    try:
        # If the key has a printable representation, display that
        print('alphanumeric key {0} pressed'.format(key.char))
    except AttributeError:
        # If the key doesn't have a printable representation (like 'ctrl' or 'alt'), display its name
        print('special key {0} pressed'.format(key))

def on_release(key):
    print('{0} released'.format(key))
    # Exit the listener when the 'esc' key is pressed
    if key == keyboard.Key.esc:
        return False

# Set up the listener to monitor key presses and releases
listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.start()
listener.join()

