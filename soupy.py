from abc import ABCMeta, abstractproperty, abstractmethod
from operator import itemgetter
from itertools import imap, takewhile, dropwhile

from six import add_metaclass


@add_metaclass(ABCMeta)
class Wrappable(object):

    @abstractmethod
    def val(self):
        pass

    @abstractmethod
    def orelse(self, value):
        pass

    @abstractmethod
    def map(self, func):
        pass

    @classmethod
    def wrap(cls, value):
        """
        Wrap value in the appropriate wrapper class,
        based upon its type
        """
        if hasattr(value, 'children'):
            return Node(value)
        return Scalar(value)

    def __getitem__(self, key):
        return self.map(itemgetter(key))


class NullValueError(ValueError):
    pass


class Scalar(Wrappable):
    def __init__(self, val):
        self._val = val

    def val(self):
        return self._val

    def orelse(self, value):
        return self

    def map(self, func):
        return Scalar(func(self._val))


class Collection(Wrappable):

    def __init__(self, items):
        self._items = items

    def val(self):
        return list(self.iter_val())

    def iter_val(self):
        return (item.val() for item in self._items)

    def map(self, func):
        return Collection((item.map(func) for item in self._items))

    def filter(self, func):
        return Collection(filter(func, self._items))

    def takewhile(self, func):
        return Collection(takewhile(func, self._items))

    def dropwhile(self, func):
        return Collection(dropwhile(func, self._items))

    def orelse(self):
        raise NotImplementedError()

    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self._items)[key]

        # slice
        return Collection(list(self._items).__getitem__(key))


class NullCollection(Collection):

    def __init__(self):
        pass

    def iter_val(self):
        raise NullValueError()

    def map(self, func):
        return NullCollection()

    def filter(self, func):
        return NullCollection()

    def takewhile(self, func):
        return NullCollection()

    def dropwhile(self, func):
        return NullCollection()

    def orelse(self):
        raise NotImplementedError()

    def __getitem__(self, key):
        if isinstance(key, int):
            return NullNode()  # XXX don't like this assumption

        # slice
        return NullCollection()


@add_metaclass(ABCMeta)
class NodeLike(object):

    # should return NodeLike
    parent = abstractproperty()
    text = abstractproperty()
    attrs = abstractproperty()
    next_sibling = abstractproperty()
    previous_sibling = abstractproperty()

    # should return CollectionLike
    children = abstractproperty()
    contents = abstractproperty()
    descendants = abstractproperty()
    parents = abstractproperty()
    next_siblings = abstractproperty()
    previous_siblings = abstractproperty()

    @abstractmethod
    def find(self, name=None, attrs={}, recursive=True, text=None, **kwargs):
        pass

    #@abstractmethod
    def find_all(self, name=None, attrs={}, recursive=True, text=None, **kwargs):
        pass

    #@abstractmethod
    def select(self, selector):
        pass


class Node(NodeLike, Wrappable):

    def __init__(self, value):
        self._value = value

    def val(self):
        return self._value

    def _wrap_single(self, attr):
        val = getattr(self._value, attr)
        if val is None:
            return NullNode()
        return Node(val)

    def _wrap_multi(self, attr):
        return Collection(imap(Node, getattr(self._value, attr)))

    @property
    def children(self):
        return self._wrap_multi('children')

    @property
    def parents(self):
        return self._wrap_multi('parents')

    @property
    def contents(self):
        return self._wrap_multi('contents')

    @property
    def descendants(self):
        return self._wrap_multi('descendants')

    @property
    def next_siblings(self):
        return self._wrap_multi('next_siblings')

    @property
    def previous_siblings(self):
        return self._wrap_multi('previous_siblings')

    @property
    def parent(self):
        return self._wrap_single('parent')

    @property
    def next_sibling(self):
        return self._wrap_single('next_sibling')

    @property
    def previous_sibling(self):
        return self._wrap_single('previous_sibling')

    @property
    def attrs(self):
        return Scalar(self._value.attrs)

    @property
    def text(self):
        return Scalar(self._value.text)

    def orelse(self, value):
        return self

    def find(self, name=None, attrs={}, recursive=True, text=None, **kwargs):
        result = self._value.find(name, attrs, recursive, text, **kwargs)
        if result is not None:
            return Node(result)
        return NullNode()

    def find_all(self, name=None, attrs={}, recursive=True,
                 text=None, **kwargs):
        result = self._value.find_all(name, attrs,
                                      recursive, text, **kwargs)
        return Collection(imap(Node, result))

    def map(self, func):
        result = func(self._value)
        return Wrappable.wrap(result)


class NullNode(NodeLike, Wrappable):

    def _get_null(self):
        return NullNode()

    def _get_null_set(self):
        return Collection([])

    def orelse(self, value):
        return Node(value)

    def map(self, func):
        return NullNode()

    def val(self):
        raise NullValueError()

    children = property(_get_null_set)
    parents = property(_get_null_set)
    contents = property(_get_null_set)
    descendants = property(_get_null_set)
    next_siblings = property(_get_null_set)
    previous_siblings = property(_get_null_set)

    parent = property(_get_null)
    next_sibling = property(_get_null)
    previous_sibling = property(_get_null)

    attrs = property(lambda self: Scalar({}))
    text = property(lambda self: Scalar(''))

    def find(self, name=None, attrs={}, recursive=True, text=None, **kwargs):
        return NullNode()

    def find_all(self, name=None, attrs={},
                 recursive=True, text=None, **kwargs):
        return NullCollection()

class NodeCollection(object):

    def __init__(self, nodes, extractors=tuple()):
        self._nodes = nodes
        self._extractors = extractors

    def extract(self, name, selector):
        return NodeCollection(self._nodes, self._extractors + ((name, selector),))

    def dump(self):
        return [node._dump(self._extractors) for node in self._nodes]

    def apply(self, func):
        return NodeCollection(imap(func, self._nodes), self._extractors)

    def __iter__(self):
        return iter(self._nodes)

    def get(self):
        return [node.get() for node in self._nodes]

    def take_while(self, func):
        return NodeCollection(takewhile(lambda node: func(node).get(), self._nodes), self._extractors)

    def drop_while(self, func):
        return NodeCollection(dropwhile(lambda node: func(node).get(), self._nodes), self._extractors)

    def __getitem__(self, slc):
        if isinstance(slc, int):
            for i, val in enumerate(self._nodes):
                if i == slc:
                    return val

        return NodeCollection(list(self._nodes).__getitem__(slc), self._extractors)


class NodeWrapper(NodeLike):
    """Wrapper for BeautifulSoup tags"""

    def __init__(self, node):
        self._node = node

    @property
    def children(self):
        return NodeCollection(imap(NodeWrapper, self._node.chidren))

    @property
    def descendants(self):
        return self._node.descendants

    @property
    def parents(self):
        return self._node.parents

    @property
    def next_siblings(self):
        return self._node.next_siblings

    @property
    def previous_siblings(self):
        return self._node.previous_siblings

    def find_all(self, *args, **kwargs):
        result = self._node.find_all(*args, **kwargs)
        return NodeCollection(imap(NodeWrapper, result))

    def find(self, *args, **kwargs):
        result = self._node.find(*args, **kwargs)
        if result:
            return NodeWrapper(result)
        return NullNode()

