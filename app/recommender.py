from app import dictionary, index, article_ids, db
from config import Config
from flask_login import current_user
from app.models import User, News, News_sel, Category
import random
from collections import Counter, defaultdict
from operator import itemgetter
from sqlalchemy import desc
from gensim.models import TfidfModel
from app.experimentalconditions import number_stories_on_newspage, number_stories_recommended

# OBSOLETE fields from the times we still used elastic search as backend. 
# TODO adapt code in this file so that these values are not referenced any more
topicfield = "title"
textfield = "text"
teaserfield = "teaser"
teaseralt = "title"
doctypefield = "publisher"
titlefield = "title"

# OBSOLETE fields, it seems
# TODO figure out exact working - it seems not to be in (real) use any more
# num_less is the initial number of articles per source that will be scraped,
# num_more is the number that will be used when running out of stories(e.g. person has already seen all the stories retrieved)

num_less = 20
num_more = 200

# MORE OBSOLETE FIELDS
# REMOVE AFTER CLEANUP OF THIS FILE
'''
TOPICS
topic_list: The different topic categories that can be displayed to the user
classifier_dict: map numbers in elasticsearch database to strings (for the topic tag)
all_categories: map topic strings to topic numbers (that are stored in the SQL database)
'''
topic_list = ["Binnenland","Buitenland", "Economie", "Milieu", "Wetenschap", "Immigratie",\
"Justitie","Sport","Entertainment","Anders"]

classifier_dict = {topic_list[0]:['13','14','20', '3', '4', '5', '6'], topic_list[1]:['16', '19', '2'],\
 topic_list[2]:['1','15'], topic_list[3]:['8', '7'],  topic_list[4]:['17'], topic_list[5]:['9'],  topic_list[6]:['12'],\
  topic_list[7]:['29'], topic_list[8]:['23'], topic_list[9]:['10','99']}

all_categories = {"topic1":topic_list[0], "topic2":topic_list[1], "topic3":topic_list[2], "topic4":topic_list[3],\
 "topic5":topic_list[4], "topic6":topic_list[5], "topic7":topic_list[6], "topic8":topic_list[7], \
 "topic9":topic_list[8], "topic10":topic_list[9]}











import pandas as pd

import random

from dbConnect import dbconnection


_, connection = dbconnection

class recommender():

    def __init__(self):
        self.num_less = num_less
        self.num_more = num_more
        self.number_stories_on_newspage = number_stories_on_newspage
        self.topicfield = topicfield
        self.textfield = textfield
        self.teaserfield = teaserfield
        self.teaseralt = teaseralt
        self.doctypefield = doctypefield
        self.classifier_dict = classifier_dict
        self.all_categories = all_categories
        self.titlefield = titlefield
        self.number_stories_recommended = number_stories_recommended

    def get_selected(self):
        user = User.query.get(current_user.id)
        selected_articles = user.selected_news.all()
        selected_ids = [a.news_id for a in selected_articles]
        docs = []
        for item in selected_ids:
            doc = es.search(index=indexName,
                body={"query":{"terms":{"_id":[item]}}}).get('hits',{}).get('hits',[""])
            for d in doc:
                docs.append(d)
        return docs

    def recent_articles(self, by_field = "META.ADDED", num = None):

        query = "SELECT * FROM articles WHERE date > DATE_SUB(NOW(), INTERVAL 48 HOUR)"
        cursor = connection.cursor(dictionary=True, buffered=True)
        cursor.execute(query)
        results = cursor.fetchall()
        return results

    def doctype_last(self, doctype, by_field = "META.ADDED", num = None):
        if num == None:
            num = self.num_less
        user = User.query.get(current_user.id)
        selected_articles = self.get_selected()
        displayed_articles = user.displayed_news.all()
        displayed_ids = [a.elasticsearch for a in displayed_articles]
        docs = es.search(index=indexName,
                  body={
                      "sort": [
                          { by_field : {"order":"desc"}}
                          ],
                      "size":num,
                      "query": { "bool":
                          { "filter":
                              { "term":
                                  { self.doctypefield: doctype
                                  }
                              }
                          }
                      }}).get('hits',{}).get('hits',[""])
        final_docs = []
        a = ["podcast", "live"]
        for doc in docs:
            if self.textfield not in doc["_source"].keys() or self.titlefield not in doc["_source"].keys() or (self.teaserfield not in doc["_source"].keys() and self.teaseralt not in doc["_source"].keys()) or doc['_id'] in displayed_ids or topicfield not in doc['_source'].keys():
                pass
            elif "paywall_na" in doc["_source"].keys():
                if doc["_source"]["paywall_na"] == True:
                    pass
                else:
                    if any(x in doc['_source'][self.textfield] for x in a):
                        pass
                    else:
                        final_docs.append(doc)
            elif any(x in doc["_source"][self.textfield] for x in a):
                pass
            else:
                final_docs.append(doc)
        return final_docs

    def random_selection(self):

        articles = self.recent_articles()
        random_sample = random.sample(articles, self.number_stories_on_newspage)

        for article in random_sample:
            article['recommended'] = 0

        return random_sample

    def past_behavior(self):
        '''
        Recommends articles based on the stories the user has selected in the past, using SoftCosineSimilarity
        The similarity coefficients should already be in the SQL database (by running the 'get_similarities' file on a regular basis) and only need to be retrieved (no calculation at this point)
        '''

        #make a query generator out of the past selected articles (using tfidf model from dictionary); retrieve the articles that are part of the index (based on article_ids)
        if None in (dictionary, index, article_ids):
            final_list = self.random_selection()
            return(final_list)

        #Get all ids of read articles of the user from the database and retrieve their similarities
        user = User.query.get(current_user.id)
        selected_articles = user.selected_news.all()

        # selected_ids = [a.id for a in selected_articles]
        selected_ids = [a.news_id for a in selected_articles]

        # if the user has made no selections print random articles
        if not selected_ids:

            articles = self.random_selection()

            for article in articles:
                article['recommended'] = 0

            random_sample = random.sample(articles, self.number_stories_on_newspage)
            return random_sample

        list_tuples = []
        cursor = connection.cursor(dictionary=True,buffered=True)

        sql = "SELECT * FROM similarities WHERE similarities.id_old in ({})".format(','.join(str(v) for v in selected_ids))
        cursor.execute(sql)

        # if the similarities have not been caclualted and the similarities db is empty print random articles
        # TODO this should be logged
        if cursor.rowcount == 0:
            articles = self.random_selection()

            for article in articles:
                article['recommended'] = 0

            random_sample = random.sample(articles, self.number_stories_on_newspage)
            return random_sample

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
