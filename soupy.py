from __future__ import print_function, division, unicode_literals

from abc import ABCMeta, abstractproperty, abstractmethod
from collections import namedtuple
from functools import wraps
from itertools import takewhile, dropwhile
import operator
import re
import sys

from bs4 import BeautifulSoup, PageElement, NavigableString
import six
from six.moves import map

__version__ = '0.3'

__all__ = ['Soupy', 'Q', 'Node', 'Scalar', 'Collection',
           'Null', 'NullNode', 'NullCollection',
           'either', 'NullValueError', 'QDebug']


# extract the thing inside string reprs (eg u'abc' -> abc)
QUOTED_STR = re.compile("^[ub]?['\"](.*?)['\"]$")

QDebug = namedtuple('QDebug', ('expr', 'inner_expr', 'val', 'inner_val'))
"""Namedtuple that holds information about a failed expression evaluation."""


@six.add_metaclass(ABCMeta)
class Wrapper(object):

    @abstractmethod
    def val(self):
        pass  # pragma: no cover

    @abstractmethod
    def orelse(self, value):
        pass  # pragma: no cover

    def nonnull(self):
        """
        Require that a node is not null

        Null values will raise NullValueError, whereas nonnull
        values return self.

        useful for being strict about portions of queries.


        Examples:

           node.find('a').nonnull().find('b').orelse(3)

           This will raise an error if find('a') doesn't match,
           but provides a fallback if find('b') doesn't match.

        """
        return self

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
        based upon its type.
        """
        if isinstance(value, Wrapper):
            return value

        if hasattr(value, 'children'):
            return Node(value)

        return Scalar(value)

    def __getitem__(self, key):
        return self.map(operator.itemgetter(key))

    def dump(self, **kwargs):
        """
        Extract derived values into a Scalar(dict)

        The keyword names passed to this function become keys in
        the resulting dictionary.

        The keyword values are functions that are called on this Node.

        Notes:

            - The input functions are called on the Node, **not** the
              underlying BeautifulSoup element
            - If the function returns a wrapper, it will be unwrapped

        Example:

            >>> soup = Soupy("<b>hi</b>").find('b')
            >>> data = soup.dump(name=Q.name, text=Q.text).val()
            >>> data == {'text': 'hi', 'name': 'b'}
            True
        """
        result = dict((name, _unwrap(self.apply(func)))
                      for name, func in kwargs.items())
        return Wrapper.wrap(result)

    @abstractmethod
    def require(self, func, msg='Requirement Violated'):
        pass  # pragma: no cover


class NullValueError(ValueError):

    """
    The NullValueError exception is raised when attempting
    to extract values from Null objects
    """
    pass


class QKeyError(KeyError):

    """
    A custom KeyError subclass that better formats
    exception messages raised inside expressions
    """

    def __str__(self):
        parts = self.args[0].split('\n\n\t')
        return parts[0] + '\n\n\t' + _dequote(repr(parts[1]))

QKeyError.__name__ = str('KeyError')


@six.python_2_unicode_compatible
class BaseNull(Wrapper):

    """
    This is the base class for null wrappers. Null values are returned
    when the result of a function is ill-defined.
    """

    def val(self):
        """
        Raise :class:`NullValueError`
        """
        raise NullValueError()

    def orelse(self, value):
        """
        Wraps value and returns the result
        """
        return Wrapper.wrap(value)

    def map(self, func):
        """
        Returns :class:`Null`
        """
        return self

    def apply(self, func):
        """
        Returns :class:`Null`
        """
        return self

    def nonnull(self):
        """
        Raises :class:`NullValueError`
        """
        raise NullValueError()

    def require(self, func, msg="Requirement is violated (wrapper is null)"):
        """
        Raises :class:`NullValueError`
        """
        raise NullValueError()

    def __setitem__(self, key, val):
        pass

    def __bool__(self):
        return False

    __nonzero__ = __bool__

    def __str__(self):
        return "%s()" % type(self).__name__

    __repr__ = __str__

    def __hash__(self):
        return hash(type(self))

    def __eq__(self, other):
        return type(self)()

    def __ne__(self, other):
        return type(self)()


@six.python_2_unicode_compatible
class Some(Wrapper):

    def __init__(self, value):
        self._value = value

    def map(self, func):
        """
        Call a function on a wrapper's value, and wrap the result if necessary.

        Parameters:

            func : function(val) -> val

        Examples:

            >>> s = Scalar(3)
            >>> s.map(Q * 2)
            Scalar(6)
        """
        return Wrapper.wrap(_make_callable(func)(self._value))

    def apply(self, func):
        """
        Call a function on a wrapper, and wrap the result if necessary.


        Parameters:

            func: function(wrapper) -> val

        Examples:

            >>> s = Scalar(5)
            >>> s.apply(lambda val: isinstance(val, Scalar))
            Scalar(True)
        """
        return Wrapper.wrap(_make_callable(func)(self))

    def orelse(self, value):
        """
        Provide a fallback value for failed matches.

        Examples:

            >>> Scalar(5).orelse(10).val()
            5
            >>> Null().orelse(10).val()
            10
        """
        return self

    def val(self):
        """
        Return the value inside a wrapper.

        Raises :class:`NullValueError` if called on a Null object
        """
        return self._value

    def require(self, func, msg="Requirement violated"):
        """
        Assert that self.apply(func) is True.

        Parameters:

            func : func(wrapper)
            msg : str
               The error message to display on failure

        Returns:

            If self.apply(func) is True, returns self.
            Otherwise, raises NullValueError.
        """
        if self.apply(func):
            return self
        raise NullValueError(msg)

    def __str__(self):
        # returns unicode
        # six builds appropriate py2/3 methods from this
        return "%s(%s)" % (type(self).__name__, _repr(self._value))

    def __repr__(self):
        return repr(self.__str__())[1:-1]  # trim off quotes

    def __setitem__(self, key, val):
        return self.map(Q.__setitem__(key, val))

    def __hash__(self):
        return hash(self._value)

    def __eq__(self, other):
        return self.map(lambda x: x == other)

    def __ne__(self, other):
        return self.map(lambda x: x != other)


class Null(BaseNull):

    """
    The class for ill-defined Scalars.
    """

    def __getattr__(self, attr):
        return Null()

    def __call__(self, *args, **kwargs):
        return Null()

    def __gt__(self, other):
        return Null()

    def __ge__(self, other):
        return Null()

    def __lt__(self, other):
        return Null()

    def __le__(self, other):
        return Null()

    def __len__(self):
        raise TypeError("Null has no len()")

    def __add__(self, other):
        return Null()

    def __sub__(self, other):
        return Null()

    def __mul__(self, other):
        return Null()

    def __div__(self, other):
        return Null()

    def __floordiv__(self, other):
        return Null()

    def __pow__(self, other):
        return Null()

    def __mod__(self, other):
        return Null()

    def __truediv__(self, other):
        return Null()

    def __hash__(self):
        return super(Null, self).__hash__()


class Scalar(Some):

    """
    A wrapper around single values.

    Scalars support boolean testing (<, ==, etc), and
    use the wrapped value in the comparison. They return
    the result as a Scalar(bool).

    Calling a Scalar calls the wrapped value, and wraps
    the result.

    Examples:

        >>> s = Scalar(3)
        >>> s > 2
        Scalar(True)
        >>> s.val()
        3
        >>> s + 5
        Scalar(8)
        >>> s + s
        Scalar(6)
        >>> bool(Scalar(3))
        True
        >>> Scalar(lambda x: x+2)(5)
        Scalar(7)

    """

    def __getattr__(self, attr):
        return self.map(operator.attrgetter(attr))

    def __call__(self, *args, **kwargs):
        return self.map(operator.methodcaller('__call__', *args, **kwargs))

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

    def __len__(self):
        return len(self._value)

    def __add__(self, other):
        if isinstance(other, BaseNull):
            return other
        return self.map(Q + _unwrap(other))

    def __sub__(self, other):
        if isinstance(other, BaseNull):
            return other
        return self.map(Q - _unwrap(other))

    def __mul__(self, other):
        if isinstance(other, BaseNull):
            return other
        return self.map(Q * _unwrap(other))

    def __div__(self, other):
        if isinstance(other, BaseNull):
            return other
        return self.map(Q / _unwrap(other))

    def __floordiv__(self, other):
        if isinstance(other, BaseNull):
            return other
        return self.map(Q // _unwrap(other))

    def __pow__(self, other):
        if isinstance(other, BaseNull):
            return other
        return self.map(Q ** _unwrap(other))

    def __mod__(self, other):
        if isinstance(other, BaseNull):
            return other
        return self.map(Q % _unwrap(other))

    def __truediv__(self, other):
        if isinstance(other, BaseNull):
            return other
        return self.map(Q / _unwrap(other))


class Collection(Some):

    """
    Collection's store lists of other wrappers.

    They support most of the list methods (len, iter, getitem, etc).
    """

    def __init__(self, items):
        super(Collection, self).__init__(list(items))
        self._items = self._value
        self._assert_items_are_wrappers()

    def _assert_items_are_wrappers(self):
        for item in self:
            if not isinstance(item, Wrapper):
                raise TypeError("Collection can only hold other wrappers")

    def val(self):
        """
        Unwraps each item in the collection, and returns as a list
        """
        return list(self.iter_val())

    def first(self):
        """
        Return the first element of the collection, or :class:`Null`
        """
        return self[0]

    def iter_val(self):
        """
        An iterator version of :meth:`val`
        """
        return (item.val() for item in self._items)

    def each(self, *funcs):
        """
        Call `func` on each element in the collection.

        If multiple functions are provided, each item
        in the output will be a tuple of each
        func(item) in self.

        Returns a new Collection.

        Example:

            >>> col = Collection([Scalar(1), Scalar(2)])
            >>> col.each(Q * 10)
            Collection([Scalar(10), Scalar(20)])
            >>> col.each(Q * 10, Q - 1)
            Collection([Scalar((10, 0)), Scalar((20, 1))])
        """

        funcs = list(map(_make_callable, funcs))

        if len(funcs) == 1:
            return Collection(map(funcs[0], self._items))

        tupler = lambda item: Scalar(
            tuple(_unwrap(func(item)) for func in funcs))
        return Collection(map(tupler, self._items))

    def filter(self, func):
        """
        Return a new Collection with some items removed.

        Parameters:

            func : function(Node) -> Node

        Returns:

            A new Collection consisting of the items
            where bool(func(item)) == True

        Examples:

            node.find_all('a').filter(Q['href'].startswith('http'))
        """
        func = _make_callable(func)
        return Collection(filter(func, self._items))

    def takewhile(self, func):
        """
        Return a new Collection with the last few items removed.

        Parameters:

            func : function(Node) -> Node

        Returns:

            A new Collection, discarding all items
            at and after the first item where bool(func(item)) == False

        Examples:

            node.find_all('tr').takewhile(Q.find_all('td').count() > 3)

        """
        func = _make_callable(func)
        return Collection(takewhile(func, self._items))

    def dropwhile(self, func):
        """
        Return a new Collection with the first few items removed.

        Parameters:

            func : function(Node) -> Node

        Returns:

            A new Collection, discarding all items
            before the first item where bool(func(item)) == True
        """
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
        """
        Build a list of dicts, by calling :meth:`Node.dump`
        on each item.

        Each keyword provides a function that extracts a value
        from a Node.

        Examples:

            >>> c = Collection([Scalar(1), Scalar(2)])
            >>> c.dump(x2=Q*2, m1=Q-1).val()
            [{'x2': 2, 'm1': 0}, {'x2': 4, 'm1': 1}]
        """
        return self.each(Q.dump(**kwargs))

    def __len__(self):
        return self.map(len).val()

    def count(self):
        """
        Return the number of items in the collection, as a :class:`Scalar`
        """
        return Scalar(len(self))

    def zip(self, *others):
        """
        Zip the items of this collection with one or more
        other sequences, and wrap the result.

        Unlike Python's zip, all sequences must be the same length.

        Parameters:

            others: One or more iterables or Collections

        Returns:

            A new collection.

        Examples:

            >>> c1 = Collection([Scalar(1), Scalar(2)])
            >>> c2 = Collection([Scalar(3), Scalar(4)])
            >>> c1.zip(c2).val()
            [(1, 3), (2, 4)]
        """
        args = [_unwrap(item) for item in (self,) + others]
        ct = self.count()
        if not all(len(arg) == ct for arg in args):
            raise ValueError("Arguments are not all the same length")
        return Collection(map(Wrapper.wrap, zip(*args)))

    def dictzip(self, keys):
        """
        Turn this collection into a Scalar(dict), by zipping keys and items.

        Parameters:

            keys: list or Collection of NavigableStrings
                The keys of the dictionary

        Examples:

            >>> c = Collection([Scalar(1), Scalar(2)])
            >>> c.dictzip(['a', 'b']).val() == {'a': 1, 'b': 2}
            True
        """
        return Scalar(dict(zip(_unwrap(keys), self.val())))

    def __iter__(self):
        for item in self._items:
            yield item

    def all(self):
        """
        Scalar(True) if all items are truthy, or collection is empty.
        """
        return self.map(all)

    def any(self):
        """
        Scalar(True) if any items are truthy. False if empty.
        """
        return self.map(any)

    def none(self):
        """
        Scalar(True) if no items are truthy, or collection is empty.
        """
        return self.map(lambda items: not any(items))

    def __bool__(self):
        return bool(self._items)

    __nonzero__ = __bool__


class NullCollection(BaseNull, Collection):

    """
    Represents in invalid Collection.

    Returned by some methods on other Null objects.
    """

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

    def dump(self, **kwargs):
        return NullCollection()

    def count(self):
        return Scalar(0)


@six.add_metaclass(ABCMeta)
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

    @abstractmethod
    def prettify(self):
        pass  # pragma: no cover

    def __iter__(self):
        for item in self.children:
            yield item

    def __call__(self, *args, **kwargs):
        return self.find_all(*args, **kwargs)


class Node(NodeLike, Some):

    """
    The Node class is the main wrapper around
    BeautifulSoup elements like Tag. It implements many of the
    same properties and methods as BeautifulSoup for navigating
    through documents, like find, select, parents, etc.
    """
    def __new__(cls, value, *args, **kwargs):
        if isinstance(value, NavigableString):
            return object.__new__(NavigableStringNode)

        return object.__new__(cls)

    def _wrap_node(self, func):
        val = func(self._value)
        return NullNode() if val is None else Node(val)

    def _wrap_multi(self, func):
        vals = func(self._value)
        return Collection(map(Node, vals))

    def _wrap_scalar(self, func):
        val = func(self._value)
        return Scalar(val)

    @property
    def children(self):
        """
        A :class:`Collection` of the child elements.
        """
        return self._wrap_multi(operator.attrgetter('children'))

    @property
    def parents(self):
        """
        A :class:`Collection` of the parents elements.
        """
        return self._wrap_multi(operator.attrgetter('parents'))

    @property
    def contents(self):
        """
        A :class:`Collection` of the child elements.
        """
        return self._wrap_multi(operator.attrgetter('contents'))

    @property
    def descendants(self):
        """
        A :class:`Collection` of all elements nested inside this Node.
        """
        return self._wrap_multi(operator.attrgetter('descendants'))

    @property
    def next_siblings(self):
        """
        A :class:`Collection` of all siblings after this node
        """
        return self._wrap_multi(operator.attrgetter('next_siblings'))

    @property
    def previous_siblings(self):
        """
        A :class:`Collection` of all siblings before this node
        """
        return self._wrap_multi(operator.attrgetter('previous_siblings'))

    @property
    def parent(self):
        """
        The parent :class:`Node`, or :class:`NullNode`
        """
        return self._wrap_node(operator.attrgetter('parent'))

    @property
    def next_sibling(self):
        """
        The :class:`Node` sibling after this, or :class:`NullNode`
        """
        return self._wrap_node(operator.attrgetter('next_sibling'))

    @property
    def previous_sibling(self):
        """
        The :class:`Node` sibling prior to this, or :class:`NullNode`
        """
        return self._wrap_node(operator.attrgetter('previous_sibling'))

    @property
    def attrs(self):
        """
        A :class:`Scalar` of this Node's attribute dictionary

        Example:

            >>> Soupy("<a val=3></a>").find('a').attrs
            Scalar({'val': '3'})
        """
        return self._wrap_scalar(operator.attrgetter('attrs'))

    @property
    def text(self):
        """
        A :class:`Scalar` of this Node's text.

        Example:

            >>> node = Soupy('<p>hi there</p>').find('p')
            >>> node
            Node(<p>hi there</p>)
            >>> node.text
            Scalar(u'hi there')

        """
        return self._wrap_scalar(operator.attrgetter('text'))

    @property
    def name(self):
        """
        A :class:`Scalar` of this Node's tag name.

        Example:

            >>> node = Soupy('<p>hi there</p>').find('p')
            >>> node
            Node(<p>hi there</p>)
            >>> node.name
            Scalar('p')
        """
        return self._wrap_scalar(operator.attrgetter('name'))

    def find(self, *args, **kwargs):
        """
        Find a single Node among this Node's descendants.

        Returns :class:`NullNode` if nothing matches.

        This inputs to this function follow the same semantics
        as BeautifulSoup. See http://bit.ly/bs4doc for more info.

        Examples:

         - node.find('a')  # look for `a` tags
         - node.find('a', 'foo') # look for `a` tags with class=`foo`
         - node.find(func) # find tag where func(tag) is True
         - node.find(val=3)  # look for tag like <a, val=3>
        """
        op = operator.methodcaller('find', *args, **kwargs)
        return self._wrap_node(op)

    def find_next_sibling(self, *args, **kwargs):
        """
        Like :meth:`find`, but searches through :attr:`next_siblings`
        """
        op = operator.methodcaller('find_next_sibling', *args, **kwargs)
        return self._wrap_node(op)

    def find_parent(self, *args, **kwargs):
        """
        Like :meth:`find`, but searches through :attr:`parents`
        """
        op = operator.methodcaller('find_parent', *args, **kwargs)
        return self._wrap_node(op)

    def find_previous_sibling(self, *args, **kwargs):
        """
        Like :meth:`find`, but searches through :attr:`previous_siblings`
        """
        op = operator.methodcaller('find_previous_sibling', *args, **kwargs)
        return self._wrap_node(op)

    def find_all(self, *args, **kwargs):
        """
        Like :meth:`find`, but selects all matches (not just the first one).

        Returns a :class:`Collection`.

        If no elements match, this returns a Collection with no items.
        """
        op = operator.methodcaller('find_all', *args, **kwargs)
        return self._wrap_multi(op)

    def find_next_siblings(self, *args, **kwargs):
        """
        Like :meth:`find_all`, but searches through :attr:`next_siblings`
        """
        op = operator.methodcaller('find_next_siblings', *args, **kwargs)
        return self._wrap_multi(op)

    def find_parents(self, *args, **kwargs):
        """
        Like :meth:`find_all`, but searches through :attr:`parents`
        """
        op = operator.methodcaller('find_parents', *args, **kwargs)
        return self._wrap_multi(op)

    def find_previous_siblings(self, *args, **kwargs):
        """
        Like :meth:`find_all`, but searches through :attr:`previous_siblings`
        """
        op = operator.methodcaller('find_previous_siblings', *args, **kwargs)
        return self._wrap_multi(op)

    def select(self, selector):
        """
        Like :meth:`find_all`, but takes a CSS selector string as input.
        """
        op = operator.methodcaller('select', selector)
        return self._wrap_multi(op)

    def prettify(self):
        return self.map(Q.prettify()).val()

    def __len__(self):
        return len(self._value)

    def __bool__(self):
        return True

    __nonzero__ = __bool__


class NavigableStringNode(Node):

    """
    The NavigableStringNode is a special case Node that wraps
    BeautifulSoup NavigableStrings. This class implements sensible
    versions of properties and methods that are missing from
    the NavigableString object.
    """

    @property
    def attrs(self):
        """
        An empty :class:`Scalar` dict
        """
        return Scalar({})

    @property
    def text(self):
        """
        A :class:`Scalar` of the string value
        """
        return Scalar(self._value.string)

    @property
    def name(self):
        """
        An empty :class:`Scalar` dict
        """
        return Scalar('')

    @property
    def children(self):
        """
        An empty :class:`Collection`
        """
        return Collection([])

    @property
    def contents(self):
        """
        An empty :class:`Collection`
        """
        return Collection([])

    @property
    def descendants(self):
        """
        An empty :class:`Collection`
        """
        return Collection([])

    def find(self, *args, **kwargs):
        """
        Returns :class:`NullNode`
        """
        return NullNode()

    def find_all(self, *args, **kwargs):
        """
        Returns an empty :class:`Collection`
        """
        return Collection([])

    def select(self, selector):
        """
        Returns an empty :class:`Collection`
        """
        return Collection([])

    def prettify(self):
        return self.text.val()


class NullNode(NodeLike, BaseNull):

    """
    NullNode is returned when a query doesn't match any node
    in the document.
    """

    def _get_null(self):
        """
        Returns the NullNode
        """
        return NullNode()

    def _get_null_set(self):
        """
        Returns the NullCollection
        """
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
        """
        Returns :class:`NullNode`
        """
        return NullNode()

    def find_parent(self, *args, **kwargs):
        """
        Returns :class:`NullNode`
        """
        return NullNode()

    def find_previous_sibling(self, *args, **kwargs):
        """
        Returns :class:`NullNode`
        """
        return NullNode()

    def find_next_sibling(self, *args, **kwargs):
        """
        Returns :class:`NullNode`
        """
        return NullNode()

    def find_all(self, *args, **kwargs):
        """
        Returns :class:`NullCollection`
        """
        return NullCollection()

    def find_parents(self, *args, **kwargs):
        """
        Returns :class:`NullCollection`
        """
        return NullCollection()

    def find_next_siblings(self, *args, **kwargs):
        """
        Returns :class:`NullCollection`
        """
        return NullCollection()

    def find_previous_siblings(self, *args, **kwargs):
        """
        Returns :class:`NullCollection`
        """
        return NullCollection()

    def select(self, selector):
        """
        Returns :class:`NullCollection`
        """
        return NullCollection()

    def dump(self, **kwargs):
        """
        Returns :class:`Null`
        """
        return Null()

    def prettify(self):
        return "Null Node"

    def __len__(self):
        return 0


def either(*funcs):
    """
    A utility function for selecting the first non-null query.

    Parameters:

      funcs: One or more functions

    Returns:

       A function that, when called with a :class:`Node`, will
       pass the input to each `func`, and return the first non-Falsey
       result.

    Examples:

       >>> s = Soupy("<p>hi</p>")
       >>> s.apply(either(Q.find('a'), Q.find('p').text))
       Scalar('hi')
    """
    def either(val):
        for func in funcs:
            result = val.apply(func)
            if result:
                return result
        return Null()

    return either


def _helpful_failure(method):
    """
    Decorator for eval_ that prints a helpful error message
    if an exception is generated in a Q expression
    """

    @wraps(method)
    def wrapper(self, val):
        try:
            return method(self, val)
        except:
            exc_cls, inst, tb = sys.exc_info()

            if hasattr(inst, '_RERAISE'):
                _, expr, _, inner_val = Q.__debug_info__
                Q.__debug_info__ = QDebug(self, expr, val, inner_val)
                raise

            if issubclass(exc_cls, KeyError):  # Overrides formatting
                exc_cls = QKeyError

            # Show val, unless it's too long
            prettyval = repr(val)
            if len(prettyval) > 150:
                prettyval = "<%s instance>" % (type(val).__name__)

            msg = "{0}\n\n\tEncountered when evaluating {1}{2}".format(
                inst, prettyval, self)

            new_exc = exc_cls(msg)
            new_exc._RERAISE = True
            Q.__debug_info__ = QDebug(self, self, val, val)

            six.reraise(exc_cls, new_exc, tb)

    return wrapper


@six.python_2_unicode_compatible
class Expression(object):

    """
    Soupy expressions are a shorthand for building single-argument functions.

    Users should use the ``Q`` object, which is just an instance of Expression.
    """

    def __str__(self):
        return 'Q'

    def __repr__(self):
        return repr(str(self))[1:-1]  # trim quotes

    def __iter__(self):
        yield self

    def _chain(self, other):
        return Chain(tuple(iter(self)) + tuple(iter(other)))

    def __getattr__(self, key):
        return self._chain(Attr(key))

    def __getitem__(self, key):
        return self._chain(GetItem(key))

    def __call__(self, *args, **kwargs):
        return self._chain(Call(args, kwargs))

    def __gt__(self, other):
        return BinaryOp(operator.gt, '>', self, other)

    def __ge__(self, other):
        return BinaryOp(operator.ge, '>=', self, other)

    def __lt__(self, other):
        return BinaryOp(operator.lt, '<', self, other)

    def __le__(self, other):
        return BinaryOp(operator.le, '<=', self, other)

    def __eq__(self, other):
        return BinaryOp(operator.eq, '==', self, other)

    def __ne__(self, other):
        return BinaryOp(operator.ne, '!=', self, other)

    def __add__(self, other):
        return BinaryOp(operator.add, '+', self, other)

    def __sub__(self, other):
        return BinaryOp(operator.sub, '-', self, other)

    def __div__(self, other):
        return BinaryOp(operator.__div__, '/', self, other)

    def __floordiv__(self, other):
        return BinaryOp(operator.floordiv, '//', self, other)

    def __truediv__(self, other):
        return BinaryOp(operator.truediv, '/', self, other)

    def __mul__(self, other):
        return BinaryOp(operator.mul, '*', self, other)

    def __rmul__(self, other):
        return BinaryOp(operator.mul, '*', other, self)

    def __pow__(self, other):
        return BinaryOp(operator.pow, '**', self, other)

    def __mod__(self, other):
        return BinaryOp(operator.mod, '%', self, other)

    @_helpful_failure
    def eval_(self, val):
        """
        Pass the argument ``val`` to the function, and return the result.

        This special method is necessary because the ``__call__`` method
        builds a new function stead of evaluating the current one.
        """
        return val

    def debug_(self):
        """
        Returns debugging information for the previous error raised
        during expression evaluation.

        Returns a QDebug namedtuple with four fields:

          - expr is the last full expression to have raised an exception
          - inner_expr is the specific sub-expression that raised the exception
          - val is the value that expr tried to evaluate.
          - inner_val is the value that inner_expr tried to evaluate

        If no exceptions have been triggered from expression evaluation,
        then each field is None.

        Examples:

            >>> Scalar('test').map(Q.upper().foo)
            Traceback (most recent call last):
            ...
            AttributeError: 'str' object has no attribute 'foo'
            ...
            >>> dbg = Q.debug_()
            >>> dbg.expr
            Q.upper().foo
            >>> dbg.inner_expr
            .foo
            >>> dbg.val
            'test'
            >>> dbg.inner_val
            'TEST'
        """
        result = self.__debug_info__
        if isinstance(result, QDebug):
            return result
        return QDebug(None, None, None, None)


@six.python_2_unicode_compatible
class Call(Expression):

    """An expression for calling a function or method"""

    def __init__(self, args, kwargs):
        self._args = args
        self._kwargs = kwargs

    @_helpful_failure
    def eval_(self, val):
        return val.__call__(*self._args, **self._kwargs)

    def __str__(self):
        result = list(map(_uniquote, self._args))
        if self._kwargs:
            result.append('**%s' % _uniquote(self._kwargs))
        return '(%s)' % (', '.join(result))


@six.python_2_unicode_compatible
class BinaryOp(Expression):

    """A binary operation"""

    def __init__(self, op, symbol, left, right):
        self.op = op
        self.left = left
        self.right = right
        self.symbol = symbol

    @_helpful_failure
    def eval_(self, val):
        left = self.left
        right = self.right
        if isinstance(left, Expression):
            left = left.eval_(val)

        if isinstance(right, Expression):
            right = right.eval_(val)

        return self.op(left, right)

    def __str__(self):
        l, r = self.left, self.right
        if isinstance(l, BinaryOp):
            l = '(%s)' % str(l)
        if isinstance(r, BinaryOp):
            r = '(%s)' % str(r)

        return "%s %s %s" % (l, self.symbol, r)


@six.python_2_unicode_compatible
class Attr(Expression):

    """An expression for fetching an attribute (eg, obj.item)"""

    def __init__(self, attribute_name):
        self._name = attribute_name

    @_helpful_failure
    def eval_(self, val):
        return operator.attrgetter(self._name)(val)

    def __str__(self):
        return '.%s' % self._name


@six.python_2_unicode_compatible
class GetItem(Expression):

    """An expression for getting an item (eg, obj['item'])"""

    def __init__(self, key):
        self._name = key

    @_helpful_failure
    def eval_(self, val):
        return operator.itemgetter(self._name)(val)

    def __str__(self):
        return "[%s]" % _uniquote(self._name)


@six.python_2_unicode_compatible
class Chain(Expression):

    """An chain of expressions (eg a.b.c)"""

    def __init__(self, items):
        self._items = items

    def __iter__(self):
        for item in self._items:
            yield item

    @_helpful_failure
    def eval_(self, val):
        for item in self._items:
            val = item.eval_(val)
        return val

    def __str__(self):
        return ''.join(map(_uniquote, self._items))


def _make_callable(func):
    # If func is an expression, we call via eval_
    # otherwise, we call func directly
    return getattr(func, 'eval_', func)


def _unwrap(val):
    if isinstance(val, Wrapper):
        return val.val()
    return val


def _dequote(str):
    try:
        return QUOTED_STR.findall(str)[0]
    except IndexError:
        raise AssertionError("Not a quoted string")


def _uniquote(value):
    """
    Convert to unicode, and add quotes if initially a string
    """
    if isinstance(value, six.binary_type):
        try:
            value = value.decode('utf-8')
        except UnicodeDecodeError:  # Not utf-8. Show the repr
            value = six.text_type(_dequote(repr(value)))  # trim quotes

    result = six.text_type(value)

    if isinstance(value, six.text_type):
        result = "'%s'" % result
    return result


def _repr(value):
    value = repr(value)
    if isinstance(value, six.binary_type):
        value = value.decode('utf-8')
    return value


class Soupy(Node):

    def __init__(self, val, *args, **kwargs):
        if not isinstance(val, PageElement):
            val = BeautifulSoup(val, *args, **kwargs)
        super(Soupy, self).__init__(val)


Q = Expression()
