#!/usr/bin/env python3
"""
使用纯 GNU Radio 模块生成 4-RRC-FSK 信号并绘制频谱
这作为正确实现的参考
"""
import numpy as np
import matplotlib.pyplot as plt

try:
    from gnuradio import gr
    from gnuradio import blocks
    from gnuradio import filter as gr_filter
    from gnuradio import digital
    from gnuradio import analog
    from gnuradio.filter import firdes
    
    GNURADIO_AVAILABLE = True
except ImportError:
    GNURADIO_AVAILABLE = False
    print("GNU Radio not available, using numpy-only implementation")

def generate_4rrc_fsk_gnuradio(num_symbols=10000, sample_rate=2e6, symbol_rate=250e3, alpha=0.25, sensitivity=0.54):
    """
    使用 GNU Radio 模块生成 4-RRC-FSK 信号
    完全匹配 untitled.py 的实现
    """
    if not GNURADIO_AVAILABLE:
        return None
    
    sps = int(sample_rate / symbol_rate)
    
    # Create a top block
    class SignalGenerator(gr.top_block):
        def __init__(self, num_symbols):
            gr.top_block.__init__(self, "Signal Generator")
            
            # Random source (0-3)
            random_data = np.random.randint(0, 4, num_symbols).astype(np.uint8)
            self.source = blocks.vector_source_b(random_data.tolist(), False)
            
            # Chunks to symbols: 0->-3, 1->-1, 2->1, 3->3
            self.chunks_to_symbols = digital.chunks_to_symbols_bf([-3, -1, 1, 3], 1)
            
            # RRC interpolating filter
            ntaps = 88
            rrc_taps = firdes.root_raised_cosine(1.0, sample_rate, symbol_rate, alpha, ntaps)
            self.rrc_filter = gr_filter.interp_fir_filter_fff(sps, rrc_taps)
            
            # FM modulator
            self.fm_mod = analog.frequency_modulator_fc(sensitivity)
            
            # Sink
            self.sink = blocks.vector_sink_c()
            
            # Connect
            self.connect(self.source, self.chunks_to_symbols, self.rrc_filter, self.fm_mod, self.sink)
    
    # Run
    tb = SignalGenerator(num_symbols)
    tb.run()
    samples = np.array(tb.sink.data())
    
    return samples

def generate_4rrc_fsk_numpy(num_symbols=10000, sample_rate=2e6, symbol_rate=250e3, alpha=0.25, sensitivity=0.54):
    """
    使用 numpy 生成 4-RRC-FSK 信号
    尝试匹配 GNU Radio 行为
    """
    sps = int(sample_rate / symbol_rate)
    
    # Random symbols (0-3 -> -3,-1,1,3)
    symbol_map = {0: -3.0, 1: -1.0, 2: 1.0, 3: 3.0}
    random_indices = np.random.randint(0, 4, num_symbols)
    symbols = np.array([symbol_map[i] for i in random_indices])
    
    # Upsample
    upsampled = np.zeros(len(symbols) * sps)
    upsampled[::sps] = symbols
    
    # RRC filter
    if GNURADIO_AVAILABLE:
        from gnuradio.filter import firdes
        ntaps = 88
        rrc_taps = np.array(firdes.root_raised_cosine(1.0, sample_rate, symbol_rate, alpha, ntaps))
    else:
        # Fallback
        t = np.arange(-5.5*sps, 5.5*sps + 1) / sps
        rrc_taps = np.sinc(t) * np.cos(np.pi * alpha * t) / (1 - (2*alpha*t)**2 + 1e-10)
        rrc_taps = rrc_taps / np.sum(rrc_taps)
    
    # Apply filter
    filtered = np.convolve(upsampled, rrc_taps, mode='full')
    
    # FM modulation: phase = cumsum(sensitivity * input)
    phase = np.cumsum(sensitivity * filtered)
    iq = np.exp(1j * phase)
    
    return iq.astype(np.complex64)

def plot_spectrum_comparison():
    """比较 GNU Radio 和 numpy 实现的频谱"""
    num_symbols = 10000
    
    print("Generating signals...")
    
    samples_numpy = generate_4rrc_fsk_numpy(num_symbols)
    print(f"Numpy: {len(samples_numpy)} samples")
    
    if GNURADIO_AVAILABLE:
        samples_gnuradio = generate_4rrc_fsk_gnuradio(num_symbols)
        print(f"GNU Radio: {len(samples_gnuradio)} samples")
    
    # Compute spectra
    from scipy import signal as sp
    
    fig, axes = plt.subplots(2 if GNURADIO_AVAILABLE else 1, 1, figsize=(12, 8 if GNURADIO_AVAILABLE else 4))
    if not GNURADIO_AVAILABLE:
        axes = [axes]
    
    for idx, (name, samples) in enumerate([("Numpy Implementation", samples_numpy)] + 
                                           ([("GNU Radio Reference", samples_gnuradio)] if GNURADIO_AVAILABLE else [])):
        freqs, psd = sp.welch(samples, fs=2e6, nperseg=2048, noverlap=1024, 
                              return_onesided=False, scaling='density')
        freqs = np.fft.fftshift(freqs) / 1e6
        psd = np.fft.fftshift(psd)
        psd_db = 10 * np.log10(psd + 1e-12)
        
        axes[idx].plot(freqs, psd_db)
        axes[idx].set_title(f"{name}")
        axes[idx].set_xlabel("Frequency Offset (MHz)")
        axes[idx].set_ylabel("PSD (dB)")
        axes[idx].set_xlim(-1, 1)
        axes[idx].set_ylim(-80, 20)
        axes[idx].grid(True)
        
        # Add annotations for key features
        peak_idx = np.argmax(psd_db)
        peak_freq = freqs[peak_idx]
        peak_power = psd_db[peak_idx]
        axes[idx].annotate(f'Peak: {peak_power:.1f} dB', xy=(peak_freq, peak_power), 
                          xytext=(peak_freq + 0.2, peak_power - 10),
                          arrowprops=dict(arrowstyle='->', color='red'))
    
    plt.tight_layout()
    plt.savefig('/home/shark/桌面/SharkRadio/gnuradio_comparison.png', dpi=150)
    plt.close()
    print("\nSaved comparison to gnuradio_comparison.png")

if __name__ == "__main__":
    plot_spectrum_comparison()
