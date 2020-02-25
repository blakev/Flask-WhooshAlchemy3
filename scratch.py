#! /usr/bin/env python
# -*- coding: utf-8 -*-
# >>
#     Flask-WhooshAlchemy3, 2017
# <<

import random
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
import flask_whooshalchemy

from whoosh.analysis import StemmingAnalyzer
app = Flask(__name__)
app.config.update(dict(
    SQLALCHEMY_DATABASE_URI='sqlite:///db.sqlite',
    SQL_TRACK_MODIFICATIONS=True,
    WHOOSH_INDEX_PATH='whooshIndex',
    WHOOSH_ANALYZER='StemmingAnalyzer',
))

db = SQLAlchemy()


class Org(db.Model):
    __searchable__ = ['orgName', 'phone1', 'phone2', 'phone3', 'email1', 'email2', 'email3', 'backgroundInfo']
    __analyzer__ = StemmingAnalyzer()
    __tablename__ = 'Org'

    id = db.Column(db.Integer, primary_key=True)
    active = db.Column(db.Boolean, unique=False, default=True)
    orgName = db.Column(db.String(200), unique=True, nullable=False)
    postalStreet = db.Column(db.String(200))
    postalTown = db.Column(db.String(60))
    postalState = db.Column(db.String(20))
    postalPostCode = db.Column(db.String(10))
    backgroundInfo = db.Column(db.String(1000))
    phone1 = db.Column(db.String(128))
    phone2 = db.Column(db.String(128))
    phone3 = db.Column(db.String(128))
    phone1Type = db.Column(db.String(24))
    phone2Type = db.Column(db.String(24))
    phone3Type = db.Column(db.String(24))
    email1 = db.Column(db.String(128))
    email2 = db.Column(db.String(128))
    email3 = db.Column(db.String(128))
    email1Type = db.Column(db.String(24))
    email2Type = db.Column(db.String(24))
    email3Type = db.Column(db.String(24))

    def __repr__(self):  # this is how our object is printed when we print it out
        return f"Org('{self.orgName}')"


@app.route('/search')
def search():
    num_posts = min(int(request.args.get('limit', 10)), 50)
    query = request.args.get('q', '')
    results = Org.query.search(query, limit=num_posts)
    return '\n'.join(map(str, results))


BOOL = (True, False,)
STATES = ('UT', 'ID', 'CA', 'CO', 'WY', 'AR', 'NV',)
NAMES = ('Red', 'Green', 'Blue', 'Yellow',)

@app.before_first_request
def bootstrap():
    db.create_all()
    flask_whooshalchemy.search_index(app, Org)

    for x in range(100):
        rec = Org(active=random.choice(BOOL),
                  orgName=f'{random.choice(NAMES)}_{x}',
                  postalState=random.choice(STATES),
                  postalStreet=random.randrange(100, 1500))
        db.session.add(rec)
    db.session.commit()


if __name__ == "__main__":
    db.init_app(app)
    app.run()


