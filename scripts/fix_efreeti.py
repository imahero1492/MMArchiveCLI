#!/usr/bin/env python3
"""Fix Efreeti Sounds - Copy and convert only missing Efreeti files."""

import subprocess
import shutil
from pathlib import Path

source_dir = Path("J:/Heroes/sound/01 RoE 1.0/Data/Heroes3_snd")
renamed_dir = Path("J:/Heroes/renamed-sound/inferno")
webm_dir = Path("J:/Heroes/webm-sounds/inferno")

efreeti_sounds = {
    "EFRTATTK": "Heroes3 - Efreeti - AttackSound.wav",
    "EFRTDFND": "Heroes3 - Efreeti - DefendSound.wav",
    "EFRTKILL": "Heroes3 - Efreeti - DeathSound.wav",
    "EFRTMOVE": "Heroes3 - Efreeti - MoveSound.wav",
    "EFRTWNCE": "Heroes3 - Efreeti - HurtSound.wav"
}

renamed_dir.mkdir(parents=True, exist_ok=True)
webm_dir.mkdir(parents=True, exist_ok=True)

for source_name, target_name in efreeti_sounds.items():
    source_file = None
    for wav in source_dir.glob("*.wav"):
        if wav.stem.upper() == source_name.upper():
            source_file = wav
            break
    
    if not source_file:
        print(f"✗ Not found: {source_name}.wav")
        continue
    
    target_wav = renamed_dir / target_name
    shutil.copy2(source_file, target_wav)
    print(f"✓ Copied: {target_name}")
    
    target_webm = webm_dir / target_name.replace('.wav', '.webm')
    subprocess.run(['ffmpeg', '-i', str(target_wav), '-y', str(target_webm)],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    print(f"✓ Converted: {target_webm.name}")

print("\nDone!")
