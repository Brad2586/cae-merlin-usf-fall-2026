# Merlin Wake-Word Recording Layout

Do not place sensitive or proprietary speech in this dataset.

## Folders

- `positive/`: isolated recordings containing only the word "Merlin"
- `negative_speech/`: the same speakers saying varied phrases without "Merlin"
- `background_noise/`: simulator, room, headset, fan, and equipment noise
- `converted/`: normalized WAV files produced from source recordings

Create these folders when recordings are ready. Keep original recordings
outside `converted/` so preprocessing can be repeated.

## Recording guidance

- Prefer lossless WAV at capture time. MP3 is accepted as source material.
- Record at least 20-50 positive examples per speaker.
- Vary speaking speed, volume, microphone distance, and background conditions.
- Include at least 10 seconds of varied negative speech per speaker.
- Capture representative simulator and headset noise without the wake word.
- Obtain consent from every recorded speaker.

## Required training format

Convert source clips to mono, 16 kHz, signed 16-bit PCM WAV. Example with
FFmpeg:

```powershell
ffmpeg -i input.mp3 -ac 1 -ar 16000 -sample_fmt s16 converted\merlin_001.wav
```

Use short positive clips with roughly 0.2-0.5 seconds of context around the
wake word. Do not duplicate the same recording to inflate the sample count.

## Training note

A model trained only on one speaker is a personalized prototype. A general
CAE model should combine recordings from multiple consenting speakers,
synthetic positive examples, and large negative speech/noise datasets. Model
training and threshold selection must be evaluated with held-out recordings
and false-activations-per-hour testing before simulator deployment.
