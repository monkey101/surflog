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
spots_col = connection.surf_log.spots
surf_sessions_col = connection.surf_log.surf_sessions

datetime_format='%m-%d-%Y %I:%M%p'

""" Utility methods """

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
        g.user = User.get_user_by_id(session['user_id'])



@app.template_filter('datetimeformat')
def datetimeformat(value, format=datetime_format):
    return value.strftime(format)


""" Register the mongo models """
class RootDocument(Document):
    structure = {}
    skip_validation = False
    use_autorefs = True
    use_dot_notation = True


@connection.register        
class User(RootDocument):
    __collection__ = 'users'
    __database__ = 'surf_log'

    structure = {
        'email': unicode,
        'username': unicode,
        'password_md5': unicode
    }
    validators = {
        'email': max_length(120),
        'username': max_length(50),
    }
    
    @classmethod
    def get_user_by_name(cls, username):
        return users_col.User.find_one({"username": username})

    @classmethod
    def get_user_by_id(cls, user_id):
        return users_col.User.find_one({"_id": user_id})

    def __repr__(self):
        return '<User %r>' % (self.username)


@connection.register        
class Buoy(RootDocument):
    __database__ = 'surf_log'
    __collection__ = 'buoys'
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

    """
    FIXME: ADD LATER
    indexes = [
        {
            'fields':[('loc', '2d')]
         },
     ]
    """
    @classmethod
    def get_by_id(cls, buoy_id):
        return buoys_col.Buoy.find_one({"_id": buoy_id})
    
    @classmethod
    def get_all(cls):
        return buoys_col.Buoy.find()

    def __repr__(self):
        return '<Buoy %r>' % (self._id)

@connection.register        
class SurfSession(RootDocument):
    __database__ = 'surf_log'
    __collection__ = 'surf_sessions'
    structure = {
        'when': datetime,
        'yyyymmdd': unicode,
        'duration': int, # in minutes
        'rating': int,
        'spot': ObjectId,
        'user_email': unicode,
        'notes': unicode
    }

    default_values = {'notes': u'', 'when': datetime.now(), 'duration': 0}
    
    @classmethod
    def get_by_id(cls, surf_session_id):
        return surf_sessions_col.SurfSession.find_one({'_id': ObjectId(surf_session_id)})
    
    @classmethod
    def get_by_user(cls, user_email):
        return surf_sessions_col.SurfSession.find({'user_email': user_email})
    
    def __repr__(self):
        return '<SurfSession for %r at %r on %r>' % (self.user_email, self.spot, self.when)

@connection.register
class SurfSpot(RootDocument):
    __database__ = 'surf_log'
    __collection__ = 'spots'
    structure = {
        'loc': [float], #x,y
        'name': unicode,
        'description': unicode,
    }
    default_values = {'loc':[0,0], 'name': u'', 'description': u''}

    @classmethod
    def get_by_id(cls, spot_id):
        return spots_col.SurfSpot.find_one({"_id": spot_id})

    @classmethod
    def get_all(cls):
        return spots_col.SurfSpot.find()
    
    def __repr__(self):
        return '<SurfSpot %r>' % (self.name)        

@connection.register
class SurfConditions(RootDocument):
    __database__ = 'surf_log'
    __collection__ = 'surf_conditions'
    structure = {
        '_id': unicode, #hash(buoy_id + yyyymmdd)
        'day': unicode, #yyyymmdd
        'hour': [{unicode:unicode}], # array of dicts of condition by hour (0 - 23)
    }
    def __repr__(self):
        return '<SurfConditions %r>' % (self._id)        

""" Define the routes and controllers """

@app.route('/')
def home():
    buoys = Buoy.get_all()
    return render_template('home.html', count=buoys.count(), buoys=buoys)

@app.route('/buoy/<buoy_id>', methods=['GET', 'POST'])
def buoy(buoy_id):
    buoy = Buoy.get_by_id(buoy_id)
    if request.method == 'POST':
        if g.user is None:
            flash('You cannot edit a buoy without being logged in', 'error')            
        else:
            buoy.description = unicode(request.form['description'])
            buoy.save()
            flash('Buoy saved', 'success')
    return render_template('buoy.html', buoy=buoy)

@app.route('/spot/<int:spot_id>', methods=['GET', 'POST'])
def spot(spot_id):
    spot = connection.SurfSpot()
    if spot_id:
        spot = SurfSpot.get_by_id(spot_id)

    if request.method == 'POST':
        if g.user is None:
            flash('You cannot edit a spot without being logged in', 'error')            
        else:
            spot.name = unicode(request.form['name'])
            spot.description = unicode(request.form['description'])
            spot.loc[0] = float(request.form['longitude'])
            spot.loc[1] = float(request.form['latitude'])
            spot.save()
            flash('Spot saved', 'success')
    return render_template('spot.html', spot=spot)


@app.route('/surf_session/<surf_session_id>', methods=['GET', 'POST'])
def surf_session(surf_session_id):
    if g.user is None:
        flash('You cannot create a session without being logged in', 'error')
        return redirect(url_for("login"))

    
    surf_session = connection.SurfSession()
    if surf_session_id != '0':
        print surf_session_id

        surf_session = SurfSession.get_by_id(surf_session_id)
        print surf_session
    if request.method == 'POST':
        surf_session.spot = ObjectId(request.form['spot'])
        surf_session.notes = unicode(request.form['notes'])

        surf_session.when = datetime.strptime(request.form['when'], datetime_format)        
        surf_session.duration = int(request.form['duration'])        
        surf_session.user_email = g.user.email
        surf_session.save()
        flash('Spot saved', 'success')
        return redirect(url_for('surf_session', surf_session_id=surf_session._id))

    # FIXME: only return users spots ordered by num times surfed
    spots = SurfSpot.get_all()
    return render_template('surf_session.html', surf_session=surf_session, spots=spots)


        
@app.route('/user_sessions', methods=['GET'])
def user_sessions():
    if g.user is None:
        flash('You cannot view your sessions without being logged in', 'error')
        return redirect(url_for("login"))
    sessions = SurfSession.get_by_user(g.user.email)
    print sessions.count()
    return render_template('user_sessions.html', sessions=sessions)


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
        elif User.get_user_by_name(request.form['username']) is not None:
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
        user = User.get_user_by_name(request.form['username'])
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
