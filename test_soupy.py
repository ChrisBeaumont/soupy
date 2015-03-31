import pytest

from bs4 import BeautifulSoup

from query import Node, NullValueError, NullNode, Collection, NullCollection


COLLECTION_PROPS = ('children',
                    'parents',
                    'contents',
                    'descendants',
                    'next_siblings',
                    'previous_siblings',
                    )

SCALAR_PROPS = ('parent', 'next_sibling', 'previous_sibling')


class TestNode(object):

    def test_val(self):
        assert Node(3).val() == 3

    @pytest.mark.parametrize('attr', COLLECTION_PROPS)
    def test_passthrough_collections(self, attr):
        dom = BeautifulSoup('<a class="foo"><b><c>test</c></b></a>').find('b')
        node = Node(dom)
        assert list(getattr(node, attr).val()) == list(getattr(dom, attr))

    @pytest.mark.parametrize('attr', SCALAR_PROPS)
    def test_passthrough_scalars(self, attr):
        dom = BeautifulSoup('<b><d></d><c>test</c><d></d></b>').find('c')
        node = Node(dom)
        assert getattr(node, attr).val() == getattr(dom, attr)

    @pytest.mark.parametrize('attr', SCALAR_PROPS)
    def test_empty_scalars(self, attr):
        dom = BeautifulSoup('<a></a>')
        node = Node(dom)
        assert getattr(dom, attr) is None
        assert isinstance(node.parent, NullNode)

    @pytest.mark.parametrize('attr', ('attrs', 'text'))
    def test_nonclosed(self, attr):
        dom = BeautifulSoup('<a class="foo"><b><c>test</c></b></a>').find('c')
        node = Node(dom)
        assert getattr(node, attr).val() == getattr(dom, attr)

    def test_orelse_returns_self(self):
        n = Node(3)
        assert n.orelse(5) is n

    def test_slice_text(self):
        dom = BeautifulSoup('<a>test</a>').find('a')
        node = Node(dom)
        assert node.text[1:-1].val() == 'es'

    def test_getkey(self):
        dom = BeautifulSoup('<a class="test">test</a>').find('a')
        node = Node(dom)
        assert node['class'].val() == dom['class']

    def test_find(self):
        dom = BeautifulSoup('<a class="test">test</a>')
        node = Node(dom)

        assert node.find('a').val() == dom.find('a')

    def test_find_fail(self):
        dom = BeautifulSoup('<a class="test">test</a>')
        node = Node(dom)

        assert isinstance(node.find('b'), NullNode)

    def test_find_all(self):
        dom = BeautifulSoup('<a class="test">test</a>')
        node = Node(dom)

        assert node.find_all('a').val() == dom.find_all('a')


class TestNullNode(object):

    def test_val_raises(self):
        with pytest.raises(NullValueError):
            assert NullNode().val()

    @pytest.mark.parametrize('attr', COLLECTION_PROPS)
    def test_passthrough_collections(self, attr):
        node = NullNode()
        assert list(getattr(node, attr).val()) == []

    @pytest.mark.parametrize('attr', SCALAR_PROPS)
    def test_passthrough_scalars(self, attr):
        node = NullNode()
        assert isinstance(getattr(node, attr), NullNode)

    def test_attrs_on_null(self):
        assert NullNode().attrs.val() == {}

    def test_text_on_null(self):
        assert NullNode().text.val() == u''

    def test_orelse_returns_other(self):
        assert NullNode().orelse(3).val() == 3

    def test_find(self):
        assert isinstance(NullNode().find('a'), NullNode)

    def test_find_all(self):
        assert isinstance(NullNode().find_all('a'), NullCollection)


class TestCollection(object):

    def test_slice(self):
        dom = BeautifulSoup('<a>1</a><a>2</a><a>3</a>')
        node = Node(dom)

        assert isinstance(node.children[::2], Collection)
        assert node.children[::2].val() == list(dom.children)[::2]

    def test_get_single(self):
        dom = BeautifulSoup('<a>1</a><a>2</a><a>3</a>').body
        print dom.contents
        node = Node(dom)

        assert node.children[1].val() == dom.contents[1]

