from config import Config
import gensim
from gensim.corpora import Dictionary
from gensim.models import TfidfModel
from gensim.models import Word2Vec
from gensim.similarities import SoftCosineSimilarity
import gensim.downloader as api
from gensim.similarities import WordEmbeddingSimilarityIndex
from gensim.similarities import SparseTermSimilarityMatrix
import mysql.connector
from sklearn.feature_extraction.text import TfidfVectorizer
import pickle

# adapt this using the model / method I used in get_similarities.py
model = api.load('glove-wiki-gigaword-50')

# add information to connect to mysql db, use same code from get_similarities.py
connection = mysql.connector.connect(host = Config.MYSQL_HOST,
                                     port=Config.MYSQL_PORT,
                                     database = Config.MYSQL_DB,
                                     user = Config.MYSQL_USER, 
                                     password = Config.MYSQL_PASSWORD)cursor = connection.cursor(prepared = True)

def make_matrix():

    # i believe these three lines grab the 40 most recent articles and articles id from elastic search db
    # i need to recreate this to grab from mysql. I don't think in need the doctype_last function

    # make a list of dictionaries of 40 most recent articles text and their ids

    query = "SELECT * FROM articles ORDER BY id DESC LIMIT 40"
    cursor = connection.cursor(dictionary=True)
    cursor.execute(query)
    new_articles = cursor.fetchall()

    articles_ids = [a["id"] for a in new_articles]

    print(articles_ids)

    # make this corpus directly from the new mysql database
    corpus = [a["text"].split() for a in new_articles]
    dictionary = Dictionary(corpus)
    dictionary.save('index.dict')



    # replace this with new cosine similarity from get_similarities.py

    tfidf = TfidfModel(dictionary=dictionary)

    termsim_index = WordEmbeddingSimilarityIndex(model)
    termsim_matrix = SparseTermSimilarityMatrix(termsim_index, dictionary, tfidf)

    index = SoftCosineSimilarity(tfidf[[dictionary.doc2bow(d) for d in corpus]],termsim_matrix)

    # ---------------------------------------------------------------------------

    index.save("SimIndex.index")
    with open("sim_list.txt", "wb") as fp:
        pickle.dump(articles_ids, fp)


if __name__ == '__main__':
    make_matrix()
