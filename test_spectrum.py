
import numpy as np
import matplotlib.pyplot as plt
import sys
import os

sys.path.append(os.path.join(os.getcwd(), 'backend'))

from sdr.signal_generator import generate_signal, get_signal_params

def test_spectrum():
    print("=== Testing signal spectrum ===\n")
    
    # Test 1: Short payload (like broadcast)
    print("Test 1: Short payload (12 bytes)")
    samples_short = generate_signal('red_broadcast', payload="C80090019600960000005802", sample_rate=2000000)
    print(f"  Samples: {len(samples_short)}")
    
    # Test 2: Random interference (no payload)
    print("\nTest 2: Random interference (no payload)")
    samples_random = generate_signal('red_jam_2', payload=None, sample_rate=2000000)
    print(f"  Samples: {len(samples_random)}")
    
    # Compute and compare spectra
    from scipy import signal as sp
    
    fig, axes = plt.subplots(2, 1, figsize=(12, 8))
    
    for idx, (name, samples) in enumerate([("Short Payload (Broadcast)", samples_short), 
                                            ("Random (Interference)", samples_random)]):
        # Use Welch method
        freqs, psd = sp.welch(samples, fs=2e6, nperseg=1024, noverlap=512, 
                              return_onesided=False, scaling='density')
        freqs = np.fft.fftshift(freqs) / 1e6  # MHz
        psd = np.fft.fftshift(psd)
        psd_db = 10 * np.log10(psd + 1e-12)
        
        axes[idx].plot(freqs, psd_db)
        axes[idx].set_title(f"{name} - {len(samples)} samples")
        axes[idx].set_xlabel("Frequency Offset (MHz)")
        axes[idx].set_ylabel("PSD (dB)")
        axes[idx].set_xlim(-1, 1)
        axes[idx].grid(True)
    
    plt.tight_layout()
    plt.savefig('/home/shark/桌面/SharkRadio/spectrum_comparison.png', dpi=150)
    plt.close()
    print("\nSaved spectrum comparison to spectrum_comparison.png")

if __name__ == "__main__":
    test_spectrum()
