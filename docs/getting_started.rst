
Getting Started
===============

.. currentmodule:: soupy

The Problem Soupy Aims to Solve
-------------------------------

BeautifulSoup is a great library for searching through HTML and XML documents.
However, the datatypes returned by BeautifulSoup methods can be inconsistent,
especially with messily-structured files. For example, consider the following
sensible query to find the first p tag inside the content div under an h2 tag:

::

  dom.find('h2').find('div', 'content').find('p')

Depending on the document, each of these find calls may return a Tag, a unicode
string, an integer (if the previous ``find`` returned a string instead of a
Tag), None, or raise an AttributeError (if the previous ``find`` returned an
integer or None instead of a Tag). Of these, only Tags can be safely chained
together. In general, code like the line above risks generating exceptions. There are lots of other examples like this in BeautifulSoup.

In a nutshell, Soupy lets you safely chain queries together more gracefully, even when searches fail.

::

    dom.find('h2').find('div', 'content').find('p').orelse('not found').val()

Let's see how that works.

Comparison to BeautifulSoup
---------------------------


Soupy wraps BeautifulSoup objects inside special wrappers:

 - A :class:`Node` wraps a BeautifulSoup DOM object like a `Tag <http://www.crummy.com/software/BeautifulSoup/bs4/doc/#tag>`_
   or a `NavigableString <http://www.crummy.com/software/BeautifulSoup/bs4/doc/#navigablestring>`_.
 - A :class:`Collection` wraps a list of other wrappers together.
 - A :class:`Scalar` wraps other objects (numbers, strings, dicts, etc).

The most important object is :class:`Node`. It behaves very similarly
to a BeautifulSoup ``Tag``, but its behavior is more predictable.

When BeautifulSoup is well-behaved, Soupy code is basically
identical:

.. testcode::

    html = "<html>Hello<b>world</b></html>"
    bs = BeautifulSoup(html)
    soup = Soupy(html)

    bs_val = bs.find('b').text
    soup_val = soup.find('b').text.val()
    assert bs_val == soup_val

.. testcode::

    bs_val = bs.find('b').parent
    soup_val = soup.find('b').parent.val()
    assert bs_val == soup_val

Notice that in these examples, the only difference is that
you always call ``val()`` to pull data out of a Soupy wrapper
when you are ready. **This is the essential concept to learn
when transitioning from BeautifulSoup to Soupy**.

Things get more interesting when we look at corner cases (and
the web is *full* of corner cases). For example,
consider what happens when a search doesn't match anything:

.. testsetup::

    html = "<html>Hello<b>world</b></html>"
    bs = BeautifulSoup(html)
    soup = Soupy(html)

.. doctest::

  >>> bs.find('b').find('a')   # AttributeError
  >>> soup.find('b').find('a')
  NullNode()

BeautifulSoup returns ``None`` when a match fails, which makes it
impossible to chain expressions together. Soupy returns
a :class:`NullNode`, which can be further chained without
raising exceptions. However, since :class:`NullNode` represents
a failed match, trying to extract any data raises an error:

.. doctest::

  >>> soup.find('b').find('a').val()
  Traceback (most recent call last):
  ...
  NullValueError:

Fortunately the :meth:`Node.orelse` method can be used to specify a fallback
value when a query doesn't match:

.. testsetup::

    html = "<html>Hello<b>world</b></html>"
    soup = Soupy(html)

.. doctest::

  >>> soup.find('b').find('a').orelse('Not Found').val()
  'Not Found'

There are lots of little corner cases like this in BeautifulSoup --
sometimes functions return strings instead of Tags, sometimes they
return None, sometimes certain methods or attributes aren't
defined, etc.

Soupy's API is more predictable, and better suited for searching through
messily-formated documents. Here are the main properties and methods copied over
from BeautifulSoup. All of these features perform the same conceptual task as
their BeautifulSoup counterparts, but they *always* return the same wrapper
class. The primary goal of Soupy's design is to allow you to string together
complex queries, without worrying about query failures at each step of the
search.

- Properties and Methods that return :class:`Node` (or :class:`NullNode`)

 - :attr:`Node.parent`
 - :attr:`Node.next_sibling`
 - :attr:`Node.previous_sibling`
 - :meth:`Node.find`
 - :meth:`Node.find_parent`
 - :meth:`Node.find_next_sibling`
 - :meth:`Node.find_previous_sibling`

- Properties that return :class:`Scalar` (or :class:`Null`)

 - :attr:`Node.text`
 - :attr:`Node.attrs`
 - :attr:`Node.name`

- Properties and Methods that return a :class:`Collection` of Nodes

 - :attr:`Node.children`
 - :attr:`Node.contents`
 - :attr:`Node.descendants`
 - :attr:`Node.parents`
 - :attr:`Node.next_siblings`
 - :attr:`Node.previous_siblings`
 - :meth:`Node.find_all`
 - :meth:`Node.select`
 - :meth:`Node.find_parents`
 - :meth:`Node.find_next_siblings`
 - :meth:`Node.find_previous_siblings`


Functional API
--------------

The main benefit of Soupy's wrappers is the ability to reliably chain them
together. This also allows you to use general purpose libraries like itertools,
functools, `toolz <http://toolz.readthedocs.org/en/latest/>`_,  `more_itertools
<https://pythonhosted.org/more-itertools/index.html>`_,  etc., to compose more
complex data processing pipelines. For convenience, Soupy also priovides several
such utilities to support more extensive method chaining.


Iterating over results with each, dump, dictzip
...............................................

A common pattern in BeautifulSoup is to iterate over results from a
call like :meth:`~Node.find_all` using a list comprehension. For example,
consider the query to extract all the movie titles on `this IMDB page <http://chrisbeaumont.github.io/soupy/imdb_demo.html>`_


.. testcode:: imdb

    import requests
    url = 'http://chrisbeaumont.github.io/soupy/imdb_demo.html'
    html = requests.get(url).text
    bs = BeautifulSoup(html, 'html.parser')
    soup = Soupy(html, 'html.parser')

    print([node.find('a').text
           for node in bs.find_all('td', 'title')])

.. testoutput:: imdb

   [u'The Shawshank Redemption', u'The Dark Knight', u'Inception',...]

Soupy provides an additional syntax for this with the :meth:`~Collection.each` method:


.. doctest:: imdb

    >>> print(soup.find_all('td', 'title').each(
    ...       lambda node: node.find('a').text).val())
    [u'The Shawshank Redemption',...]

:meth:`Collection.each` applies a function to every node in a collection, and
wraps the result into a new collection.

Because typing ``lambda`` all the time is cumbersome, Soupy
also has a shorthand ``Q`` object to make this task easier. This same
query can be written as

.. doctest:: imdb

    >>> print(soup.find_all('td', 'title').each(Q.find('a').text).val())
    [u'The Shawshank Redemption',...]


Think of ``Q[stuff]`` as shorthand for ``lambda x: x[stuff]``.

The :meth:`Collection.dump` method works similarly to :meth:`~Collection.each`,
except that it extracts multiple values from each node, and packs
them into a list of dictionaries. It's a convenient way to extract a JSON blob out of a document.

For example,

.. testcode:: imdb

    print(soup.find_all('td', 'title').dump(
          name=Q.find('a').text,
          year=Q.find('span', 'year_type').text[1:-1]
    ).val())

.. testoutput:: imdb

  [{'name': u'The Shawshank Redemption', 'year': u'1994'}, ...]


.. note::

    You can also run dump on a node to extract a single dictionary.

If you want to set keys based on a list of values (instead of hardcoding them),
you can use the :meth:`Collection.dictzip` method.

.. testcode:: dictzip

  keys = Soupy('<b>a</b><b>b</b><b>c</b>')
  vals = Soupy('<b>1</b><b>2</b><b>3</b>')

  keys = keys.find_all('b').each(Q.text)
  vals = vals.find_all('b').each(Q.text)
  print(vals.dictzip(keys).val() == {'a': '1', 'b': '2', 'c': '3'})

.. testoutput:: dictzip

  True

:meth:`~Collection.dictzip` is so-named because the output is equivalent to
``dict(zip((keys.val(), vals.val())))``

Transforming values with map and apply
......................................

Notice in the IMDB example above that we extracted each "year" value as a string.

.. doctest:: imdb

    >>> y = soup.find('td', 'title').find('span', 'year_type').text[1:-1]
    >>> y
    Scalar(u'1994')


We'd like to use integers instead. The :meth:`~Collection.map`
and :meth:`~Collection.apply` methods
let us transform the data inside a Soupy wrapper, and build a new
wrapper out of the transformed value.

:meth:`~Collection.map` takes a function as input, applies that function to the
wrapped data, and returns a new wrapper. So we can extract integer years
via

.. doctest:: imdb

    >>> y.map(int)
    Scalar(1994)


:meth:`~Collection.map` can be applied to any wrapper:

 - Scalar.map applies the transformation to the data in the scalar
 - Node.map applies the transformation to the BeautifulSoup element
 - Collection.map applies the transformation to the list of nodes (rarely used)

The :meth:`~Collection.apply` function is similar to :meth:`~Collection.map`, except that the input function is called on the wrapper itself, and not the data inside the wrapper (the output will be re-wrapped automatically if needed).

Note also that Q-expressions are not restricted to working with Soupy
nodes -- they can be used on any object. For example, to uppercase
all movie titles:

.. doctest:: imdb

    >>> soup.find('td', 'title').find('a').text.map(Q.upper())
    Scalar(u'THE SHAWSHANK REDEMPTION')

Filtering Collections with filter, takewhile, dropwhile
........................................................

The :meth:`~Collection.filter`, :meth:`~Collection.takewhile`, and
:meth:`~Collection.dropwhile` methods remove unwanted nodes
from collections. They accept a function which is applied to each
element in the collection, and converted to a boolean value.
``filter(func)`` removes items where ``func(item)``
is False. ``takewhile(func)`` removes items
on and after the first False, and ``dropwhile(func)`` drops items
until the first True return value.

.. doctest:: imdb

  >>> soup.find_all('td', 'title').each(Q.find('a').text).filter(Q.startswith('B')).val()
  [u'Batman Begins', u'Braveheart', u'Back to the Future']

This query selects only movies whose titles begin with "B".

You can also filter lists using slice syntax ``nodes[::3]``.

Combining most of these ideas, here's a succinct JSON-summary of the
IMDB movie list:

.. testcode:: imdb

    cast_split = Q.text != '\n    With: '

    print(soup.find_all('td', 'title').dump(
          name=Q.find('a').text,
          year=Q.find('span', 'year_type').text,
          genres=Q.find('span', 'genre').find_all('a').each(Q.text),
          cast=(Q.find('span', 'credit').contents.dropwhile(cast_split)[1::2].each(Q.text)),
          directors=(Q.find('span', 'credit').contents.takewhile(cast_split)[1::2].each(Q.text)),
          rating=(Q.select('div.user_rating span.rating-rating span.value')[0].text.map(float)),
    ).val())

.. testoutput:: imdb
  :options: +NORMALIZE_WHITESPACE

  [{'rating': 9.3,
    'genres': [u'Crime', u'Drama'],
    'name': u'The Shawshank Redemption',
    'cast': [u'Tim Robbins', u'Morgan Freeman', u'Bob Gunton']...


Enforcing Assertions with nonnull and require
.............................................

Soupy prevents unmatched queries from raising errors until ``val``
is called. Usually that's convenient, but sometimes you want to
"fail loudly" in the event of unexpected input. There are a few
methods to help with this.

:meth:`~Node.nonnull` raises a ``NullValueError`` if called on
a Null wrapper, and returns the unmodified wrapper otherwise.
Thus, it can be used to require that part of a query has matched.

.. doctest::

  >>> s = Soupy('<p> No links here </p>')
  >>> s.find('p').nonnull().find('a')['href'].orelse(None)
  Scalar(None)
  >>> s.find('b').nonnull().find('a')['href'].orelse(None)
  Traceback (most recent call last):
  ...
  NullValueError:

Here we require that the first ``find`` matches against something,
while providing a fallback in case the second ``find`` fails.

:meth:`~Node.require` behaves like ``assert``: it takes a function
which is ``apply``-ed to the wrapper, and raises an exception if
the result isn't Truthy.

.. doctest::

  >>> s = Scalar(3)
  >>> s.require(Q > 2, 'Too small!')
  Scalar(3)
  >>> s.require(Q > 5, 'Too small!')
  Traceback (most recent call last):
  ...
  NullValueError: Too small!


Working with Q Expressions
--------------------------

Many of the previous examples have used the `Q` function-builder as a
shorthand for ``lambda`` or manually defined functions. As mentioned
above, ``Q[stuff]`` is rougly equivalent to ``lambda x: x[stuff]``,
so it should feel natural to pick up. Here are some example Q expressions,
and their lambda equivalents:


   ================== ====================================
   Q Expression       lambda expression
   ================== ====================================
   ``Q + 3``          ``lambda x: x + 3``
   ``Q.a``            ``lambda x: x.a``
   ``Q(5)``           ``lambda x: x(5)``
   ``Q.func(3)``      ``lambda x: x.func(3)``
   ``Q[key]``         ``lambda x: x['key']``
   ``Q.map(Q > 3)``   ``lambda x: x.map(lambda y: y > 3)``
   ================== ====================================

The third example introduces a slight twist with Q expressions. Because
``Q(5)`` builds a function like ``lambda x: x(5)``, we can't directly
call this function using the normal ``(arg)`` syntax -- doing so would
actually build a *new* function behaving like ``lambda x: x(5)(arg)``.
You normally don't need to manually evaulate Q expressions, but if you
do you can use the :meth:`~Expression.eval_` method.

.. doctest::

  >>> x = Q.upper()[0:2]
  >>> x('testing')  # No! Builds a new function
  Q.upper()[slice(0, 2, None)]('testing')
  >>> x.eval_('testing')  # Yes!
  'TE'

.. _q_debug:

Debugging Q expressions
........................


Despite your best efforts, you will *still* encounter messy documents
that trigger errors in your code. Here's a simplified example:

.. doctest:: qdebug

  >>> html = ['<a href="/index"></a>'] * 100
  >>> html[30] = '<a href="#"></a>'
  >>> dom = Soupy(''.join(html))
  >>> dom.find_all('a').each(Q['href'].split('/')[1])
  Traceback (most recent call last):
  ...
  IndexError: list index out of range

      Encountered when evaluating Scalar(['#'])[1]

This code tries to extract the links in all ``a`` tags, but fails
on links that don't have a slash. Debugging issues
like this can be frustrating, because these errors are often triggered
by rare edge cases in the document that can be hard to track down.

If your errors are generated inside a Q expression (as is the case here),
the :meth:`Q.debug_ <Expression.debug_>` method will return data to isolate
the failure.

.. doctest:: qdebug

  >>> dbg = Q.debug_()
  >>> dbg
  QDebug(expr=Q['href'].split('/')[1], inner_expr=[1], val=Node(<a href="#"></a>), inner_val=Scalar(['#']))
  >>> dbg.expr
  Q['href'].split('/')[1]
  >>> dbg.inner_expr
  [1]
  >>> dbg.val
  Node(<a href="#"></a>)
  >>> dbg.inner_val
  Scalar(['#'])

The attributes returned by ``debug_`` are the full Q expression
that triggered the error, the specific subexpression that triggered
the error (in this case, the ``['href']`` part), the value that
was passed to ``full_expr``, and the value passsed to ``expr``.
So for example we can re-trigger the error via

.. doctest:: qdebug

  >>> dbg.expr.eval_(dbg.val)
  Traceback (most recent call last):
  ...
  IndexError: list index out of range

      Encountered when evaluating Scalar(['#'])[1]

