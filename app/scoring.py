"""
Functionality to calculate user points, scores, etc.
"""

from app import app, db
from app.models import User, Points_logins, User_invite, News_sel, Points_invites
from flask_login import current_user, login_required

from app.experimentalconditions import req_finish_days, req_finish_points



from sqlalchemy.orm import Session

@app.context_processor
def get_leaderboard_score():
    '''Returns the current score of the user. In case the user does not exist, create it and assign a score of 0.'''
    try:
        user_id = current_user.id
    except AttributeError as err:
        return{"error":err}

    # check to see if user exists in leaderboard table
    sql = "SELECT * FROM leaderboard WHERE user_id = {}".format(user_id)
    result = db.session.execute(sql)
    # if user not in leaderboard table add them with a score of 0
    if(result.rowcount == 0):
        sql = "INSERT INTO leaderboard(user_id, totalPoints,streak) VALUES ({},{},{})".format(user_id,0,0)
        print("Inserting row in leaderboard table for userid {}".format(user_id))
        db.session.execute(sql)
        db.session.commit()
        currentScore = 0
    else:
        # read current user score
        sql = "SELECT totalPoints FROM leaderboard WHERE user_id = {}".format(user_id)
        result = db.session.execute(sql).fetchone()
        currentScore = result[0]
    return {"currentScore": currentScore}

@app.context_processor
def get_leaderboard_multiplier(dryrun=False):
    try:
        user_id = current_user.id
    except AttributeError as err:
        return{"error":err}

    multiplier = 1

    sql = "SELECT * FROM share_data WHERE user_id = {} AND timestamp > DATE_SUB(NOW(), INTERVAL 24 HOUR)".format(user_id)
    result = db.session.execute(sql)

    if(result.rowcount > 0):
        sql = "SELECT * FROM share_data WHERE user_id = {} AND timestamp < DATE_SUB(NOW(), INTERVAL 24 HOUR) AND timestamp > DATE_SUB(NOW(), INTERVAL 48 HOUR)".format(user_id)
        result = db.session.execute(sql)

        if(result.rowcount > 0):
            multiplier = 2
            sql = "SELECT * FROM share_data WHERE user_id = {} AND timestamp < DATE_SUB(NOW(), INTERVAL 48 HOUR) AND timestamp > DATE_SUB(NOW(), INTERVAL 72 HOUR)".format(user_id)
            result = db.session.execute(sql)

            if(result.rowcount > 0):
                multiplier = 3
                sql = "SELECT * FROM share_data WHERE user_id = {} AND timestamp < DATE_SUB(NOW(), INTERVAL 72 HOUR) AND timestamp > DATE_SUB(NOW(), INTERVAL 96 HOUR)".format(user_id)
                result = db.session.execute(sql)

                if(result.rowcount > 0):
                    multiplier = 4
                    sql = "SELECT * FROM share_data WHERE user_id = {} AND timestamp < DATE_SUB(NOW(), INTERVAL 96 HOUR) AND timestamp > DATE_SUB(NOW(), INTERVAL 120 HOUR)".format(user_id)
                    result = db.session.execute(sql)

                    if(result.rowcount > 0):
                        multiplier = 5


    print("The multiple for user {} is {}".format(user_id, multiplier))

    if not dryrun:
        sql = "UPDATE leaderboard SET streak = {} WHERE user_id = {}".format(multiplier, user_id)
        db.session.execute(sql)
        db.session.commit()
        print("Updated db")
    return {"multiplier":multiplier}

@app.context_processor
def update_leaderboard_score(dryrun=False):
    try:
        user_id = current_user.id
    except AttributeError as err:
        return{"error":err}
    ## start with diversity share score
    # get all topics of all available articles
    sql = "SELECT DISTINCT articles.topic FROM articles"
    allArticleTopics = [e[0] for e in db.session.execute(sql).fetchall()]

    # get all topics of all the articles that the user has shared in the last three days ??
    sql = "SELECT DISTINCT articles.topic FROM share_data INNER JOIN articles ON \
        share_data.articleId = articles.id WHERE share_data.scored = 1 AND share_data.timestamp > DATE_SUB(NOW(), INTERVAL 72 HOUR) AND share_data.user_id={}".format(user_id)
    shareArticleTopics = [e[0] for e in db.session.execute(sql).fetchall()]

    # create a list of which topics are missing from the topics the user has shared
    notSharedTopics = list(set(allArticleTopics) - set(shareArticleTopics))

    sql = "SELECT share_data.id, share_data.articleId, articles.topic FROM share_data INNER JOIN articles ON share_data.articleId = articles.id WHERE share_data.scored = 0 AND share_data.user_id={}".format(user_id)
    unScoredShares =  db.session.execute(sql).fetchall()
    addedScore = 0

    # call other functions to get relevant user info
    print(user_id)
    currentScore = get_leaderboard_score().get("currentScore",None)
    multiplier = get_leaderboard_multiplier().get("multiplier",None)
    if currentScore is None or multiplier is None:
        return {"error":"There is an upstrema error that prevents us from calculating scores."}

    if(len(unScoredShares) == 0):
        # return early if nothing has changed
        return {"currentScore":currentScore}

    for share in unScoredShares:
        # check to see how many scores have occured in the last 24 hours, if 10 stop scoring
        sql = "SELECT * FROM scored WHERE user_id = {} AND timestamp > DATE_SUB(NOW(), INTERVAL 24 HOUR)".format(format(user_id))                
        if(db.session.execute(sql).rowcount < 10):
            print("Topic is {}".format(share[2]))
            if(share[2] in notSharedTopics):
                print("extra score")
                addedScore = addedScore + (multiplier * 2)
                sql = "INSERT INTO scored (user_id, totalPoints) VALUES ({},{})".format(user_id,multiplier * 2)
                db.session.execute(sql)
                db.session.commit()
            else:
                print("regular score")
                addedScore = addedScore + (multiplier)
                sql = "INSERT INTO scored (user_id, totalPoints) VALUES ({},{})".format(user_id,multiplier)
                db.session.execute(sql)
                db.session.commit()
            # mark share as scored
            sql = "UPDATE share_data SET scored=1 WHERE id = {}".format(share[0])
            db.session.execute(sql)
            db.session.commit()
        else:
            # set all remaining unscored shares to 1 for this user
            sql = "UPDATE share_data SET scored=1 WHERE user_id = {}".format(user_id)
            db.session.execute(sql)
            db.session.commit()
            print("Reached max of 10 shared scored in a 24 hour period")
            break

    pointsAfterCalculation = currentScore + addedScore

    if not dryrun:
        # update the leaderboard table to add the newly assigned leaderboard
        sql = "UPDATE leaderboard SET totalPoints = {} WHERE user_id = {}".format(pointsAfterCalculation, user_id)
        print("Updating leaderboard for userid {}. New point total is {}".format(user_id, pointsAfterCalculation))
        db.session.execute(sql)
        db.session.commit()

    return {"pointsAfterCalculation": pointsAfterCalculation}










@app.context_processor
def may_finalize():
    '''Determines if a participant has fullfilled all requirements and is allowed to fill in the final questionnaire'''
    
    # TURN ON FOR CHEATING:
    # return {'may_finalize': True, 'has_finalized': False}

    if current_user.is_authenticated:
        return {'may_finalize': (days_logged_in()['different_dates'] >= req_finish_days and 
        points_overview()['points'] >= req_finish_points),
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

        points_remaining = req_finish_points - (points_logins + points_stories + points_ratings)
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
