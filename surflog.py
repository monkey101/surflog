"""
    SurfLog
    ~~~~~~~~

    A surf session logging application written with Flask and mongodb.

"""
from datetime import datetime
import time
import calendar

from flask import Flask
from flask import Flask, request, session, url_for, redirect, \
     render_template, abort, g, flash

from werkzeug import check_password_hash, generate_password_hash
from flaskext.wtf import ValidationError, Form, TextField, PasswordField, \
     BooleanField, Required, validators

from mongokit import Connection, Document
from pymongo.objectid import ObjectId
from pymongo import dbref


# configuration
MONGODB_HOST = 'localhost'
MONGODB_PORT = 27017
DEBUG = True
SECRET_KEY = 'development key'
SESSION_KEY = ''
CSRF_ENABLED = False  # FIXME: Why isn't CSRF_ENABLED working?

# create the application object
app = Flask(__name__)
app.config.from_object(__name__)


# connect to the database
connection = Connection(app.config['MONGODB_HOST'],
                        app.config['MONGODB_PORT'])

# Globals
buoys_col = connection.surf_log.buoys
users_col = connection.surf_log.users
spots_col = connection.surf_log.spots
surf_sessions_col = connection.surf_log.surf_sessions

# used in the template filter and for creating the datetime from the form
datetime_format='%m-%d-%Y %I:%M%p'

""" Utility methods """

def max_length(length):
    """ Validator for string fields """
    def validate(value):
        if len(value) <= length:
            return True
        raise Exception('%s must be at most %s characters long' % length)
    return validate

def local_to_utc(dt):
    """ Converts from local time to UTC """
    utc_struct_time = time.gmtime(time.mktime(dt.timetuple()))
    return datetime.fromtimestamp(time.mktime(utc_struct_time))

def utc_to_local(dt):
    """ Converts from UTC to local time """
    secs = calendar.timegm(dt.timetuple())
    return datetime.fromtimestamp(time.mktime(time.localtime(secs)))

@app.before_request
def before_request():
    """look up the current user so that we know he's there.
    FIXME: Use mongo for session tracking
    """
    g.user = None
    if 'user_id' in session:
        g.user = User.get_user_by_id(session['user_id'])

@app.template_filter('datetime_format_utc')
def datetime_format_utc(value, format=datetime_format):
    """ Used in the templates for date formatting """
    local_time = utc_to_local(value)
    return local_time.strftime(format)



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
        'email': max_length(50),
        'username': max_length(50),
    }

    @classmethod
    def get_user_by_email(cls, email):
        return users_col.User.find_one({"email": email})

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
        '_id': unicode,
        'loc': (float,float), # long, lat
        'description': unicode,
        'online': bool
        # FIXME: do we need this? 'last_update': datetime.datetime
    }
    validators = {
        '_id': max_length(5),
        'description': max_length(120)
    }
    default_values = {'online': True, 'loc':(float(0), float(0))}

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
class SurfSpot(RootDocument):
    __database__ = 'surf_log'
    __collection__ = 'spots'
    structure = {
        'loc': (float,float), #long, lat
        'name': unicode,
        'description': unicode,
        'buoy': Buoy
    }
    default_values = {'loc':(0,0), 'name': u'', 'description': u''}

    @classmethod
    def get_by_id(cls, spot_id):
        return spots_col.SurfSpot.find_one({"_id": ObjectId(spot_id)})

    @classmethod
    def get_all(cls):
        return spots_col.SurfSpot.find()
    
    def __repr__(self):
        return '<SurfSpot %r>' % (self.name)        

@connection.register        
class SurfSession(RootDocument):
    __database__ = 'surf_log'
    __collection__ = 'surf_sessions'
    structure = {
        'when': datetime,
        'yyyymmdd': unicode,
        'duration': int, # in minutes
        'rating': int,
        'spot': SurfSpot,
        'user_email': unicode,
        'notes': unicode
    }

    default_values = {'notes': u'', 'when': datetime.utcnow(), 'duration': 0}
    
    @classmethod
    def get_by_id(cls, surf_session_id):
        return surf_sessions_col.SurfSession.find_one({'_id': ObjectId(surf_session_id)})

    @classmethod
    def get_by_user(cls, user_email):
        return surf_sessions_col.SurfSession.find_one({'user_email': user_email})

    def __repr__(self):
        return '<SurfSession for %r at %r on %r>' % (self.user_email, self.spot, self.when)

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
            if request.form.get('online'):
                buoy.online = True
            else:
                buoy.online = False
            buoy.save()
            flash('Buoy saved', 'success')
    return render_template('buoy.html', buoy=buoy)

@app.route('/spot/<spot_id>', methods=['GET', 'POST'])
def spot(spot_id):
    spot = connection.SurfSpot()
    if spot_id != '0':
        spot = SurfSpot.get_by_id(spot_id)

    if request.method == 'POST':
        if g.user is None:
            flash('You cannot edit a spot without being logged in', 'error')            
        else:
            spot.name = unicode(request.form['name'])
            spot.description = unicode(request.form['description'])
            spot.loc = (float(request.form['longitude']), float(request.form['latitude']))
            spot.buoy = Buoy.get_by_id(request.form['buoy_id'])
            spot.save()
            flash('Spot saved', 'success')
            return redirect(url_for('spot', spot_id=spot._id))
            
    return render_template('spot.html', spot=spot)


@app.route('/surf_session/<surf_session_id>', methods=['GET', 'POST'])
def surf_session(surf_session_id):
    if g.user is None:
        flash('You cannot create a session without being logged in', 'error')
        return redirect(url_for("login"))
    
    surf_session = connection.SurfSession()
    if surf_session_id != '0':
        surf_session = SurfSession.get_by_id(surf_session_id)

    if request.method == 'POST':
        surf_session.spot = SurfSpot.get_by_id(request.form['spot'])
        surf_session.notes = unicode(request.form['notes'])

        # convert date to utc before importing
        surf_session.when = \
            local_to_utc(datetime.strptime(request.form['when'], datetime_format))
        surf_session.duration = int(request.form['duration'])        
        surf_session.user_email = g.user.email
        surf_session.save()
        flash('Session saved', 'success')
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

class RegistrationForm(Form):
    """ Use WTForms for validation """
    username = TextField('Username', [validators.Length(min=4, max=50)])
    email = TextField('Email Address', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.Required(),
        validators.EqualTo('confirm', message='Passwords must match')
    ])
    confirm = PasswordField('Repeat Password')
    accept_tos = BooleanField('I accept the TOS', [validators.Required()])
    
    def validate_email(form, field):
        if User.get_user_by_email(field.data):
            raise ValidationError('The email is already taken')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registers the user."""
    if g.user:
        return redirect(url_for('home'))

    form = RegistrationForm()
    if request.method == "POST" and form.validate():
        user = users_col.User()
        user.username = unicode(form.username.data)
        user.email = unicode(form.email.data)
        user.password_md5 = unicode(generate_password_hash(form.password.data))
        user.save()
        g.user = user
        print user
        flash('You were successfully registered and can login now', 'success')
        return redirect(url_for('login'))

    if form.errors:
        flash(form.errors, 'error')
    return render_template('register.html', form=form)


class LoginForm(Form):
    """ Use WTForms for validation """
    email = TextField('Email Address', [validators.Required()])
    password = PasswordField('Password', [validators.Required()])
    

@app.route('/login', methods=['GET', 'POST'])
def login():
    if g.user:
        return redirect(url_for('home'))
    
    form = LoginForm()
    if request.method == 'POST' and form.validate():
        user = User.get_user_by_email(request.form['email'])
        if user is None:
            flash('Invalid email', 'error')
        elif not check_password_hash(user['password_md5'],
                                     request.form['password']):
            flash('Invalid password', 'error')
        else:
            flash('You were logged in', 'success')
            session['user_id'] = user['_id']
            return redirect(url_for('home'))
    if form.errors:
        flash(form.errors, 'error')
    return render_template('login.html', form=form)


@app.route('/logout')
def logout():
    """Logs the user out."""
    flash('You were logged out', 'success')
    session.pop('user_id', None)
    return redirect(url_for('home'))

# Run Flask!
if __name__ == '__main__':
    app.run()
