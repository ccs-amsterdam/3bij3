"""
Functionality to calculate user points, scores, etc.
"""

from app import app
from app.models import User, Points_logins, User_invite, News_sel, Points_invites
from flask_login import current_user

from experimentalconditions import req_finish_days_min, req_finish_points_min

@app.context_processor
def may_finalize():
    '''Determines if a participant has fullfilled all requirements and is allowed to fill in the final questionnaire'''
    
    # TURN ON FOR CHEATING:
    # return {'may_finalize': True, 'has_finalized': False}

    if current_user.is_authenticated:
        return {'may_finalize': (days_logged_in()['different_dates'] >= req_finish_days_min and 
        points_overview()['points'] >= req_finish_points_min),
        'has_finalized': current_user.phase_completed == 255}   # 255 is the hardcoded value of final phase
    else:
        return {'may_finalize': False, 'has_finalized': False}  # could consider checking has_finalized but should be logically impossible

    
    



@app.context_processor
def days_logged_in():
    if current_user.is_authenticated:
        points_logins = Points_logins.query.filter_by(user_id = current_user.id).all()
        if points_logins is None:
            different_dates = 0
        else:
            dates = [item.timestamp.date() for item in points_logins]
            different_dates = len(list(set(dates)))
    else:
        different_dates = 0
    return dict(different_dates = different_dates)


@app.context_processor
def time_logged_in():
    if current_user.is_authenticated:
        try:
            first_login = current_user.first_login
            difference_raw = datetime.utcnow() - first_login
            difference = difference_raw.days
        except:
            difference = 0
    else:
        difference = 0
    return dict(difference = difference)


@app.context_processor
def number_read():
    if current_user.is_authenticated:
        try:
            selected_news = News_sel.query.filter_by(user_id = current_user.id).all()
            selected_news = len(selected_news)
        except:
            selected_news = 0
    else:
        selected_news = 0
    return dict(selected_news = selected_news)


@app.context_processor
def points_overview():
    if current_user.is_authenticated:
        user = User.query.filter_by(id = current_user.id).first()
        try:
            points_logins = user.sum_logins
            if points_logins is None:
                points_logins = 0
        except:
            points_logins = 0
        try:
            points_stories = user.sum_stories
            if points_stories is None:
                points_stories = 0
        except:
            points_stories = 0
        try:
            points_ratings = float(user.sum_ratings)
            if points_ratings is None:
                points_ratings = 0
        except:
            points_ratings = 0
        user_host = current_user.id
        user_invite_host = User_invite.query.filter_by(user_host = user_host).all()
        if user_invite_host is None:
            points_invites = 0
        else:
            number_invited = []
            for item in user_invite_host:
                item1 = item.__dict__
                if item1["stories_read"] >= 5 and item1["times_logged_in"] >= 2:
                    number_invited.append(item1['id'])
                    invites_points = Points_invites.query.filter_by(user_guest_new = item1['user_guest']).first()
                    if invites_points is None:
                         points_invites = Points_invites(user_guest_new = item1['user_guest'], points_invites = 5, user_id = current_user.id)
                         db.session.add(points_invites)
                         db.session.commit()
                    else:
                        points_invites = 0
                else:
                    points_invites = 0
        try:
            points_invites = user.sum_invites
            if points_invites is None:
                points_invites = 0
        except:
            points_invites = 0
        points = points_stories + points_invites + points_ratings + points_logins

        points_remaining = req_finish_points_min - (points_logins + points_stories + points_ratings)
        if points_remaining <= 0:
            points_remaining = 0
    else:
        points_stories = 0
        points_invites = 0
        points_ratings = 0
        points_logins = 0
        points = 0
        points_remaining = 0

    return dict(points = points, 
        points_ratings = points_ratings,
        points_stories = points_stories, 
        points_invites = points_invites, 
        points_logins = points_logins, 
        points_remaining = points_remaining)
