import numpy as np
from scipy import signal
import matplotlib.pyplot as plt
import csv
import argparse
import os

def detect_r_peaks(ecg_signal, sampling_rate, min_distance=0.4, threshold_factor=1.5, prominence_factor=1.0):
    """
    Detect R peaks in the ECG signal from AD8232 sensor.
    
    Parameters:
    -----------
    ecg_signal : array-like
        The ECG signal to analyze
    sampling_rate : int
        Sampling rate of the signal in Hz
    min_distance : float
        Minimum distance between peaks in seconds (default: 0.4s for ~150 BPM max)
    threshold_factor : float
        Factor multiplied by standard deviation above mean for peak detection (default: 1.5)
    prominence_factor : float
        Factor multiplied by standard deviation for peak prominence (default: 1.0)
        
    Returns:
    --------
    peaks : array
        Indices of detected R peaks
    """
    # Create a mask for valid data (not lead-off)
    valid_mask = ecg_signal > 0  # Values of 0 indicate lead-off in AD8232
    
    # Work with valid data only
    working_signal = np.copy(ecg_signal)
    working_signal[~valid_mask] = np.nan
    
    # Simple moving average to remove high-frequency noise
    window_size = int(0.02 * sampling_rate)  # 20ms window
    if window_size % 2 == 0:
        window_size += 1
    
    # Pad the signal to handle edges
    pad_width = window_size // 2
    padded_signal = np.pad(working_signal, (pad_width, pad_width), mode='edge')
    
    # Apply moving average
    smoothed = np.zeros_like(working_signal)
    for i in range(len(working_signal)):
        window = padded_signal[i:i + window_size]
        smoothed[i] = np.nanmean(window)
    
    # Find peaks in the smoothed signal
    min_samples = int(min_distance * sampling_rate)
    
    # Use absolute threshold based on signal statistics
    valid_data = smoothed[~np.isnan(smoothed)]
    if len(valid_data) > 0:
        # Calculate adaptive threshold
        signal_mean = np.mean(valid_data)
        signal_std = np.std(valid_data)
        peak_threshold = signal_mean + threshold_factor * signal_std
        
        # Find peaks above threshold
        peaks, properties = signal.find_peaks(
            smoothed,
            distance=min_samples,
            height=peak_threshold,
            prominence=signal_std * prominence_factor,  # Minimum prominence
            width=(0.02 * sampling_rate, 0.12 * sampling_rate)  # 20-120ms width
        )
        
        # If no peaks found, try with lower threshold
        if len(peaks) == 0:
            peak_threshold = signal_mean + (threshold_factor * 0.7) * signal_std
            peaks, properties = signal.find_peaks(
                smoothed,
                distance=min_samples,
                height=peak_threshold,
                prominence=signal_std * prominence_factor * 0.5,
                width=(0.02 * sampling_rate, 0.12 * sampling_rate)
            )
        
        # Refine peak locations
        if len(peaks) > 0:
            refined_peaks = []
            for peak in peaks:
                # Look for maximum in original signal within ±50ms window
                window_size = int(0.05 * sampling_rate)
                start = max(0, peak - window_size)
                end = min(len(working_signal), peak + window_size + 1)
                # Get window of original signal
                window = working_signal[start:end]
                if not np.all(np.isnan(window)):  # Check if window has valid data
                    local_max_idx = start + np.nanargmax(window)
                    refined_peaks.append(local_max_idx)
            
            peaks = np.array(refined_peaks)
            
            # Additional filtering: remove peaks that are too low compared to neighbors
            if len(peaks) > 2:
                peak_values = working_signal[peaks]
                peak_mean = np.nanmean(peak_values)
                peak_std = np.nanstd(peak_values)
                valid_peaks = peaks[peak_values > (peak_mean - peak_std)]
                peaks = valid_peaks
    else:
        peaks = np.array([])
    
    return peaks

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
        return np.array([]), np.array([])
    
    # Calculate RR intervals
    rr_intervals = np.diff(peaks) / sampling_rate
    
    # Filter out physiologically impossible intervals
    # Allow range from 40 BPM (1.5s) to 180 BPM (0.33s)
    valid_intervals = (rr_intervals >= 0.33) & (rr_intervals <= 1.5)
    
    # Additional check for sudden large changes in intervals
    if len(rr_intervals) > 2:
        # Calculate percentage change between adjacent intervals
        interval_changes = np.abs(np.diff(rr_intervals)) / rr_intervals[:-1]
        # Mark intervals with sudden changes (>50%) as invalid
        valid_intervals[1:] = valid_intervals[1:] & (interval_changes <= 0.5)
    
    rr_intervals = rr_intervals[valid_intervals]
    valid_peaks = peaks[1:][valid_intervals]
    
    if len(rr_intervals) < 2:
        return np.array([]), np.array([])
    
    # Calculate instantaneous heart rates
    heart_rates = 60 / rr_intervals
    times = valid_peaks / sampling_rate
    
    # Apply moving average with smaller window for better responsiveness
    if len(heart_rates) > 3:
        heart_rates = np.convolve(heart_rates, np.ones(3)/3, mode='valid')
        times = times[1:-1]
    
    return heart_rates, times

def calculate_average_heart_rate(heart_rates):
    """Calculate the average heart rate from an array of heart rates."""
    if len(heart_rates) == 0:
        return 0.0
    
    # Filter out unrealistic values (e.g., below 40 or above 200 BPM)
    valid_rates = heart_rates[(heart_rates >= 40) & (heart_rates <= 200)]
    if len(valid_rates) == 0:
        return 0.0
    return np.mean(valid_rates)

def analyze_ecg(ecg_signal, sampling_rate, window_size=10, threshold_factor=1.5, prominence_factor=1.0):
    """
    Analyze ECG signal to detect R peaks and calculate heart rate.
    
    Parameters:
    -----------
    ecg_signal : array-like
        The ECG signal to analyze from AD8232 sensor
    sampling_rate : int
        Sampling rate of the signal in Hz
    window_size : int
        Size of the window for calculating moving average in seconds
    threshold_factor : float
        Factor for peak detection threshold
    prominence_factor : float
        Factor for peak prominence threshold
        
    Returns:
    --------
    peaks : array
        Indices of detected R peaks
    heart_rates : array
        Array of heart rates in BPM
    times : array
        Times corresponding to heart rate measurements
    avg_hr : float
        Average heart rate in BPM
    lead_off_mask : array
        Boolean mask indicating lead-off periods
    """
    # Create lead-off mask (AD8232 outputs 0 when leads are off)
    lead_off_mask = ecg_signal == 0
    
    # Detect peaks
    peaks = detect_r_peaks(ecg_signal, sampling_rate, 
                          threshold_factor=threshold_factor,
                          prominence_factor=prominence_factor)
    
    # Calculate heart rates
    heart_rates, times = calculate_heart_rate(peaks, sampling_rate, window_size)
    
    # Calculate average heart rate
    avg_hr = calculate_average_heart_rate(heart_rates)
    
    return peaks, heart_rates, times, avg_hr, lead_off_mask

def plot_analysis(t, ecg_signal, peaks, heart_rates, times, avg_hr, lead_off_mask, 
                 time_range=None):
    """
    Plot the ECG signal with detected R peaks and heart rate.
    
    Parameters:
    -----------
    t : array
        Time points
    ecg_signal : array
        ECG signal values
    peaks : array
        Indices of detected R peaks
    heart_rates : array
        Array of heart rates in BPM
    times : array
        Times corresponding to heart rate measurements
    avg_hr : float
        Average heart rate in BPM
    lead_off_mask : array
        Boolean mask indicating lead-off periods
    time_range : tuple
        Optional (start_time, end_time) in seconds for zoomed view
    """
    # Create figure with specific size and spacing
    fig = plt.figure(figsize=(12, 8))
    gs = plt.GridSpec(2, 1, height_ratios=[1.5, 1], hspace=0.3)
    
    # If time range is specified, create mask for the range
    if time_range is not None:
        start_time, end_time = time_range
        time_mask = (t >= start_time) & (t <= end_time)
        plot_t = t[time_mask]
        plot_signal = ecg_signal[time_mask]
        plot_mask = lead_off_mask[time_mask]
        
        # Filter peaks within range
        peak_mask = (t[peaks] >= start_time) & (t[peaks] <= end_time)
        plot_peaks = peaks[peak_mask]
        
        # Adjust peak indices to match zoomed array
        if len(plot_peaks) > 0:
            plot_peaks = np.searchsorted(plot_t, t[plot_peaks])
    else:
        plot_t = t
        plot_signal = ecg_signal
        plot_mask = lead_off_mask
        plot_peaks = peaks
    
    # ECG plot
    ax1 = fig.add_subplot(gs[0])
    ax1.plot(plot_t, plot_signal, label='ECG', color='blue', linewidth=1)
    
    # Highlight lead-off periods
    lead_off_periods = np.where(plot_mask)[0]
    lead_off_plotted = False
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
                # Only add label for the first lead-off region
                if not lead_off_plotted:
                    ax1.axvspan(plot_t[start_idx], plot_t[end_idx-1], color='red', alpha=0.3, label='Lead Off')
                    lead_off_plotted = True
                else:
                    ax1.axvspan(plot_t[start_idx], plot_t[end_idx-1], color='red', alpha=0.3)
    
    # Plot peaks
    if len(plot_peaks) > 0:
        ax1.plot(plot_t[plot_peaks], plot_signal[plot_peaks], 
                'ro', label='R Peaks', markersize=8)
    
    ax1.set_title('ECG Signal with Detected R Peaks')
    ax1.set_ylabel('Raw ADC Value')
    ax1.grid(True, alpha=0.3)
    
    # Create legend without duplicates
    handles, labels = ax1.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax1.legend(by_label.values(), by_label.keys(), loc='upper right')
    
    # Heart rate plot
    ax2 = fig.add_subplot(gs[1])
    if len(heart_rates) > 0 and len(times) > 0:
        # Filter heart rates within time range if specified
        if time_range is not None:
            start_time, end_time = time_range
            hr_mask = (times >= start_time) & (times <= end_time)
            plot_times = times[hr_mask]
            plot_rates = heart_rates[hr_mask]
        else:
            plot_times = times
            plot_rates = heart_rates
            
        if len(plot_times) > 0:
            ax2.plot(plot_times, plot_rates, 'r-', 
                    label=f'Heart Rate (Avg: {avg_hr:.1f} BPM)')
            
            # Add heart rate range guidelines
            normal_range = ax2.axhspan(60, 100, color='g', alpha=0.1, label='Normal Range')
            ax2.axhline(y=60, color='g', linestyle='--', alpha=0.3)
            ax2.axhline(y=100, color='g', linestyle='--', alpha=0.3)
            
            # Set y-axis limits with padding
            hr_min = max(40, min(plot_rates) - 10)
            hr_max = min(200, max(plot_rates) + 10)
            ax2.set_ylim(hr_min, hr_max)
            
            # Set x-axis limits to match ECG plot
            if time_range is not None:
                ax2.set_xlim(time_range)
    else:
        ax2.text(0.5, 0.5, 'No heart rate data available', 
                horizontalalignment='center', verticalalignment='center',
                transform=ax2.transAxes)
    
    ax2.set_title('Heart Rate')
    ax2.set_ylabel('Heart Rate (BPM)')
    ax2.set_xlabel('Time (s)')
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='upper right')
    
    # Adjust layout
    plt.subplots_adjust(left=0.1, right=0.95, top=0.95, bottom=0.1)
    plt.show()

def load_ecg_from_csv(filename, duration=10.0):
    """
    Load ECG data from a CSV file.
    
    Parameters:
    -----------
    filename : str
        Name of the CSV file to load
    duration : float
        Duration of data to load in seconds (default: 10.0)
        
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
            time = float(row[0])
            if time > duration:  # Stop reading after duration
                break
            t.append(time)
            ecg.append(float(row[1]))  # Raw ADC value
    
    t = np.array(t)
    ecg = np.array(ecg)
    
    # Estimate sampling rate
    if len(t) > 1:
        dt = np.mean(np.diff(t))
        sampling_rate = int(1 / dt)
    else:
        sampling_rate = 400  # Default value matching Arduino code
    
    print(f"Loaded {len(t)} samples over {t[-1]:.1f} seconds")
    print(f"Estimated sampling rate: {sampling_rate} Hz")
    
    return t, ecg, sampling_rate

def save_results_to_csv(t, ecg_signal, peaks, heart_rates, times, avg_hr, 
                       sampling_rate, output_filename="ecg_analysis_results.csv"):
    """Save analysis results to a CSV file."""
    with open(output_filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write summary information
        writer.writerow(['ECG Analysis Results'])
        writer.writerow(['Sampling Rate (Hz)', sampling_rate])
        writer.writerow(['Average Heart Rate (BPM)', f"{avg_hr:.1f}"])
        writer.writerow(['Number of R Peaks', len(peaks)])
        writer.writerow([])
        
        # Write R peaks
        writer.writerow(['R Peaks'])
        writer.writerow(['Index', 'Time (s)', 'Raw Value'])
        for i, peak in enumerate(peaks):
            writer.writerow([i+1, f"{t[peak]:.3f}", int(ecg_signal[peak])])
        writer.writerow([])
        
        # Write heart rates
        writer.writerow(['Heart Rates'])
        writer.writerow(['Time (s)', 'Heart Rate (BPM)'])
        for i in range(len(times)):
            writer.writerow([f"{times[i]:.3f}", f"{heart_rates[i]:.1f}"])
    
    print(f"Analysis results saved to {output_filename}")

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Analyze ECG signal from CSV file')
    parser.add_argument('--input', '-i', type=str, required=True,
                        help='Input CSV file containing ECG data')
    parser.add_argument('--output', '-o', type=str, default='ecg_analysis_results.csv',
                        help='Output CSV file for analysis results (default: ecg_analysis_results.csv)')
    parser.add_argument('--sampling-rate', '-sr', type=int, default=None,
                        help='Sampling rate in Hz (if not specified, will be estimated from the data)')
    parser.add_argument('--window-size', '-w', type=int, default=10,
                        help='Window size for heart rate calculation in seconds (default: 10)')
    parser.add_argument('--duration', '-d', type=float, default=10.0,
                        help='Duration of data to analyze in seconds (default: 10.0)')
    parser.add_argument('--threshold', '-t', type=float, default=1.5,
                        help='Threshold factor for R peak detection (default: 1.5)')
    parser.add_argument('--prominence', '-p', type=float, default=1.0,
                        help='Prominence factor for R peak detection (default: 1.0)')
    parser.add_argument('--zoom-start', type=float, default=None,
                        help='Start time for zoomed view in seconds')
    parser.add_argument('--zoom-end', type=float, default=None,
                        help='End time for zoomed view in seconds')
    
    args = parser.parse_args()
    
    # Load ECG data
    t, ecg, estimated_sampling_rate = load_ecg_from_csv(args.input, args.duration)
    
    # Use provided sampling rate or estimated one
    sampling_rate = args.sampling_rate if args.sampling_rate is not None else estimated_sampling_rate
    
    print(f"Analyzing ECG data from {args.input}")
    print(f"Sampling rate: {sampling_rate} Hz")
    print(f"Threshold factor: {args.threshold}")
    print(f"Prominence factor: {args.prominence}")
    
    # Analyze the ECG
    peaks, heart_rates, times, avg_hr, lead_off_mask = analyze_ecg(
        ecg, sampling_rate, args.window_size,
        threshold_factor=args.threshold,
        prominence_factor=args.prominence
    )
    
    # Save results to CSV
    save_results_to_csv(t, ecg, peaks, heart_rates, times, avg_hr, 
                       sampling_rate, args.output)
    
    # Create time range for zoomed view if specified
    time_range = None
    if args.zoom_start is not None and args.zoom_end is not None:
        time_range = (args.zoom_start, args.zoom_end)
        print(f"Zooming to time range: {args.zoom_start:.1f}s - {args.zoom_end:.1f}s")
    
    # Plot results
    plot_analysis(t, ecg, peaks, heart_rates, times, avg_hr, lead_off_mask,
                 time_range=time_range) 