from config import Config
from flask_login import current_user
from app.models import User, News, News_sel, Category
import random
from collections import Counter, defaultdict
from operator import itemgetter
from sqlalchemy import desc
from gensim.models import TfidfModel
import pandas as pd
from app import db
from app.experimentalconditions import number_stories_on_newspage, number_stories_recommended, maxage
import logging

logger = logging.getLogger('app.recommender')
MYSTERYBOXPOSITION = 4 

def _get_selected_ids():
    '''retrieves the ids of the article the user has previously selected'''
    user = User.query.get(current_user.id)
    selected_ids = [article.news_id for article in user.selected_news.all()]
    logger.debug(f"these IDs have been selected before by user: {selected_ids}")
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

    mysterybox : bool
        Should the recommender also return a mystery box/blind box item that
        is meant to surprise the user? Not all recommenders have to implement this.
    
    Methods
    -------
    recommend():
        Returns a set of recommended articles
    '''

    def __init__(self, number_stories_recommended = number_stories_recommended,
                    number_stories_on_newspage = number_stories_on_newspage,  
                    maxage = maxage,
                    mysterybox = False):
        self.number_stories_recommended = number_stories_recommended
        self.number_stories_on_newspage = number_stories_on_newspage
        self.maxage = maxage
        self.mysterybox = mysterybox


    def _get_candidates(self, exclude = None):
        '''returns a list of dictionaries with articles the recommender can choose from
        
        Arguments
        ---------
        exclude : None, List
            Allows to specify a list of article IDs that are to be excluded
        '''

        if not exclude:
            sql = f"SELECT * FROM articles WHERE date > DATE_SUB(NOW(), INTERVAL {self.maxage} HOUR)"
            logger.debug("Nothing to exclude")
        else:
            sql = f"SELECT * FROM articles WHERE date > DATE_SUB(NOW(), INTERVAL {self.maxage} HOUR) AND id NOT IN ({','.join(str(v) for v in exclude)})"
            logger.debug(f"Excluded: {','.join(str(v) for v in exclude)}")

        resultset = db.session.execute(sql)
        results = [dict(e) for e in resultset.mappings().all()]
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
            article['mystery'] = 0
        logger.debug(f"sampled: {[e['id'] for e in random_sample]}")        
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


# Add your own recommenders below, inheriting from the _BaseRecommender:


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
            sql = f"SELECT * FROM articles WHERE date > DATE_SUB(NOW(), INTERVAL {self.maxage} HOUR) ORDER BY date LIMIT {self.number_stories_on_newspage}"
            logger.debug("Nothing to exclude")
        else:
            exclude = _get_selected_ids()
            sql = f"SELECT * FROM articles WHERE date > DATE_SUB(NOW(), INTERVAL {self.maxage} HOUR) AND id NOT IN ({','.join(str(v) for v in exclude)}) ORDER BY date LIMIT {self.number_stories_on_newspage}"
            logger.debug(f"Excluded: {','.join(str(v) for v in exclude)}")
        
        resultset = db.session.execute(sql)
        articles = [dict(e) for e in resultset.mappings().all()]
        
        # set 'recommended' flag to 0 as we can hardly consider a the latest articles (that are identical for everyone) recommended
        for article in articles:
            article['recommended'] = 0
        return articles

        articles = self._get_candidates(exclude=exclude)
        random_sample = random.sample(articles, self.number_stories_on_newspage)

        for article in random_sample:
            article['recommended'] = 0
        logger.debug(f"sampled: {[e['id'] for e in random_sample]}")        
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
        logger.debug('SOFTCOSINE')     

        selected_ids = _get_selected_ids()
        print(selected_ids)
        if not selected_ids:
            logger.debug('user has not selected anything - returning random instead')
            return self._get_random_sample()
      
        sql = "SELECT * FROM similarities WHERE similarities.id_old in ({})".format(','.join(str(v) for v in selected_ids))
        resultset = db.session.execute(sql)
        results = [dict(e) for e in resultset.mappings().all()]
        if len(results) == 0:
            logger.debug('WARNING - we have not pre-calculated similarities - returning random instead')
            return self._get_random_sample()

        #make datatframe to get the three most similar articles to every read article, then select the ones that are most often in thet top 3 and retrieve those as selection
        data = pd.DataFrame(results, columns=['sim_id', 'id_old', 'id_new', 'similarity'])
        logger.debug(f"Created a dataframe with the dimensions {data.shape}")
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
            logger.debug(f"We do not want to recommend articles that have already been seen, removed {_lenbeforeremove - len(data)} rows")

        # find the top three similar articles for each article previously read
        topValues = data.sort_values(by=['similarity'], ascending = False).groupby('id_old').head(3).reset_index(drop=True)

        # from topValues count how many times each article appears in the top three
        countValues = topValues.groupby(['id_new']).agg({'id_new':'count'}).rename(columns={'id_new':'count'}).reset_index()

        # sort these dataframe to rank by the amount of times each article has appeared in the top
        sortedValues = countValues.sort_values(by=['count'], ascending=False)

        recommender_ids = sortedValues['id_new'].to_list()
        recommender_ids = [int(a) for a in recommender_ids[:number_stories_recommended]]

        # get the recommended articles from database here
        
        query = "SELECT * FROM articles WHERE id IN ({})".format(','.join(str(v) for v in recommender_ids))

        resultset = db.session.execute(query)
        recommender_selection = [dict(e) for e in resultset.mappings().all()]

        for article in recommender_selection:
                article['recommended'] = 1
                article['mystery'] = 0

        logger.debug(f'We selected {len(recommender_selection)} articles based on previous behavior')
        logger.debug(f"These are {[e['id'] for e in recommender_selection]}")
        # get the other articles not recommended and not selected here

        selectedAndRecommendedIds = recommender_ids + selected_ids
        
        if self.mysterybox:
            bottom_10pct = max(1, 10//len(recommender_ids))
            logger.debug(f"Chosing mystery box content from {bottom_10pct} least similar articles")
            mysteryid = random.choice(recommender_ids[-bottom_10pct:])
            query = f"SELECT * FROM articles WHERE id IN ({mysteryid})"
            resultset = db.session.execute(query)
            mystery_selection = [dict(e) for e in resultset.mappings().all()]
            assert len(mystery_selection) == 1
            logger.debug(f"We selected {mystery_selection[0]['id']} as mystery box article.")
            mystery_selection[0]['mystery'] = 1
            mystery_selection[0]['recommended'] = 0
            selectedAndRecommendedIds.append(mysteryid)
            other_selection = self._get_random_sample(n=self.number_stories_on_newspage - len(recommender_selection) - 1, exclude=selectedAndRecommendedIds)
            for article in other_selection:
                article['recommended'] = 0
                article['mystery'] = 0
            
            final_list = recommender_selection + other_selection 
            random.shuffle(final_list)
            final_list.insert(MYSTERYBOXPOSITION, mystery_selection[0])

        else:
            other_selection = self._get_random_sample(n=self.number_stories_on_newspage - len(recommender_selection), exclude=selectedAndRecommendedIds)
            for article in other_selection:
                article['recommended'] = 0
                article['mystery'] = 0
            final_list = recommender_selection + other_selection
            random.shuffle(final_list)
     
        logger.debug(f'We also selected {len(other_selection)} random other articles that have not been viewed before')
        logger.debug(f"these are {[e['id'] for e in other_selection]}")

        if len(final_list) < self.number_stories_on_newspage:
            logger.warn(f"There are not enough articles left, could only select {len(final_list)} instead of required {self.number_stories_on_newspage}")
     
        return(final_list)
        
