import sounddevice as sd; 

devices = sd.query_devices()

for idx, device in enumerate(devices):
    print(f"{idx}: {device['name']}")