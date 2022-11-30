#!/usr/bin/env python

# make it possible to import from parent directory
import sys, os, inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
# ... which we need for this:
from dbConnect import dbconnection

from app.experimentalconditions import select_leaderboard, select_nudging, number_of_groups
_, connection = dbconnection 
                       
cursor = connection.cursor(buffered=True)
cursor2 = connection.cursor(buffered=True)

# get all the users that are part of the gamified group
groups_in_gamified_conditions = [str(i) for i in range(1, number_of_groups+1) if select_leaderboard(i) or select_nudging(i)]
print(f"Calculating scores for users in experimental conditions {groups_in_gamified_conditions} only -- the other conditions do not need this.")

# use backticks because 'group' is a reserved keyword in mysql
sql = f"SELECT id FROM user WHERE `group` IN ({','.join(groups_in_gamified_conditions)})"
cursor.execute(sql)
users = cursor.fetchall()

for user in users:

    # check to see if user exists in points table
    sql = "SELECT * FROM points WHERE user_id = {}".format(user[0])
    cursor.execute(sql)

    # if user not in points table add them with a score of 0
    if(cursor.rowcount == 0):
        sql = "INSERT INTO points(user_id, totalPoints,streak) VALUES ({},{},{})".format(user[0],0,0)
        print("Inserting row in points table for userid {}".format(user[0]))
        cursor.execute(sql)
        connection.commit()
        currentScore = 0
    else:
        # read current user score
        sql = "SELECT totalPoints FROM points WHERE user_id = {}".format(user[0])
        cursor.execute(sql)
        result = cursor.fetchone()
        currentScore = result[0]

    ### begin streak multiplier functionality

    # caclulate multplier

    multiplier = 1

    sql = "SELECT * FROM share_data WHERE user_id = {} AND timestamp > DATE_SUB(NOW(), INTERVAL 24 HOUR)".format(user[0])
    cursor.execute(sql)

    if(cursor.rowcount > 0):

        sql = "SELECT * FROM share_data WHERE user_id = {} AND timestamp < DATE_SUB(NOW(), INTERVAL 24 HOUR) AND timestamp > DATE_SUB(NOW(), INTERVAL 48 HOUR)".format(user[0])
        cursor.execute(sql)

        if(cursor.rowcount > 0):
            multiplier = 2

            sql = "SELECT * FROM share_data WHERE user_id = {} AND timestamp < DATE_SUB(NOW(), INTERVAL 48 HOUR) AND timestamp > DATE_SUB(NOW(), INTERVAL 72 HOUR)".format(user[0])
            cursor.execute(sql)

            if(cursor.rowcount > 0):
                multiplier = 3
                sql = "SELECT * FROM share_data WHERE user_id = {} AND timestamp < DATE_SUB(NOW(), INTERVAL 72 HOUR) AND timestamp > DATE_SUB(NOW(), INTERVAL 96 HOUR)".format(user[0])
                cursor.execute(sql)

                if(cursor.rowcount > 0):
                    multiplier = 4
                    sql = "SELECT * FROM share_data WHERE user_id = {} AND timestamp < DATE_SUB(NOW(), INTERVAL 96 HOUR) AND timestamp > DATE_SUB(NOW(), INTERVAL 120 HOUR)".format(user[0])
                    cursor.execute(sql)

                    if(cursor.rowcount > 0):
                        multiplier = 5


    print("The multiple for user {} is {}".format(user[0], multiplier))

    sql = "UPDATE points SET streak = {} WHERE user_id = {}".format(multiplier, user[0])
    cursor2.execute(sql)
    connection.commit()

    ### end streak multiplier functionality

    ## start with diversity share score

    # get all topics of all available articles
    sql1 = "SELECT DISTINCT articles.topic FROM articles"
    cursor = connection.cursor()
    cursor.execute(sql1)
    articleTopics = cursor.fetchall()

    listArticleTopics = []

    for article in articleTopics:
        listArticleTopics.append(article[0])

    # get all topics of all the articles that the user has shared in the last three days ??
    sql2 = "SELECT DISTINCT articles.topic FROM share_data INNER JOIN articles ON \
        share_data.articleId = articles.id WHERE share_data.scored = 1 AND share_data.timestamp > DATE_SUB(NOW(), INTERVAL 72 HOUR) AND share_data.user_id={}".format(user[0])

    cursor = connection.cursor(buffered=True)
    cursor.execute(sql2)
    shareTopics = cursor.fetchall()

    shareArticleTopics = []

    for share in shareTopics:
        shareArticleTopics.append(share[0])

    # create a list of which topics are missing from the topics the user has shared
    notSharedTopics = list(set(listArticleTopics) - set(shareArticleTopics))

    sql = "SELECT share_data.id, share_data.articleId, articles.topic FROM share_data INNER JOIN articles ON share_data.articleId = articles.id WHERE share_data.scored = 0 AND share_data.user_id={}".format(user[0])
    cursor = connection.cursor(buffered=True)
    cursor.execute(sql)
    unScoredShares = cursor.fetchall()

    addedScore = 0

    if(len(unScoredShares) > 0):

        for share in unScoredShares:

            # check to see how many scores have occured in the last 24 hours, if 10 stop scoring
            sql = "SELECT * FROM scored WHERE user_id = {} AND timestamp > DATE_SUB(NOW(), INTERVAL 24 HOUR)".format(format(user[0]))
            cursor = connection.cursor(buffered=True)
            cursor.execute(sql)

            if(cursor.rowcount < 10):

                print("Topic is {}".format(share[2]))

                if(share[2] in notSharedTopics):
                    print("extra score")
                    addedScore = addedScore + (multiplier * 2)
                    sql = "INSERT INTO scored (user_id, totalPoints) VALUES ({},{})".format(user[0],multiplier * 2)
                    cursor.execute(sql)
                    connection.commit()

                else:
                    print("regular score")
                    addedScore = addedScore + (multiplier)
                    sql = "INSERT INTO scored (user_id, totalPoints) VALUES ({},{})".format(user[0],multiplier)
                    cursor.execute(sql)
                    connection.commit()

                # mark share as scored
                sql = "UPDATE share_data SET scored=1 WHERE id = {}".format(share[0])
                cursor = connection.cursor(buffered=True)
                cursor.execute(sql)
                connection.commit()
            else:
                # set all remaining unscored shares to 1 for this user
                sql = "UPDATE share_data SET scored=1 WHERE user_id = {}".format(user[0])
                cursor = connection.cursor(buffered=True)
                cursor.execute(sql)
                connection.commit()
                print("Reached max of 10 shared scored in a 24 hour period")
                break

        pointsAfterCalculation = currentScore + addedScore

        # update the points table to add the newly assigned points
        sql = "UPDATE points SET totalPoints = {} WHERE user_id = {}".format(pointsAfterCalculation, user[0])
        print("Updating points for userid {}. New point total is {}".format(user[0], pointsAfterCalculation))
        cursor2.execute(sql)
        connection.commit()
