import os
import ast
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = 465
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_USE_TLS = False
    MAIL_USE_SSL = True
    ADMINS = ast.literal_eval(os.environ.get('ADMINS', "['admin@example.com']"))
    MYSQL_HOST=os.environ.get('MYSQL_HOST')
    MYSQL_PORT=os.environ.get('MYSQL_PORT')
    MYSQL_DB=os.environ.get('MYSQL_DB')
    MYSQL_USER=os.environ.get('MYSQL_USER')
    MYSQL_PASSWORD=os.environ.get('MYSQL_PASSWORD')
    # for now, let's hardcode the supported languages. 
    # TODO: think of a way to do this dynamically/automatically
    # LANGUAGES = ['en', 'nl']
    LANGUAGES = ['nl']

    SQLALCHEMY_DATABASE_URI = f"mysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
