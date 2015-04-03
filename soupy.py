from __future__ import print_function, division, unicode_literals

from abc import ABCMeta, abstractproperty, abstractmethod
from itertools import takewhile, dropwhile
import operator

from bs4 import BeautifulSoup, PageElement, NavigableString
from six import add_metaclass
from six.moves import map as imap


@add_metaclass(ABCMeta)
class Wrapper(object):

    @abstractmethod
    def val(self):
        pass  # pragma: no cover

    @abstractmethod
    def orelse(self, value):
        pass  # pragma: no cover

    def nonnull(self):
        pass  # pragma: no cover

    @abstractmethod
    def map(self, func):
        pass  # pragma: no cover

    @abstractmethod
    def apply(self, func):
        pass  # pragma: no cover

    @classmethod
    def wrap(cls, value):
        """
        Wrap value in the appropriate wrapper class,
        based upon its type
        """
        if isinstance(value, Wrapper):
            return value

        if hasattr(value, 'children'):
            return Node(value)

        return Scalar(value)

    def __getitem__(self, key):
        return self.map(operator.itemgetter(key))


class NullValueError(ValueError):
    pass


class Null(Wrapper):

    def val(self):
        raise NullValueError()

    def orelse(self, value):
        return Wrapper.wrap(value)

    def map(self, func):
        return self

    def apply(self, func):
        return self

    def nonnull(self):
        raise NullValueError()

    def __bool__(self):
        return False

    __nonzero__ = __bool__


class Some(Wrapper):

    def __init__(self, value):
        self._value = value

    def map(self, func):
        return Wrapper.wrap(_make_callable(func)(self._value))

    def apply(self, func):
        return Wrapper.wrap(_make_callable(func)(self))

    def orelse(self, value):
        return self

    def val(self):
        return self._value


class Scalar(Some):

    def __getattr__(self, attr):
        return self.map(operator.attrgetter(attr))

    def __call__(self, *args, **kwargs):
        return self.map(operator.methodcaller('__call__', *args, **kwargs))

    def __eq__(self, other):
        return self.map(operator.methodcaller('__eq__', other))

    def __ne__(self, other):
        return self.map(operator.methodcaller('__ne__', other))

    def __gt__(self, other):
        return self.map(lambda x: x > other)

    def __ge__(self, other):
        return self.map(lambda x: x >= other)

    def __lt__(self, other):
        return self.map(lambda x: x < other)

    def __le__(self, other):
        return self.map(lambda x: x <= other)

    def __bool__(self):
        return bool(self._value)

    __nonzero__ = __bool__


class Collection(Some):

    def __init__(self, items):
        super(Collection, self).__init__(list(items))
        self._items = self._value

    def val(self):
        return list(self.iter_val())

    def first(self):
        return self[0]

    def iter_val(self):
        return (item.val() for item in self._items)

    def each(self, func):
        func = _make_callable(func)
        return Collection(imap(func, self._items))

    def filter(self, func):
        func = _make_callable(func)
        return Collection(filter(func, self._items))

    def takewhile(self, func):
        func = _make_callable(func)
        return Collection(takewhile(func, self._items))

    def dropwhile(self, func):
        func = _make_callable(func)
        return Collection(dropwhile(func, self._items))

    def __getitem__(self, key):
        if isinstance(key, int):
            try:
                return self._items[key]
            except IndexError:
                return NullNode()

        # slice
        return Collection(list(self._items).__getitem__(key))

    def dump(self, *args, **kwargs):
        return self.each(Q._dump(**kwargs)).val()

    def __len__(self):
        return self.map(len).val()


class NullCollection(Null, Collection):

    def __init__(self):
        pass

    def iter_val(self):
        raise NullValueError()

    def each(self, func):
        return self

    def filter(self, func):
        return self

    def takewhile(self, func):
        return self

    def dropwhile(self, func):
        return self

    def first(self):
        return NullNode()  # XXX don't like this assumption

    def __getitem__(self, key):
        if isinstance(key, int):
            return NullNode()  # XXX don't like this assumption

        # slice
        return self

    def dump(self):
        raise NullValueError()


@add_metaclass(ABCMeta)
class NodeLike(object):

    # should return NodeLike
    parent = abstractproperty()
    next_sibling = abstractproperty()
    previous_sibling = abstractproperty()

    # should return scalar-like
    text = abstractproperty()
    attrs = abstractproperty()
    name = abstractproperty()

    # should return CollectionLike
    children = abstractproperty()
    contents = abstractproperty()
    descendants = abstractproperty()
    parents = abstractproperty()
    next_siblings = abstractproperty()
    previous_siblings = abstractproperty()

    @abstractmethod
    def find(self, name=None, attrs={}, recursive=True,
             text=None, **kwargs):
        pass  # pragma: no cover

    @abstractmethod
    def find_all(self, name=None, attrs={}, recursive=True,
                 text=None, **kwargs):
        pass  # pragma: no cover

    @abstractmethod
    def select(self, selector):
        pass  # pragma: no cover

    @abstractmethod
    def find_next_sibling(self, *args, **kwargs):
        pass  # pragma: no cover

    @abstractmethod
    def find_previous_sibling(self, *args, **kwargs):
        pass  # pragma: no cover

    @abstractmethod
    def find_parent(self, *args, **kwargs):
        pass  # pragma: no cover

    @abstractmethod
    def find_next_siblings(self, *args, **kwargs):
        pass  # pragma: no cover

    @abstractmethod
    def find_previous_siblings(self, *args, **kwargs):
        pass  # pragma: no cover

    @abstractmethod
    def find_parents(self, *args, **kwargs):
        pass  # pragma: no cover


class Node(NodeLike, Some):

    def __new__(cls, value):
        if isinstance(value, NavigableString):
            return object.__new__(NavigableStringNode)

        return object.__new__(cls)

    def _wrap_node(self, func):
        val = func(self._value)
        return NullNode() if val is None else Node(val)

    def _wrap_multi(self, func):
        vals = func(self._value)
        return Collection(imap(Node, vals))

    def _wrap_scalar(self, func):
        val = func(self._value)
        return Scalar(val)

    @property
    def children(self):
        return self._wrap_multi(operator.attrgetter('children'))

    @property
    def parents(self):
        return self._wrap_multi(operator.attrgetter('parents'))

    @property
    def contents(self):
        return self._wrap_multi(operator.attrgetter('contents'))

    @property
    def descendants(self):
        return self._wrap_multi(operator.attrgetter('descendants'))

    @property
    def next_siblings(self):
        return self._wrap_multi(operator.attrgetter('next_siblings'))

    @property
    def previous_siblings(self):
        return self._wrap_multi(operator.attrgetter('previous_siblings'))

    @property
    def parent(self):
        return self._wrap_node(operator.attrgetter('parent'))

    @property
    def next_sibling(self):
        return self._wrap_node(operator.attrgetter('next_sibling'))

    @property
    def previous_sibling(self):
        return self._wrap_node(operator.attrgetter('previous_sibling'))

    @property
    def attrs(self):
        return self._wrap_scalar(operator.attrgetter('attrs'))

    @property
    def text(self):
        return self._wrap_scalar(operator.attrgetter('text'))

    @property
    def name(self):
        return self._wrap_scalar(operator.attrgetter('name'))

    def find(self, *args, **kwargs):
        op = operator.methodcaller('find', *args, **kwargs)
        return self._wrap_node(op)

    def find_next_sibling(self, *args, **kwargs):
        op = operator.methodcaller('find_next_sibling', *args, **kwargs)
        return self._wrap_node(op)

    def find_parent(self, *args, **kwargs):
        op = operator.methodcaller('find_parent', *args, **kwargs)
        return self._wrap_node(op)

    def find_previous_sibling(self, *args, **kwargs):
        op = operator.methodcaller('find_previous_sibling', *args, **kwargs)
        return self._wrap_node(op)

    def find_all(self, *args, **kwargs):
        op = operator.methodcaller('find_all', *args, **kwargs)
        return self._wrap_multi(op)

    def find_next_siblings(self, *args, **kwargs):
        op = operator.methodcaller('find_next_siblings', *args, **kwargs)
        return self._wrap_multi(op)

    def find_parents(self, *args, **kwargs):
        op = operator.methodcaller('find_parents', *args, **kwargs)
        return self._wrap_multi(op)

    def find_previous_siblings(self, *args, **kwargs):
        op = operator.methodcaller('find_previous_siblings', *args, **kwargs)
        return self._wrap_multi(op)

    def select(self, selector):
        op = operator.methodcaller('select', selector)
        return self._wrap_multi(op)

    def _dump(self, **kwargs):
        result = dict((name, _make_callable(func)(self).val())
                      for name, func in kwargs.items())
        return Wrapper.wrap(result)


class NavigableStringNode(Node):

    @property
    def attrs(self):
        return Scalar({})

    @property
    def text(self):
        return Scalar(self._value.string)

    @property
    def name(self):
        return Scalar('')

    @property
    def children(self):
        return Collection([])

    @property
    def contents(self):
        return Collection([])

    @property
    def descendants(self):
        return Collection([])

    def find(self, *args, **kwargs):
        return NullNode()

    def find_all(self, *args, **kwargs):
        return Collection([])

    def select(self, selector):
        return Collection([])


class NullNode(NodeLike, Null):

    def _get_null(self):
        return NullNode()

    def _get_null_set(self):
        return NullCollection()

    children = property(_get_null_set)
    parents = property(_get_null_set)
    contents = property(_get_null_set)
    descendants = property(_get_null_set)
    next_siblings = property(_get_null_set)
    previous_siblings = property(_get_null_set)

    parent = property(_get_null)
    next_sibling = property(_get_null)
    previous_sibling = property(_get_null)

    attrs = property(lambda self: Null())
    text = property(lambda self: Null())
    name = property(lambda self: Null())

    def find(self, *args, **kwargs):
        return NullNode()

    def find_parent(self, *args, **kwargs):
        return NullNode()

    def find_previous_sibling(self, *args, **kwargs):
        return NullNode()

    def find_next_sibling(self, *args, **kwargs):
        return NullNode()

    def find_all(self, *args, **kwargs):
        return NullCollection()

    def find_parents(self, *args, **kwargs):
        return NullCollection()

    def find_next_siblings(self, *args, **kwargs):
        return NullCollection()

    def find_previous_siblings(self, *args, **kwargs):
        return NullCollection()

    def select(self, selector):
        return NullCollection()


def either(*funcs):

    def either(val):
        for func in funcs:
            result = val.apply(func)
            if result:
                return result
        return Null()

    return either


class Expression(object):

    def _chain(self, other):
        ops = []
        if isinstance(self, Chain):
            ops = self._items
        else:
            ops = [self]
        if isinstance(other, Chain):
            ops.extend(other._items)
        else:
            ops.append(other)

        return Chain(ops)

    def __getattr__(self, key):
        return self._chain(Attr(key))

    def __getitem__(self, key):
        return self._chain(GetItem(key))

    def __call__(self, *args, **kwargs):
        return self._chain(Call(args, kwargs))

    def __gt__(self, other):
        return BinaryOp(operator.gt, self, other)

    def __ge__(self, other):
        return BinaryOp(operator.ge, self, other)

    def __lt__(self, other):
        return BinaryOp(operator.lt, self, other)

    def __le__(self, other):
        return BinaryOp(operator.le, self, other)

    def __eq__(self, other):
        return BinaryOp(operator.eq, self, other)

    def __ne__(self, other):
        return BinaryOp(operator.ne, self, other)

    def __eval__(self, val):
        return val


class Call(Expression):

    def __init__(self, args, kwargs):
        self._args = args
        self._kwargs = kwargs

    def __eval__(self, val):
        return val.__call__(*self._args, **self._kwargs)


class BinaryOp(Expression):

    def __init__(self, op, left, right):
        self.op = op
        self.left = left
        self.right = right

    def __eval__(self, val):
        left = self.left
        right = self.right
        if isinstance(left, Expression):
            left = left.__eval__(val)

        if isinstance(right, Expression):
            right = right.__eval__(val)

        return self.op(left, right)


class Attr(Expression):

    def __init__(self, attribute_name):
        self._name = attribute_name

    def __eval__(self, val):
        return operator.attrgetter(self._name)(val)


class GetItem(Expression):

    def __init__(self, key):
        self._name = key

    def __eval__(self, val):
        return operator.itemgetter(self._name)(val)


class Chain(Expression):

    def __init__(self, items):
        self._items = items

    def __eval__(self, val):
        for item in self._items:
            val = item.__eval__(val)
        return val


def _make_callable(func):
    # If func is an expression, we call via __eval__
    # otherwise, we call func directly
    return getattr(func, '__eval__', func)


class Soupy(Node):

    def __init__(self, val):
        if not isinstance(val, PageElement):
            val = BeautifulSoup(val)
        super(Soupy, self).__init__(val)


Q = Expression()
