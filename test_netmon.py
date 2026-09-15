"""Tests for the connection monitor.

Everything runs locally: the only network involved is a listening socket on
127.0.0.1, so the tests pass without an internet connection.
"""

import socket

import pytest

from netmon import (Dropout, DropoutTracker, Sample, jitter_ms, parse_args,
                    percentile, probe, report_line, summarize)


def samples(*rtts):
    """Build samples one second apart; None means the probe went unanswered."""
    return [Sample(timestamp=float(i), rtt_ms=rtt) for i, rtt in enumerate(rtts)]


def test_jitter_is_the_average_change_between_consecutive_probes():
    assert jitter_ms([]) == 0.0
    assert jitter_ms([10.0]) == 0.0
    assert jitter_ms([10.0, 20.0, 10.0]) == 10.0


def test_percentile_uses_nearest_rank():
    values = list(range(1, 11))
    assert percentile(values, 50) == 5
    assert percentile(values, 95) == 10
    assert percentile(values, 100) == 10
    assert percentile([42.0], 0) == 42.0
    with pytest.raises(ValueError):
        percentile([], 50)


def test_short_hiccup_is_not_a_dropout():
    tracker = DropoutTracker(threshold=3)
    edges = [tracker.add(s) for s in samples(10, None, None, 12)]
    assert edges == [None, None, None, None]
    assert tracker.dropouts == []


def test_dropout_starts_at_first_failure_and_ends_at_next_answer():
    tracker = DropoutTracker(threshold=3)
    edges = [tracker.add(s) for s in samples(10, None, None, None, None, 15, 16)]
    assert edges == [None, None, None, "start", None, "end", None]
    assert tracker.dropouts == [Dropout(start=1.0, end=5.0)]
    assert tracker.dropouts[0].duration() == 4.0
    assert tracker.current is None


def test_unfinished_dropout_is_measured_up_to_now():
    tracker = DropoutTracker(threshold=1)
    tracker.add(Sample(timestamp=100.0, rtt_ms=None))
    assert tracker.current is not None
    assert tracker.dropouts[0].duration(now=107.5) == 7.5


def test_tracker_rejects_a_threshold_below_one():
    with pytest.raises(ValueError):
        DropoutTracker(threshold=0)


def test_summary_counts_loss_and_latency():
    tracker = DropoutTracker(threshold=2)
    run = samples(10, 20, None, None, 30)
    for s in run:
        tracker.add(s)
    summary = summarize(run, tracker.dropouts)
    assert summary["sent"] == 5
    assert summary["lost"] == 2
    assert summary["loss_pct"] == 40.0
    assert summary["dropouts"] == 1
    assert summary["dropout_seconds"] == 2.0
    assert summary["min_ms"] == 10 and summary["max_ms"] == 30
    assert summary["avg_ms"] == 20.0
    assert summary["jitter_ms"] == 10.0


def test_summary_without_any_answer_has_no_latency_figures():
    summary = summarize(samples(None, None), [])
    assert summary["loss_pct"] == 100.0
    assert "avg_ms" not in summary
    assert summarize([], [])["loss_pct"] == 0.0


def test_report_line_mentions_loss_and_latency():
    line = report_line(samples(10, None), 10)
    assert "2 sent, 1 lost (50%)" in line
    assert "avg 10.0 ms" in line
    assert "no answer at all" in report_line(samples(None), 10)


def test_probe_measures_a_reachable_port_and_reports_none_for_a_closed_one():
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen()
        port = server.getsockname()[1]
        rtt = probe("127.0.0.1", port, timeout=2.0)
        assert rtt is not None and 0 <= rtt < 2000
    # The port is closed again now, so the connection is refused.
    assert probe("127.0.0.1", port, timeout=2.0) is None


def test_arguments_have_sane_defaults_and_are_validated():
    args = parse_args([])
    assert (args.host, args.port, args.interval, args.dropout_after) == ("1.1.1.1", 443, 1.0, 3)
    assert parse_args(["--duration", "5", "--csv", "x.csv"]).duration == 5.0
    with pytest.raises(SystemExit):
        parse_args(["--interval", "0"])
    with pytest.raises(SystemExit):
        parse_args(["--dropout-after", "0"])
