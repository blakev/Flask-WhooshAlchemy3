#! /usr/bin/env python
# -*- coding: utf-8 -*-
# >>
#     Flask-WhooshAlchemy3, 2017
# <<

import os
import heapq
import logging
from collections import defaultdict

import whoosh
import sqlalchemy
import flask_sqlalchemy
import whoosh.index
from whoosh import fields as whoosh_fields
from whoosh.analysis import StemmingAnalyzer
from whoosh.qparser import OrGroup, AndGroup, MultifieldParser
from whoosh.filedb.filestore import RamStorage
from whoosh.writing import AsyncWriter
from sqlalchemy import types as sql_types
from sqlalchemy.orm import EXT_CONTINUE

logger = logging.getLogger(__name__)


# DEFAULTS
DEFAULT_WHOOSH_ANALYZER = StemmingAnalyzer()
DEFAULT_WHOOSH_INDEX_PATH = os.path.join(
    os.path.abspath(os.getcwd()), '.indexes')

UPDATE_FIELDS = ('update', 'insert')
TEXT_TYPES = (sql_types.String, sql_types.Unicode, sql_types.Text)
DATE_TYPES = (sql_types.DateTime, sql_types.Date)
NUM_TYPES = (sql_types.Integer, sql_types.BigInteger, sql_types.SmallInteger,
             sql_types.Float, sql_types.Binary)


class WhooshAlchemyError(Exception):
    """ Base exception class for Flask-WhooshAlchemy3 """


class QueryProxy(flask_sqlalchemy.BaseQuery):
    def __init__(self, entities, session=None):
        super(QueryProxy, self).__init__(entities, session)

        # sqlalchemy database model base class
        self._model_cls = self._mapper_zero().class_

        # references into our Whoosh index
        self._pk = self._model_cls.whoosh_pk
        self._searcher = self._model_cls.whoosh

        # place to store our whoosh results against db results
        self._whoosh_results = None

    def __iter__(self):
        """ Sort the results by Whoosh rank; relevance. """
        _iter = super(QueryProxy, self).__iter__()

        if self._whoosh_results is None or self._order_by is not False:
            return _iter

        ordered = []

        for row in _iter:
            # we have to convert the primary-key, as stored in the SQL database
            #  into a string because the key is stored as an `ID` in whoosh.
            #  The ID field is string only; plus, this allows for uuid pk's.
            str_pk = str(getattr(row, self._pk))
            heapq.heappush(
                ordered, (self._whoosh_results[str_pk], row))

        def inner():
            while ordered:
                yield heapq.heappop(ordered)[1]
        return inner()

    def search(self, query, limit=None, fields=None, or_=False):
        """ Perform a woosh index search. """

        if not isinstance(query, str):
            raise WhooshAlchemyError('query parameter must be string-like')

        results = self._searcher(query, limit, fields, or_)

        if not results:
            return self.filter(sqlalchemy.text('null'))

        result_set = set()
        result_rank = {}

        for rank, result in enumerate(results):
            result_set.add(result)
            result_rank[result] = rank

        f = self.filter(getattr(self._model_cls, self._pk).in_(result_set))
        f._whoosh_results = result_rank
        return f


class Searcher(object):
    __slots__ = ('pk', 'index', 'searcher', 'fields')

    def __init__(self, primary_key, index):
        self.pk = primary_key
        self.index = index
        self.searcher = self.index.searcher
        self.fields = list(set(index.schema._fields.keys()) - {self.pk})

    def __call__(self, query, limit=None, fields=None, or_=False):
        if fields is None:
            fields = self.fields
        group = OrGroup if or_ else AndGroup
        parser = MultifieldParser(fields, self.index.schema, group=group)
        results = []
        with self.searcher() as searcher:
            for doc in searcher.search(parser.parse(query), limit=limit):
                results.append(doc[self.pk])
        return results


def _post_flush(app, changes):
    by_type = defaultdict(list)

    for instance, change in changes:
        update = change in UPDATE_FIELDS

        if hasattr(instance.__class__, '__searchable__'):
            by_type[instance.__class__].append((update, instance))

    procs = app.config.get('WHOOSH_INDEXING_CPUS', 2)
    limit = app.config.get('WHOOSH_INDEXING_RAM', 256)

    for model_name, values in by_type.items():
        ref = values[0][1]

        index = AsyncWriter(search_index(app, ref),
                            delay=0.15,
                            writerargs=dict(proc=procs, limitmb=limit))
        primary_field = ref.whoosh.pk
        searchable = ref.__searchable__

        with index as writer:
            for do_update, v in values:
                pk = str(getattr(v, primary_field))

                if do_update:
                    # get all the columns defined in `__searchable__`
                    attrs = {}
                    for k in searchable:
                        try:
                            attrs[k] = str(getattr(v, k))
                        except AttributeError:
                            raise AttributeError('invalid attribute `%s`' % k)

                    attrs[primary_field] = pk

                    # create a new document, or update an old one, with all
                    #  of our new column values
                    writer.update_document(**attrs)
                else:
                    # remove the document by field `primary field` value `pk`
                    writer.delete_by_term(primary_field, pk)
    return EXT_CONTINUE


def create_index(app, model):
    path = app.config.get('WHOOSH_INDEX_PATH', DEFAULT_WHOOSH_INDEX_PATH)
    name = model.__tablename__
    # this is where all the search indexes will be stored on disk
    full_path = os.path.join(path, name)

    analyzer = get_analyzer(app, model)
    schema, pk = get_schema(model, analyzer)

    if whoosh.index.exists_in(full_path):
        index = whoosh.index.open_dir(full_path, schema=schema)

    else:
        if not os.path.exists(full_path):
            os.makedirs(full_path)
        index = whoosh.index.create_in(full_path, schema)

    app.search_indexes[name] = index

    model.whoosh = Searcher(pk, index)
    model.whoosh_pk = pk
    model.query_class = QueryProxy

    if app.config.get('WHOOSH_RAM_CACHE', False):
        model.whoosh.searcher.set_caching_policy(storage=RamStorage())
    return index


def get_analyzer(app, model):
    analyzer = getattr(model, '__analyzer__', None)
    if not analyzer:
        analyzer = app.config.get('WHOOSH_ANALYZER', DEFAULT_WHOOSH_ANALYZER)
        setattr(model, '__analyzer__', analyzer)
    return analyzer


def get_schema(model, analyzer):
    schema = {}
    primary = None
    searchable = set(getattr(model, '__searchable__', []))

    for field in model.__table__.columns:
        # primary key id
        if field.primary_key:
            schema[field.name] = whoosh_fields.ID(
                stored=True, unique=True, sortable=True)
            primary = field.name

        if field.name not in searchable:
            continue

        # text types
        if isinstance(field.type, TEXT_TYPES):
            schema[field.name] = whoosh_fields.TEXT(analyzer=analyzer)

        elif isinstance(field.type, DATE_TYPES):
            is_unique = getattr(field, 'unique', False)
            schema[field.name] = whoosh_fields.DATETIME(unique=is_unique)

        elif isinstance(field.type, sql_types.Boolean):
            schema[field.name] = whoosh_fields.BOOLEAN()

        else:
            raise WhooshAlchemyError(
                'cannot index column of type %s' % field.type)

    return whoosh_fields.Schema(**schema), primary


def search_index(app, model):
    if not hasattr(app, 'search_indexes'):
        app.search_indexes = {}
    index = app.search_indexes.get(
        model.__tablename__, create_index(app, model))
    return index


flask_sqlalchemy.models_committed.connect(_post_flush)
