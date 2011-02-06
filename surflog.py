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
from pymongo.objectid import ObjectId


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
    return users_col.User.find_one({"username": username})


def get_user_by_id(user_id):
    return users_col.User.find_one({"_id": user_id})


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
    FIXME: Use mongo for session tracking
    """
    g.user = None
    if 'user_id' in session:
        g.user = get_user_by_id(session['user_id'])



""" Register the mongo models """
class RootDocument(Document):
     structure = {}
     skip_validation = False
     use_autorefs = True


@connection.register        
class User(RootDocument):
    __collection__ = 'surf_log'
    __database__ = 'users'

    structure = {
        'email': unicode,
        'username': unicode,
        'password_md5': unicode
    }
    validators = {
        'email': max_length(120),
        'username': max_length(50),
    }
    use_dot_notation = True
    def __repr__(self):
        return '<User %r>' % (self.username)


@connection.register        
class Buoy(RootDocument):
    __collection__ = 'surf_log'
    __database__ = 'buoys'
    structure = {
        '_id': unicode, #FIXME: what do i do to override the _id to be the 5 char buoy id?
        'loc': [float],
        'description': unicode, 
        # FIXME: do we need this? 'last_update': datetime.datetime
    }
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
class SurfSession(RootDocument):
    __collection__ = 'surf_log'
    __database__ = 'buoys'
    structure = {
        'time': datetime,
        'yyyymmdd': unicode,
        'duration': int, # in minutes
        'location': unicode,
        'rating': int,
        'spot_id': ObjectId,
        'user_email': unicode
    }
    use_dot_notation = True


@connection.register
class SurfSpot(RootDocument):
    __collection__ = 'surf_log'
    __database__ = 'buoys'
    structure = {
        'loc': [float], #x,y
        'name': unicode,
        'description': unicode,        
    }
        

@connection.register
class SurfConditions(RootDocument):
    __collection__ = 'surf_log'
    __database__ = 'buoys'
    structure = {
        '_id': unicode, #hash(buoy_id + yyyymmdd)
        'day': unicode, #yyyymmdd
        'hour': [{unicode:unicode}], # array of dicts of condition by hour (0 - 23)
    }
    use_dot_notation = True


""" Define the routes and controllers """

@app.route('/')
def home():
    buoys = buoys_col.Buoy.find()
    return render_template('home.html', count=buoys.count(), buoys=buoys)


@app.route('/buoy/<buoy_id>', methods=['GET', 'POST'])
def buoy(buoy_id):
    buoy = buoys_col.Buoy.find_one({"_id": buoy_id})
    if request.method == 'POST':
        if g.user is None:
            flash('You cannot edit a buoy without being logged in', 'error')            
        else:
            print buoy
            buoy.description = unicode(request.form['description'])
            buoy.save()
            flash('Buoy saved', 'success')
    return render_template('buoy.html', buoy=buoy)

@app.route('/surf_session/<session_id>', methods=['GET', 'POST'])
def surf_session(session_id):
    if g.user is None:
        return redirect(url_for("login"))
    if request.method == 'POST':
        pass
        
    return render_template('surf_session.html', session=session)
        
@app.route('/user_sessions', methods=['GET'])
def user_sessions():
    if g.user is None:
        return redirect(url_for("login"))
        
    return render_template('user_sessions.html', session=session)


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registers the user."""
    if g.user:
        return redirect(url_for('home'))
    if request.method == 'POST':
        if not request.form['username']:
            flash('You have to enter a username', 'error')
        elif not request.form['email'] or \
                 '@' not in request.form['email']:
            flash('You have to enter a valid email address', 'error')
        elif not request.form['password']:
            flash('You have to enter a password', 'error')
        elif not request.form['password2']:
            flash('Your passwords do not match', 'error')
        elif get_user_by_name(request.form['username']) is not None:
            flash('The username is already taken', 'error')
        else:
            user = users_col.User()
            user.username = unicode(request.form['username'])
            user.email = unicode(request.form['email'])
            user.password_md5 = unicode(generate_password_hash(request.form['password']))
            user.save()
            g.user = user
            flash('You were successfully registered and can login now', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Logs the user in."""
    if g.user:
        return redirect(url_for('home'))
    if request.method == 'POST':
        user = get_user_by_name(request.form['username'])
        if user is None:
            flash('Invalid username', 'error')
        elif not check_password_hash(user['password_md5'],
                                     request.form['password']):
            flash('Invalid password', 'error')
        else:
            flash('You were logged in', 'success')
            session['user_id'] = user['_id']
            return redirect(url_for('home'))
    return render_template('login.html')


@app.route('/logout')
def logout():
    """Logs the user out."""
    flash('You were logged out', 'success')
    session.pop('user_id', None)
    return redirect(url_for('home'))

# Run Flask!
if __name__ == '__main__':
    app.run()