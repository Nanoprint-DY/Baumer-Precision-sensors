import numpy as np
import scipy.signal
from matplotlib import pyplot as plt

np.random.seed(42)  # for reproducibility
fs = 30  # sampling rate, Hz
ts = np.arange(0, 5, 1.0 / fs)  # time vector - 5 seconds
ys = np.sin(2*np.pi * 1.0 * ts)  # signal @ 1.0 Hz, without noise
yerr = 0.5 * np.random.normal(size=len(ts))  # Gaussian noise
yraw = ys + yerr


b, a = scipy.signal.iirfilter(4, Wn=2.5, fs=fs, btype="low", ftype="butter")
print(b, a, sep="\n")
y_lfilter = scipy.signal.lfilter(b, a, yraw)


plt.figure(figsize=[6.4, 2.4])

plt.plot(ts, yraw, label="Raw signal")
plt.plot(ts, y_lfilter, alpha=0.8, lw=3, label="SciPy lfilter")

plt.xlabel("Time / s")
plt.ylabel("Amplitude")
plt.legend(loc="lower center", bbox_to_anchor=[0.5, 1],
           ncol=2, fontsize="smaller")
