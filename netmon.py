#!/usr/bin/env python3
"""Measure the quality of an internet connection over time.

Repeatedly measures the round-trip time to a server and reports latency,
jitter, packet loss and *dropouts*: stretches of time where nothing gets
through at all.  It answers questions like "when did my connection drop, and
for how long?", for example on a phone hotspot that loses 5G whenever a call
comes in.

Only the Python standard library is used, so it runs on Windows, macOS and
Linux without installing anything and without administrator rights::

    python netmon.py                            # probe 1.1.1.1:443 every second
    python netmon.py --host 8.8.8.8 --port 53   # probe another server
    python netmon.py --interval 0.5 --report 5  # probe faster, report more often
    python netmon.py --duration 600             # stop by itself after 10 minutes
    python netmon.py --csv hotspot.csv          # also log every probe to a CSV

Press Ctrl+C to stop; a summary of the whole run is printed at the end.

The probe is a plain TCP connect (the same thing a browser does when it opens
a page), so the measured time is the round trip to the server.  ICMP ping is
deliberately not used: it needs admin rights on some systems and the output
of the ``ping`` command is different on every platform and in every language.
"""

import argparse
import csv
import math
import socket
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Sequence

DEFAULT_HOST = "1.1.1.1"
DEFAULT_PORT = 443


@dataclass
class Sample:
    """One probe: when it was sent and how long it took (None = no answer)."""

    timestamp: float
    rtt_ms: Optional[float]

    @property
    def ok(self) -> bool:
        return self.rtt_ms is not None


@dataclass
class Dropout:
    """A stretch of consecutive unanswered probes."""

    start: float
    end: Optional[float] = None  # None while the dropout is still going on

    def duration(self, now: Optional[float] = None) -> float:
        """Length in seconds; an unfinished dropout is measured up to ``now``."""
        if self.end is not None:
            return self.end - self.start
        return (now if now is not None else time.time()) - self.start


class DropoutTracker:
    """Turn a stream of samples into a list of dropouts.

    A dropout starts once ``threshold`` probes in a row go unanswered (its
    start time is that of the first unanswered probe) and ends at the first
    answered probe after it.
    """

    def __init__(self, threshold: int = 3) -> None:
        if threshold < 1:
            raise ValueError("threshold must be at least 1")
        self.threshold = threshold
        self.dropouts: List[Dropout] = []
        self.current: Optional[Dropout] = None
        self._failures = 0
        self._first_failure: Optional[float] = None

    def add(self, sample: Sample) -> Optional[str]:
        """Record a sample; return ``"start"`` or ``"end"`` on a dropout edge."""
        if sample.ok:
            self._failures = 0
            self._first_failure = None
            if self.current is not None:
                self.current.end = sample.timestamp
                self.current = None
                return "end"
            return None

        self._failures += 1
        if self._first_failure is None:
            self._first_failure = sample.timestamp
        if self.current is None and self._failures >= self.threshold:
            self.current = Dropout(start=self._first_failure)
            self.dropouts.append(self.current)
            return "start"
        return None


def jitter_ms(rtts: Sequence[float]) -> float:
    """Average change in latency between consecutive answered probes."""
    if len(rtts) < 2:
        return 0.0
    return sum(abs(b - a) for a, b in zip(rtts, rtts[1:])) / (len(rtts) - 1)


def percentile(values: Sequence[float], pct: float) -> float:
    """Nearest-rank percentile (``pct`` in 0..100) of a non-empty sequence."""
    if not values:
        raise ValueError("percentile of an empty sequence")
    ordered = sorted(values)
    rank = max(1, math.ceil(pct / 100.0 * len(ordered)))
    return ordered[min(rank, len(ordered)) - 1]


def summarize(samples: Sequence[Sample], dropouts: Sequence[Dropout],
              now: Optional[float] = None) -> dict:
    """Collect the numbers that describe a run (or a window of one)."""
    sent = len(samples)
    rtts = [s.rtt_ms for s in samples if s.ok]
    lost = sent - len(rtts)
    summary = {
        "sent": sent,
        "lost": lost,
        "loss_pct": (100.0 * lost / sent) if sent else 0.0,
        "dropouts": len(dropouts),
        "dropout_seconds": sum(d.duration(now) for d in dropouts),
    }
    if rtts:
        summary.update({
            "min_ms": min(rtts),
            "avg_ms": sum(rtts) / len(rtts),
            "median_ms": percentile(rtts, 50),
            "p95_ms": percentile(rtts, 95),
            "max_ms": max(rtts),
            "jitter_ms": jitter_ms(rtts),
        })
    return summary


def resolve(host: str) -> str:
    """Resolve a host name once, so DNS time never ends up in the probes."""
    try:
        return socket.getaddrinfo(host, None, socket.AF_UNSPEC, socket.SOCK_STREAM)[0][4][0]
    except (socket.gaierror, IndexError):
        raise SystemExit(f"Cannot resolve {host!r}; is the connection up? "
                         f"Try an IP address such as {DEFAULT_HOST}.")


def probe(address: str, port: int, timeout: float) -> Optional[float]:
    """TCP-connect to ``address:port``; return the round trip in ms, or None."""
    started = time.perf_counter()
    try:
        with socket.create_connection((address, port), timeout=timeout):
            pass
    except OSError:
        return None
    return (time.perf_counter() - started) * 1000.0


def clock(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%H:%M:%S")


def report_line(window: Sequence[Sample], seconds: float) -> str:
    """One line describing the last ``seconds`` worth of samples."""
    s = summarize(window, [])
    text = f"{clock(time.time())}  last {seconds:g}s: {s['sent']} sent, " \
           f"{s['lost']} lost ({s['loss_pct']:.0f}%)"
    if "avg_ms" in s:
        text += f", avg {s['avg_ms']:.1f} ms, max {s['max_ms']:.1f} ms, " \
                f"jitter {s['jitter_ms']:.1f} ms"
    else:
        text += ", no answer at all"
    return text


def print_summary(samples: Sequence[Sample], dropouts: Sequence[Dropout]) -> None:
    now = time.time()
    s = summarize(samples, dropouts, now)
    print("Summary")
    print(f"  probes sent   : {s['sent']}")
    print(f"  lost          : {s['lost']} ({s['loss_pct']:.1f}%)")
    if "avg_ms" in s:
        print(f"  latency (ms)  : min {s['min_ms']:.1f}  avg {s['avg_ms']:.1f}  "
              f"median {s['median_ms']:.1f}  p95 {s['p95_ms']:.1f}  max {s['max_ms']:.1f}")
        print(f"  jitter        : {s['jitter_ms']:.1f} ms")
    print(f"  dropouts      : {s['dropouts']}, {s['dropout_seconds']:.1f} s in total")
    for d in dropouts:
        end = clock(d.end) if d.end is not None else "still down"
        print(f"    {clock(d.start)} - {end}  ({d.duration(now):.1f} s)")


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Measure latency, jitter, packet loss and dropouts of your connection.")
    parser.add_argument("--host", default=DEFAULT_HOST,
                        help=f"server to probe (default: {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help=f"TCP port to connect to (default: {DEFAULT_PORT})")
    parser.add_argument("--interval", type=float, default=1.0,
                        help="seconds between probes (default: 1)")
    parser.add_argument("--timeout", type=float, default=1.0,
                        help="seconds to wait for an answer (default: 1)")
    parser.add_argument("--report", type=float, default=10.0,
                        help="seconds between report lines (default: 10)")
    parser.add_argument("--dropout-after", type=int, default=3, metavar="N",
                        help="unanswered probes in a row that count as a dropout (default: 3)")
    parser.add_argument("--duration", type=float, default=None,
                        help="stop after this many seconds (default: run until Ctrl+C)")
    parser.add_argument("--csv", metavar="FILE",
                        help="append every probe to this CSV file")
    parser.add_argument("--verbose", action="store_true",
                        help="print a line for every single probe")
    args = parser.parse_args(argv)
    for name in ("interval", "timeout", "report"):
        if getattr(args, name) <= 0:
            parser.error(f"--{name} must be greater than 0")
    if args.dropout_after < 1:
        parser.error("--dropout-after must be at least 1")
    return args


def run(args: argparse.Namespace) -> int:
    address = resolve(args.host)
    tracker = DropoutTracker(threshold=args.dropout_after)
    samples: List[Sample] = []
    window: List[Sample] = []

    csv_file = csv_writer = None
    if args.csv:
        csv_file = open(args.csv, "a", newline="", encoding="utf-8")
        csv_writer = csv.writer(csv_file)
        if csv_file.tell() == 0:
            csv_writer.writerow(["time", "epoch", "rtt_ms", "ok"])

    where = args.host if args.host == address else f"{args.host} ({address})"
    print(f"Probing {where} port {args.port} every {args.interval:g}s; "
          f"report every {args.report:g}s; Ctrl+C to stop.")

    started = time.time()
    next_report = started + args.report
    try:
        while args.duration is None or time.time() - started < args.duration:
            sent_at = time.time()
            sample = Sample(sent_at, probe(address, args.port, args.timeout))
            samples.append(sample)
            window.append(sample)

            if csv_writer:
                csv_writer.writerow([datetime.fromtimestamp(sent_at).isoformat(timespec="milliseconds"),
                                     f"{sent_at:.3f}",
                                     "" if sample.rtt_ms is None else f"{sample.rtt_ms:.1f}",
                                     int(sample.ok)])
                csv_file.flush()
            if args.verbose:
                answer = "no answer" if sample.rtt_ms is None else f"{sample.rtt_ms:.1f} ms"
                print(f"{clock(sent_at)}  {answer}")

            edge = tracker.add(sample)
            if edge == "start":
                print(f"{clock(sent_at)}  !!! DROPOUT: {args.dropout_after} probes in a row "
                      f"unanswered (since {clock(tracker.current.start)})")
            elif edge == "end":
                last = tracker.dropouts[-1]
                print(f"{clock(sent_at)}  ... connection back after {last.duration():.1f} s")

            now = time.time()
            if now >= next_report:
                print(report_line(window, args.report))
                window.clear()
                next_report = now + args.report

            remaining = args.interval - (time.time() - sent_at)
            if remaining > 0:
                time.sleep(remaining)
    except KeyboardInterrupt:
        print()
    finally:
        if csv_file:
            csv_file.close()

    print_summary(samples, tracker.dropouts)
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    return run(parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
