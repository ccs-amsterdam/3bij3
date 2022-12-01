from config import Config
from flask_login import current_user
from app.models import User, News, News_sel, Category
import random
from collections import Counter, defaultdict
from operator import itemgetter
from sqlalchemy import desc
from gensim.models import TfidfModel
import pandas as pd
from dbConnect import dbconnection
from app.experimentalconditions import number_stories_on_newspage, number_stories_recommended, maxage


# TODO this is (semi-) obsolete now, as we do not have a recommender that shows topic tags like in the
# first iteration of 3bij3. Should be reimplemented at one point, in a more generalizable fashion.
# topic_list: The different topic categories that can be displayed to the user

topic_list = ["Binnenland","Buitenland", "Economie", "Milieu", "Wetenschap", "Immigratie",\
"Justitie","Sport","Entertainment","Anders"]


_, connection = dbconnection


def _get_selected_ids():
    '''retrieves the ids of the article the user has previously selected'''
    user = User.query.get(current_user.id)
    selected_ids = [article.news_id for article in user.selected_news.all()]
    print(f"these IDs have been selected before by user: {selected_ids}")
    return selected_ids



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


    def _get_candidates(self, exclude = None):
        '''returns a list of dictionaries with articles the recommender can choose from
        
        Arguments
        ---------
        exclude : None, List
            Allows to specify a list of article IDs that are to be excluded
        '''

        if not exclude:
            query = f"SELECT * FROM articles WHERE date > DATE_SUB(NOW(), INTERVAL {self.maxage} HOUR)"
            print("Nothing to exclude")
        else:
            query = f"SELECT * FROM articles WHERE date > DATE_SUB(NOW(), INTERVAL {self.maxage} HOUR) AND id NOT IN ({','.join(str(v) for v in exclude)})"
            print(f"Excluded: {','.join(str(v) for v in exclude)}")
        cursor = connection.cursor(dictionary=True, buffered=True)
        cursor.execute(query)
        results = cursor.fetchall()
        return results

    def _get_random_sample(self, n=None, exclude=None):
        '''Many recommenders need a random selection as fallback option
        
        Arguments
        ---------
        n : None, int
           An integer that specifies how many articles to return. Typically, the number of articles
           displayed on the news page. If None, the app's default will be used .
        
        exclude : None, List
            Allows to specify a list of article IDs that are to be excluded
        '''
        if n is None:
            n = self.number_stories_on_newspage
        articles = self._get_candidates(exclude=exclude)
        random_sample = random.sample(articles, n)

        for article in random_sample:
            article['recommended'] = 0
        print(f"sampled: {[e['id'] for e in random_sample]}")        
        return random_sample


    def recommend(self, include_previously_selected=False):
        '''Please overwrite this method with your own recommendation logic. Make sure to implement a logic that let's the user select wether it's OK to show articles that have been previously read (selected)
        
        Arguments
        ---------
        include_previously_selected : Bool
            If True, also articles that the user has selected (read) before may be recommended.
            That could be useful if the amount of available articles is limited
        '''
        raise NotImplementedError


class RandomRecommender(_BaseRecommender):
    '''A "recommender" to return random articles'''

    def recommend(self, include_previously_selected=False):
        '''Returns random articles, always.'''
        if include_previously_selected:
            articles = self._get_random_sample()
        else:
            articles = self._get_random_sample(exclude=_get_selected_ids())

        # set 'recommended' flag to 0 as we can hardly consider a random thing recommended
        for article in articles:
            article['recommended'] = 0
        return articles

class LatestRecommender(_BaseRecommender):
    '''A "recommender" to simply return the most recent articles, nothing else'''

    def recommend(self, include_previously_selected=False):
        '''Returns the most recent articles'''

        if include_previously_selected:
            query = f"SELECT * FROM articles WHERE date > DATE_SUB(NOW(), INTERVAL {self.maxage} HOUR) ORDER BY date LIMIT {self.number_stories_on_newspage}"
            print("Nothing to exclude")
        else:
            exclude = _get_selected_ids()
            query = f"SELECT * FROM articles WHERE date > DATE_SUB(NOW(), INTERVAL {self.maxage} HOUR) AND id NOT IN ({','.join(str(v) for v in exclude)}) ORDER BY date LIMIT {self.number_stories_on_newspage}"
            print(f"Excluded: {','.join(str(v) for v in exclude)}")
        cursor = connection.cursor(dictionary=True, buffered=True)
        cursor.execute(query)
        articles = cursor.fetchall()
        
        # set 'recommended' flag to 0 as we can hardly consider a the latest articles (that are identical for everyone) recommended
        for article in articles:
            article['recommended'] = 0
        return articles



        articles = self._get_candidates(exclude=exclude)
        random_sample = random.sample(articles, n)

        for article in random_sample:
            article['recommended'] = 0
        print(f"sampled: {[e['id'] for e in random_sample]}")        
        return random_sample




class PastBehavSoftCosineRecommender(_BaseRecommender):
    '''A recommender that recommends articles based on the stories the user has selected in the past, using SoftCosineSimilarity
    The similarity coefficients should already be in the SQL database (by running the 'get_similarities' file on a regular basis) and only need to be retrieved (no calculation at this point)
    '''

    def recommend(self, include_previously_selected=False):
        '''Returns articles that are like articles the user has read before, based on the cosine similarity
        
        Arguments
        ---------
        include_previously_selected : Bool
            If True, also articles that the user has selected (read) before may be recommended.
            That could be useful if the amount of available articles is limited
        '''

        print('SOFTCOSINE')     
        #Get all ids of read articles of the user from the database and retrieve their similarities

        selected_ids = _get_selected_ids()

        # if the user has made no selections return random articles
        if not selected_ids:
            print('user has not selected anything - returning random instead')
            return self._get_random_sample()
      
        list_tuples = []
        cursor = connection.cursor(dictionary=True,buffered=True)

        sql = "SELECT * FROM similarities WHERE similarities.id_old in ({})".format(','.join(str(v) for v in selected_ids))
        cursor.execute(sql)

        # if the similarities have not been caclualted and the similarities db is empty print random articles
        # TODO this should be logged
        if cursor.rowcount == 0:
            print('WARNING - we have not pre-calculated similarities - returning random instead')
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

        # may we alsorecommend articles that have already been read?
        if not include_previously_selected:
            _lenbeforeremove = len(data)
            data = data[~data.id_new.isin(selected_ids)]
            print(f"We do not want to recommend articles that have already been seen, removed {_lenbeforeremove - len(data)} rows")

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

        for article in recommender_selection:
                article['recommended'] = 1

        print(f'We selected {len(recommender_selection)} articles based on previous behavior')
        print(f"These are {[e['id'] for e in recommender_selection]}")
        # get the other articles not recommended and not selected here

        selectedAndRecommendedIds = recommender_ids + selected_ids
        other_selection = self._get_random_sample(n=self.number_stories_on_newspage - len(recommender_selection), exclude=selectedAndRecommendedIds)
        
        print(f'We also selected {len(other_selection)} random other articles that have not been viewed before')
        print(f"these are {[e['id'] for e in other_selection]}")
        
        # compose final recommendation, shuffle recommended and random articles
        final_list = recommender_selection + other_selection
        assert len(final_list) == self.number_stories_on_newspage, f"There are no articles left, could only select len({len(final_list)} instead of required {self.number_stories_on_newspage}"
        random.shuffle(final_list)
      
        return(final_list)