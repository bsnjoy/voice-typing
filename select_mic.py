#!/usr/bin/env python3

import sounddevice as sd
import config
import json

def select_mic():
    """
    Returns the index and name of the desired microphone in JSON format based on availability.
    Prioritize config.primary_mic_name, if not available, then use config.backup_mic_name if available.
    If both not available, fallback to config.fallback_mic_index
    """
    mic_info = {"index": config.fallback_mic_index, "name": "Default"}
    try:
        devices = sd.query_devices()

        for device in devices:
            if device['name'] == config.primary_mic_name:
                mic_info = {"index": device["index"], "name": device["name"]}
                break

            if device['name'] == config.backup_mic_name:
                mic_info = {"index": device["index"], "name": device["name"]}

        return {"status": "success", **mic_info}

    except Exception as e:
        return {"status": "error", **mic_info, "message": str(e)}

if __name__ == "__main__":
    mic_selected = select_mic()
    print(json.dumps(mic_selected))