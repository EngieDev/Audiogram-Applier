# Introduction
This is an attempt to simulate the acoustic implications of 
certain types of hearing loss.

The idea is to use a medically obtained audiogram and apply 
its values to arbitrary audiofiles to give a 3rd person the
possibility to get an impression how the owner of that 
audiogram experiences their world

# Install Requirements
- python 3.7 or higher
  - https://www.python.org/downloads/
  - Or use the inbuilt package manager, i.e
    - ```sudo apt install python3```
- scipy and matplotlib 
    - Run below command in cmd prompt/powershell/terminal
        - ```python3 -m pip install scipy matplotlib```
- ffmpeg
    - Download from https://ffbinaries.com/downloads and 
      place into same folder as AA.py or on the $PATH.
    - Or via inbuilt package manager, i.e
        - ```sudo apt install ffmpeg```

# Usage:
```bash
python AA.py -i "path/to/media/file"
             -o "path/to/output/folder"
             -a "path/to/audiogram/file"
             [--anim] 
```

- Paths can be relative or absolute
- Output folder will be created if it doesn't exist
- --anim is an optional flag, produces an updating animation 
  of the spectrums, however it takes a while to process


# Audiogram:
The audio processing is based on an audiogram file.

This file contains 2 arrays, one for the left audio channel,
one for the right audio channel. 

Each channel array contains
a number of frequency/dB pairs which will be applied to
the audio signal by the Python script.

The format of the file is:

``` 
[
    # Left channel parameters
    [
        [Hz, dB],
        [Hz, dB],
        [Hz, dB],
        [Hz, dB],
        ...,
        ...
    ],

    # Right channel parameters
    [
        [Hz, dB],
        [Hz, dB],
        [Hz, dB],
        [Hz, dB],
        ...,
        ...
    ]
]
```

Since most audiograms will not contain points beyond ~8 KHz,
you'll have to extend the curve beyond that point manually,
for example by repeating the last point's dB for 12, 16, 18
and 22 Khz.

You can also increase the attenuation (dB values)
gradually if that fits your hearing curve better.

# Acknowledgements
Thank you E@gle for your continuous support and aid throughout
<3

