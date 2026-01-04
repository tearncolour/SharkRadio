
import numpy as np
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from sdr.signal_generator import generate_signal, get_signal_params

def test_signal_gen():
    sig_type = 'red_jam_2'
    print(f"Testing Signal: {sig_type}")
    
    # Generate
    samples = generate_signal(sig_type, payload=None, sample_rate=2000000)
    
    print(f"Generated {len(samples)} samples")
    print(f"Max Amplitude: {np.max(np.abs(samples))}")
    print(f"Mean Amplitude: {np.mean(np.abs(samples))}")
    
    # Demodulate FM to check deviation
    # Instantaneous Freq = fs * diff(unwrap(angle)) / 2pi
    phase = np.unwrap(np.angle(samples))
    diff_phase = np.diff(phase)
    
    # Fix wrap around if unwrap didn't catch (unlikely for continuous) or loose ends
    # Convert to Hz
    inst_freq = diff_phase * 2000000.0 / (2 * np.pi)
    
    print(f"Max Freq Dev: {np.max(np.abs(inst_freq))/1000:.2f} kHz")
    print(f"Mean Freq Dev: {np.mean(np.abs(inst_freq)):.2f} Hz")
    
    # Check Histogram of Freq Dev (should show 4 peaks)
    hist, bins = np.histogram(inst_freq, bins=50)
    print("Freq Dev Histogram (Top 5 bins):")
    # Simplify output
    for i in range(len(hist)):
        if hist[i] > len(inst_freq)*0.01:
            print(f"  {bins[i]/1000:.1f} kHz: {hist[i]}")

if __name__ == "__main__":
    test_signal_gen()
