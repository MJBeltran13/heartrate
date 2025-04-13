import numpy as np
from scipy import signal
import matplotlib.pyplot as plt
import csv
import argparse
import os

def detect_r_peaks(ecg_signal, sampling_rate, min_distance=0.2, prominence=0.5, is_fetal=False):
    """
    Detect R peaks in the ECG signal.
    
    Parameters:
    -----------
    ecg_signal : array-like
        The ECG signal to analyze
    sampling_rate : int
        Sampling rate of the signal in Hz
    min_distance : float
        Minimum distance between peaks in seconds
    prominence : float
        Minimum prominence of peaks
    is_fetal : bool
        Whether to detect fetal ECG peaks (uses different parameters)
        
    Returns:
    --------
    peaks : array
        Indices of detected R peaks
    """
    # Apply bandpass filter to remove noise
    nyquist = sampling_rate / 2
    
    if is_fetal:
        # Fetal ECG has higher frequency components
        low = 10 / nyquist
        high = 40 / nyquist
    else:
        # Maternal ECG has lower frequency components
        low = 5 / nyquist
        high = 15 / nyquist
        
    b, a = signal.butter(4, [low, high], btype='band')
    filtered_signal = signal.filtfilt(b, a, ecg_signal)
    
    # Find peaks using scipy's find_peaks
    min_samples = int(min_distance * sampling_rate)
    peaks, _ = signal.find_peaks(filtered_signal, 
                               distance=min_samples,
                               prominence=prominence)
    
    # If no peaks found, try with lower prominence
    if len(peaks) == 0:
        peaks, _ = signal.find_peaks(filtered_signal, 
                                   distance=min_samples,
                                   prominence=prominence/2)
    
    # If still no peaks, try with even lower prominence
    if len(peaks) == 0:
        peaks, _ = signal.find_peaks(filtered_signal, 
                                   distance=min_samples,
                                   prominence=prominence/4)
    
    return peaks

def separate_maternal_fetal_peaks(ecg_signal, sampling_rate):
    """
    Separate maternal and fetal R peaks from a combined ECG signal.
    
    Parameters:
    -----------
    ecg_signal : array-like
        The combined ECG signal to analyze
    sampling_rate : int
        Sampling rate of the signal in Hz
        
    Returns:
    --------
    maternal_peaks : array
        Indices of detected maternal R peaks
    fetal_peaks : array
        Indices of detected fetal R peaks
    """
    # Detect maternal peaks (slower heart rate, larger amplitude)
    maternal_peaks = detect_r_peaks(ecg_signal, sampling_rate, 
                                   min_distance=0.6,  # ~100 BPM max
                                   prominence=0.5,
                                   is_fetal=False)
    
    # Detect fetal peaks (faster heart rate, smaller amplitude)
    fetal_peaks = detect_r_peaks(ecg_signal, sampling_rate, 
                                min_distance=0.3,  # ~200 BPM max
                                prominence=0.2,
                                is_fetal=True)
    
    # Remove peaks that are too close to each other (likely duplicates)
    if len(maternal_peaks) > 0 and len(fetal_peaks) > 0:
        # Create a mask for fetal peaks that are not too close to maternal peaks
        min_distance_samples = int(0.1 * sampling_rate)  # 100ms minimum distance
        valid_fetal_peaks = []
        
        for f_peak in fetal_peaks:
            # Check if this fetal peak is far enough from all maternal peaks
            is_valid = True
            for m_peak in maternal_peaks:
                if abs(f_peak - m_peak) < min_distance_samples:
                    is_valid = False
                    break
            
            if is_valid:
                valid_fetal_peaks.append(f_peak)
        
        fetal_peaks = np.array(valid_fetal_peaks)
    
    return maternal_peaks, fetal_peaks

def calculate_heart_rate(peaks, sampling_rate, window_size=10):
    """
    Calculate heart rate from R peaks.
    
    Parameters:
    -----------
    peaks : array
        Indices of R peaks
    sampling_rate : int
        Sampling rate of the signal in Hz
    window_size : int
        Size of the window for calculating moving average in seconds
        
    Returns:
    --------
    heart_rates : array
        Array of heart rates in BPM
    times : array
        Times corresponding to heart rate measurements
    """
    if len(peaks) < 2:
        # Return empty arrays with the same shape
        return np.array([]), np.array([])
    
    # Calculate RR intervals
    rr_intervals = np.diff(peaks) / sampling_rate
    
    # Calculate instantaneous heart rates
    heart_rates = 60 / rr_intervals
    
    # Calculate times for each heart rate measurement
    times = peaks[1:] / sampling_rate
    
    # Apply moving average
    window_samples = int(window_size * sampling_rate)
    if len(heart_rates) > window_samples:
        heart_rates = np.convolve(heart_rates, 
                                 np.ones(window_samples)/window_samples, 
                                 mode='valid')
        times = times[window_samples-1:]
    
    return heart_rates, times

def calculate_average_heart_rate(heart_rates):
    """
    Calculate the average heart rate from an array of heart rates.
    
    Parameters:
    -----------
    heart_rates : array
        Array of heart rates in BPM
        
    Returns:
    --------
    average_hr : float
        Average heart rate in BPM
    """
    if len(heart_rates) == 0:
        return 0.0
    
    return np.mean(heart_rates)

def analyze_ecg(ecg_signal, sampling_rate, window_size=10):
    """
    Analyze ECG signal to detect maternal and fetal R peaks and calculate heart rates.
    
    Parameters:
    -----------
    ecg_signal : array-like
        The ECG signal to analyze
    sampling_rate : int
        Sampling rate of the signal in Hz
    window_size : int
        Size of the window for calculating moving average in seconds
        
    Returns:
    --------
    maternal_peaks : array
        Indices of detected maternal R peaks
    fetal_peaks : array
        Indices of detected fetal R peaks
    maternal_heart_rates : array
        Array of maternal heart rates in BPM
    fetal_heart_rates : array
        Array of fetal heart rates in BPM
    maternal_times : array
        Times corresponding to maternal heart rate measurements
    fetal_times : array
        Times corresponding to fetal heart rate measurements
    maternal_avg_hr : float
        Average maternal heart rate in BPM
    fetal_avg_hr : float
        Average fetal heart rate in BPM
    """
    # Separate maternal and fetal peaks
    maternal_peaks, fetal_peaks = separate_maternal_fetal_peaks(ecg_signal, sampling_rate)
    
    # Calculate heart rates
    maternal_heart_rates, maternal_times = calculate_heart_rate(maternal_peaks, sampling_rate, window_size)
    fetal_heart_rates, fetal_times = calculate_heart_rate(fetal_peaks, sampling_rate, window_size)
    
    # Calculate average heart rates
    maternal_avg_hr = calculate_average_heart_rate(maternal_heart_rates)
    fetal_avg_hr = calculate_average_heart_rate(fetal_heart_rates)
    
    return maternal_peaks, fetal_peaks, maternal_heart_rates, fetal_heart_rates, maternal_times, fetal_times, maternal_avg_hr, fetal_avg_hr

def plot_analysis(ecg_signal, maternal_peaks, fetal_peaks, 
                 maternal_heart_rates, fetal_heart_rates, 
                 maternal_times, fetal_times, sampling_rate,
                 maternal_avg_hr, fetal_avg_hr):
    """
    Plot the ECG signal with detected maternal and fetal R peaks and heart rates.
    """
    t = np.arange(len(ecg_signal)) / sampling_rate
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
    
    # Plot ECG with R peaks
    ax1.plot(t, ecg_signal, label='ECG', color='blue')
    
    # Plot maternal peaks
    if len(maternal_peaks) > 0:
        ax1.plot(maternal_peaks/sampling_rate, ecg_signal[maternal_peaks], 
                'ro', label='Maternal R peaks', markersize=8)
    
    # Plot fetal peaks
    if len(fetal_peaks) > 0:
        ax1.plot(fetal_peaks/sampling_rate, ecg_signal[fetal_peaks], 
                'go', label='Fetal R peaks', markersize=6)
    
    ax1.set_title('ECG Signal with Detected Maternal and Fetal R Peaks')
    ax1.set_xlabel('Time (s)')
    ax1.set_ylabel('Amplitude')
    ax1.grid(True)
    ax1.legend()
    
    # Plot heart rates
    if len(maternal_heart_rates) > 0 and len(maternal_times) > 0:
        ax2.plot(maternal_times, maternal_heart_rates, 'r-', 
                label=f'Maternal Heart Rate (Avg: {maternal_avg_hr:.1f} BPM)')
    
    if len(fetal_heart_rates) > 0 and len(fetal_times) > 0:
        ax2.plot(fetal_times, fetal_heart_rates, 'g-', 
                label=f'Fetal Heart Rate (Avg: {fetal_avg_hr:.1f} BPM)')
    
    if (len(maternal_heart_rates) == 0 or len(maternal_times) == 0) and \
       (len(fetal_heart_rates) == 0 or len(fetal_times) == 0):
        ax2.text(0.5, 0.5, 'No heart rate data available', 
                horizontalalignment='center', verticalalignment='center',
                transform=ax2.transAxes)
    
    ax2.set_title('Heart Rate')
    ax2.set_xlabel('Time (s)')
    ax2.set_ylabel('Heart Rate (BPM)')
    ax2.grid(True)
    ax2.legend()
    
    # Add average heart rate text box
    avg_text = f"Maternal Avg: {maternal_avg_hr:.1f} BPM\nFetal Avg: {fetal_avg_hr:.1f} BPM"
    plt.figtext(0.02, 0.02, avg_text, fontsize=10, bbox=dict(facecolor='white', alpha=0.8))
    
    plt.tight_layout()
    plt.show()

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
    sampling_rate : int
        Estimated sampling rate in Hz
    """
    t = []
    ecg = []
    
    with open(filename, 'r', newline='') as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # Skip header row
        for row in reader:
            t.append(float(row[0]))
            ecg.append(float(row[1]))
    
    t = np.array(t)
    ecg = np.array(ecg)
    
    # Estimate sampling rate
    if len(t) > 1:
        dt = np.mean(np.diff(t))
        sampling_rate = int(1 / dt)
    else:
        sampling_rate = 1000  # Default value
    
    return t, ecg, sampling_rate

def save_results_to_csv(maternal_peaks, fetal_peaks, maternal_heart_rates, fetal_heart_rates, 
                       maternal_times, fetal_times, maternal_avg_hr, fetal_avg_hr, 
                       sampling_rate, output_filename="ecg_analysis_results.csv"):
    """
    Save analysis results to a CSV file.
    
    Parameters:
    -----------
    maternal_peaks : array
        Indices of detected maternal R peaks
    fetal_peaks : array
        Indices of detected fetal R peaks
    maternal_heart_rates : array
        Array of maternal heart rates in BPM
    fetal_heart_rates : array
        Array of fetal heart rates in BPM
    maternal_times : array
        Times corresponding to maternal heart rate measurements
    fetal_times : array
        Times corresponding to fetal heart rate measurements
    maternal_avg_hr : float
        Average maternal heart rate in BPM
    fetal_avg_hr : float
        Average fetal heart rate in BPM
    sampling_rate : int
        Sampling rate of the signal in Hz
    output_filename : str
        Name of the CSV file to save
    """
    with open(output_filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write summary information
        writer.writerow(['ECG Analysis Results'])
        writer.writerow(['Sampling Rate (Hz)', sampling_rate])
        writer.writerow(['Maternal Average Heart Rate (BPM)', maternal_avg_hr])
        writer.writerow(['Fetal Average Heart Rate (BPM)', fetal_avg_hr])
        writer.writerow(['Number of Maternal R Peaks', len(maternal_peaks)])
        writer.writerow(['Number of Fetal R Peaks', len(fetal_peaks)])
        writer.writerow([])
        
        # Write maternal peaks
        writer.writerow(['Maternal R Peaks'])
        writer.writerow(['Index', 'Time (s)', 'Amplitude'])
        for i, peak in enumerate(maternal_peaks):
            writer.writerow([i+1, peak/sampling_rate, 'N/A'])
        writer.writerow([])
        
        # Write fetal peaks
        writer.writerow(['Fetal R Peaks'])
        writer.writerow(['Index', 'Time (s)', 'Amplitude'])
        for i, peak in enumerate(fetal_peaks):
            writer.writerow([i+1, peak/sampling_rate, 'N/A'])
        writer.writerow([])
        
        # Write heart rates
        writer.writerow(['Heart Rates'])
        writer.writerow(['Time (s)', 'Maternal HR (BPM)', 'Fetal HR (BPM)'])
        
        # Find the common time range
        all_times = sorted(set(list(maternal_times) + list(fetal_times)))
        
        for time in all_times:
            maternal_hr = 'N/A'
            fetal_hr = 'N/A'
            
            # Find maternal heart rate at this time
            for i, t in enumerate(maternal_times):
                if abs(t - time) < 0.01:  # Within 10ms
                    maternal_hr = maternal_heart_rates[i]
                    break
            
            # Find fetal heart rate at this time
            for i, t in enumerate(fetal_times):
                if abs(t - time) < 0.01:  # Within 10ms
                    fetal_hr = fetal_heart_rates[i]
                    break
            
            writer.writerow([time, maternal_hr, fetal_hr])
    
    print(f"Analysis results saved to {output_filename}")

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Analyze ECG signal from CSV file')
    parser.add_argument('--input', '-i', type=str, default='ecg_data.csv',
                        help='Input CSV file containing ECG data (default: ecg_data.csv)')
    parser.add_argument('--output', '-o', type=str, default='ecg_analysis_results.csv',
                        help='Output CSV file for analysis results (default: ecg_analysis_results.csv)')
    parser.add_argument('--sampling-rate', '-sr', type=int, default=None,
                        help='Sampling rate in Hz (if not specified, will be estimated from the data)')
    parser.add_argument('--window-size', '-w', type=int, default=10,
                        help='Window size for heart rate calculation in seconds (default: 10)')
    parser.add_argument('--generate', '-g', action='store_true',
                        help='Generate a sample ECG signal if no input file is provided')
    
    args = parser.parse_args()
    
    # Check if input file exists
    if not os.path.exists(args.input) and not args.generate:
        print(f"Input file {args.input} not found. Generating a sample ECG signal...")
        from ecg_generator import generate_combined_ecg, save_ecg_to_csv
        t, ecg = generate_combined_ecg(duration=10, sampling_rate=1000)
        save_ecg_to_csv(t, ecg, args.input)
    
    # Load ECG data
    t, ecg, estimated_sampling_rate = load_ecg_from_csv(args.input)
    
    # Use provided sampling rate or estimated one
    sampling_rate = args.sampling_rate if args.sampling_rate is not None else estimated_sampling_rate
    
    print(f"Analyzing ECG data from {args.input}")
    print(f"Sampling rate: {sampling_rate} Hz")
    
    # Analyze the ECG
    maternal_peaks, fetal_peaks, maternal_heart_rates, fetal_heart_rates, maternal_times, fetal_times, maternal_avg_hr, fetal_avg_hr = analyze_ecg(ecg, sampling_rate, args.window_size)
    
    # Save results to CSV
    save_results_to_csv(maternal_peaks, fetal_peaks, maternal_heart_rates, fetal_heart_rates, 
                       maternal_times, fetal_times, maternal_avg_hr, fetal_avg_hr, 
                       sampling_rate, args.output)
    
    # Plot results
    plot_analysis(ecg, maternal_peaks, fetal_peaks, 
                 maternal_heart_rates, fetal_heart_rates, 
                 maternal_times, fetal_times, sampling_rate,
                 maternal_avg_hr=maternal_avg_hr, fetal_avg_hr=fetal_avg_hr) 