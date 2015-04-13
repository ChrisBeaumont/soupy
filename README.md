# Soupy

[![Latest Version](https://pypip.in/version/soupy/badge.svg)](https://pypi.python.org/pypi/soupy/)
[![License](https://pypip.in/license/soupy/badge.svg)](https://pypi.python.org/pypi/soupy/)
[![Build Status](https://travis-ci.org/ChrisBeaumont/soupy.svg?branch=master)](https://travis-ci.org/ChrisBeaumont/soupy) [![Coverage Status](https://coveralls.io/repos/ChrisBeaumont/soupy/badge.svg)](https://coveralls.io/r/ChrisBeaumont/soupy)

Soupy is a wrapper around BeautifulSoup that makes it easier
to build complex queries when wrangling web data.

Here's an example of a Soupy query.

```python
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

# ['The web is messy', 'and full of traps', 'but Soupy loves you']
```

The same query using BeautifulSoup:

```python
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
```

For more information, see the [Soupy Documentation](http://soupy.readthedocs.org)

## Installation

```
pip install soupy
```

## Dependencies

six and BeautifulSoup4

Soupy is supported on Python 2.6+ and 3.3+
