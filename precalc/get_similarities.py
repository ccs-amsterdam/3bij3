#!/usr/bin/env python

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
from itertools import chain
from gensim.test.utils import common_texts
import time

# make it possible to import from parent directory
import sys, os, inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
# ... which we need for this:
from config import Config

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

model = api.load('glove-wiki-gigaword-50')

db = create_engine(Config.SQLALCHEMY_DATABASE_URI)


# get all of the recently selected articles

with Session(db) as session:
    results = session.execute('SELECT DISTINCT news_id, id from news_sel WHERE endtime >= DATE_ADD(CURDATE(), INTERVAL -30 DAY);').fetchall()
    all_ids = []
    all_numbers = []
    for item in results:
        all_ids.append(int(item[0]))
        all_numbers.append(item[1])

    ids_dict = dict(zip(all_ids, all_numbers))

    # empty the similarities table, there is probably a better way not to have do all this work again
    session.execute("DELETE FROM similarities WHERE sim_id > 0")
    session.commit()
    time.sleep(10)

    # GET THE ARTICLE INFORMATION FOR THE ARTICLES FROM THE LAST 48 HOURS, MAY NEED TO LENGTHEN THIS
    sql = "SELECT * FROM articles WHERE date > DATE_SUB(NOW(), INTERVAL 48 HOUR)"
    #cursor = connection.cursor(dictionary=True,buffered=True)
    #cursor.execute(query)

    resultset = session.execute(sql)
    new_articles = [dict(e) for e in resultset.mappings().all() ]

    #if(cursor.rowcount > 0):
    #    results = cursor.fetchall()
    #
    #    for result in results:
    #        new_articles.append(result)

    old_articles = []

    # GET THE ARTICLE INFORMATION FOR THE SELECTED ARTICLES
    for idIdv in all_ids:

        #query = "SELECT * FROM articles WHERE id = %s"
        #values = (idIdv,)
        #cursor = connection.cursor(dictionary=True)
        #cursor.execute(query,values)
        #results = cursor.fetchall()
        #doc = results[0]
        #old_articles.append(doc)
        resultset = session.execute(f'SELECT * FROM articles WHERE id = "{idIdv}"')
        doc = dict(resultset.mappings().all()[0])   # TODO we most likely can just do fetchfirst or sth instead of getting all and selecting [0]
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
    print(new_ids)

    assert len(old_ids) > 0, "No articles have been selected yet - you probably just installed 3bij3? Just log in and click on some articles to get started!"

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

        df.columns = ['source', 'target', 'similarity']
        subset = df[['source', 'target', 'similarity']]

        tuples = list(subset.itertuples(index=False, name=None))

        try:
            #sql_insert_query = "INSERT INTO similarities (id_old, id_new, similarity) VALUES (%s, %s, %s)"
            #cursor.executemany(sql_insert_query, tuples)
            #connection.commit()
            #print(cursor.rowcount, "Record inserted successfully into similarities table")
            sql_insert_query = "INSERT INTO similarities (id_old, id_new, similarity) VALUES (%s, %s, %s)"
            
            # OK super ugly that we use session for the rest and connection here, but just to try it out for the bulk insert
            # see https://towardsdatascience.com/how-to-perform-bulk-inserts-with-sqlalchemy-efficiently-in-python-23044656b97d
            conn = db.connect()
            result = conn.exec_driver_sql(sql_insert_query, tuples)
            print(f"{result.rowcount} records inserted successfully into similarities table")
            conn.close()
        except Exception as error:
            print("Failed inserting record into similarities table: {}".format(error))
