# Flask-WhooshAlchemy3
[![PyPI version](https://badge.fury.io/py/flask-whooshalchemy3.svg)](https://badge.fury.io/py/flask-whooshalchemy3)
[![license](https://img.shields.io/github/license/blakev/flask-whooshalchemy3.svg)]()

Whoosh indexing capabilities for Flask-SQLAlchemy, Python 3 compatibility fork.
Performance improvements and suggestions are readily welcome.

Inspired from gyllstromk's [Flask-WhooshAlchemy](https://github.com/gyllstromk/Flask-WhooshAlchemy).

- [Whoosh](http://whoosh.readthedocs.io/en/latest/intro.html)
- [Flask-SqlAlchemy](http://flask-sqlalchemy.pocoo.org/2.1/)


## Install

```bash
$ pip install flask-whooshalchemy3
```

..alternatively from source,

```bash
$ pip install git+git://github.com/blakev/Flask-WhooshAlchemy3.git@master
```


## Quickstart

```python

from datetime import datetime

import flask_sqlalchemy
import flask_whooshalchemy
from whoosh.analysis import StemmingAnalyzer

db = flask_sqlalchemy.SQLAlchemy()

class BlogPost(db.Model):
    __tablename__ = 'posts'
    __searchable__ = ['title', 'content', 'summary']  # indexed fields
    __analyzer__ = StemmingAnalyzer()
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), unique=True)
    content = db.Column(db.Text(32*1024))
    summary = db.Column(db.String(1024))
    created = db.Column(db.DateTime, default=datetime.utcnow)

```

Committing model instances to the session will write or update the Whoosh index.

```python
db.session.add(BlogPost(title='First Post!', content='This is awesome.'))
db.session.commit()
```

Searching is done via `Model.query.search(..)`. However, the request must be done within the Flask
request context otherwise the database connection may not be established.

```python
@app.route('/posts')
def posts():
    num_posts = min(request.args.get('limit', 10), 50)
    query = request.args.get('q', '')
    results = BlogPost.query.search(query, limit=num_posts)
```


Results are ordered by Whoosh's ranking-algorithm, but can be overwritten with SQLAlchemy `.order_by`.

```python
yesterday = datetime.utcnow() - timedelta(days=1)
results = BlogPost.query
            .filter(BlogPost.created > yesterday)
            .search('first')
            .order_by(desc(BlogPost.created))
```

## Flask Configuration

`WHOOSH_ANALYZER` **(whoosh.Analyzer)**
- Sets the global text analyzer, available options [in Whoosh documentation](http://whoosh.readthedocs.io/en/latest/analysis.html). 
- Default: `StemmingAnalyzer`.

`WHOOSH_INDEX_PATH` (str)
- File path to where the text indexes will be saved. 
- Default: `{cwd}/.indexes/*`

`WHOOSH_INDEXING_CPUS` (int)
- The number of system processes to spawn for indexing new and modified documents.
- Default: `2`

`WHOOSH_INDEXING_RAM` (int)
- The amount of RAM, in megabytes, to reserve per indexing process for data processing.
- Default: `256`

`WHOOSH_RAM_CACHE` (bool)
- Allows common queries and their fields to be stored in cache, in RAM.
- Default: `False`

## License

```text
MIT License

Copyright (c) 2017 Blake VandeMerwe

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```