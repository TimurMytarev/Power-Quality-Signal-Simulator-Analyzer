"""
Power Quality Signal Simulator & Analyzer

Features:
- Synthetic three-phase voltage generation (Va, Vb, Vc)
- Power quality anomalies: Harmonics, Sags, Swells, Flicker, and Noise
- Nyquist criterion validation for sampling frequency
- Digital Signal Processing: Corrected FFT amplitude scaling and dynamic THD
- Rolling RMS calculation (20 ms window for 50 Hz power systems)
- Automatic directory management and data export (CSV, Excel, Plots)
"""

import os
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# =========================================================
# VALIDATION
# =========================================================

def validate_inputs(fs, duration, f0, harmonics, noise_std):
    """
    Validate generator parameters and check the Nyquist criterion.
    """
    if fs <= 0:
        raise ValueError("Sampling frequency fs must be > 0")
    if duration <= 0:
        raise ValueError("Duration must be > 0")
    if f0 <= 0:
        raise ValueError("Fundamental frequency f0 must be > 0")
    if noise_std < 0:
        raise ValueError("Noise standard deviation must be >= 0")

    if harmonics:
        max_harmonic = max(n for n, _ in harmonics)
        f_max = f0 * max_harmonic

        # Check Nyquist criterion
        if fs <= 2 * f_max:
            raise ValueError(
                f"Sampling frequency fs={fs} Hz violates Nyquist criterion "
                f"for max harmonic frequency {f_max} Hz (f0={f0} Hz, max_n={max_harmonic}). "
                f"fs must be strictly greater than {2 * f_max} Hz."
            )


# =========================================================
# EVENTS
# =========================================================

def apply_event(signal, fs, start, end, magnitude):
    """
    Apply event safely without modifying the original signal.
    Includes boundary checks to prevent IndexError.
    """
    modified = signal.copy()

    i0 = int(start * fs)
    i1 = int(end * fs)

    # Array bounds protection
    i0 = max(0, i0)
    i1 = min(len(signal), i1)

    modified[i0:i1] *= magnitude
    return modified


# =========================================================
# SIGNAL GENERATION
# =========================================================

def generate_three_phase(
        fs=5000,
        duration=6.0,
        f0=50.0,
        v_nom=230.0,
        harmonics=None,
        sag_events=None,
        swell_events=None,
        flicker_amp=0.04,
        flicker_freq=7.0,
        noise_std=1.2,
        unbalance=(1.0, 0.98, 1.02),
        seed=42
):
    """
    Generate synthetic three-phase voltage signals with power quality disturbances.

    Parameters
    ----------
    fs : int, optional (default: 5000)
        Sampling frequency [Hz]
    duration : float, optional (default: 6.0)
        Signal duration [s]
    f0 : float, optional (default: 50.0)
        Fundamental frequency [Hz]
    v_nom : float, optional (default: 230.0)
        Nominal RMS phase voltage [V]
    harmonics : list of tuples, optional
        Harmonic definition: [(harmonic_order, relative_amplitude)]
    sag_events : list of tuples, optional
        Voltage sag events: [(start, end, magnitude, affected_phases)]
    swell_events : list of tuples, optional
        Voltage swell events: [(start, end, magnitude, affected_phases)]
    flicker_amp : float, optional (default: 0.04)
        Flicker modulation amplitude (relative)
    flicker_freq : float, optional (default: 7.0)
        Flicker modulation frequency [Hz]
    noise_std : float, optional (default: 1.2)
        Standard deviation of Gaussian noise [V]
    unbalance : tuple of floats, optional (default: (1.0, 0.98, 1.02))
        Voltage unbalance factors for phases A, B, and C
    seed : int, optional (default: 42)
        Random seed for reproducibility

    Returns
    -------
    t : ndarray
        Time axis
    Va, Vb, Vc : ndarray
        Three-phase voltage signals
    metadata : dict
        Simulation parameters used for generation
    """
    if harmonics is None:
        harmonics = [(3, 0.08), (5, 0.04), (7, 0.02)]
    if sag_events is None:
        sag_events = [(0.8, 1.0, 0.45, ["A"])]
    if swell_events is None:
        swell_events = [(3.0, 3.12, 1.5, ["A"])]

    # Parameter validation and Nyquist criterion check
    validate_inputs(fs, duration, f0, harmonics, noise_std)

    rng = np.random.default_rng(seed)
    N = int(fs * duration)
    t = np.linspace(0, duration, N, endpoint=False)
    Vpeak = v_nom * np.sqrt(2)

    # Phase shift in radians (120°)
    phase_shifts = [0.0, -2 * np.pi / 3, 2 * np.pi / 3]
    phase_names = ["A", "B", "C"]
    signals = {}

    # Amplitude modulation (Flicker)
    flicker = 1.0 + flicker_amp * np.sin(2 * np.pi * flicker_freq * t)

    # Generate ideal signal + harmonics + flicker + unbalance + noise
    for idx, shift in enumerate(phase_shifts):
        # Fundamental harmonic
        signal = Vpeak * np.sin(2 * np.pi * f0 * t + shift)

        # Higher harmonics
        for n, rel_amp in harmonics:
            signal += Vpeak * rel_amp * np.sin(2 * np.pi * f0 * n * t + n * shift)

        signal *= flicker
        signal *= unbalance[idx]
        signal += rng.normal(0, noise_std, size=N)

        signals[phase_names[idx]] = signal

    # Apply voltage sags
    for start, end, mag, phases in sag_events:
        for phase in phases:
            signals[phase] = apply_event(signals[phase], fs, start, end, mag)

    # Apply voltage swells
    for start, end, mag, phases in swell_events:
        for phase in phases:
            signals[phase] = apply_event(signals[phase], fs, start, end, mag)

    metadata = {
        "fs": fs, "duration": duration, "f0": f0, "v_nom": v_nom,
        "harmonics": harmonics, "sag_events": sag_events, "swell_events": swell_events,
        "flicker_amp": flicker_amp, "flicker_freq": flicker_freq, "noise_std": noise_std,
        "unbalance": unbalance, "seed": seed
    }

    return t, signals["A"], signals["B"], signals["C"], metadata


# =========================================================
# DIGITAL SIGNAL PROCESSING & ANALYSIS
# =========================================================

def compute_fft(signal, fs):
    """
    Compute One-Sided FFT with proper amplitude scaling for real signals.
    """
    N = len(signal)
    fft_vals = np.fft.rfft(signal)
    fft_freq = np.fft.rfftfreq(N, d=1 / fs)

    magnitude = np.abs(fft_vals) / N
    magnitude[1:] *= 2  # Correct transfer of energy from negative frequencies

    return fft_freq, magnitude


def calculate_rolling_rms(signal, fs, window_ms=20.0):
    """
    Calculate Rolling RMS using a moving window (e.g., 20 ms for 50 Hz).
    This properly reflects power quality events like sags and swells.
    """
    window_size = int((window_ms / 1000.0) * fs)
    if window_size < 1:
        window_size = 1

    squared_signal = signal ** 2
    # Fast moving average using convolution
    window = np.ones(window_size) / window_size
    rolling_mean_square = np.convolve(squared_signal, window, mode='same')

    return np.sqrt(rolling_mean_square)


def calculate_thd(signal, fs, f0=50.0):
    """
    Calculate Total Harmonic Distortion (THD) using dynamic harmonic bin scanning.
    Ignores DC component and the fundamental frequency band.
    """
    freq, magnitude = compute_fft(signal, fs)

    # Skip DC (zero frequency)
    freq = freq[1:]
    magnitude = magnitude[1:]

    # Find index of fundamental frequency (f0)
    fundamental_idx = np.argmin(np.abs(freq - f0))
    V1 = magnitude[fundamental_idx]

    if V1 == 0:
        return 0.0

    harmonic_power = 0.0
    for i in range(len(freq)):
        current_freq = freq[i]

        # Skip area around fundamental frequency
        if abs(current_freq - f0) < 1.0:
            continue

        harmonic_number = current_freq / f0
        # If frequency is close to an integer harmonic (delta < 0.05)
        if abs(harmonic_number - round(harmonic_number)) < 0.05:
            harmonic_power += magnitude[i] ** 2

    return np.sqrt(harmonic_power) / V1


# =========================================================
# VISUALIZATION
# =========================================================

def plot_three_phase(t, Va, Vb, Vc, cycles=5, f0=50.0):
    """
    Plot three-phase waveform zoomed to a specific number of network cycles.
    """
    os.makedirs("plots", exist_ok=True)
    period = 1 / f0
    zoom_time = cycles * period

    plt.figure(figsize=(12, 5))
    plt.plot(t, Va, label="Phase A", color="#1f77b4")
    plt.plot(t, Vb, label="Phase B", color="#ff7f0e")
    plt.plot(t, Vc, label="Phase C", color="#2ca02c")

    plt.xlim(0, min(zoom_time, t[-1]))
    plt.xlabel("Time [s]")
    plt.ylabel("Voltage [V]")
    plt.title(f"Three-Phase Voltage Signals (Zoomed to {cycles} Cycles)")
    plt.legend(loc="upper right")
    plt.grid(True, linestyle="--", alpha=0.7)
    plt.tight_layout()

    plt.savefig("plots/three_phase_signal.png", dpi=200)
    plt.show()


def plot_fft(freqA, magA, freqB, magB, freqC, magC, max_freq=500):
    """
    Plot FFT Spectrum for all three phases side by side.
    """
    os.makedirs("plots", exist_ok=True)
    plt.figure(figsize=(12, 5))

    plt.plot(freqA, magA, label="Phase A Spectrum", color="#1f77b4", alpha=0.8)
    plt.plot(freqB, magB, label="Phase B Spectrum", color="#ff7f0e", alpha=0.7)
    plt.plot(freqC, magC, label="Phase C Spectrum", color="#2ca02c", alpha=0.6)

    plt.xlim(0, max_freq)
    plt.xlabel("Frequency [Hz]")
    plt.ylabel("Amplitude [V Peak]")
    plt.title("FFT Spectrum Analysis")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.7)
    plt.tight_layout()

    plt.savefig("plots/fft_spectrum.png", dpi=200)
    plt.show()


# =========================================================
# MAIN EXECUTION
# =========================================================

def main():
    parser = argparse.ArgumentParser(description="Advanced Power Quality Simulator & Analyzer")
    parser.add_argument("--duration", type=float, default=6.0, help="Signal duration in seconds")
    parser.add_argument("--fs", type=int, default=5000, help="Sampling frequency in Hz")
    parser.add_argument("--noise", type=float, default=1.2, help="Noise standard deviation")
    args = parser.parse_args()

    out_dir = "data"
    os.makedirs(out_dir, exist_ok=True)

    print("--- Running Simulation ---")
    # Generate data (with event simulation on different phases)
    t, Va, Vb, Vc, metadata = generate_three_phase(
        fs=args.fs,
        duration=args.duration,
        noise_std=args.noise,
        sag_events=[(0.8, 1.2, 0.45, ["A", "B"])],  # Sag on phases A and B
        swell_events=[(3.5, 3.8, 1.4, ["A", "B", "C"])]  # Swell on all three phases
    )

    # Export to DataFrame
    df = pd.DataFrame({"time": t, "Va": Va, "Vb": Vb, "Vc": Vc})

    csv_path = os.path.join(out_dir, "synthetic_three_phase.csv")
    excel_path = os.path.join(out_dir, "synthetic_three_phase.xlsx")

    df.to_csv(csv_path, index=False)
    # Use openpyxl (make sure the library is installed: pip install openpyxl)
    df.to_excel(excel_path, index=False, engine='openpyxl')
    print(f"[SUCCESS] Dataset saved to relative paths:\n  -> {csv_path}\n  -> {excel_path}")

    # RMS analysis (compute mean value from rolling RMS)
    rms_a = np.mean(calculate_rolling_rms(Va, args.fs))
    rms_b = np.mean(calculate_rolling_rms(Vb, args.fs))
    rms_c = np.mean(calculate_rolling_rms(Vc, args.fs))

    print("\n--- Power Quality Metrics ---")
    print(f"Phase A | Mean Rolling RMS: {rms_a:.2f} V | THD: {calculate_thd(Va, args.fs):.4%}")
    print(f"Phase B | Mean Rolling RMS: {rms_b:.2f} V | THD: {calculate_thd(Vb, args.fs):.4%}")
    print(f"Phase C | Mean Rolling RMS: {rms_c:.2f} V | THD: {calculate_thd(Vc, args.fs):.4%}")

    # Compute spectrum for plotting
    freqA, magA = compute_fft(Va, args.fs)
    freqB, magB = compute_fft(Vb, args.fs)
    freqC, magC = compute_fft(Vc, args.fs)

    print("\n--- Generating Plots ---")
    plot_three_phase(t, Va, Vb, Vc, cycles=6, f0=metadata["f0"])
    plot_fft(freqA, magA, freqB, magB, freqC, magC, max_freq=450)
    print("[SUCCESS] Plots displayed and saved to /plots directory.")


if __name__ == "__main__":
    main()