import argparse
import pandas as pd
from typing import List, Dict, Any
from . import GameLogs_pb2 as pb
from .parser_utils import RingBufferParser


def main():
    parser = argparse.ArgumentParser(description="Parse RingBufferLog protobuf into CSV.")
    parser.add_argument("input_file", type=str, help="Path to the protobuf log file (.pb or .bin)")
    parser.add_argument("--mode", type=str, default="all",
                        help="Parsing mode: events_all, packets_all, events_cheat, etc.")
    parser.add_argument("--output", type=str, default=None,
                        help="Path to output CSV file (optional)")

    args = parser.parse_args()

    # Load protobuf log
    rb_parser = RingBufferParser.from_file(args.input_file)

    # Convert to DataFrame
    df = rb_parser.to_dataframe(mode=args.mode)

    # Save to CSV if requested
    if args.output:
        df.to_csv(args.output, index=False)
        print(f"Saved {len(df)} rows to {args.output}")
    else:
        print(df.head())


if __name__ == "__main__":
    main()