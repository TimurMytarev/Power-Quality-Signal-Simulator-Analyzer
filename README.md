# Power Quality Signal Simulator & Analyzer

> A mathematical simulator and digital signal processor for three-phase voltage signals. It generates synthetic power quality anomalies (Sags, Swells, Harmonics, Flicker, Noise) and performs spectral analysis using FFT and THD tracking.

---

## Table of Contents
- [Key Features](#-key-features)
- [Tech Stack](#-tech-stack)
- [Quick Start](#-quick-start)
- [CLI Arguments](#-cli-arguments)
- [Advanced Customization](#-advanced-customization)
- [Output Structure](#-output-structure)
- [Contact](#-contact)

---

## Key Features

- **Three-Phase Generation ($V_a, V_b, V_c$):** Synthesizes ideal sinusoidal waveforms with a precise $120^\circ$ phase shift.
- **Power Quality Anomalies:** Simulates real-world grid disturbances:
  * Voltage Sags & Swells (configurable timeframes and affected phases)
  * Higher-order Harmonics
  * Amplitude modulation (Flicker)
  * Gaussian Noise & Phase Unbalance
- **Nyquist Criterion Validation:** Automatically verifies the sampling frequency $f_s$ against the maximum harmonic frequency to prevent aliasing before running the simulation.
- **Digital Signal Processing (DSP):**
  * One-sided Fast Fourier Transform (FFT) with correct amplitude energy scaling.
  * Total Harmonic Distortion (THD) using dynamic harmonic bin scanning.
  * Rolling RMS calculation using a high-performance 20 ms moving window (optimized for 50 Hz power systems).
- **Data Export:** Automated file management saving datasets to CSV/Excel and exporting high-resolution plots.

---

## Tech Stack

- **Language:** Python 3.8+
- **Mathematical & Data Analysis:** NumPy, Pandas
- **Visualization:** Matplotlib
- **Excel Processing:** OpenPyXL

---

## Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com
cd power-quality-simulator
```

### 2. Install Dependencies
It is highly recommended to use a virtual environment:
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Linux/macOS
# or
venv\Scripts\activate     # On Windows

# Install required packages
pip install numpy pandas matplotlib openpyxl
```

### 3. Run the Simulation
Execute the script using default configurations:
```bash
python main.py
```

---

## CLI Arguments

You can dynamically adjust key parameters directly from your terminal:


| Flag | Type | Default | Description |
| :--- | :---: | :---: | :--- |
| `--duration` | float | `6.0` | Total signal duration in seconds |
| `--fs` | int | `5000` | Sampling frequency in Hz |
| `--noise` | float | `1.2` | Standard deviation of Gaussian noise |

**Example of custom execution:**
```bash
python main.py --duration 10.0 --fs 8000 --noise 0.5
```

---

## Advanced Customization

To modify specific anomalies, open `main.py` and tweak the parameters inside the `generate_three_phase` function call:

```python
# Custom configuration example in main()
t, Va, Vb, Vc, metadata = generate_three_phase(
    fs=args.fs,
    duration=args.duration,
    noise_std=args.noise,
    harmonics=[(3, 0.10), (5, 0.05)],          # 10% 3rd harmonic, 5% 5th harmonic
    sag_events=[(0.5, 1.5, 0.3, ["A"])],       # Deep sag on Phase A from 0.5s to 1.5s
    swell_events=[(4.0, 4.5, 1.3, ["B", "C"])] # Voltage swell on Phase B & C
)
```

---

## Output Structure & Visualization

Upon execution, the script automatically manages and creates output directories. The generated data is kept locally (ignored by Git), while the visualization plots are saved and tracked:

### Signal Waveform Plot
The script generates an oscilloscope-like view of the three-phase signal, zoomed into specific cycles to clearly display simulated power quality events (such as sags and swells):

![Three-Phase Voltage Signal](Source%20code/plots/three_phase_signal.png)

### FFT Spectrum Plot
The dynamic FFT analysis plots the frequency spectrum side-by-side for all three phases, allowing immediate identification of higher-order harmonics:

![FFT Spectrum](Source%20code/plots/fft_spectrum.png)

### Generated Data (Local Only)
- `data/synthetic_three_phase.csv` — Raw time-series voltage data for all three phases.
- `data/synthetic_three_phase.xlsx` — Microsoft Excel compatible version of the dataset.


---

## Contact

- **Author:** Timur Mytarev
- **Email:** [timurmytarev@gmail.com](mailto:timurmytarev@gmail.com)
- **Project Link:** [https://github.com](https://github.com)
