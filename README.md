# LagSwitch Detector

Code accompanying our conference submission *Towards Server-Side Detection of LagSwitch Attacks through Network Traffic Analysis*. This
repository processes Unreal Engine server logs and PCAP captures to detect
**lag-switch cheating** in real game sessions, and reproduces the paper's
detection and evaluation results.


## Overview

Lag-switching is a form of cheating where a player deliberately throttles
their own network connection to gain an advantage, then releases it in a
short burst. The core signal is the packet inter-arrival time (IAT) on each
player's flow: a lag switch produces an abnormally large gap followed by a
burst of packets arriving faster than usual, as the client "catches up."

The pipeline in `LagSwitchDetector.ipynb`:

1. **Parses** Unreal Engine server trace logs (`trace_server_*.bin`) and the
   corresponding network captures (`capture_server_*.pcap`) for each game
   session.
2. **Labels** every packet with its game phase (warmup / playing / postgame),
   the player it belongs to, and whether it falls inside a known cheat
   interval (ground truth, from the server logs).
3. **Detects** suspicious IAT bursts using an *adaptive* detector: for each
   flow, a gap/burst threshold is derived from that flow's own decayed
   (exponentially-weighted) mean and standard deviation of IATs, rather than
   a single fixed threshold across all players and network conditions.
4. **Evaluates** the detector against three baselines (a fixed
   IAT threshold, a fixed gap+burst threshold, and a random baseline).
5. **Aggregates** per-event detector output into a per-player
   verdict.

## Repository structure

```
.
├── LagSwitchDetector.ipynb      # Main notebook: parsing, detection, evaluation
├── libs/
│   └── ParserProtobufLogs/
|       ├── parser_utils.py      # RingBufferParser: reads the protobuf server trace logs
│       └── ...      
├── data/                        # Input sessions (see "Data layout" below) — not included
│   └── <session>/Server/
│       ├── trace_server_YYYY.MM.DD-HH.MM.SS[_anonymized].bin
│       └── capture_server_YYYY.MM.DD-HH.MM.SS[_anonymized].pcap
└── cache/
    └── ip_cache_anonymized.json # Cached GeoIP/ISP lookups (anonymized for this release)
```

`data/` is included in an anonimyzed form in this release to not break double-blind review. 
A cache of anonimized GeoIP/ISP lookups (`cache/ip_cache_anonymized.json`) in order to maintain the per-region/per-ISP evaluation, without actually leaking player's locations. This enables to reproduce cells behaviour without without re-querying a
GeoIP service or exposing real player IPs.

## Requirements

**Python** ≥ 3.10, with:

```
numpy
pandas
matplotlib
protobuf
requests
```

(installable via the commented-out `%pip install` line in the notebook's
first cell.)

**System dependency:** [`tshark`](https://www.wireshark.org/docs/man-pages/tshark.html)
(part of Wireshark) must be installed and available on `PATH`. It's used to
extract UDP payloads from the `.pcap` captures.

## Setup

1. Clone the repository and install the Python dependencies above.
2. Install `tshark` and make sure it's on `PATH` (`tshark --version` should
   work in a terminal).
3. (in case you want to analyze your own data) Place session recordings under `data/` following the layout below.
4. (in case you want to analyze your own data) Open `LagSwitchDetector.ipynb` and update the configuration cell near the
   top if your paths differ:

   ```python
   PROTO_PARSER_PATH = Path("libs")
   PATH_LOGS = Path("data/")
   CACHE_FILE = Path("cache/ip_cache_anonymized.json")
   SERVER_IP = "137.74.44.5"   # server-side IP used to disambiguate flow direction
   ```

5. Run the notebook top to bottom.

## Data layout

Each recorded game session is expected as a subfolder of `PATH_LOGS`
containing a `Server/` directory with a matched pair of files:

- `trace_server_<YYYY.MM.DD-HH.MM.SS>.bin` — the Unreal Engine server's
  protobuf ring-buffer trace log (player joins, phase transitions, cheat
  start/stop events).
- `capture_server_<YYYY.MM.DD-HH.MM.SS>.pcap` — the matching raw network
  capture on the server, filtered to the game's UDP ports.

The notebook walks `PATH_LOGS` recursively looking for any `Server/`
subfolder, so sessions can be nested arbitrarily deep (e.g. grouped by date
or by region).

## Notebook structure

The notebook is organized to mirror the pipeline above:

- **Setup** — dependency install, imports, configuration.
- **Helper Functions** — generic pandas utilities for flattening
  protobuf-style payload columns and converting protobuf timestamps.
- **1. Parse Server Logs** — log/PCAP parsing, player/phase/cheat
  extraction, IAT computation, adaptive (decayed) IAT statistics, and
  packet labeling (phase, ground-truth cheat, GeoIP/ISP).
- **2. Detection** — the adaptive detector, packet/window/gap-event-level
  evaluation, the half-life sensitivity sweep, per-player LLR-based
  inference, and three baseline detectors (fixed threshold, fixed
  gap+burst, random).
- **Baselines** / **Evaluate per player** — the driver cells that actually
  run the above on `pcap_inthewild` and produce the paper's result tables.

Re-run the notebook from top to bottom before generating figures/tables for
submission — cell outputs are cleared in this release so they always reflect
the current code.

## Anonymization

This release is anonymized for double-blind review:

- `cache/ip_cache_anonymized.json` contains GeoIP/ISP lookups with real
  player IPs stripped or replaced.
- Trace/PCAP filenames and internal identifiers may carry an
  `_anonymized` suffix; the parsing regexes in the notebook accept both the
  plain and `_anonymized` filename forms.

<!-- 
## Citation

```
[BibTeX entry ]
``` -->

## License

[Add a license — e.g. MIT, Apache-2.0 — before making the repository public.]
