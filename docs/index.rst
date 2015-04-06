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


Contents:

.. toctree::
   :maxdepth: 3

   getting_started.rst
   api.rst



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

