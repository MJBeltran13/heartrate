# ECG Generator and Analyzer

This project provides tools for generating synthetic maternal and fetal ECG signals with noise, and analyzing them to detect R peaks and calculate heart rate.

## Setup

1. Make sure you have Python 3.7+ installed on your system.

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Running the ECG Generator

The ECG generator creates synthetic maternal and fetal ECG signals with noise. To run it:

```
python ecg_generator.py
```

This will generate a 5-second ECG signal with:
- Maternal ECG (75 BPM)
- Fetal ECG (140 BPM)
- Added noise (SNR = 20 dB)

The signal will be displayed in a plot.

## Running the ECG Analyzer

The ECG analyzer detects R peaks and calculates heart rate from an ECG signal. To run it:

```
python ecg_analyzer.py
```

This will:
1. Generate a sample ECG signal
2. Detect R peaks in the signal
3. Calculate the heart rate
4. Display two plots:
   - ECG signal with detected R peaks
   - Heart rate over time

## Using the Functions in Your Code

You can also import and use the functions in your own Python scripts:

```python
# Generate ECG signal
from ecg_generator import generate_combined_ecg
t, ecg = generate_combined_ecg(duration=10, sampling_rate=1000, snr_db=20)

# Analyze ECG
from ecg_analyzer import analyze_ecg, plot_analysis
peaks, heart_rates, times = analyze_ecg(ecg, sampling_rate=1000)
plot_analysis(ecg, peaks, heart_rates, times, sampling_rate=1000)
```

## Parameters

### ECG Generator Parameters:
- `duration`: Length of the signal in seconds (default: 10)
- `sampling_rate`: Sampling rate in Hz (default: 1000)
- `snr_db`: Signal-to-noise ratio in dB (default: 20)

### ECG Analyzer Parameters:
- `min_distance`: Minimum distance between R peaks in seconds (default: 0.2)
- `window_size`: Size of the window for calculating moving average in seconds (default: 10) 