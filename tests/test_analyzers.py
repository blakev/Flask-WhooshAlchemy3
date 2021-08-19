#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# >>
#   Flask-WhooshAlchemy3, 2021
#   Blake VandeMerwe <blakev@null.net>
# <<

import pytest
from whoosh.analysis import SimpleAnalyzer

from .conftest import Blog
from flask_whooshalchemy3 import search_index


@pytest.fixture(scope='function', autouse=True)
def db_app_model(app, db):

    class Simple(db.Model, Blog):
        __tablename__ = 'simpleBlog'
        __searchable__ = ['title', 'content', 'blurb']

    return db, app, Simple


@pytest.mark.parametrize('analyzer', [
    SimpleAnalyzer(),
    SimpleAnalyzer,
    'SimpleAnalyzer',
])
def test_analyzer_type(analyzer, db_app_model):
    db, app, model = db_app_model

    setattr(model, '__analyzer__', analyzer)

    db.create_all()
    index = search_index(app, model)

    assert index.doc_count() == 0

    db.session.add(model(title='jumping'))
    db.session.commit()

    assert not list(model.query.search('jump'))
    assert model.query.search('jumping')[0].title == 'jumping'

    db.session.add(model(title='Travelling'))  # Stemming
    db.session.add(model(title='travel'))  # Un-stemmed, normal
    db.session.add(model(title='trevel'))  # Misspelled
    db.session.commit()

    assert len(list(model.query.search('trevel'))) == 1
    assert len(list(model.query.search('travelling'))) == 1
    assert index.doc_count() == 4
