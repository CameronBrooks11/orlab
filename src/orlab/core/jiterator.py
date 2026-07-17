__all__ = ['JIterator']


class JIterator:
    """This class is a wrapper for java iterators to allow them to be used as python iterators"""

    def __init__(self, jit):
        """Give this any java object which implements iterable"""
        self.jit = jit.iterator(True)

    def __iter__(self):
        return self

    def __next__(self):
        if not self.jit.hasNext():
            raise StopIteration()
        else:
            return next(self.jit)