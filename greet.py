"""A tiny greeting helper used for practicing the pull request workflow."""


def greet(name):
    """Return a friendly greeting for the given name.

    >>> greet("Jack")
    'Hello, Jack!'
    """
    return f"Hello, {name}!"


if __name__ == "__main__":
    print(greet("world"))
