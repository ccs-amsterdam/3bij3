'''
Define here what the different user groups are allowed to do, what recommendations they get, etc.
'''

from flask_login import current_user
from app.recommender import recommender

rec = recommender()


def which_recommender():
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



