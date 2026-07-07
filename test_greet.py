"""Tests for the greet function."""

from greet import greet


def test_greet_uses_the_name():
    assert greet("Jack") == "Hello, Jack!"


def test_greet_handles_empty_string():
    assert greet("") == "Hello, !"
