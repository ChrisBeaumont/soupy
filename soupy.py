from __future__ import print_function, division, unicode_literals

from abc import ABCMeta, abstractproperty, abstractmethod
from itertools import takewhile, dropwhile
import operator

from bs4 import BeautifulSoup, PageElement, NavigableString
import six
from six.moves import map as imap


__all__ = ['Soupy', 'Q', 'Node', 'Scalar', 'Collection',
           'Null', 'NullNode', 'NullCollection',
           'either', 'NullValueError']


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


class NullValueError(ValueError):

    """
    The NullValueError exception is raised when attempting
    to extract values from Null objects
    """
    pass


@six.python_2_unicode_compatible
class Null(Wrapper):

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

    def __bool__(self):
        return False

    __nonzero__ = __bool__

    def __str__(self):
        return "%s()" % type(self).__name__

    __repr__ = __str__


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

    def __str__(self):
        # returns unicode
        # six builds appropriate py2/3 methods from this
        value = repr(self._value)

        if isinstance(value, six.binary_type):
            value = value.decode('utf-8')

        return "%s(%s)" % (type(self).__name__, value)

    def __repr__(self):
        return repr(self.__str__())[1:-1]  # trim off quotes


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

    def __len__(self):
        return len(self._value)

    def __add__(self, other):
        return self.map(Q + _unwrap(other))

    def __sub__(self, other):
        return self.map(Q - _unwrap(other))

    def __mul__(self, other):
        return self.map(Q * _unwrap(other))

    def __div__(self, other):
        return self.map(Q / _unwrap(other))

    def __floordiv__(self, other):
        return self.map(Q // _unwrap(other))

    def __pow__(self, other):
        return self.map(Q ** _unwrap(other))

    def __mod__(self, other):
        return self.map(Q % _unwrap(other))

    def __truediv__(self, other):
        return self.map(Q / _unwrap(other))


class Collection(Some):

    """
    Collection's store lists of other wrappers.

    They support most of the list methods (len, iter, getitem, etc).
    """

    def __init__(self, items):
        super(Collection, self).__init__(list(items))
        self._items = self._value

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

    def each(self, func):
        """
        Call `func` on each element in the collection

        Returns a new Collection.
        """
        func = _make_callable(func)
        return Collection(imap(func, self._items))

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


class NullCollection(Null, Collection):

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
        return Collection(imap(Node, vals))

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


class NullNode(NodeLike, Null):

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

    def __add__(self, other):
        return BinaryOp(operator.add, self, other)

    def __sub__(self, other):
        return BinaryOp(operator.sub, self, other)

    def __div__(self, other):
        return BinaryOp(operator.__div__, self, other)

    def __floordiv__(self, other):
        return BinaryOp(operator.floordiv, self, other)

    def __truediv__(self, other):
        return BinaryOp(operator.truediv, self, other)

    def __mul__(self, other):
        return BinaryOp(operator.mul, self, other)

    def __pow__(self, other):
        return BinaryOp(operator.pow, self, other)

    def __mod__(self, other):
        return BinaryOp(operator.mod, self, other)

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


def _unwrap(val):
    if isinstance(val, Wrapper):
        return val.val()
    return val


class Soupy(Node):

    def __init__(self, val, *args, **kwargs):
        if not isinstance(val, PageElement):
            val = BeautifulSoup(val, *args, **kwargs)
        super(Soupy, self).__init__(val)


Q = Expression()
