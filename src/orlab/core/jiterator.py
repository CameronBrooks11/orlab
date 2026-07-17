__all__ = ["JIterator"]


class JIterator:
    """Wraps a Java iterable as a Python iterator.

    Built for walking a rocket's component tree:
    ``for component in JIterator(rocket): print(component.getName())``

    :param jit: any Java object exposing ``iterator(boolean)`` — in practice a
        ``RocketComponent`` (the boolean requests iteration over the full
        subtree, the component itself included).
    """

    def __init__(self, jit):
        self.jit = jit.iterator(True)

    def __iter__(self):
        return self

    def __next__(self):
        if not self.jit.hasNext():
            raise StopIteration()
        else:
            return next(self.jit)
