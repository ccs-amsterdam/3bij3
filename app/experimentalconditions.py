'''
Define here what the different user groups are allowed to do, what recommendations they get, etc.
'''

'''
NUMBER OF DIFFERENT EXPERIMENTAL CONDITIONS
number_of_groups: How many experimental conditions are there? To how many different groups are people assigned on signup?
'''
number_of_groups = 4

'''
REQUIREMENTS FOR FINISHING STUDY
req_finish_days: How many days need participants to use the application?
req_finish_points: How many points do they need to collect?
Typical defaults are 9 and 100
For testing purposes, consider setting them to 1 and 4 to be able to finish
'''
req_finish_days = 2
req_finish_points = 10

'''
number_stories_on_newspage is the number of stories that will be displayed to the user
number_stories_recommended is the number of stories that will be chosen by the recommender (if applicable)
maxage is the maximum age of an article in hours to be recommended - older articles will not be shown
'''
# it's called 3bij3, so this really should be 9
number_stories_on_newspage = 9 
# it sounds reasonable to have 6 our of 9 stories recommended as default. See below for the
# customization of 'aggressiveness_preference', which with which you can allow users
# to change this number in the app.
number_stories_recommended = 6  
maxage = 48


# Yes, it's right that we do the import afterwards. It's to prevent circular imports

from flask_login import current_user
from app.recommender import RandomRecommender, PastBehavSoftCosineRecommender
# from dbConnect import dbconnection
from app import db
import random
from hashlib import md5
from datetime import datetime




def assign_group(force_equal_size=True):
    '''Assigns an experimental group (condition) to a participant when signing up for 3bij3'''
    if  force_equal_size:
        # we get the group of the last user and then put the new user in the next one
        sql = "SELECT `group` FROM user WHERE ID = (SELECT MAX(id) FROM user)"
        try:
            group = int(db.session.execute(sql).fetchall()[0][0])
        except IndexError:
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
        group_list = list(range(1, number_of_groups + 1))
        return random.choices(population = group_list, weights = [0.25, 0.25, 0.25, 0.25], k = 1)[0]
   

    


def select_recommender(group=None):
    '''Determine the recommender for the experimental condition a user is in. Change this function to reflect your experimental design.
    Instantiates that recommender and returns the instance'''
    if not group:
        group = current_user.group
    if(group == 1):
        # RANDOM SELECTION WITH GAMIFICATION
        return RandomRecommender()
    elif(group == 2):
        # RANDOM SELECTION NO GAMIFICATION
        return RandomRecommender()
    elif(group == 3):
        # ALGORTHMIC SELECTION WITH GAMIFICATION
        return PastBehavSoftCosineRecommender(mysterybox=True)
    elif(group == 4):
        # ALGORTHMIC SELECTION NO GAMIFICATION
        return PastBehavSoftCosineRecommender()



def select_nudging(group=None):
    '''Determine whether users in the experimental condition should receive nudges (e.g., popup reminders to share articles)'''
    if not group:
        group = current_user.group
    if (group == 1) or (group == 3):
        return True
    else:
        return False

def select_leaderboard(group=None):
    '''Determine whether users in the experimental condition should be displayed a (gamification) leaderboard'''
    if not group:
        group = current_user.group
    if (group == 1) or (group == 3):
        return True
    else:
        return False

def select_detailed_stats(group=None):
    '''Determine whether users in the experimental condition are allowed to see detailed statistics on their Profile Page, comparing them with others'''
    if not group:
        group = current_user.group

    if (group == 1) or (group == 3):
        return {'detailed_stats': True}
    else:
        return {'detailed_stats': False}


def select_customizations(group=None):
    '''Determine which customizations the user is allowed to to'''
    if not group:
        group = current_user.group   

    # in our current experiment, nobody may do nothing
    # but typically, this would depend on the group
    return {'topic_preference': False,
            'diversity_preference': False,
            'aggressiveness_preference': False}

def get_voucher_code():
    '''Creates a (unique) voucher code that participants get emailed after succesfully completed.
    It is crucial that the code cannot be linked back to a person, it should be pseudo-random.
    The logic in routes.py stores the codes we gave out in the database table Vouchers so that we can later check whether
    the code is valid when people want to redeem them. '''
    return md5(datetime.now().isoformat().encode('utf=8')).hexdigest()
