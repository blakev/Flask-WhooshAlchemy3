#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# >>
#   Flask-WhooshAlchemy3, 2021
#   Blake VandeMerwe <blakev@null.net>
# <<

import os
import shutil
import tempfile
from datetime import datetime

import pytest
from flask import Flask
from sqlalchemy import Column
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.types import (
    Text,
    String,
    Integer,
    DateTime,
)

import flask_whooshalchemy3
from flask_whooshalchemy3 import WhooshAlchemyError


class Blog:
    # yapf: disable
    id      = Column(Integer, primary_key=True)
    title   = Column(Text)
    content = Column(String)
    blurb   = Column(String)
    ignored = Column(String)
    created = Column(DateTime(), default=datetime.utcnow)
    # yapf: enable

    def __repr__(self):
        return '{0}(title={1})'.format(self.__class__.__name__, self.title)


def create_app():
    tmp = tempfile.mkdtemp()

    app = Flask(__name__)
    app.config['WHOOSH_BASE'] = os.path.join(tmp, 'whoosh')
    app.config['WHOOSH_INDEX_PATH'] = os.path.join(tmp, 'whoosh')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///%s' % os.path.join(tmp, 'db.sqlite')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

    @app.route('/')
    def index():
        return 'SUCCESS'

    return app


@pytest.fixture
def app():
    app = create_app()
    yield app


@pytest.fixture
def db(app):
    db = SQLAlchemy()
    db.init_app(app)

    yield db
    db.drop_all()

    try:
        shutil.rmtree(app.config['WHOOSH_BASE'])
    except FileNotFoundError:
        pass
