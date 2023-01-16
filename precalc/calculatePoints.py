#!/usr/bin/env python

# TODO Integrate with app/scoring.py . In particular, 
# TODO - scores should be directly visible after somebody did this
# TODO - there is no need to calculate this for all users at the same time - every user can just be
# TODO   responsible for calculating their own scores (in essence, every time they do sth that triggers a change )

# make it possible to import from parent directory
import sys, os, inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
# ... which we need for this:
from config import Config
from app.experimentalconditions import select_leaderboard, select_nudging, number_of_groups

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

db = create_engine(Config.SQLALCHEMY_DATABASE_URI)


def get_leaderboard_score(user):
    '''Returns the current score of the user. In case the user does not exist, create it and assign a score of 0.'''
    with Session(db) as session:
        # check to see if user exists in leaderboard table
        sql = "SELECT * FROM leaderboard WHERE user_id = {}".format(user)
        result = session.execute(sql)
        # if user not in leaderboard table add them with a score of 0
        if(result.rowcount == 0):
            sql = "INSERT INTO leaderboard(user_id, totalPoints,streak) VALUES ({},{},{})".format(user,0,0)
            print("Inserting row in leaderboard table for userid {}".format(user))
            session.execute(sql)
            session.commit()
            currentScore = 0
        else:
            # read current user score
            sql = "SELECT totalPoints FROM leaderboard WHERE user_id = {}".format(user)
            result = session.execute(sql).fetchone()
            currentScore = result[0]
        return currentScore


def get_leaderboard_multiplier(user, dryrun=False):
    with Session(db) as session:
        multiplier = 1

        sql = "SELECT * FROM share_data WHERE user_id = {} AND timestamp > DATE_SUB(NOW(), INTERVAL 24 HOUR)".format(user)
        result = session.execute(sql)

        if(result.rowcount > 0):
            sql = "SELECT * FROM share_data WHERE user_id = {} AND timestamp < DATE_SUB(NOW(), INTERVAL 24 HOUR) AND timestamp > DATE_SUB(NOW(), INTERVAL 48 HOUR)".format(user)
            result = session.execute(sql)

            if(result.rowcount > 0):
                multiplier = 2
                sql = "SELECT * FROM share_data WHERE user_id = {} AND timestamp < DATE_SUB(NOW(), INTERVAL 48 HOUR) AND timestamp > DATE_SUB(NOW(), INTERVAL 72 HOUR)".format(user)
                result = session.execute(sql)

                if(result.rowcount > 0):
                    multiplier = 3
                    sql = "SELECT * FROM share_data WHERE user_id = {} AND timestamp < DATE_SUB(NOW(), INTERVAL 72 HOUR) AND timestamp > DATE_SUB(NOW(), INTERVAL 96 HOUR)".format(user)
                    result = session.execute(sql)

                    if(result.rowcount > 0):
                        multiplier = 4
                        sql = "SELECT * FROM share_data WHERE user_id = {} AND timestamp < DATE_SUB(NOW(), INTERVAL 96 HOUR) AND timestamp > DATE_SUB(NOW(), INTERVAL 120 HOUR)".format(user)
                        result = session.execute(sql)

                        if(result.rowcount > 0):
                            multiplier = 5


        print("The multiple for user {} is {}".format(user, multiplier))

        if not dryrun:
            sql = "UPDATE leaderboard SET streak = {} WHERE user_id = {}".format(multiplier, user)
            session.execute(sql)
            session.commit()
            print("Updated db")
        return multiplier


def update_leaderboard_score(user, dryrun=False):
    with Session(db) as session:
        ## start with diversity share score
        # get all topics of all available articles
        sql = "SELECT DISTINCT articles.topic FROM articles"
        allArticleTopics = [e[0] for e in session.execute(sql).fetchall()]

        # get all topics of all the articles that the user has shared in the last three days ??
        sql = "SELECT DISTINCT articles.topic FROM share_data INNER JOIN articles ON \
            share_data.articleId = articles.id WHERE share_data.scored = 1 AND share_data.timestamp > DATE_SUB(NOW(), INTERVAL 72 HOUR) AND share_data.user_id={}".format(user)
        shareArticleTopics = [e[0] for e in session.execute(sql).fetchall()]

        # create a list of which topics are missing from the topics the user has shared
        notSharedTopics = list(set(allArticleTopics) - set(shareArticleTopics))

        sql = "SELECT share_data.id, share_data.articleId, articles.topic FROM share_data INNER JOIN articles ON share_data.articleId = articles.id WHERE share_data.scored = 0 AND share_data.user_id={}".format(user)
        unScoredShares =  session.execute(sql).fetchall()
        addedScore = 0

        # call other functions to get relevant user info
        currentScore = get_leaderboard_score(user)
        multiplier = get_leaderboard_multiplier(user)

        if(len(unScoredShares) == 0):
            # return early if nothing has changed
            return currentScore
    
        for share in unScoredShares:
            # check to see how many scores have occured in the last 24 hours, if 10 stop scoring
            sql = "SELECT * FROM scored WHERE user_id = {} AND timestamp > DATE_SUB(NOW(), INTERVAL 24 HOUR)".format(format(user))                
            if(session.execute(sql).rowcount < 10):
                print("Topic is {}".format(share[2]))
                if(share[2] in notSharedTopics):
                    print("extra score")
                    addedScore = addedScore + (multiplier * 2)
                    sql = "INSERT INTO scored (user_id, totalPoints) VALUES ({},{})".format(user,multiplier * 2)
                    session.execute(sql)
                    session.commit()
                else:
                    print("regular score")
                    addedScore = addedScore + (multiplier)
                    sql = "INSERT INTO scored (user_id, totalPoints) VALUES ({},{})".format(user,multiplier)
                    session.execute(sql)
                    session.commit()
                # mark share as scored
                sql = "UPDATE share_data SET scored=1 WHERE id = {}".format(share[0])
                session.execute(sql)
                session.commit()
            else:
                # set all remaining unscored shares to 1 for this user
                sql = "UPDATE share_data SET scored=1 WHERE user_id = {}".format(user)
                session.execute(sql)
                session.commit()
                print("Reached max of 10 shared scored in a 24 hour period")
                break

        pointsAfterCalculation = currentScore + addedScore

        if not dryrun:
            # update the leaderboard table to add the newly assigned leaderboard
            sql = "UPDATE leaderboard SET totalPoints = {} WHERE user_id = {}".format(pointsAfterCalculation, user)
            print("Updating leaderboard for userid {}. New point total is {}".format(user, pointsAfterCalculation))
            session.execute(sql)
            session.commit()

        return pointsAfterCalculation


if __name__ == '__main__':
    with Session(db) as session:
        # get all the users that are part of the gamified group
        groups_in_gamified_conditions = [str(i) for i in range(1, number_of_groups+1) if select_leaderboard(i) or select_nudging(i)]
        print(f"Calculating scores for users in experimental conditions {groups_in_gamified_conditions} only -- the other conditions do not need this.")
        # use backticks because 'group' is a reserved keyword in mysql
        sql = f"SELECT id FROM user WHERE `group` IN ({','.join(groups_in_gamified_conditions)})"
        users = [e[0] for e in session.execute(sql).fetchall()]   # it's a list of tuples [(1,), (2,), ...], therefore the list comprehension

        for user in users:
            update_leaderboard_score(user)
