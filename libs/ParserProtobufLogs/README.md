# ProtoParser — RingBufferLog to Pandas

A Python utility to parse Unreal Engine logs generated with the protobuffer specification that can be found under `GameLogs.proto`. The tool can convert the logs into **pandas DataFrames** , or **CSVs**.

---

## Table of Contents

- [Installation](#installation)  
- [Usage](#usage)  
  - [Direct usage of the proto structure](#direct-usage-of-the-proto-structure)  
  - [Load a binary log to Pandas DataFrames](#load-a-binary-log-to-pandas-dataframes)  
  - [Available Parsing Modes](#available-parsing-modes)  
  - [Flattening Nested Bunches](#flattening-nested-bunches)  
- [Extending the Parser](#extending-the-parser)  
- [Examples](#examples)  
- [Command-Line Interface (CLI)](#command-line-interface-cli)  
  - [Saving output to CSV](#saving-output-to-csv)  
- [Requirements](#requirements)  
- [License](#license)
---

## Installation

1. Git clone <url_repo>
2. Install Python dependencies:
```
pip install pandas protobuf
```

## Usage

### Direct usage of the structure defined in the speecification

1) import 

```
from proto_parser import GameLogs_pb2 as pb
```

Make sure it is in the import path. You can add the module path to the import path with: 
```
import sys, os
sys.path.append(os.path.abspath("../"))
```


2) load from a file

```
path = "path/to/protobuf/logs.bin"
bufferLogs = pb.RingBufferLog()

with open(path, "rb") as f:
    bufferLogs.ParseFromString(f.read())
```

3) Manipulate the data structure of the proto

Example:

```
for entry in bufferLogs.entries:
  if entry.HasField("event") and entry.event.WhichOneof("payload") == "cheat":
    cheat_event = entry.event.cheat
    print("Cheat activated: ", cheat_event)
```



### Load a binary log to python dataframes

1) import the module
```
from proto_parser.parser_utils import RingBufferParser
```

Make sure it is in the import path. You can add the module path to the import path with: 
```
import sys, os
sys.path.append(os.path.abspath("../"))
```

2) Load from a specific file to a dataframe
```
path = "path/to/protobuf/logs.bin"
parser = RingBufferParser.from_file(path)
df_logs = parser.to_dataframe()
```

It is also possible to apply a filter to the logs loaded (see below).


---


### Available Parsing Modes

You can select what to extract with the `mode` argument:

| Mode | Description |
|------|------------|
| `events_all` | All GameEvent entries |
| `packets_all` | All packets |
| `events_basic` | Movement, Weapon, Health events |
| `events_cheat` | Cheat events only |
| `event_movement` | Movement events only |
| `event_weapon` | WeaponFired events only |
| `event_health` | HealthUpdate events only |
| `packet_header` | Packet headers only |
| `packet_notification_header` | Notification headers from packets |
| `packet_connection_error` | ConnectionError from packets |
| `packet_bunches` | Flattened `bunches` inside packets |
<!-- not working properly yet -->
<!-- | `packet_bunches_filtered:<rule>` | Flattened `bunches` with a filter rule (e.g., `bopen=True`) | -->

---

### Flattening Nested Bunches

Each packet may contain multiple `bunches`. The utility can flatten them so **one row per bunch**:
```
df_bunches = parser.to_dataframe("packet_bunches")
```


Example columns:
```
ts | ind | frame | bunch_bopen | bunch_bclose | bunch_name | bunch_index
```

---

<!-- ### Filtered Bunches

You can filter bunches based on field values:

#### Only bunches where bopen=True
```
df_filtered = parser.to_dataframe("packet_bunches_filtered:bopen=True")
```
#### Only bunches for PlayerA
```
df_filtered = parser.to_dataframe("packet_bunches_filtered:name=PlayerA")
``` -->


*(Future extension: support multiple filters, comparison operators, partial string matches)*

---

## Extending the Parser

- **Add new event filters:** Just add more `event_type` in `to_dataframe()`.  
- **Add new packet filters:** Extend the `packet_*` modes.  
- **Flatten nested messages:** Use `pandas.json_normalize` on payloads to expand nested fields into separate columns:

```
import pandas as pd

df = parser.to_dataframe("events_basic")
df_payload = pd.json_normalize(df["payload"])
df = pd.concat([df.drop(columns=["payload"]), df_payload], axis=1)
```


---

## Examples

All events
```
df_all_events = parser.to_dataframe("events_all")
```
Only cheat events
```
df_cheat = parser.to_dataframe("events_cheat")
```
Only movement events
```
df_move = parser.to_dataframe("event_movement")
```
All packets
```
df_packets = parser.to_dataframe("packets_all")
```
Flatten all bunches
```
df_bunches = parser.to_dataframe("packet_bunches")
```
<!-- Not working properly yet -->
<!-- Filtered bunches: only open bunches
```
df_filtered = parser.to_dataframe("packet_bunches_filtered:bopen=True")
```
--- -->

## Command-Line Interface (CLI)

You can also run the parser from the command line, from the parent folder:

```
python -m proto_parser.parser_cli <binary_file> --mode <mode> --output <csv_file>
```
Example:
Flatten all bunches into CSV
```
python -m proto_parser.parser_cli ringbuffer_log.bin --mode packet_bunches --output bunches.csv
```
<!-- Filtered bunches
```
python parser_cli.py ringbuffer_log.bin --mode packet_bunches_filtered:bopen=True --output bunches_open.csv
``` -->

---

## Requirements

- Python ≥ 3.8  
- `protobuf`  
- `pandas`  

Install via:
```
pip install protobuf pandas
```

---

