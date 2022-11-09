import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    # SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or  'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_DATABASE_URI = "mysql://newsflow:Bob416!@172.17.0.1:3307/3bij3"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = 465
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_USE_TLS = False
    MAIL_USE_SSL = True
    ADMINS = os.environ.get('ADMINS', 'admin@example.com')
    # NEW MYSQL CONFIG
    # host = '172.17.0.1', database = '3bij3', user = 'newsflow', password = 'Bob416!', port=3307)
    MYSQL_HOST=os.environ.get('MYSQL_HOST')
    MYSQL_PORT=os.environ.get('MYSQL_PORT')
    MYSQL_DB=os.environ.get('MYSQL_DB')
    MYSQL_USER=os.environ.get('MYSQL_USER')
    MYSQL_PASSWORD=os.environ.get('MYSQL_PASSWORD')