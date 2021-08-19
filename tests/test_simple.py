#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# >>
#   Flask-WhooshAlchemy3, 2021
#   Blake VandeMerwe <blakev@null.net>
# <<

import pytest

from .conftest import Blog
from flask_whooshalchemy3 import search_index


@pytest.fixture(scope='function', autouse=True)
def db_model(app, db):

    class Simple(db.Model, Blog):
        __tablename__ = 'simpleBlog'
        __searchable__ = ['title', 'content', 'blurb']

    db.create_all()
    search_index(app, Simple)

    return db, Simple


def test_single_document(db_model):
    db, model = db_model

    assert not list(model.query.search('*'))
    assert model.whoosh.index.doc_count() == 0

    for idx in range(5):
        db.session.add(model(title='Hello', content='World'))
        db.session.commit()
        results = list(model.query.search('*'))
        assert len(results) == idx + 1
        assert results[0].title == 'Hello'

    assert model.whoosh.index.doc_count() == 5


def test_single_doc_cleanup(db_model):
    db, model = db_model
    assert model.whoosh.index.doc_count() == 0


def test_chaining(db_model):
    db, model = db_model

    objs = [
        ('title', 'poem'),
        ('title', 'testing'),
        ('titled', 'tested'),
        ('test', 'tests'),
    ]

    for obj in objs:
        db.session.add(model(title=obj[0], content=obj[1]))
    db.session.commit()

    assert len(list(model.query.search('title'))) == 3
    assert len(list(model.query.search('test'))) == 3
    assert len(list(model.query.search('title').search('test'))) == 2
    assert len(list(model.query.search('title').search('poem'))) == 1

