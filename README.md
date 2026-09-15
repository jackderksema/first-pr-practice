# first-pr-practice

A tiny practice project for learning the GitHub pull request workflow.

It contains one small function, `greet`, in [`greet.py`](greet.py).

## Usage

```python
from greet import greet

print(greet("Jack"))   # -> "Hello, Jack!"
```

## Running the tests

```bash
python -m pytest
```

## Connection monitor

[`netmon.py`](netmon.py) measures the quality of your internet connection over
time: latency, jitter, packet loss and dropouts (periods where nothing gets
through at all). It only uses the Python standard library, so it runs on
Windows, macOS and Linux without installing anything.

```bash
python netmon.py                     # probe 1.1.1.1:443 once a second until Ctrl+C
python netmon.py --duration 600      # run for 10 minutes, then print the summary
python netmon.py --csv hotspot.csv   # also log every probe to a CSV file
python netmon.py --help              # all options
```

Every 10 seconds it prints the latency, loss and jitter of that window, it
warns the moment a dropout starts and ends, and it prints a summary of the
whole run when it stops. Run it on the computer that is on the hotspot while
you play, and the timestamps tell you exactly when the connection dropped and
for how long.

### Why a 5G hotspot drops when a call comes in

On most networks 5G is "non-standalone": data goes over 5G, but voice calls
still go over 4G (VoLTE). When a call comes in, the phone leaves 5G to handle
the call and only returns afterwards, so a hotspot on that phone stalls or
drops for everything connected to it. Silencing the phone (Do Not Disturb)
does not help: the call still reaches the phone. What does help is stopping
the call *in the network*, before it reaches the phone:

- Forward all calls to voicemail: Phone app → Settings → Call forwarding →
  Always forward, or dial `**21*<voicemail number>#` (undo with `##21#`).
- Or bar all incoming calls: dial `*35*<barring password>#` (undo with
  `#35*<password>#`); not every provider supports this.
- Or keep gaming and calling apart: a data-only SIM or a 5G router for the
  games, or 5G standalone with VoNR if your provider and phone support it.
