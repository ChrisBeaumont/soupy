.. soupy documentation master file, created by
   sphinx-quickstart on Thu Apr  2 18:06:34 2015.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to the Soupy documentation
==================================

.. currentmodule:: soupy

Soupy is a wrapper around `BeautifulSoup <http://www.crummy.com/software/BeautifulSoup/>`_ that makes it easier to
search through HTML and XML documents.

.. testcode::

    from soupy import Soupy, Q

    html = """
    <div id="main">
      <div>The web is messy</div>
      and full of traps
      <div>but Soupy loves you</div>
    </div>"""

    print(Soupy(html).find(id='main').children
          .each(Q.text.strip()) # extract text from each node, trim whitespace
          .filter(len)          # remove empty strings
          .val())               # dump out of Soupy

.. testoutput::

  [u'The web is messy', u'and full of traps', u'but Soupy loves you']

Compare to the same task in BeautifulSoup:

.. testcode::

    from bs4 import BeautifulSoup, NavigableString

    html = """
    <div id="main">
      <div>The web is messy</div>
      and full of traps
      <div>but Soupy loves you</div>
    </div>"""

    result = []
    for node in BeautifulSoup(html).find(id='main').children:
        if isinstance(node, NavigableString):
            text = node.strip()
        else:
            text = node.text.strip()
        if len(text):
            result.append(text)

    print(result)

.. testoutput::

  [u'The web is messy', u'and full of traps', u'but Soupy loves you']

Soupy uses BeautifulSoup under the hood and provides a very similar API,
while smoothing over some of the warts in BeautifulSoup. Soupy also
adds a functional interface for chaining together operations,
gracefully dealing with failed searches, and extracting data into
simpler formats.

Installation
------------

::

    pip install soupy

or download the `GitHub source <http://github.com/ChrisBeaumont/soupy>`_.


Quickstart
----------

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
when you are ready.

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
a ``NullNode``, which can be further chained without
raising exceptions. Of course, since ``NullNode`` represents
a failed match, trying to extract any data raises an error:

.. doctest::

  >>> soup.find('b').find('a').val()
  Traceback (most recent call last):
  ...
  NullValueError:

However the :meth:`Node.orelse` method can be used to specify a fallback
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
defined.

Soupy's API is more predictable, and better suited for searching through
messily-formated documents. Here are the main properties and methods
copied over from BeautifulSoup. All of these features perform the same
conceptual task as in BeautifulSoup, but they *always* return the same
wrapper class.

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

So far we have explored how Soupy wrappers allow us to chain together
familiar features from the BeautifulSoup API, without worrying about
corner cases at each step in the chain.

Soupy also provides new functions that enable us to build richer
expressions than what is possible with BeautifulSoup.

Iterating over results with each and dump
.........................................

A common pattern in BeautifulSoup is to iterate over results from a
call like :meth:`~Node.find_all` using a list comprehension. For example,
consider the query to extract all the movie Titles on `this IMDB page <http:;//chrisbeaumont.github.io/soupy/imdb_demo.html>`_


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

Soupy provides an alternative syntax via the :meth:`~Collection.each` method:


.. doctest:: imdb

    >>> print(soup.find_all('td', 'title').each(lambda node: node.find('a').text).val())
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

The :meth:`~Collection.dump` method works similarly to :meth:`~Collection.each`,
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

    You can also run dump on a single node to extract a single dictionary.

Transforming values with map and apply
......................................

Notice above that we extracted each "year" value as a string.
We'd like to use integers instead. The :meth:`~Collection.map`
and :meth:`~Collection.apply` methods
let us transform the data inside a Soupy wrapper, and build a new
wrapper out of the transformed value.

:meth:`~Collection.map` takes a function as input, applies that function to the
wrapped data, and returns a new wrapper. So we can extract integer years
via

.. doctest:: imdb

    >>> soup.find('td', 'title').find('span', 'year_type').text[1:-1].map(int)
    Scalar(1994)


:meth:`~Collection.map` can be applied to any wrapper:

 - Scalar.map applies the transformation to the data in the scalar
 - Node.map applies the transformation to the BeautifulSoup element
 - Collection.map applies the transformation to the list of nodes (rarely used)

The :meth:`~Collection.apply` function is similar to :meth:`~Collection.map`, except that the input function is called on the wrapper itself, and not the data inside the wrapper (the output will be re-wrapped automatically).

Note also that Q-expressions are not restricted to working with Soupy
nodes -- they can be used to express any chain of methods on an object:

.. doctest:: imdb

    >>> soup.find('td', 'title').find('a').text.map(Q.upper())
    Scalar(u'THE SHAWSHANK REDEMPTION')

Filtering Collections with filter, takewhile, dropwhile
........................................................

The :meth:`~Collection.filter`, :meth:`~Collection.takewhile`, and
:meth:`~Collection.dropwhile` methods remove unwanted nodes
from collections. They accept a function which is applied to each
element in the collection, and converted to a boolean value.
:meth:`~Collection.filter` removes items where ``func(item)``
is False. :meth:`~Collection.takewhile` removes items
on and after the first False, and :meth:`~Collection.dropwhile` drops items
until the first True return value.

.. doctest:: imdb

  >>> soup.find_all('td', 'title').each(Q.find('a').text).filter(Q.startswith('B')).val()
  [u'Batman Begins', u'Braveheart', u'Back to the Future']

This query selects only movies whose titles begin with "The".

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

  [{'rating': 9.3, 'genres': [u'Crime', u'Drama'], 'name': u'The Shawshank Redemption', 'cast': [u'Tim Robbins', u'Morgan Freeman', u'Bob Gunton']...

Contents:

.. toctree::
   :maxdepth: 2

   api.rst



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

