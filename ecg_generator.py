import numpy as np
import matplotlib.pyplot as plt
from scipy import signal
import csv
import os

def generate_ecg_waveform(t, period, sampling_rate, amplitude=1.0, phase_shift=0):
    """Generate a realistic ECG waveform for a single beat."""
    # Normalize time to one period
    t_norm = (t - phase_shift) % period / period
    
    # Create the basic ECG shape using a combination of Gaussian functions
    ecg = np.zeros_like(t_norm)
    
    # P wave (atrial depolarization)
    p_peak = 0.2
    p_width = 0.1
    ecg += 0.25 * amplitude * np.exp(-(t_norm - p_peak)**2 / (2 * p_width**2))
    
    # QRS complex
    # Q wave
    q_peak = 0.4
    q_width = 0.05
    ecg -= 0.1 * amplitude * np.exp(-(t_norm - q_peak)**2 / (2 * q_width**2))
    
    # R wave
    r_peak = 0.5
    r_width = 0.05
    ecg += amplitude * np.exp(-(t_norm - r_peak)**2 / (2 * r_width**2))
    
    # S wave
    s_peak = 0.6
    s_width = 0.05
    ecg -= 0.1 * amplitude * np.exp(-(t_norm - s_peak)**2 / (2 * s_width**2))
    
    # T wave
    t_peak = 0.8
    t_width = 0.15
    ecg += 0.35 * amplitude * np.exp(-(t_norm - t_peak)**2 / (2 * t_width**2))
    
    return ecg

def add_baseline_wander(t, amplitude=0.1, frequency=0.5):
    """Add realistic baseline wander."""
    return amplitude * np.sin(2 * np.pi * frequency * t)

def add_muscle_noise(t, sampling_rate, amplitude=0.05):
    """Add realistic muscle noise."""
    noise = np.random.normal(0, 1, len(t))
    # Filter to simulate muscle noise spectrum
    b, a = signal.butter(4, [20/(sampling_rate/2), 60/(sampling_rate/2)], btype='band')
    filtered_noise = signal.filtfilt(b, a, noise)
    return amplitude * filtered_noise

def generate_maternal_ecg(duration, sampling_rate):
    """Generate realistic maternal ECG signal."""
    t = np.linspace(0, duration, int(duration * sampling_rate))
    
    # Basic ECG parameters
    base_heart_rate = 75  # beats per minute
    base_period = 60 / base_heart_rate  # seconds per beat
    
    # Add heart rate variability
    rr_intervals = np.random.normal(base_period, 0.02, int(duration / base_period))
    cumulative_time = np.cumsum(rr_intervals)
    
    # Generate ECG signal
    ecg = np.zeros_like(t)
    for i, interval in enumerate(rr_intervals):
        if cumulative_time[i] > duration:
            break
        phase_shift = cumulative_time[i] - interval
        ecg += generate_ecg_waveform(t, interval, sampling_rate, 
                                   amplitude=1.0, 
                                   phase_shift=phase_shift)
    
    # Add baseline wander
    ecg += add_baseline_wander(t, amplitude=0.1, frequency=0.5)
    
    # Add muscle noise
    ecg += add_muscle_noise(t, sampling_rate, amplitude=0.05)
    
    return t, ecg

def generate_fetal_ecg(duration, sampling_rate):
    """Generate realistic fetal ECG signal."""
    t = np.linspace(0, duration, int(duration * sampling_rate))
    
    # Fetal ECG parameters (faster heart rate with more variability)
    base_heart_rate = 140  # beats per minute
    base_period = 60 / base_heart_rate  # seconds per beat
    
    # Add heart rate variability (more than maternal)
    rr_intervals = np.random.normal(base_period, 0.03, int(duration / base_period))
    cumulative_time = np.cumsum(rr_intervals)
    
    # Generate ECG signal with variable amplitude
    ecg = np.zeros_like(t)
    for i, interval in enumerate(rr_intervals):
        if cumulative_time[i] > duration:
            break
        phase_shift = cumulative_time[i] - interval
        # Vary the amplitude to simulate fetal movement
        amplitude = 0.3 * (1 + 0.2 * np.sin(2 * np.pi * 0.1 * cumulative_time[i]))
        ecg += generate_ecg_waveform(t, interval, sampling_rate, 
                                   amplitude=amplitude, 
                                   phase_shift=phase_shift)
    
    # Add fetal-specific noise
    ecg += add_muscle_noise(t, sampling_rate, amplitude=0.03)
    
    return t, ecg

def add_noise(signal, snr_db=20):
    """Add Gaussian noise to the signal with specified SNR."""
    signal_power = np.mean(signal ** 2)
    noise_power = signal_power / (10 ** (snr_db / 10))
    noise = np.random.normal(0, np.sqrt(noise_power/2), len(signal))
    return signal + noise

def generate_combined_ecg(duration=10, sampling_rate=1000, snr_db=20):
    """Generate combined maternal and fetal ECG with realistic noise."""
    # Generate maternal ECG
    t, maternal_ecg = generate_maternal_ecg(duration, sampling_rate)
    
    # Generate fetal ECG
    _, fetal_ecg = generate_fetal_ecg(duration, sampling_rate)
    
    # Combine signals
    combined_ecg = maternal_ecg + fetal_ecg
    
    # Add measurement noise
    noisy_ecg = add_noise(combined_ecg, snr_db)
    
    return t, noisy_ecg

def save_ecg_to_csv(t, ecg, filename="ecg_data.csv"):
    """
    Save ECG data to a CSV file.
    
    Parameters:
    -----------
    t : array-like
        Time points
    ecg : array-like
        ECG signal values
    filename : str
        Name of the CSV file to save
    """
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Time (s)', 'ECG Amplitude'])
        for i in range(len(t)):
            writer.writerow([t[i], ecg[i]])
    
    print(f"ECG data saved to {filename}")

def load_ecg_from_csv(filename):
    """
    Load ECG data from a CSV file.
    
    Parameters:
    -----------
    filename : str
        Name of the CSV file to load
        
    Returns:
    --------
    t : array
        Time points
    ecg : array
        ECG signal values
    """
    t = []
    ecg = []
    
    with open(filename, 'r', newline='') as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # Skip header row
        for row in reader:
            t.append(float(row[0]))
            ecg.append(float(row[1]))
    
    return np.array(t), np.array(ecg)

if __name__ == "__main__":
    # Generate and plot the signal
    t, ecg = generate_combined_ecg(duration=5, sampling_rate=1000, snr_db=20)
    
    # Save to CSV
    save_ecg_to_csv(t, ecg, "ecg_data.csv")
    
    # Plot the signal
    plt.figure(figsize=(12, 6))
    plt.plot(t, ecg)
    plt.title('Combined Maternal and Fetal ECG with Realistic Noise')
    plt.xlabel('Time (s)')
    plt.ylabel('Amplitude')
    plt.grid(True)
    plt.show() 