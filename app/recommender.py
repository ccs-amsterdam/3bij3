# TODO CAN'T WE BETTER SPECIFY THESE HERE INSTEAD OF IN __INIT__.PY? OR ARE THEY NECESSARY ELSEWHERE?
from app import dictionary, index, article_ids, db

from config import Config
from flask_login import current_user
from app.models import User, News, News_sel, Category
import random
from collections import Counter, defaultdict
from operator import itemgetter
from sqlalchemy import desc
from gensim.models import TfidfModel
from app.experimentalconditions import number_stories_on_newspage, number_stories_recommended, maxage

# kindof OBSOLETE field, it seems
# TODO figure out exact working 
# num_more is the number that will be used when running out of stories(e.g. person has already seen all the stories retrieved)

num_more = 200



# TODO this is (semi-) obsolete now, as we do not have a recommender that shows topic tags like in the
# first iteration of 3bij3. Should be reimplemented at one point, in a more generalizable fashion.
# topic_list: The different topic categories that can be displayed to the user

topic_list = ["Binnenland","Buitenland", "Economie", "Milieu", "Wetenschap", "Immigratie",\
"Justitie","Sport","Entertainment","Anders"]











import pandas as pd

import random

from dbConnect import dbconnection


_, connection = dbconnection

class _BaseRecommender():
    '''
    Base recommender class. Build your own recommender by inheriting from this class and overwriting its methods.
    
    Attributes
    ----------
    number_stories_on_newspage : int
        How many stories are to be returned? If there are 9 stories to be shown to 
        a user, then this should be 9.
    
    number_stories_recommended : int
        Out of all stories that are returned, how many should be recommended?
        If out of the 9 stories, you want only 6 to be personalized and 3 to be
        random, then this should be 6
    
    Methods
    -------
    recommend():
        Returns a set of recommended articles
    '''

    def __init__(self, number_stories_recommended = number_stories_recommended,
                    number_stories_on_newspage = number_stories_on_newspage,  
                    maxage = maxage):
        self.number_stories_recommended = number_stories_recommended
        self.number_stories_on_newspage = number_stories_on_newspage
        self.maxage = maxage


    def _get_candidates(self):
        '''returns a list of dictionaries with articles the recommender can choose from'''

        query = f"SELECT * FROM articles WHERE date > DATE_SUB(NOW(), INTERVAL {self.maxage} HOUR)"
        cursor = connection.cursor(dictionary=True, buffered=True)
        cursor.execute(query)
        results = cursor.fetchall()
        return results

    def _get_random_sample(self):
        '''Many recommenders need a random selection as fallback option'''
        articles = self._get_candidates()
        random_sample = random.sample(articles, self.number_stories_on_newspage)

        for article in random_sample:
            article['recommended'] = 0
        
        return random_sample


    def recommend():
        raise NotImplementedError


class RandomRecommender(_BaseRecommender):
    '''A "recommender" to return random articles'''

    def recommend(self):
        '''Returns random articles, always.'''
        articles = self._get_random_sample()
        return articles

class PastBehavSoftCosineRecommender(_BaseRecommender):
    '''A recommender that recommends articles based on the stories the user has selected in the past, using SoftCosineSimilarity
    The similarity coefficients should already be in the SQL database (by running the 'get_similarities' file on a regular basis) and only need to be retrieved (no calculation at this point)
    '''

    def recommend(self):
        '''Returns articles that are like articles the user has read before, based on the cosine similarity'''
        
        #make a query generator out of the past selected articles (using tfidf model from dictionary); retrieve the articles that are part of the index (based on article_ids)
        
        # TODO check out exact reason for this fallback - iof there are no articles, then we cannot do this (?)
        if None in (dictionary, index, article_ids):
            return self._get_random_sample()

        #Get all ids of read articles of the user from the database and retrieve their similarities
        user = User.query.get(current_user.id)
        selected_articles = user.selected_news.all()

        # selected_ids = [a.id for a in selected_articles]
        selected_ids = [a.news_id for a in selected_articles]

        # if the user has made no selections return random articles
        if not selected_ids:
            return self._get_random_sample()

      
        list_tuples = []
        cursor = connection.cursor(dictionary=True,buffered=True)

        sql = "SELECT * FROM similarities WHERE similarities.id_old in ({})".format(','.join(str(v) for v in selected_ids))
        cursor.execute(sql)

        # if the similarities have not been caclualted and the similarities db is empty print random articles
        # TODO this should be logged
        if cursor.rowcount == 0:
            return self._get_random_sample()

        for item in cursor:
            list_tuples.append(item)

        #make datatframe to get the three most similar articles to every read article, then select the ones that are most often in thet top 3 and retrieve those as selection
        data = pd.DataFrame(list_tuples, columns=['sim_id', 'id_old', 'id_new', 'similarity'])

        try:
            number_stories_recommended = User.query.get(current_user.num_recommended)
        except:
            number_stories_recommended = self.number_stories_recommended

        # remove all items that have a similarity value of over 9
        data = data[data['similarity'] < 0.9]

        # find the top three similar articles for each article previously read
        topValues = data.sort_values(by=['similarity'], ascending = False).groupby('id_old').head(3).reset_index(drop=True)

        # from topValues count how many times each article appears in the top three
        countValues = topValues.groupby(['id_new']).agg({'id_new':'count'}).rename(columns={'id_new':'count'}).reset_index()

        # sort these dataframe to rank by the amount of times each article has appeared in the top
        sortedValues = countValues.sort_values(by=['count'], ascending=False)

        # take the id_new column and turn into a list of values
        recommender_ids = sortedValues['id_new'].to_list()

        # convert the items in the list first to a float, then to an int, not sure why it is read in a string to db
        recommender_ids = [int(a) for a in recommender_ids[:number_stories_recommended]]

        # get the recommended articles from database here
        query = "SELECT * FROM articles WHERE id IN ({})".format(','.join(str(v) for v in recommender_ids))
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query)
        recommender_selection = cursor.fetchall()

        # get the other articles not recommended and not selected here
        selectedAndRecommendedIds = recommender_ids + selected_ids
        query = "SELECT * FROM articles WHERE date > DATE_SUB(NOW(), INTERVAL 48 HOUR) AND id NOT IN ({})".format(','.join(str(v) for v in selectedAndRecommendedIds))
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query)
        other_selection = cursor.fetchall()

        #Mark the selected articles as recommended, select random articles from the non-recommended articles
        #(and get more if not enough unseen articles available), put the two lists together, randomize the ordering and return them

        num_random = self.number_stories_on_newspage - len(recommender_selection)

        try:
            random_selection = random.sample(other_selection, num_random)
            for article in random_selection:
                article['recommended'] = 0
        except ValueError:
            try:
                newtry = self.num_more
                new_articles = [self.doctype_last(s, num = newtry) for s in list_of_sources]
                new_articles = [a for b in articles for a in b]
                random_list = [a for a in new_articles if a["_id"] not in recommender_ids]
                random_selection = random.sample(random_list, num_random)
            except:
                random_selection = "not enough stories"
                return(random_selection, num_random, len(recommender_selection))

        for article in random_selection:
            article['recommended'] = 0
        for article in recommender_selection:
            article['recommended'] = 1
        final_list = recommender_selection + random_selection
        final_list = random.sample(final_list, len(final_list))
        return(final_list)