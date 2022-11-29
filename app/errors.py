from flask import render_template
from app import app, db

@app.errorhandler(404)
def not_found_error(error):
    return render_template('multilingual.404.html')

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    print(error)
    return render_template('multilingual.500.html'), 500
