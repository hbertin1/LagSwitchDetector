# LagSwitchDetector

A data-processing and detection notebook pipeline for identifying lag-switch cheating in Unreal Engine server captures and logs.

## What this repo contains
- `LagSwitchDetector.ipynb` — main analysis notebook: parsing server trace logs, extracting players/phases/cheats, processing PCAPs (via tshark), computing IAT features with exponential decay, running adaptive/fixed detectors, and producing evaluation and plots.
- `cache/` — cache folder used for GeoIP lookups (`ip_cache.json`).

## Key features
- Parse RingBuffer server traces (requires the `proto_parser` utility).
- Extract players, phases and cheat intervals from server logs.
- Process PCAP captures with `tshark` to extract packets, headers and payloads.
- Compute raw and adaptive IAT features with decay smoothing (half-life parameter).
- Multiple detectors and baseline implementations (adaptive, fixed gap, gap+burst, random baseline).
- Evaluation tools: packet-level, windowed, gap-event, per-flow and per-player metrics and visualizations.

## Prerequisites
- Python 3.9+ (recommended in a virtualenv)
- System: `tshark` (Wireshark CLI) installed and on PATH for PCAP parsing
- Python packages: pandas, numpy, matplotlib, protobuf, requests

You can install Python packages (example):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # PowerShell on Windows
pip install --upgrade pip
pip install pandas numpy matplotlib protobuf requests
```

## Configuration
Open `LagSwitchDetector.ipynb` and update the configuration section near the top:
- `PROTO_PARSER_PATH` — path to the local `proto_parser` package / Unreal proto parser utility.
- `PATH_LOGS` — path to your Sessions folder containing `Server` subfolders.
- `CACHE_FILE` — path to store GeoIP cache (defaults to `cache/ip_cache.json`).
- `SERVER_IP` — server IP used to decide packet direction (default present in notebook).

Make sure `CACHE_FILE` parent folder exists (not required if you run the notebook as the notebook code makes it).

## Quickstart (recommended order)
1. Open the notebook `LagSwitchDetector.ipynb` in Jupyter / VS Code and run cells sequentially.
2. Update configuration values at the top of the notebook.
3. If you need to parse PCAPs, ensure `tshark` is installed and accessible.

Example high-level calls inside the notebook:
- Build labeled PCAP dict for a single server folder:

```python
pcap_dict = get_pcap_dict_labelled(r"C:\path\to\ServerFolder", half_life=10, inlab=False)
```

- Collect all sessions recursively and compute IATs:

```python
merged = gather_all_pcaps_with_iats(r"C:\path\to\SessionsFolder", half_life=10)
```

- Run adaptive detector (sweep half-life, choose best per-ISP, evaluate):

```python
half_life_values = np.logspace(np.log10(1), np.log10(40), num=10)
sweep_df, details = compare_half_life_impact_detection_gap_events_per_isp(merged, half_life_values)
best_per_isp = find_best_half_life_per_isp(sweep_df)
adaptive = run_adaptive_half_life_detector(merged, best_per_isp, default_half_life=20)
```

- Evaluate baselines and compare:

```python
gap_out = extract_suspicious_window_fixed_threshold(merged, gap_threshold_ms=400)
gap_results = evaluate_detector_gap_events(gap_out, detector_col='detector_suspicious_fixed')
```

## Notes and tips
- The notebook contains numerous helper functions — run top-level cells (imports/config) first.
- PCAP parsing can be slow and memory intensive; consider processing subsets or enabling multiprocessing carefully.
- GeoIP lookups are rate-limited; the notebook caches results in `CACHE_FILE`.
- There are duplicate helper function definitions in older versions of the notebook; ensure you run the notebook from top to bottom after making edits to avoid stale definitions in the kernel.

## Troubleshooting
- FileNotFoundError for `PROTO_PARSER_PATH`: set `PROTO_PARSER_PATH` to the correct local path where the `proto_parser` module lives.
- `tshark` errors: verify `tshark -v` works in your shell and that the PCAP files are readable.
- Rate limits on GeoIP API: increase the sleep between requests, or populate `cache/ip_cache.json` manually for known IPs.

## License & contact
This repository contains research code. No license file is included — if you plan to share publicly, add a `LICENSE` file.


