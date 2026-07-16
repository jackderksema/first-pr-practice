# first-pr-practice

A tiny practice project for learning the GitHub pull request workflow.

It contains one small function, `greet`, in [`greet.py`](greet.py).

## Usage

```python
from greet import greet

print(greet("Jack"))   # -> "Hello, Jack!"
```

## Takenbord koelwerkplaats

[`werkplaats.py`](werkplaats.py) bevat een eerste opzet van een takenbord
voor de koelwerkplaats: apparaten met garantie (waaronder leenapparaten
die je aan een klant kunt uitlenen), een (bewust begrensde) bakwagen en
een takenbord met voorbeeldtaken.

```python
from werkplaats import standaard_takenbord

bord = standaard_takenbord()
bord.rond_af("Koelwerkbank schoonmaken")
print([taak.omschrijving for taak in bord.open_taken()])
```

## Running the tests

```bash
python -m pytest
```
