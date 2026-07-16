"""Takenbord voor de koelwerkplaats.

Een eerste opzet op basis van een paar ideeën:

- ``Apparaat``: een apparaat in de werkplaats, met (optioneel) garantie.
- ``Bakwagen``: bewust begrensd gehouden — alleen kenteken en maximale lading.
- ``Taak``: een taak op het takenbord, eventueel gekoppeld aan een apparaat.
- ``Takenbord``: taken toevoegen, afronden en opvragen.

``standaard_takenbord()`` geeft een bord met de voorbeeldtaken:
koelwerkbank schoonmaken, onderdelen bestellen en de technische check
van de showroom.
"""

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Apparaat:
    """Een apparaat in de werkplaats, eventueel met garantie."""

    naam: str
    garantie_tot: date | None = None

    def heeft_garantie(self, op: date | None = None) -> bool:
        """Geef aan of het apparaat op de gegeven dag nog garantie heeft.

        Zonder ``op`` wordt vandaag gebruikt. Een apparaat zonder
        garantiedatum heeft nooit garantie.
        """
        if self.garantie_tot is None:
            return False
        if op is None:
            op = date.today()
        return op <= self.garantie_tot


@dataclass
class Bakwagen:
    """De bakwagen — begrensd: alleen kenteken en maximale lading."""

    kenteken: str
    max_lading_kg: int

    def kan_laden(self, gewicht_kg: int) -> bool:
        """Geef aan of het gewicht binnen de maximale lading past."""
        return 0 <= gewicht_kg <= self.max_lading_kg


@dataclass
class Taak:
    """Een taak op het takenbord."""

    omschrijving: str
    apparaat: Apparaat | None = None
    klaar: bool = False

    def rond_af(self) -> None:
        self.klaar = True


@dataclass
class Takenbord:
    """Het takenbord in de koelwerkplaats."""

    taken: list[Taak] = field(default_factory=list)

    def voeg_toe(self, omschrijving: str, apparaat: Apparaat | None = None) -> Taak:
        """Zet een nieuwe taak op het bord en geef die terug."""
        taak = Taak(omschrijving, apparaat)
        self.taken.append(taak)
        return taak

    def rond_af(self, omschrijving: str) -> Taak:
        """Rond de eerste open taak met deze omschrijving af.

        Gooit een ``ValueError`` als er geen open taak met deze
        omschrijving op het bord staat.
        """
        for taak in self.taken:
            if taak.omschrijving == omschrijving and not taak.klaar:
                taak.rond_af()
                return taak
        raise ValueError(f"Geen open taak gevonden: {omschrijving!r}")

    def open_taken(self) -> list[Taak]:
        return [taak for taak in self.taken if not taak.klaar]

    def afgeronde_taken(self) -> list[Taak]:
        return [taak for taak in self.taken if taak.klaar]


def standaard_takenbord() -> Takenbord:
    """Maak een takenbord met de vaste voorbeeldtaken."""
    bord = Takenbord()
    bord.voeg_toe("Koelwerkbank schoonmaken")
    bord.voeg_toe("Onderdelen bestellen waar nodig")
    bord.voeg_toe("Technische check showroom")
    return bord


if __name__ == "__main__":
    bord = standaard_takenbord()
    print("Open taken op het bord:")
    for taak in bord.open_taken():
        print(f"- {taak.omschrijving}")
