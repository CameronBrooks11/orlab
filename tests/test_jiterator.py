from orlab import JIterator


class FakeJavaIterator:
    def __init__(self, items):
        self._items = list(items)

    def hasNext(self):
        return bool(self._items)

    def __next__(self):
        return self._items.pop(0)


class FakeJavaIterable:
    """Mimics OpenRocket components: iterator(bool) returns a Java-style iterator."""

    def __init__(self, items):
        self._items = items

    def iterator(self, _include_self):
        return FakeJavaIterator(self._items)


def test_jiterator_walks_all_items():
    assert list(JIterator(FakeJavaIterable(["rocket", "stage", "fin"]))) == [
        "rocket",
        "stage",
        "fin",
    ]


def test_jiterator_empty():
    assert list(JIterator(FakeJavaIterable([]))) == []
