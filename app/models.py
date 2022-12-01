from app import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import login
from hashlib import md5
from time import time
import jwt
from app import app
from sqlalchemy_utils import aggregated
from app.experimentalconditions import number_stories_recommended

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index = True, unique = True)
    password_hash = db.Column(db.String(128))
    email_hash = db.Column(db.String(128))
    email_contact = db.Column(db.String(128))
    group = db.Column(db.Integer)
    first_login = db.Column(db.DateTime, index = True, default = datetime.utcnow)
    points_stories = db.relationship('Points_stories', backref = 'user', lazy = 'dynamic')
    points_invites = db.relationship('Points_invites', backref = 'user', lazy = 'dynamic')
    points_ratings = db.relationship('Points_ratings', backref = 'user', lazy = 'dynamic')
    points_logins = db.relationship('Points_logins', backref = 'user', lazy = 'dynamic')
    categories = db.relationship('Category', backref = 'user', lazy = 'dynamic')
    displayed_news = db.relationship('News', backref = 'user', lazy = 'dynamic')
    selected_news = db.relationship('News_sel', backref = 'user', lazy = 'dynamic')
    recommended_num = db.relationship('Num_recommended', backref = 'user', lazy = 'dynamic')
    divers = db.relationship('Diversity', backref = 'user', lazy = 'dynamic')
    again_showed = db.relationship('Show_again', backref = 'user', lazy = 'dynamic')
    last_visit = db.Column(db.DateTime, default=datetime.utcnow)
    phase_completed = db.Column(db.Integer, default = 1)
    fake = db.Column(db.Integer, default = 0)
    panel_id = db.Column(db.String(128), default = "noIDyet")
    activated = db.Column(db.Integer, default = 0)
    reminder_sent = db.Column(db.Integer, default = 0)
    # intake questionnaire
    age = db.Column(db.Integer)
    gender = db.Column(db.String(30))
    education = db.Column(db.Integer)
    newsinterest = db.Column(db.Integer)
    polorient = db.Column(db.Integer)
    # final questionnaire
    eval_diversity = db.Column(db.Integer)
    eval_personalization = db.Column(db.Integer)
    comments = db.Column(db.TEXT)
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    def set_email(self, email):
        self.email_hash = generate_password_hash(email)

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {'reset_password': self.id, 'exp':time() + expires_in},
            app.config['SECRET_KEY'], algorithm='HS256')
    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, app.config['SECRET_KEY'],
                            algorithms = ['HS256'])['reset_password']
        except:
            return
        return User.query.get(id)

    def __repr__(self):
        return '<User {}>'.format(self.username)

    @aggregated('logins_sum', db.Column(db.Integer))
    def sum_logins(self):
        return db.func.sum(Points_logins.points_logins)
    logins_sum = db.relationship('Points_logins')
    @aggregated('ratings_sum', db.Column(db.Numeric(5,1)))
    def sum_ratings(self):
        return db.func.sum(Points_ratings.points_ratings)
    ratings_sum = db.relationship('Points_ratings')
    @aggregated('invites_sum', db.Column(db.Integer))
    def sum_invites(self):
        return db.func.sum(Points_invites.points_invites)
    invites_sum = db.relationship('Points_invites')
    @aggregated('stories_sum', db.Column(db.Integer))
    def sum_stories(self):
        return db.func.sum(Points_stories.points_stories)
    stories_sum = db.relationship('Points_stories')

class Category(db.Model):
    id = db.Column(db.Integer, primary_key =True)
    topic1 = db.Column(db.Integer)
    topic2= db.Column(db.Integer)
    topic3 = db.Column(db.Integer)
    topic4 =db.Column(db.Integer)
    topic5 =db.Column(db.Integer)
    topic6 =db.Column(db.Integer)
    topic7 =db.Column(db.Integer)
    topic8 =db.Column(db.Integer)
    topic9 =db.Column(db.Integer)
    topic10 =db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, index = True, default = datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class News(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    article_id = db.Column(db.Integer)
    recommended = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, index = True, default = datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    url = db.Column(db.String(500))
    position = db.Column(db.Integer)

class News_sel(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    news_id = db.Column(db.Integer)
    starttime = db.Column(db.DateTime, index = True, default = datetime.utcnow)
    endtime = db.Column(db.DateTime, index = True, default = datetime.utcnow)
    time_spent = db.Column(db.Interval)
    rating = db.Column(db.Numeric(2,1), default = 0)
    rating2 = db.Column(db.Numeric(2,1), default = 0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    position = db.Column(db.Integer)
    recommended = db.Column(db.Integer)

class User_invite(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    timestamp = db.Column(db.DateTime, index = True, default = datetime.utcnow)
    stories_read = db.Column(db.Integer, default = 0)
    times_logged_in = db.Column(db.Integer, default = 0)
    user_host = db.Column(db.Integer, db.ForeignKey('user.id'))
    user_guest = db.Column(db.String(64), db.ForeignKey('user.username'))

class Points_stories(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    points_stories = db.Column(db.Integer, default = 0)
    timestamp = db.Column(db.DateTime, index = True, default = datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class Points_invites(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    user_guest_new = db.Column(db.String(64), db.ForeignKey('user_invite.user_guest'))
    points_invites = db.Column(db.Integer, default = 0)
    timestamp = db.Column(db.DateTime, index = True, default = datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class Points_ratings(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    points_ratings = db.Column(db.Numeric(5,1), default = 0.0)
    timestamp = db.Column(db.DateTime, index = True, default = datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class Points_logins(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    points_logins = db.Column(db.Integer, default = 0)
    timestamp = db.Column(db.DateTime, index = True, default = datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user_agent = db.Column(db.String(500))

class All_news(db.Model):
    id = db.Column(db.Integer, primary_key = True)

class Show_again(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    timestamp = db.Column(db.DateTime, index = True, default = datetime.utcnow)
    show_again = db.Column(db.Integer, default = 99)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class Similarities(db.Model):
    sim_id = db.Column(db.Integer, primary_key = True)
    # id_old = db.Column(db.Integer, db.ForeignKey('news_sel.news_id'))
    # we are a bit less strict than the previous line  and don't enforce here that it has been
    # selected before - databasewise, one could envision a scenario where
    # one wants to calculate similarities nonethess and that's OK
    id_old = db.Column(db.Integer, db.ForeignKey('all_news.id'))
    id_new = db.Column(db.Integer, db.ForeignKey('all_news.id'))
    similarity = db.Column(db.Numeric(10,9))

class Num_recommended(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    num_recommended = db.Column(db.Integer, default=number_stories_recommended)
    timestamp = db.Column(db.DateTime, index = True, default = datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    real = db.Column(db.Integer, default=number_stories_recommended)

class Diversity(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    diversity = db.Column(db.Integer, default=1)
    timestamp = db.Column(db.DateTime, index = True, default = datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    real = db.Column(db.Integer, default=number_stories_recommended)

class ShareData(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    platform = db.Column(db.String(500))
    timestamp = db.Column(db.DateTime, index = True, default = datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    articleId = db.Column(db.Integer)
    timeSpentSeconds = db.Column(db.Integer)
    scored = db.Column(db.Integer, default = 0)
    fromNudge = db.Column(db.Integer, default = 0)

class Points(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    totalPoints = db.Column(db.Integer)
    streak = db.Column(db.Integer)

class Nudges(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.DateTime, index = True, default = datetime.utcnow)
    nudgeType = db.Column(db.String(500))

class Scored(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.DateTime, index = True, default = datetime.utcnow)
    totalPoints = db.Column(db.Integer)

class Articles(db.Model):
    # TODO: IMPROVE DATABASE SCHEMA (e.g., reasonable length values for strings)
    id = db.Column(db.Integer, primary_key = True)
    title = db.Column(db.String(200))
    teaser = db.Column(db.Text())
    text = db.Column(db.Text())
    publisher = db.Column(db.String(40))
    topic = db.Column(db.String(40))
    url = db.Column(db.String(400))
    date = db.Column(db.DateTime, index = True, default = datetime.utcnow)
    imageUrl = db.Column(db.String(400))
    imageFilename = db.Column(db.String(100))
    lang = db.Column(db.String(5))


@login.user_loader
def load_user(id):
    return User.query.get(int(id))
