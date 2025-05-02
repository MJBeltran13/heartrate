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

def simulate_ad8232_output(ecg_signal, sampling_rate, vcc=3.3, vref=1.65, 
                          lead_off_detection=False, lead_off_duration=0.5, 
                          lead_off_start=5.0):
    """
    Simulate the output of an AD8232 ECG sensor.
    
    Parameters:
    -----------
    ecg_signal : array-like
        The raw ECG signal
    sampling_rate : int
        Sampling rate of the signal in Hz
    vcc : float
        Supply voltage (typically 3.3V)
    vref : float
        Reference voltage (typically 1.65V for 3.3V supply)
    lead_off_detection : bool
        Whether to simulate lead-off detection
    lead_off_duration : float
        Duration of lead-off detection in seconds
    lead_off_start : float
        Start time of lead-off detection in seconds
        
    Returns:
    --------
    ad8232_output : array
        Simulated AD8232 output signal
    lead_off_status : array
        Lead-off detection status (1 = leads connected, 0 = leads disconnected)
    """
    # AD8232 has a gain of approximately 100
    gain = 100
    
    # Scale the ECG signal to match AD8232 output range
    # AD8232 outputs around Vref when no signal is present
    # and varies by approximately ±1V for typical ECG signals
    max_amplitude = 1.0  # Maximum expected ECG amplitude in mV
    scaled_signal = ecg_signal * (1.0 / max_amplitude)  # Scale to ±1V range
    
    # Apply gain
    amplified_signal = scaled_signal * gain / 1000  # Convert to V
    
    # Center around Vref
    centered_signal = amplified_signal + vref
    
    # Clip to VCC and GND
    clipped_signal = np.clip(centered_signal, 0, vcc)
    
    # Add some quantization noise (AD8232 has 10-bit ADC)
    quantization_levels = 2**10
    quantization_step = vcc / quantization_levels
    quantized_signal = np.round(clipped_signal / quantization_step) * quantization_step
    
    # Simulate lead-off detection
    lead_off_status = np.ones_like(quantized_signal)
    
    if lead_off_detection:
        # Find the indices for lead-off detection
        start_idx = int(lead_off_start * sampling_rate)
        end_idx = int((lead_off_start + lead_off_duration) * sampling_rate)
        
        # Set lead-off status to 0 during the specified period
        lead_off_status[start_idx:end_idx] = 0
        
        # During lead-off, the output goes to VCC (3.3V)
        quantized_signal[start_idx:end_idx] = vcc
    
    return quantized_signal, lead_off_status

def generate_combined_ecg(duration=10, sampling_rate=1000, snr_db=20, 
                         lead_off_detection=False, lead_off_duration=0.5, 
                         lead_off_start=5.0):
    """Generate combined maternal and fetal ECG with realistic noise."""
    # Generate maternal ECG
    t, maternal_ecg = generate_maternal_ecg(duration, sampling_rate)
    
    # Generate fetal ECG
    _, fetal_ecg = generate_fetal_ecg(duration, sampling_rate)
    
    # Combine signals
    combined_ecg = maternal_ecg + fetal_ecg
    
    # Add measurement noise
    noisy_ecg = add_noise(combined_ecg, snr_db)
    
    # Simulate AD8232 output
    ad8232_output, lead_off_status = simulate_ad8232_output(
        noisy_ecg, sampling_rate, 
        lead_off_detection=lead_off_detection,
        lead_off_duration=lead_off_duration,
        lead_off_start=lead_off_start
    )
    
    return t, ad8232_output, lead_off_status

def save_ecg_to_csv(t, ecg, lead_off_status, filename="ecg_data.csv"):
    """
    Save ECG data to a CSV file.
    
    Parameters:
    -----------
    t : array-like
        Time points
    ecg : array-like
        ECG signal values
    lead_off_status : array-like
        Lead-off detection status
    filename : str
        Name of the CSV file to save
    """
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Time (s)', 'Raw ECG Value'])
        for i in range(len(t)):
            # Convert ECG value to raw ADC value (0-4095 for 12-bit ADC)
            # Assuming 3.3V reference voltage
            raw_value = int((ecg[i] / 3.3) * 4095)
            # Format time with 3 decimal places and no leading spaces
            writer.writerow([f"{t[i]:.3f}", raw_value])
    
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
    lead_off_status : array
        Lead-off detection status
    """
    t = []
    ecg = []
    lead_off_status = []
    
    with open(filename, 'r', newline='') as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # Skip header row
        for row in reader:
            t.append(float(row[0]))
            # Convert raw ADC value back to voltage
            # Assuming 3.3V reference voltage and 12-bit ADC
            raw_value = float(row[1])
            voltage = (raw_value / 4095) * 3.3
            ecg.append(voltage)
            if len(row) > 2:
                lead_off_status.append(float(row[2]))
            else:
                lead_off_status.append(1.0)  # Default to leads connected
    
    return np.array(t), np.array(ecg), np.array(lead_off_status)

if __name__ == "__main__":
    # Generate and plot the signal
    t, ecg, lead_off_status = generate_combined_ecg(
        duration=5, sampling_rate=1000, snr_db=20,
        lead_off_detection=True, lead_off_duration=0.5, lead_off_start=2.0
    )
    
    # Save to CSV
    save_ecg_to_csv(t, ecg, lead_off_status, "ecg_data.csv")
    
    # Plot the signal
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    
    # Plot ECG signal
    ax1.plot(t, ecg)
    ax1.set_title('AD8232 ECG Output')
    ax1.set_ylabel('Voltage (V)')
    ax1.grid(True)
    
    # Highlight lead-off detection periods
    lead_off_periods = np.where(lead_off_status == 0)[0]
    if len(lead_off_periods) > 0:
        # Group consecutive indices
        lead_off_groups = []
        current_group = [lead_off_periods[0]]
        
        for i in range(1, len(lead_off_periods)):
            if lead_off_periods[i] == lead_off_periods[i-1] + 1:
                current_group.append(lead_off_periods[i])
            else:
                lead_off_groups.append(current_group)
                current_group = [lead_off_periods[i]]
        
        lead_off_groups.append(current_group)
        
        # Highlight each group
        for group in lead_off_groups:
            if len(group) > 0:
                start_idx = group[0]
                end_idx = group[-1] + 1
                ax1.axvspan(t[start_idx], t[end_idx-1], color='red', alpha=0.3)
    
    # Plot lead-off status
    ax2.plot(t, lead_off_status, 'g-', linewidth=2)
    ax2.set_title('Lead-Off Detection Status')
    ax2.set_xlabel('Time (s)')
    ax2.set_ylabel('Status (1=Connected, 0=Disconnected)')
    ax2.set_ylim(-0.1, 1.1)
    ax2.set_yticks([0, 1])
    ax2.set_yticklabels(['Disconnected', 'Connected'])
    ax2.grid(True)
    
    plt.tight_layout()
    plt.show() 