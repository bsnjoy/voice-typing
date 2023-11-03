#!/bin/bash

# stop all possible Threads from previous run.
pkill -f voice_typing.py

python3 voice_typing.py
