from config import Config

import gensim
from gensim.corpora import Dictionary
from gensim.models import TfidfModel
from gensim.models import Word2Vec
from gensim.similarities import SoftCosineSimilarity
from gensim.similarities import WordEmbeddingSimilarityIndex
from gensim.similarities import SparseTermSimilarityMatrix
import gensim.downloader as api

from sklearn.feature_extraction.text import TfidfVectorizer
import pandas as pd
import mysql.connector
from itertools import chain
from gensim.test.utils import common_texts
import time


model = api.load('glove-wiki-gigaword-50')
connection = mysql.connector.connect(host = Config.MYSQL_HOST,
                                     port=Config.MYSQL_PORT,
                                     database = Config.MYSQL_DB,
                                     user = Config.MYSQL_USER, 
                                     password = Config.MYSQL_PASSWORD)cursor = connection.cursor(prepared = True)

# get all of the recently selected articles
cursor.execute('SELECT DISTINCT news_id, id from news_sel WHERE endtime >= DATE_ADD(CURDATE(), INTERVAL -30 DAY);')
all_ids = []
all_numbers = []
for item in cursor:
    all_ids.append(int(item[0]))
    all_numbers.append(item[1])

ids_dict = dict(zip(all_ids, all_numbers))

"""

# USING INELEGANT SOLUTION OF TRUNCATING THE SIMILARITES TABLE BUT A BETTER SOLUTION SHOULD BE FOUND THAT DOESN'T REQUIRE RECALCULATING PREEXISTING COMPARISONS
cursor.execute("TRUNCATE TABLE similarities")
# sleep to give the truncate some time to complete, before next command?
time.sleep(10)

"""

cursor.execute("DELETE FROM similarities WHERE sim_id > 0")
connection.commit()
time.sleep(10)

new_articles = []

# GET THE ARTICLE INFORMATION FOR THE ARTICLES FROM THE LAST 48 HOURS, MAY NEED TO LENGTHEN THIS
query = "SELECT * FROM articles WHERE date > DATE_SUB(NOW(), INTERVAL 48 HOUR)"
cursor = connection.cursor(dictionary=True,buffered=True)
cursor.execute(query)

if(cursor.rowcount > 0):
    results = cursor.fetchall()

    for result in results:
        new_articles.append(result)

print("Thew new articles are {}".format(new_articles))

old_articles = []

# GET THE ARTICLE INFORMATION FOR THE SELECTED ARTICLES

print("All ids are {}".format(all_ids))

for idIdv in all_ids:

    query = "SELECT * FROM articles WHERE id = %s"
    values = (idIdv,)
    cursor = connection.cursor(dictionary=True)
    cursor.execute(query,values)
    results = cursor.fetchall()
    doc = results[0]
    old_articles.append(doc)

# GET THE WORDS FOR THE OLD AND NEW TEXT
new_text = [doc['text'].split() for doc in new_articles]
old_text = [doc['text'].split() for doc in old_articles]

# GET THE IDS FOR THE OLD AND NEW TEXT
new_ids = [doc['id'] for doc in new_articles]
old_ids = [doc['id'] for doc in old_articles]

table_ids = [ids_dict[i] for i in old_ids]

print(ids_dict)
print(table_ids)
print(old_ids)

if (len(new_ids) > 0):

    dictionary = Dictionary(new_text + old_text)
    tfidf = TfidfModel(dictionary=dictionary)

    termsim_index = WordEmbeddingSimilarityIndex(model)
    termsim_matrix = SparseTermSimilarityMatrix(termsim_index, dictionary, tfidf)

    corpus = [dictionary.doc2bow(d) for d in new_text]
    query = tfidf[[dictionary.doc2bow(d) for d in old_text]]

    index = SoftCosineSimilarity(tfidf[[dictionary.doc2bow(d) for d in new_text]], termsim_matrix)

    sims = index[query]

    df = pd.DataFrame(sims, columns = new_ids, index = old_ids).stack().reset_index()

    print("This is df\n {}".format(df.head()))

    df.columns = ['source', 'target', 'similarity']
    subset = df[['source', 'target', 'similarity']]

    tuples = list(subset.itertuples(index=False, name=None))

    try:
        sql_insert_query = "INSERT INTO similarities (id_old, id_new, similarity) VALUES (%s, %s, %s)"
        cursor.executemany(sql_insert_query, tuples)
        connection.commit()
        print(cursor.rowcount, "Record inserted successfully into similarities table")
    except mysql.connector.Error as error:
        print("Failed inserting record into similarities table {}".format(error))
