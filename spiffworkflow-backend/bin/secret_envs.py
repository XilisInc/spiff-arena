#!/usr/bin/env python3
"""
Extract keys and values from ASM_SECRET environment variable to export as individual key/values
"""

import os

import json

ASM_SECRET = os.environ.get('ASM_SECRET')
OUTPUT = ""
if ASM_SECRET:
    secret_dict = json.loads(ASM_SECRET)
    secret_list = [f"{k.upper()}={v}" for k, v in secret_dict.items()]
    print(" ".join(secret_list))
else:
    raise Exception("No ASM_SECRET variable found! Aborting!")
