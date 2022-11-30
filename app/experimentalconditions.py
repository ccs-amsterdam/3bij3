'''
Define here what the different user groups are allowed to do, what recommendations they get, etc.
'''

from flask_login import current_user
from app.recommender import recommender
from dbConnect import dbconnection
import random

# Define consant
# How many experimental conditions do you have?
NUMBER_OF_GROUPS = 4


rec = recommender()

cursor, connection = dbconnection 


def assign_group(force_equal_size=True):
    '''Assigns an experimental group (condition) to a participant when signing up for 3bij3'''
    
    if  force_equal_size:
        # we get the group of the last user and then put the new user in the next one
        sql = "SELECT `group` FROM user WHERE ID = (SELECT MAX(id) FROM user)"
        cursor.execute(sql)
        try:
            group = cursor.fetchall()[0][0]
            connection.commit()
        except IndexError:
            # There is no user yet
            group=None

        if(group == 1):
            newGroup=2
        elif(group == 2):
            newGroup=3
        elif(group == 3):
            newGroup=4
        elif(group == 4):
            newGroup=1
        else:
            newGroup=1

        return newGroup
        
    else:
        # if we do not force equal choice, we can just do random choice
        group_list = list(range(1, NUMBER_OF_GROUPS + 1))
        return random.choices(population = group_list, weights = [0.25, 0.25, 0.25, 0.25], k = 1)[0]
   

    


def select_recommender():
    '''Determine the recommender for the experimental condition a user is in. Change this function to reflect your experimental design.'''
    group = current_user.group
    if(group == 1):
        # RANDOM SELECTION WITH GAMIFICATION
        method = rec.random_selection()
    elif(group == 2):
        # RANDOM SELECTION NO GAMIFICATION
        method = rec.random_selection()
    elif(group == 3):
        # ALGORTHMIC SELECTION WITH GAMIFICATION
        method = rec.past_behavior()
    elif(group == 4):
        # ALGORTHMIC SELECTION NO GAMIFICATION
        method = rec.past_behavior()
    return(method)



def select_nudging():
    '''Determine whether users in the experimental condition should receive nudges (e.g., popup reminders to share articles)'''
    group = current_user.group
    if (group == 1) or (group == 3):
        return True
    else:
        return False

def select_leaderboard():
    '''Determine whether users in the experimental condition should be displayed a (gamification) leaderboard'''
    group = current_user.group
    if (group == 1) or (group == 3):
        return True
    else:
        return False


def may_customize():
    '''Determine whether users in the experimental condition may customize their preferences on their profile page'''
    
    # in our current experiment, nobody may do this
    return False

