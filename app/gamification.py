'''
This file contains functionality for trying to engage the user (in some conditions,
in paricular the engagement leaderboard as well as nudging functionality
'''

from app import app, db
from app.models import Nudges
from app.experimentalconditions import select_nudging, number_stories_on_newspage
from flask_login import current_user

import random
import logging
logger = logging.getLogger('app.gamification')

@app.context_processor
def get_nudge():
    '''determines whether the user is to receive a nudge notification, and if so, which one'''
    
    # default no nudge
    nudge = {"nudge": "no"}   
    try:
        gets_nudge = select_nudging()   # only do nudges if in correct experimental group
    except AttributeError:              # usually: user not logged in
        return nudge

    if not gets_nudge:
        return nudge

    nudge = _get_sharing_nudge(nudge)
    if nudge.get('nudge') != 'yes':
        nudge = _get_reading_nudge(nudge)
    logger.debug(f"returning nudge {nudge}")
    return nudge


def _get_sharing_nudge(nudge):
    '''adds sharing nudges to the nudge dict'''

    sql = "SELECT COUNT(*) FROM share_data WHERE user_id = {} AND timestamp > DATE_SUB(NOW(), INTERVAL 24 HOUR)".format(current_user.id)
    nudge["sql"] = sql # is this even necessary, storing in the dict?
    number_shared_24h = db.session.execute(sql).scalar()
    logger.debug(f"Number of shares in the last 24 hours: {number_shared_24h}")
    nudgeDone = 0

    if number_shared_24h == 0:
        sql = "SELECT COUNT(*) FROM nudges WHERE user_id = {} AND nudgeType='recency' AND timestamp > DATE_SUB(NOW(), INTERVAL 36 HOUR)".format(current_user.id)
        number_shared_recency = db.session.execute(sql).scalar()
        nudge["sql"] = sql
        nudge["rowcount"] = number_shared_recency

        if number_shared_recency == 0:
            nudge["nudge"] = "yes"
            nudge["type"] = "recency"

            # add nudge details to nudge table
            nudgeInfo = Nudges(user_id=current_user.id,nudgeType="recency")
            db.session.add(nudgeInfo)
            db.session.commit()

            # randomly select a story the user has not shared
            sql = "SELECT * FROM articles WHERE  date > DATE_SUB(NOW(), INTERVAL 24 HOUR) AND id NOT IN (SELECT articleId FROM share_data WHERE user_id={})".format(current_user.id)
            
            potentialArticles = db.session.execute(sql).fetchall()
            assert len(potentialArticles)>=number_stories_on_newspage, "There are less than nine (recent) articles in our database. Probably the script that is supposed to update the database is not running."
            nudge['selectedArticle'] = potentialArticles[random.randrange(0,len(potentialArticles))]

            nudgeDone = 1

    ### NOW CHECK TO SEE IF THERE IS A TOPIC THEY HAVEN'T SHARED RECENTLY, IF THERE IS DO A NUDGE BASED ON TOPIC

    if(nudgeDone == 0):
        # get all topics of all available articles
        sql1 = "SELECT DISTINCT articles.topic FROM articles"
        listArticleTopics = [e[0] for e in db.session.execute(sql1).fetchall()]

        # get all topics of all the articles that the user has shared
        sql2 = "SELECT DISTINCT articles.topic FROM share_data INNER JOIN articles ON share_data.articleId = articles.id WHERE share_data.user_id={}".format(current_user.id)
        shareArticleTopics = [e[0] for e in db.session.execute(sql2).fetchall()]

        # create a list of which topics are missing from the topics the user has shared
        notSharedTopics = list(set(listArticleTopics) - set(shareArticleTopics))

        # double check to make sure there are some not shared topics then create a nudge if they haven't receieved a topic nudge in the last 36 hours
        if(len(notSharedTopics) > 0):
            sql = "SELECT COUNT(*) FROM nudges WHERE user_id = {} AND nudgeType='topic' AND timestamp > DATE_SUB(NOW(), INTERVAL 36 HOUR)".format(current_user.id)
            if db.session.execute(sql).scalar() == 0:
                nudge["nudge"] = "yes"
                nudge["type"] = "topic"

                # add nudge details to nudge table
                nudgeInfo = Nudges(user_id=current_user.id,nudgeType="topic")
                db.session.add(nudgeInfo)
                db.session.commit()

                removeNoneTopics = [i for i in notSharedTopics if i is not None]
                
                sql3 = "SELECT * FROM articles WHERE date > DATE_SUB(NOW(), INTERVAL 24 HOUR) AND topic IN ('{}') ORDER BY RAND() LIMIT 1".format("','".join(removeNoneTopics))
                resultset = db.session.execute(sql3)
                results = resultset.mappings().all()
                nudge['selectedArticle'] = results[0]

    return nudge



def _get_reading_nudge(nudge):
    '''adds reading nudges to the nudge dict'''

    # get all topics of all available articles
    sql1 = "SELECT DISTINCT articles.topic FROM articles"
    listArticleTopics = [e[0] for e in db.session.execute(sql1).fetchall()]

    # get all topics of all the articles that the user has read WITHIN LAST 24 hours
    sql2 = "SELECT DISTINCT articles.topic FROM news_sel INNER JOIN articles ON news_sel.news_id = articles.id WHERE news_sel.user_id={} AND news_sel.starttime > DATE_SUB(NOW(),INTERVAL 24 HOUR);".format(current_user.id)
    
    readArticleTopics = [e[0] for e in db.session.execute(sql2).fetchall()]

    notreadArticleTopics = list(set(listArticleTopics) - set(readArticleTopics))
    logger.debug(readArticleTopics,notreadArticleTopics)
    # double check to make sure there are some not shared topics then create a nudge if they haven't receieved a topic nudge in the last 24 hours
    if(len(notreadArticleTopics) > 0):
        sql = "SELECT COUNT(*) FROM nudges WHERE user_id = {} AND nudgeType='topic_read' AND timestamp > DATE_SUB(NOW(), INTERVAL 24 HOUR)".format(current_user.id)
        if db.session.execute(sql).scalar() == 0:
            nudge["nudge"] = "yes"
            nudge["type"] = "topic_read"
            nudgeInfo = Nudges(user_id=current_user.id,nudgeType="topic_read")
            db.session.add(nudgeInfo)
            db.session.commit()

            removeNoneTopics = [i for i in notreadArticleTopics if i is not None]
            
            sql3 = "SELECT * FROM articles WHERE date > DATE_SUB(NOW(), INTERVAL 24 HOUR) AND topic IN ('{}') ORDER BY RAND() LIMIT 1".format("','".join(removeNoneTopics))
            resultset = db.session.execute(sql3)
            results = resultset.mappings().all()
            nudge['selectedArticle'] = results[0]

    return nudge