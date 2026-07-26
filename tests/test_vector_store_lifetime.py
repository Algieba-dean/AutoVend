"""
Regression guard for ChromaDB client lifetime.

`ChromaVectorStore` used to close its client in `__del__`. ChromaDB caches and
shares one PersistentClient per path, so garbage-collecting any single store
tore down the client every other store was using, and they all started failing
with `'RustBindingsAPI' object has no attribute 'bindings'`.

In production that meant a transient store — built by a script, a health check,
an evaluation run — could kill the long-lived pipeline the API serves from.
"""

import pytest

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def store_cls():
    from src.rag.vector_store import ChromaVectorStore

    try:
        ChromaVectorStore()
    except Exception as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f"vector store unavailable: {exc}")
    return ChromaVectorStore


def test_store_does_not_close_the_shared_client_on_gc(store_cls):
    """A collected store must leave other stores working."""
    survivor = store_cls()
    assert survivor.collection.count() >= 0

    for _ in range(3):
        store_cls()  # created and immediately unreferenced

    import gc

    gc.collect()

    assert survivor.collection.count() >= 0, "GC of a transient store broke the live one"


def test_temporary_store_can_be_queried_inline(store_cls):
    """
    `ChromaVectorStore().collection.count()` drops the last reference to the
    store as soon as `.collection` is read, so a destructor that closed the
    client made this single expression break itself.
    """
    assert store_cls().collection.count() >= 0


def test_two_stores_share_one_catalogue(store_cls):
    assert store_cls().collection.count() == store_cls().collection.count()
