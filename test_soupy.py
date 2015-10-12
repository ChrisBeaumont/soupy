# -*- coding: utf-8 -*-

from __future__ import print_function, division, unicode_literals
import operator

import pytest
from bs4 import BeautifulSoup
from six import PY3, text_type

from soupy import (Soupy, Node, NullValueError, NullNode,
                   Collection, NullCollection, Null, Q, Some,
                   Scalar, Wrapper, NavigableStringNode, either, QDebug,
                   _dequote)


COLLECTION_PROPS = ('children',
                    'parents',
                    'contents',
                    'descendants',
                    'next_siblings',
                    'previous_siblings',
                    )

SINGLE_PROPS = ('parent', 'next_sibling', 'previous_sibling')
SCALAR_PROPS = ('name', 'text', 'attrs')
COLLECTION_TO_COLLECTION = ('filter', 'each', 'takewhile', 'dropwhile')
SINGLE_FIND = ('find', 'find_parent',
               'find_next_sibling', 'find_previous_sibling')
MULTI_FIND = ('find_all', 'find_next_siblings', 'find_previous_siblings',
              'find_parents', 'select')


class TestWrapper(object):

    def test_wrap(self):
        v = Scalar(3)
        assert isinstance(Wrapper.wrap(3), Scalar)
        assert Wrapper.wrap(v) is v
        assert isinstance(Wrapper.wrap(BeautifulSoup('a')), Node)

    def test_apply(self):
        assert Scalar(3).apply(lambda x: x.val() * 2).val() == 6
        assert isinstance(Null().apply(lambda x: x), Null)


class TestNode(object):

    def test_bool(self):
        assert bool(Node(3))

    def test_val(self):
        assert Node(3).val() == 3

    @pytest.mark.parametrize('attr', COLLECTION_PROPS)
    def test_collection_properties(self, attr):
        node = Soupy('<a class="foo"><b><c>test</c></b></a>').find('b')
        dom = node.val()
        assert list(getattr(node, attr).val()) == list(getattr(dom, attr))

    @pytest.mark.parametrize('attr', SCALAR_PROPS)
    def test_scalar_properties(self, attr):
        node = Soupy('<a class="foo"><b><c>test</c></b></a>').find('c')
        dom = node.val()
        assert getattr(node, attr).val() == getattr(dom, attr)

    @pytest.mark.parametrize('attr', SINGLE_PROPS)
    def test_node_properties(self, attr):
        node = Soupy('<b><d></d><c>test</c><d></d></b>').find('c')
        dom = node.val()
        assert getattr(node, attr).val() == getattr(dom, attr)

    def test_empty_scalars_return_nullnode(self):
        node = Soupy('<a></a>').find('a')
        assert isinstance(node.next_sibling, NullNode)
        assert isinstance(node.previous_sibling, NullNode)

        node = Soupy('<a></a>')
        assert isinstance(node.parent, NullNode)

    def test_orelse_returns_self(self):
        n = Node(3)
        assert n.orelse(5) is n

    @pytest.mark.parametrize('method', SINGLE_FIND)
    def test_find_single_methods(self, method):
        node = Soupy("""
            <div>
               <div></div>
               <b><div></div></b>
               <div></div>
           </div>
           """).find('b')
        dom = node.val()
        expected = getattr(dom, method)('div')
        assert expected
        actual = getattr(node, method)('div').val()
        assert actual == expected

    @pytest.mark.parametrize('method', MULTI_FIND)
    def test_find_multi_methods(self, method):
        node = Soupy("""
            <div>
               <div></div>
               <b><div></div></b>
               <div></div>
           </div>
           """).find('b')
        dom = node.val()
        expected = getattr(dom, method)('div')
        assert expected
        actual = getattr(node, method)('div').val()
        assert actual == expected

    @pytest.mark.parametrize('method', SINGLE_FIND)
    def test_find_single_fail(self, method):
        node = Soupy('<a class="test">test</a>')
        assert isinstance(getattr(node, method)('b'), NullNode)

    @pytest.mark.parametrize('method', MULTI_FIND)
    def test_find_multi_fail(self, method):
        node = Soupy('<a class="test">test</a>')
        result = getattr(node, method)('b')
        assert len(result) == 0

    def test_iter(self):
        node = Soupy('<a class="test">test</a>')
        for a, b in zip(node, node.val()):
            assert a.val() == b

    def test_call(self):
        node = Soupy('<a class="test">test</a>')
        assert node('a').val() == node.val()('a')

    def test_nonnull_returns_self(self):
        s = Soupy('')
        assert s.nonnull() == s

    def test_repr_unicode(self):

        s = Soupy('<html>∂ƒ</html>')
        print(s)
        print(repr(s))
        if not PY3:  # must be ascii-encodable on py2
            assert repr(s).encode('ascii')
        print(text_type(s))

    def test_prettify(self):
        s = Soupy('<html>∂ƒ</html>')

        assert s.prettify() == s.val().prettify()


class TestNavigableString(object):

    """
    NavigableStringS do not support all the methods of TagS
    in BeautifulSoup. Test that we handle them gracefully
    """

    def setup_method(self, method):
        self.node = Node(BeautifulSoup('<b>hi</b>').b.contents[0])

    def test_attrs(self):
        assert self.node.attrs.val() == {}

    def test_text(self):
        assert self.node.text.val() == 'hi'

    def test_name(self):
        assert self.node.name.val() == ''

    @pytest.mark.parametrize('attr', ('children', 'contents', 'descendants'))
    def test_multi_props(self, attr):
        assert len(getattr(self.node, attr)) == 0

    @pytest.mark.parametrize('attr', ('find',))
    def test_single_find(self, attr):
        assert isinstance(getattr(self.node, attr)('a'), NullNode)

    @pytest.mark.parametrize('attr', ('find_all', 'select'))
    def test_multi_find(self, attr):
        assert len(getattr(self.node, attr)('a')) == 0

    def test_prettify(self):
        assert self.node.prettify() == self.node.val()


class TestScalar(object):

    def test_eq(self):
        assert (Scalar('test') == 'test').val()

    def test_ne(self):
        assert (Scalar('test') != 'foo').val()

    def test_gt(self):
        assert (Scalar(3) > 2).val()

    def test_ge(self):
        assert (Scalar(3) >= 2).val()

    def test_lt(self):
        assert (Scalar(3) < 4).val()

    def test_le(self):
        assert (Scalar(3) <= 3).val()

    def test_len(self):
        assert len(Scalar([1, 2, 3])) == 3

    def test_slice(self):
        assert Scalar('test')[1:-1].val() == 'es'

    def test_getkey(self):
        assert Scalar({'a': 1})['a'].val() == 1

    def test_isnull(self):
        assert not Scalar(1).isnull()

    def test_arithmetic(self):

        c = Scalar(1)
        assert (c + 1).val() == 2
        assert (c - 1).val() == 0
        assert (c * 2).val() == 2
        assert (c / 1).val() == 1
        assert operator.truediv(c, 2).val() == 0.5

        if not PY3:
            assert operator.div(c, 2).val() == 0.5

        assert (c // 1).val() == 1
        assert (c ** 2).val() == 1
        assert (c % 2).val() == 1

        assert (c + c).val() == 2

    def test_repr_unicode(self):

        s = Scalar('∂ƒ')
        print(s)
        print(repr(s))
        print(text_type(s))
        assert repr(s)[0] != "'"

        s = Scalar('∂ƒ'.encode('utf-8'))
        print(s)
        print(repr(s))
        print(text_type(s))

        s = Scalar(b'\xc2')
        print(s)
        print(repr(s))
        print(text_type(s))

    def test_require(self):

        s = Scalar(3)
        assert s.require(Q > 1) is s

        with pytest.raises(NullValueError):
            s.require(Q > 4)

    def test_arithmetic_with_null(self):
        l, r = Scalar(1), Null()

        assert isinstance(l + r, Null)
        assert isinstance(l - r, Null)
        assert isinstance(l * r, Null)
        assert isinstance(l / r, Null)
        assert isinstance(l // r, Null)
        assert isinstance(l ** r, Null)
        assert isinstance(l % r, Null)
        if not PY3:
            assert isinstance(operator.div(l, r), Null)

    def test_setitem(self):

        s = Scalar({'a': 1})
        s['b'] = 2
        assert s.val() == {'a': 1, 'b': 2}

    def test_hash(self):
        """
        wrappers are hashed by their content
        """
        assert hash(Scalar(2)) == hash(Scalar(2))
        assert hash(Some(2)) == hash(Some(2))


class TestNull(object):

    def test_hash(self):
        # hashing uses the type
        assert hash(Null()) == hash(Null())
        assert hash(Null()) != hash(NullNode())

    def test_call(self):
        assert isinstance(Null()(), Null)

    def test_getattr(self):
        assert isinstance(Null().b, Null)

    def test_len(self):
        with pytest.raises(TypeError):
            len(Null())

    def test_comparison(self):

        c = Null()
        assert isinstance(c > 0, Null)
        assert isinstance(c >= 0, Null)
        assert isinstance(c < 0, Null)
        assert isinstance(c <= 0, Null)
        assert isinstance(c == 0, Null)
        assert isinstance(c != 0, Null)

    def test_arithmetic(self):

        c = Null()
        assert isinstance((c + 1), Null)
        assert isinstance((c - 1), Null)
        assert isinstance((c * 2), Null)
        assert isinstance((c / 1), Null)
        assert isinstance(operator.truediv(c, 2), Null)

        if not PY3:
            assert isinstance(operator.div(c, 2), Null)

        assert isinstance((c // 1), Null)
        assert isinstance((c ** 2), Null)
        assert isinstance((c % 2), Null)

        assert isinstance((c + c), Null)

    def test_require(self):

        with pytest.raises(NullValueError):
            Null().require(lambda x: True)

    def test_setitem(self):
        node = NullNode()
        node['a'] = 3


class TestNullNode(object):

    def test_str(self):
        assert str(NullNode()) == "NullNode()"

    def test_len(self):
        assert len(NullNode()) == 0

    def test_val_raises(self):
        with pytest.raises(NullValueError):
            assert NullNode().val()

    @pytest.mark.parametrize('attr', COLLECTION_PROPS)
    def test_collection_props(self, attr):
        node = NullNode()
        with pytest.raises(NullValueError):
            getattr(node, attr).val()

    @pytest.mark.parametrize('attr', SINGLE_PROPS)
    def test_single_props(self, attr):
        node = NullNode()
        assert isinstance(getattr(node, attr), NullNode)

    @pytest.mark.parametrize('attr', SCALAR_PROPS)
    def test_scalar_props(self, attr):
        node = NullNode()
        assert isinstance(getattr(node, attr), Null)

    def test_orelse_returns_other(self):
        assert NullNode().orelse(3).val() == 3

    @pytest.mark.parametrize('method', SINGLE_FIND)
    def test_find_single(self, method):
        assert isinstance(getattr(NullNode(), method)('a'), NullNode)

    @pytest.mark.parametrize('method', MULTI_FIND)
    def test_find_single_multi(self, method):
        assert isinstance(getattr(NullNode(), method)('a'), NullCollection)

    def test_find(self):
        assert isinstance(NullNode().find('a'), NullNode)

    def test_find_all(self):
        assert isinstance(NullNode().find_all('a'), NullCollection)

    def test_select(self):
        assert isinstance(NullNode().select('a'), NullCollection)

    def test_nonnull_overrides_orelse(self):
        with pytest.raises(NullValueError):
            NullNode().nonnull().orelse(3).val()

    def test_dump(self):
        assert isinstance(NullNode().dump(x=Q + 3), Null)

    def test_prettify(self):

        assert NullNode().prettify() == "Null Node"

    def test_isnull(self):
        assert NullNode().isnull()


class TestCollection(object):

    def setup_method(self, method):
        self.node = Soupy('<html><body><a>1</a><a>2</a><a>3</a></body></html>')

    def test_slice(self):
        node = self.node
        dom = node.val()

        assert isinstance(node.children[::2], Collection)
        assert node.children[::2].val() == list(dom.children)[::2]

    def test_slice_on_iterator(self):
        c = Collection((Scalar(i) for i in range(5)))
        assert c[::2].val() == [0, 2, 4]

    def test_get_single(self):
        node = self.node.find('body')
        dom = node.val()
        assert node.children[1].val() == dom.contents[1]

    def test_get_single_on_iterator(self):
        c = Collection((Scalar(i) for i in range(5)))
        assert c[2].val() == 2

    def test_map(self):
        node = self.node
        assert node.find_all('a').map(len).val() == 3

    def test_first(self):
        node = self.node
        assert node.find_all('a').first().text.val() == '1'

    def test_first_empty(self):
        node = self.node
        assert isinstance(node.find_all('x').first(), NullNode)

    def test_each(self):
        node = self.node
        result = node.find_all('a').each(Q.text.map(int)).val()
        assert result == [1, 2, 3]

    def test_multi_each(self):
        node = self.node
        result = node.find_all('a').each(Q.text.map(int),
                                         Q.text).val()
        assert result == [(1, '1'), (2, '2'), (3, '3')]

    def test_filter(self):
        node = self.node
        result = node.find_all('a').filter(Q.text.map(int) > 1).val()
        assert len(result) == 2

    def test_filter(self):
        node = self.node
        result = node.find_all('a').exclude(Q.text.map(int) > 1).val()
        assert len(result) == 1

    def test_filter_noarg(self):
        node = self.node
        result = node.find_all('a').each(Q.text.map(int) > 1).filter().val()
        assert len(result) == 2

    def test_takewhile(self):
        node = self.node
        result = node.find_all('a').takewhile(Q.text.map(int) < 2).val()
        assert len(result) == 1

    def test_dropwhile(self):
        node = self.node

        result = node.find_all('a').dropwhile(Q.text.map(int) < 2).val()
        assert len(result) == 2

    def test_index_oob(self):
        assert isinstance(Collection([])[5], NullNode)

    def test_bool(self):

        assert Collection([Scalar(1)])
        assert not Collection([])

    def test_count(self):

        assert Collection([]).count().val() == 0
        assert Collection([Scalar(1)]).count().val() == 1
        assert NullCollection().count().val() == 0

    def test_repr_unicode(self):

        s = Collection([Soupy('<html>∂ƒ</html>')])
        print(s)
        print(repr(s))
        print(text_type(s))

    def test_zip(self):

        c1 = Collection(map(Scalar, [1, 2, 3]))
        c2 = c1.each(Q * 2)
        c3 = c1.zip(c2)

        assert c3.val() == [(1, 2), (2, 4), (3, 6)]

        with pytest.raises(ValueError):
            c1.zip([1, 2])

    def test_dictzip(self):

        c = Collection([Scalar(1), Scalar(2)])
        result = c.dictzip(['a', 'b'])
        expected = {'a': 1, 'b': 2}

        assert result.val() == expected

        lbls = Collection([Scalar('a'), Scalar('b')])
        assert c.dictzip(lbls).val() == expected

    def test_list(self):

        items = list(map(Scalar, [1, 2]))
        assert list(Collection(items)) == items

    def test_typecheck(self):
        """ Collections must contain wrappers """
        with pytest.raises(TypeError):
            Collection([1])

    def test_all(self):

        c = Collection(map(Scalar, [True, False]))
        assert c.any().val()
        assert not c.all().val()
        assert not c.none().val()

        c = Collection(map(Scalar, [True, True]))
        assert c.any().val()
        assert c.all().val()
        assert not c.none().val()

        c = Collection(map(Scalar, [False, False]))
        assert not c.any().val()
        assert not c.all().val()
        assert c.none().val()

        c = Collection([])
        assert not c.any().val()
        assert c.none().val()
        assert c.all().val()  # this is python's behavior for empty lists


class TestNullCollection(object):

    def test_iter_val(self):
        with pytest.raises(NullValueError):
            return NullCollection().iter_val()

    def test_dump(self):
        with pytest.raises(NullValueError):
            return NullCollection().dump().val()

    @pytest.mark.parametrize('func', COLLECTION_TO_COLLECTION)
    def test_collection_to_collection_methods(self, func):
        result = getattr(NullCollection(), func)(lambda x: 1)
        assert isinstance(result, NullCollection)

    def test_slice(self):
        assert isinstance(NullCollection()[::2], NullCollection)

    def test_get(self):
        assert isinstance(NullCollection()[0], NullNode)

    def test_first(self):
        assert isinstance(NullCollection().first(), NullNode)


class TestQueries(object):

    def test_simple_dump(self):
        node = Soupy('<a>1</a><a>2</a><a>3</a>')

        result = node.find_all('a').dump(a=Q.text).val()
        assert result == [{'a': '1'}, {'a': '2'}, {'a': '3'}]

        result = node.find_all('a').dump(Q.text).val()
        assert result == [('1',), ('2',), ('3',)]

        with pytest.raises(ValueError):
            node.find('a').dump(Q.text, a=Q.text)

    def test_dump_with_method(self):
        node = Soupy('<a>1</a><a>2</a><a>3</a>')

        result = node.find_all('a').dump(
            a=Q.find('b').orelse('')).val()
        assert result == [{'a': ''}, {'a': ''}, {'a': ''}]

    def test_dump_with_getitem(self):
        node = Soupy('<a val="1">1</a>')

        result = node.find_all('a').dump(
            a=Q.attrs["val"]).val()
        assert result == [{'a': "1"}]

    def test_dump_with_map(self):
        node = Soupy('<a>1</a><a>2</a><a>3</a>')

        result = node.find_all('a').dump(
            a=Q.text.map(int)).val()
        assert result == [{'a': 1}, {'a': 2}, {'a': 3}]

    def test_dump_with_multi_map(self):
        node = Soupy('<a>1</a><a>2</a><a>3</a>')

        result = node.find_all('a').dump(
            a=Q.text.map(int).map(lambda x: x * 2)).val()
        assert result == [{'a': 2}, {'a': 4}, {'a': 6}]

    def test_multi_dump(self):
        node = Soupy('<a val="1">1</a><a>2</a><a val="3">3</a>')

        result = node.find_all('a').dump(
            a=Q.text,
            b=Q.attrs.get('val')).val()
        assert result == [{'a': '1', 'b': '1'},
                          {'a': '2', 'b': None},
                          {'a': '3', 'b': '3'}]

    def test_failed_search(self):
        node = Soupy('<a><b>1</b></a><a>2</a>')

        with pytest.raises(NullValueError):
            node.find_all('a').dump(
                a=Q.find('b').text
            )

    def test_orelse(self):
        node = Soupy('<a><b>1</b></a><a>2</a>')

        result = node.find_all('a').dump(
            a=Q.find('b').text.map(int).orelse(0)
        ).val()

        assert result == [{'a': 1}, {'a': 0}]

    def test_either(self):
        node = Soupy('<a><b>1</b></a><a>2</a>')

        assert node.apply(either(Q.find('c').text,
                                 Q.find('b').text)).val() == '1'

    def test_either_fallback(self):
        node = Soupy('<a><b>1</b></a><a>2</a>')

        assert isinstance(node.apply(either(Q.find('d').text,
                                            Q.find('d').text)),
                          Null)

    def test_navstring_dump(self):
        node = Soupy('<div><a>1</a>2<a>3</a></div>')

        result = node.find('div').contents.each(Q.text).val()
        assert result == ['1', '2', '3']

        result = (node.find('div').contents
                  .each(Q.contents[0].text.orelse('!'))
                  .val())
        assert result == ['1', '!', '3']


class TestExpression(object):

    def test_chain_two_expressions(self):

        result = Q.find('a')._chain(Q.find('b'))
        assert len(result._items) == 6

    def test_operators(self):

        assert (Q > 1).eval_(2)
        assert (Q >= 1).eval_(1)
        assert (Q <= 1).eval_(1)
        assert (Q < 1).eval_(0)
        assert (Q == 1).eval_(1)
        assert (Q != 1).eval_(2)

        assert not (Q > 1).eval_(1)
        assert not (Q >= 1).eval_(0)
        assert not (Q <= 1).eval_(2)
        assert not (Q < 1).eval_(1)
        assert not (Q == 1).eval_(2)
        assert not (Q != 1).eval_(1)

        assert (Q <= Q).eval_(5)

        assert (Q + 5).eval_(2) == 7
        assert (Q - 1).eval_(1) == 0
        assert (Q * 2).eval_(4) == 8

        if not PY3:
            assert operator.div(Q, 2).eval_(3) == 1

        assert operator.truediv(Q, 2).eval_(3) == 1.5

        assert (Q / 2).eval_(4) == 2.0
        assert (Q // 2).eval_(4) == 2
        assert (Q % 2).eval_(3) == 1
        assert (Q ** 2).eval_(3) == 9

    @pytest.mark.parametrize(('expr', 'rep'), [
        (Q, 'Q'),
        (Q.foo, 'Q.foo'),
        (Q.foo(3), 'Q.foo(3)'),
        (Q.foo(3, 4), 'Q.foo(3, 4)'),
        (Q.foo(3, 'a'), "Q.foo(3, 'a')"),
        (Q.foo(bar=1), "Q.foo(**{'bar': 1})"),
        (Q.foo(3, bar=1), "Q.foo(3, **{'bar': 1})"),
        (Q.foo(3).bar, "Q.foo(3).bar"),
        (Q[3], "Q[3]"),
        (Q[3:4], "Q[slice(3, 4, None)]"),
        (Q[3, 4, 5], "Q[(3, 4, 5)]"),
        (Q + 3, "Q + 3"),
        ((Q + 3) * 5, "(Q + 3) * 5"),
        (5 * (Q + 3), "5 * (Q + 3)"),
        (Q.map(Q + 3), "Q.map(Q + 3)"),
        (Q['∂ƒ'], "Q['∂ƒ']"),
        (Q('∂ƒ'), "Q('∂ƒ')"),
        (Q[b'\xc6'], "Q['\\xc6']"),
        (Q[b'\xc6'], "Q['\\xc6']"),
        (Q(b'"\''), "Q('\"\'')"),
        (Q('"\''), "Q('\"\'')"),
        (Q(b'"\'\xc6'), "Q('\"\\\'\\xc6')"),
        (Q['"\''], "Q['\"\'']"),
        (Q[b'"\'\xc6'], "Q['\"\\\'\\xc6']"),
    ])
    def test_str(self, expr, rep):
        assert text_type(expr) == rep
        # repr should be ascii on py2
        if not PY3:
            assert repr(expr).encode('ascii')

    def test_nice_exception_message(self):
        val = str('test')
        with pytest.raises(AttributeError) as exc:
            Q.upper().foo.eval_(val)
        assert exc.value.args[0] == (
            "'str' object has no attribute 'foo'"
            "\n\n\tEncountered when evaluating 'TEST'.foo"
        )

    def test_nice_exception_message_with_key_error(self):
        with pytest.raises(KeyError) as exc:
            Q[str('a')].eval_({})
        assert str(exc.value) == (
            "'a'\n\n\tEncountered when evaluating {}['a']"
        )

    def test_nice_long_exception_message(self):
        val = str('a' * 500)
        with pytest.raises(AttributeError) as exc:
            Q.upper().foo.eval_(val)
        assert exc.value.args[0] == (
            "'str' object has no attribute 'foo'"
            "\n\n\tEncountered when evaluating <str instance>.foo"
        )

    def test_debug_method(self):
        with pytest.raises(AttributeError):
            Q.upper().foo.eval_('test')

        dbg = Q.debug_()
        assert isinstance(dbg, QDebug)
        assert repr(dbg.expr) == 'Q.upper().foo'
        assert repr(dbg.inner_expr) == '.foo'
        assert dbg.val == 'test'
        assert dbg.inner_val == 'TEST'

    def test_debug_method_empty(self):
        del Q.__debug_info__
        dbg = Q.debug_()

        assert isinstance(dbg, QDebug)
        assert dbg == (None, None, None, None)


def _public_api(cls):
    # return names of public and magic methods
    return set(item
               for typ in cls.mro()
               for item in typ.__dict__.keys()
               if not item.startswith('_')
               or item.startswith('__')
               )


def test_scalar_api():
    """ Scalar and Null have identical interfaces """
    assert _public_api(Scalar) == _public_api(Null)


def test_node_api():
    """
    Node and NullNode have identical interfaces
    """
    assert _public_api(Node) == _public_api(NullNode)
    assert _public_api(Node) == _public_api(NavigableStringNode)


def test_collection_api():
    """
    Collection and NullCollection have identical interfaces
    """
    assert _public_api(Collection) == _public_api(NullCollection)


def test_dequote():

    assert _dequote("u'hi'") == 'hi'
    assert _dequote("b'hi'") == 'hi'
    assert _dequote("'hi'") == 'hi'
    assert _dequote('u"hi \'there\'"') == "hi 'there'"
    with pytest.raises(AssertionError):
        _dequote('abc')
