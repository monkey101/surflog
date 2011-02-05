"""
    SurfLog
    ~~~~~~~~

    A surf session logging application written with Flask and mongodb.

"""
from datetime import datetime

from flask import Flask
from flask import Flask, request, session, url_for, redirect, \
     render_template, abort, g, flash
from werkzeug import check_password_hash, generate_password_hash

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

buoys_col = connection.surf_log.buoys
users_col = connection.surf_log.users

""" Utility methods """
def get_user_by_name(username):
    return users_col.find_one({"username": username})


def get_user_by_id(user_id):
    return users_col.find_one({"_id": user_id})


def max_length(length):
    """ Validator for string fields """
    def validate(value):
        if len(value) <= length:
            return True
        raise Exception('%s must be at most %s characters long' % length)
    return validate


@app.before_request
def before_request():
    """look up the current user so that we know he's there.
    """
    g.user = None
    if 'user_id' in session:
        g.user = get_user_by_id(session['user_id'])


""" Register the mongo models """

@connection.register        
class User(Document):
    __collection__ = 'surf_log'
    __database__ = 'users'

    structure = {
        'username': unicode,
        'email': unicode,
        'password_md5': unicode
    }
    validators = {
        'username': max_length(50),
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
        '_id': unicode,
        'loc': [float],
        'description': unicode}

    validators = {
        '_id': max_length(5),
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

@connection.register        
class SurfSession(Document):
    structure = {
        'time': datetime,
        'duration': int, # in minutes
        'location': unicode
    }
    use_dot_notation = True
    
        
""" Define the routes and controllers """
    
@app.route('/')
def index():
    buoys = buoys_col.find()
    return render_template('index.html', count=buoys.count(), buoys=buoys)



@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registers the user."""
    if g.user:
        return redirect(url_for('index'))
    error = None
    if request.method == 'POST':
        if not request.form['username']:
            error = 'You have to enter a username'
        elif not request.form['email'] or \
                 '@' not in request.form['email']:
            error = 'You have to enter a valid email address'
        elif not request.form['password']:
            error = 'You have to enter a password'
        elif get_user_by_name(request.form['username']) is not None:
            error = 'The username is already taken'
        else:
            user = users_col.User()
            user.username = unicode(request.form['username'])
            user.email = unicode(request.form['email'])
            user.password_md5 = unicode(generate_password_hash(request.form['password']))
            user.save()
            g.user = user
            flash('You were successfully registered and can login now')
            return redirect(url_for('login'))
    return render_template('register.html', error=error)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Logs the user in."""
    if g.user:
        return redirect(url_for('index'))
    error = None
    if request.method == 'POST':
        user = get_user_by_name(request.form['username'])
        print user
        if user is None:
            error = 'Invalid username'
        elif not check_password_hash(user['password_md5'],
                                     request.form['password']):
            error = 'Invalid password'
        else:
            flash('You were logged in')
            session['user_id'] = user['_id']
            return redirect(url_for('index'))
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    """Logs the user out."""
    flash('You were logged out')
    session.pop('user_id', None)
    return redirect(url_for('index'))

# Run Flask!
if __name__ == '__main__':
    app.run()