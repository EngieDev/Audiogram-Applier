import scipy.io.wavfile as wavfile
import scipy.fft as fft
import numpy as np
from scipy.interpolate import interp1d
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

import time
import json
import math
import getopt
import sys
import warnings
import os
import subprocess
import pathlib

helpstr = "python3 " + __file__ + " -i <input> -o <output_folder> -a <audiogram> [--anim]"

audiogramLeft = []
audiogramRight = []

# Checks for the required command line options
try:
    opts, args = getopt.getopt(sys.argv[1:], "i:o:a:h", ["inMedia=", "outFolder=", "audiogram=", "anim"])
except getopt.GetoptError:
    print(helpstr)

# Decides ffmpeg binary name
if os.name == 'nt':
    ffmpeg = "ffmpeg.exe"
else:
    ffmpeg = "ffmpeg"

# Set the option variables based on opts
inMedia = ""
outFolder = ""
anim = False
audiogram = ""

for opt, arg in opts:
    if opt == "-h":
        print(helpstr)
        sys.exit(1)
    elif opt in ("-i", "--inMedia"):
        inMedia = arg
    elif opt in ("-o", "--outFolder"):
        outFolder = arg
    elif opt in ("-a", "--audiogram"):
        audiogram = arg
    elif opt == "--anim":
        anim = True

if opts == []:
    print(helpstr)
    sys.exit(1)

# Loads audiogram data from file
def load(path):
    global audiogramRight, audiogramLeft

    try:
        with open(path, 'r', encoding="utf-8") as f:
            audiograms = json.load(f)
            f.close()

        audiogramLeft = audiograms[0]
        audiogramRight = audiograms[1]

        audiogramLeft.sort(key=lambda x: x[0])
        audiogramRight.sort(key=lambda x: x[0])

        print("Loaded audiograms")
    except Exception as e:
        print(str(e))
        sys.exit(2)
load(audiogram)

# Makes the output folder, asks whether to continue if already exists as it could overwrite data
try:
    os.mkdir(outFolder)
except FileExistsError:
    print("Output folder already exists, there could be some data overwritten, continue? (Y/N)")
    answer = input()

    if answer not in ("Y", "y", "yes", "YES"):
        sys.exit(2)

folder = pathlib.Path(outFolder)

# Calls ffmpeg to generate the 2 channel, 16bit audio file for the script to process
print("Calling ffmpeg to get the audio")
output = subprocess.run([ffmpeg, "-y", "-i", inMedia, "-ac", "2", "-sample_fmt", "s16", folder / "originalAudio.wav"], capture_output=True)

if output.returncode != 0:
    print(output.stderr)
    print(output.stdout)
    sys.exit()

# Load the audiofile
rate, data = wavfile.read(folder / "originalAudio.wav")

N = len(data)
resolution = rate/N

# Pad the audiogram to match the fft axes
audiogramLeft.append([0, audiogramLeft[0][1]])
audiogramLeft.append([int(rate), audiogramLeft[-2][1]])

audiogramRight.append([0, audiogramRight[0][1]])
audiogramRight.append([int(rate), audiogramRight[-2][1]])

audiogramLeft.sort(key=lambda x: x[0])
audiogramRight.sort(key=lambda x: x[0])

# Splits audio into indivdual channels
left = data.T[0]
right = data.T[1]

print("Starting fft")

# Performs the FFT and scales to conserve energy
fftLeft = fft.rfft(left) * 1.0/N
fftRight = fft.rfft(right) * 1.0/N

print("Starting equalisation")

frequencies = np.linspace(0, len(fftLeft)*resolution, num=len(fftLeft))

# Converts audiogram to L/R X/Y pairs for interpolation
dbLX = []
dbLY = []
for x in audiogramLeft:
    dbLX.append(x[0])
    dbLY.append(x[1])

dbRX = []
dbRY = []
for x in audiogramRight:
    dbRX.append(x[0])
    dbRY.append(x[1])

# Interpolates the values to get a smooth curve for audiogram application
dBL = interp1d(dbLX, dbLY, kind="cubic")
dBR = interp1d(dbRX, dbRY, kind="cubic")

# Scales the fft and converts to dB, then applies the audiogram
fftLeft *= 100
fftRight *= 100
fftLeft2 = fftLeft*10**(-dBL(frequencies)/10)
fftRight2 = fftRight*10**(-dBR(frequencies)/10)

# Plots and saves the audiogram
fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(frequencies, -dBL(frequencies), color="blue", linestyle="dashed", label="Left Audiogram")
ax.plot(frequencies, -dBR(frequencies), color="red", linestyle="dashed", label="Right Audiogram")
ax.legend(loc="upper right")
plt.savefig(str(folder / "audiogram.png"))
print("Saved audiogram plot to " + str(folder / "audiogram.png"))

# Inverts the FFT after reversing the energy conservation
print("Starting inverse fft")

ifftLeft = np.fft.irfft((fftLeft2)*N)
ifftRight = np.fft.irfft((fftRight2)*N)

# Saves to new audiofile
print("Saving to wav file")
correctedData = []
for x in range(len(ifftLeft)):
    correctedData.append([ifftLeft[x], ifftRight[x]])

correctedData = np.array(correctedData)

wav = str(folder / "convertedAudio.wav")
wavfile.write(wav, rate, correctedData.astype(np.int16))

print("Saved converted audio to " + wav)

# Splices audio onto media file if its a video file
if " Video: " in str(output.stderr):
    print("Splicing audio onto original media")
    filename, extension = os.path.splitext(inMedia)
    output = subprocess.run([ffmpeg, 
                                "-y",
                                "-i", inMedia, 
                                "-i", wav,
                                "-c:v", "copy",
                                "-map", "0:v:0",
                                "-map", "1:a:0",
                                str(folder / "convertedMedia") + extension], capture_output=True)

    if output.returncode != 0:
        print(output.stderr)
        sys.exit(4)

    print("Video file saved to " + str(folder / "convertedMedia") + extension)

# Creates the animations
if anim:
    print("Processing animations")

    runtime = len(data)/rate
    oldPercentage = "0"

    correctedData = correctedData.real
    correctedData = correctedData.real

    origL = data.T[0]
    origR = data.T[1]
    afterL = correctedData.T[0]
    afterR = correctedData.T[1]

    windowStart = 0
    windowLengthSeconds = 0.1

    def animate(i):
        global windowStart, windowLengthSeconds, dBL, dBR, ax, oldPercentage, rate, origR, origL, afterL, afterR
        start = int(windowStart*rate)
        N = int(windowLengthSeconds*rate)

        if start+N > len(data):
            return
        else:
            end = start+N

        # FFT the particular time segment
        fftOrigL = fft.rfft(origL[start:end])
        fftOrigR = fft.rfft(origR[start:end])
        fftAfterL = fft.rfft(afterL[start:end])
        fftAfterR = fft.rfft(afterR[start:end])

        frequencies = np.linspace(0, rate/2, num=len(fftOrigL))

        # Converts to dB
        with np.errstate(divide='ignore'):
            fftOrigL = 10*np.log10((np.abs(fftOrigL)/32767)*1.0/N)
            fftOrigR = 10*np.log10((np.abs(fftOrigR)/32767)*1.0/N)
            fftAfterL = 10*np.log10((np.abs(fftAfterL)/32767)*1.0/N)
            fftAfterR = 10*np.log10((np.abs(fftAfterR)/32767)*1.0/N)

        # Plots
        ax.clear()
        ax.set(xlim=(0, rate/2), ylim=(-110, 0))

        ax.plot(frequencies, fftOrigL, color="blue", label="Left")
        ax.plot(frequencies, fftAfterL, color="lightblue", label="Corrected Left")
        ax.plot(frequencies, fftOrigR, color="red", label="Right")
        ax.plot(frequencies, fftAfterR, color="lightcoral", label="Corrected Right")

        percentage = "{:.2f}%".format(((start+N)/len(data))*100)

        if percentage != oldPercentage:
            oldPercentage = percentage
            print(percentage, end='\r')

        windowStart = windowStart + windowLengthSeconds

    anim = FuncAnimation(fig, animate, interval=100, frames=int(runtime*10))
    anim.save(folder / "anim.mp4")
    print("100.00%")
    print("Saved animation to " + str(folder/"anim.mp4"))

