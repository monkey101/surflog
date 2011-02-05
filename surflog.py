"""
    SurfLog
    ~~~~~~~~

    A surf session logging application written with Flask and mongodb.

"""

from flask import Flask
from flask import Flask, request, session, url_for, redirect, \
     render_template, abort, g, flash

from mongokit import Connection, Document

# configuration
MONGODB_HOST = 'localhost'
MONGODB_PORT = 27017
DEBUG = True
SECRET_KEY = 'development key'

# create the little application object
app = Flask(__name__)
app.config.from_object(__name__)

# connect to the database
connection = Connection(app.config['MONGODB_HOST'],
                        app.config['MONGODB_PORT'])


# validator for string fields
def max_length(length):
    def validate(value):
        if len(value) <= length:
            return True
        raise Exception('%s must be at most %s characters long' % length)
    return validate


@connection.register        
class User(Document):
    __collection__ = 'surf_log'
    __database__ = 'users'
    structure = {
        'name': unicode,
        'email': unicode,
    }
    validators = {
        'name': max_length(50),
        'email': max_length(120)
    }
    use_dot_notation = True
    def __repr__(self):
        return '<User %r>' % (self.name)

@connection.register        
class Buoy(Document):
    __collection__ = 'surf_log'
    __database__ = 'buoys'
    structure = {
        'buoy_id': unicode,
        'loc': [float],
        'description': unicode}

    validators = {
        'buoy_id': max_length(5),
        'description': max_length(120)
    }
    use_dot_notation = True

    """
    FIXME: ADD LATER
    indexes = [
         {
             'fields':[('loc', '2d')]
         },
     ]
     """
    
@app.route('/')
def index():
    print 'index page'
    buoys = connection.surf_log.buoys.find()
    print buoys.count()
    return render_template('index.html', buoys=buoys)

if __name__ == '__main__':
    app.run()
