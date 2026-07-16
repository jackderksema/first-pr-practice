"""Tests voor het takenbord van de koelwerkplaats."""

from datetime import date

import pytest

from werkplaats import Apparaat, Bakwagen, standaard_takenbord


def test_standaard_takenbord_heeft_de_voorbeeldtaken():
    bord = standaard_takenbord()
    omschrijvingen = [taak.omschrijving for taak in bord.open_taken()]
    assert omschrijvingen == [
        "Koelwerkbank schoonmaken",
        "Onderdelen bestellen waar nodig",
        "Technische check showroom",
    ]


def test_taak_afronden_verplaatst_taak_naar_afgerond():
    bord = standaard_takenbord()
    bord.rond_af("Koelwerkbank schoonmaken")
    assert len(bord.open_taken()) == 2
    afgerond = bord.afgeronde_taken()
    assert len(afgerond) == 1
    assert afgerond[0].omschrijving == "Koelwerkbank schoonmaken"


def test_onbekende_taak_afronden_geeft_foutmelding():
    bord = standaard_takenbord()
    with pytest.raises(ValueError):
        bord.rond_af("Bestaat niet")


def test_taak_kan_aan_apparaat_gekoppeld_worden():
    bord = standaard_takenbord()
    werkbank = Apparaat("Koelwerkbank", garantie_tot=date(2027, 1, 1))
    taak = bord.voeg_toe("Compressor nakijken", apparaat=werkbank)
    assert taak.apparaat is werkbank


def test_apparaat_garantie():
    werkbank = Apparaat("Koelwerkbank", garantie_tot=date(2027, 1, 1))
    assert werkbank.heeft_garantie(op=date(2026, 12, 31))
    assert werkbank.heeft_garantie(op=date(2027, 1, 1))
    assert not werkbank.heeft_garantie(op=date(2027, 1, 2))


def test_apparaat_zonder_garantiedatum_heeft_geen_garantie():
    oude_koelkast = Apparaat("Oude showroomkoelkast")
    assert not oude_koelkast.heeft_garantie(op=date(2026, 1, 1))


def test_leenapparaat_uitlenen_en_terugnemen():
    leenkast = Apparaat("Leenkoelkast", is_leenapparaat=True)
    assert leenkast.is_beschikbaar()

    leenkast.leen_uit("Bakkerij Jansen")
    assert leenkast.uitgeleend_aan == "Bakkerij Jansen"
    assert not leenkast.is_beschikbaar()

    leenkast.neem_terug()
    assert leenkast.uitgeleend_aan is None
    assert leenkast.is_beschikbaar()


def test_leenapparaat_kan_niet_dubbel_uitgeleend_worden():
    leenkast = Apparaat("Leenkoelkast", is_leenapparaat=True)
    leenkast.leen_uit("Bakkerij Jansen")
    with pytest.raises(ValueError):
        leenkast.leen_uit("Slagerij de Vries")


def test_gewoon_apparaat_kan_niet_uitgeleend_worden():
    werkbank = Apparaat("Koelwerkbank")
    assert not werkbank.is_beschikbaar()
    with pytest.raises(ValueError):
        werkbank.leen_uit("Bakkerij Jansen")


def test_bakwagen_is_begrensd():
    wagen = Bakwagen(kenteken="VX-123-B", max_lading_kg=1000)
    assert wagen.kan_laden(800)
    assert wagen.kan_laden(1000)
    assert not wagen.kan_laden(1200)
    assert not wagen.kan_laden(-5)
