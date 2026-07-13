import pandas as pd
from typing import List, Dict, Any
from . import GameLogs_pb2 as pb
from google.protobuf.descriptor import FieldDescriptor
from datetime import datetime, timezone
from google.protobuf.timestamp_pb2 import Timestamp


def timestamp_to_datetime(ts) -> datetime:
    """
    Convert a protobuf Timestamp to a timezone-aware Python datetime.
    If ts is already a datetime, return it directly.
    """
    if isinstance(ts, datetime):
        return ts  # already converted
    if isinstance(ts, Timestamp):
        return datetime.fromtimestamp(ts.seconds + ts.nanos / 1e9, tz=timezone.utc)
    raise TypeError(f"Expected Timestamp or datetime, got {type(ts)}")


# -------------------------
#   LOW-LEVEL FIELD EXTRACTOR (with defaults)
# -------------------------
def protobuf_to_dict(msg) -> dict:
    out = {}
    present_fields = {f.name for f, _ in msg.ListFields()}

    for field in msg.DESCRIPTOR.fields:
        name = field.name
        is_present = name in present_fields

        # Repeated fields
        if field.is_repeated:
            value = getattr(msg, name)
            if field.type == FieldDescriptor.TYPE_MESSAGE:
                out[name] = [protobuf_to_dict(v) for v in value]
            else:
                # bytes repeated? convert each element to hex
                if field.type == FieldDescriptor.TYPE_BYTES:
                    out[name] = [v.hex() for v in value]
                else:
                    out[name] = list(value)
            continue

        # Skip optional fields not present
        if field.has_presence and not is_present:
            continue

        value = getattr(msg, name)

        # Nested message
        if field.type == FieldDescriptor.TYPE_MESSAGE:
            if isinstance(value, Timestamp):
                out[name] = timestamp_to_datetime(value)
            else:
                out[name] = protobuf_to_dict(value)

        # Enum
        elif field.type == FieldDescriptor.TYPE_ENUM:
            out[name] = value

        # Scalar
        else:
            # Convert specific field names (hash_data) to hex
            if field.type == FieldDescriptor.TYPE_BYTES and name == "hash_data":
                out[name] = value.hex()
            else:
                out[name] = value

    return out


def flatten_packet_bunches(packet_dict: dict, bunch_msg_type=None) -> list[dict]:
    if "bunches" not in packet_dict or not packet_dict["bunches"]:
        return []

    base = packet_dict.copy()
    bunch_list = base.pop("bunches")
    rows = []

    for b in bunch_list:
        row = base.copy()
        if bunch_msg_type is not None:
            for field in bunch_msg_type.DESCRIPTOR.fields:
                fname = field.name
                if fname not in b:
                    if field._field.label == FieldDescriptor.LABEL_REPEATED:
                        if field.type in (FieldDescriptor.TYPE_INT32, FieldDescriptor.TYPE_INT64,
                                          FieldDescriptor.TYPE_UINT32, FieldDescriptor.TYPE_UINT64,
                                          FieldDescriptor.TYPE_FLOAT, FieldDescriptor.TYPE_DOUBLE):
                            b[fname] = 0
                        elif field.type == FieldDescriptor.TYPE_BOOL:
                            b[fname] = False
                        elif field.type == FieldDescriptor.TYPE_STRING:
                            b[fname] = ""
                        elif field.type == FieldDescriptor.TYPE_BYTES:
                            b[fname] = b""
                        elif field.type == FieldDescriptor.TYPE_ENUM:
                            b[fname] = field.enum_type.values[0].number
                        elif field.type == FieldDescriptor.TYPE_MESSAGE:
                            b[fname] = {}
        for k, v in b.items():
            row[f"bunch_{k}"] = v
        rows.append(row)

    return rows


# -------------------------
#   CORE PARSER
# -------------------------
class RingBufferParser:
    def __init__(self, buf: pb.RingBufferLog):
        self.buf = buf

    @classmethod
    def from_file(cls, path: str) -> "RingBufferParser":
        buf = pb.RingBufferLog()
        with open(path, "rb") as f:
            buf.ParseFromString(f.read())
        return cls(buf)

    # -------------------------
    #   MAIN UNIFIED PARSE
    # -------------------------
    def parse_entries(self) -> List[Dict[str, Any]]:
        rows = []

        for entry in self.buf.entries:
            row = {}
            if entry.HasField("packet"):
                row = protobuf_to_dict(entry.packet)
                row["entry_type"] = "packet"
                # Optional timestamp if present
                if "ts" in row:
                    row["timestamp"] = timestamp_to_datetime(row["ts"])

            elif entry.HasField("event"):
                ev = entry.event
                row = protobuf_to_dict(ev)
                row["entry_type"] = "event"
                row["timestamp"] = timestamp_to_datetime(ev.ts)

                payload_field = ev.WhichOneof("payload")
                row["event_type"] = payload_field
                if payload_field:
                    payload_msg = getattr(ev, payload_field)
                    row["payload"] = protobuf_to_dict(payload_msg)

            elif entry.HasField("network_stat"):
                ns = entry.network_stat
                row = protobuf_to_dict(ns)
                row["entry_type"] = "network_stat"
                if "ts" in row:
                    row["timestamp"] = timestamp_to_datetime(row["ts"])

            rows.append(row)

        return rows

    # -------------------------
    #   DATAFRAME BUILDER
    # -------------------------
    def to_dataframe(self, mode: str = "all") -> pd.DataFrame:
        rows = self.parse_entries()
        df = pd.DataFrame(rows)

        # Sort by ts_dt if it exists
        if "ts" in df.columns:
            df.sort_values("ts", inplace=True)
            df.reset_index(drop=True, inplace=True)

        # Modes for filtering
        if mode == "events_all":
            return df[df["entry_type"] == "event"]
        if mode == "packets_all":
            return df[df["entry_type"] == "packet"]
        if mode == "events_basic":
            return df[(df["entry_type"] == "event") & (df.get("event_type").isin(["movement","weapon","health"]))]
        if mode == "events_cheat":
            return df[(df["entry_type"] == "event") & (df.get("event_type") == "cheat")]
        if mode.startswith("event_"):
            event_type = mode.replace("event_", "")
            return df[(df["entry_type"] == "event") & (df.get("event_type") == event_type)]
        if mode == "packet_header":
            return pd.DataFrame([r["header"] for r in rows if r["entry_type"] == "packet" and "header" in r])
        if mode == "packet_notification_header":
            return pd.DataFrame([r["notification"]["header"]
                                 for r in rows if r["entry_type"] == "packet"
                                 and "notification" in r
                                 and "header" in r["notification"]])
        if mode == "packet_connection_error":
            return pd.DataFrame([r["connection_error"] for r in rows
                                 if r["entry_type"] == "packet"
                                 and "connection_error" in r])
        if mode == "packet_bunches":
            out = []
            for r in rows:
                if r["entry_type"] == "packet" and "bunches" in r:
                    out.extend(flatten_packet_bunches(r))
            df_bunch = pd.DataFrame(out)
            if "bunch_ts" in df_bunch.columns:
                df_bunch["bunch_ts_dt"] = df_bunch["bunch_ts"].apply(timestamp_to_datetime)
                df_bunch.sort_values("bunch_ts_dt", inplace=True)
                df_bunch.reset_index(drop=True, inplace=True)
            return df_bunch
        if mode.startswith("packet_bunches_filtered"):
            _, rule = mode.split(":", 1)
            key, val = rule.split("=")
            if val.lower() in ["true", "false"]:
                val = val.lower() == "true"
            elif val.isdigit():
                val = int(val)
            filtered = []
            for r in rows:
                if r["entry_type"] == "packet" and "bunches" in r:
                    for b in flatten_packet_bunches(r):
                        if f"bunch_{key}" in b and b[f"bunch_{key}"] == val:
                            filtered.append(b)
            df_filtered = pd.DataFrame(filtered)
            if "bunch_ts" in df_filtered.columns:
                df_filtered["bunch_ts_dt"] = df_filtered["bunch_ts"].apply(timestamp_to_datetime)
                df_filtered.sort_values("bunch_ts_dt", inplace=True)
                df_filtered.reset_index(drop=True, inplace=True)
            return df_filtered

        return df