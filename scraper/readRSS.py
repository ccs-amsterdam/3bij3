#!/usr/bin/env python

from configparser import ConfigParser

# make it possible to import from parent directory
import sys, os, inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
# ... which we need for this:
from config import Config

from app.models import Articles

from datetime import datetime
from dateutil import parser
import os

# there  is an upstream dependecy - feedparser will fail without this
# specific nltk resource, even though we don't really need it elsewhere

try:
    import nltk
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

import feedparser
import pytz
from newspaper import Article
from io import BytesIO
from PIL import Image
import requests
from requests import ConnectionError


from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy import text




def readBody(url):
    body = "ERROR"
    image = ""
    try:
        article = Article(url,keep_article_html=True)
        article.download()
        article.parse()
        article.nlp()
        body = article.text
        image = article.top_image
        publishDate = article.publish_date
    except Exception as error:
        print (error)
        body = ""
    return(body, image,publishDate)

def makeDatetime(timeString):
    #stripping the timezone out
    dateTimePython = parser.parse(timeString[:-4])
    dateTimeSQL = dateTimePython.strftime("%Y-%m-%d %H:%M:%S")
    return(dateTimeSQL)




class Scraper():
    def __init__(self, sqlalchemy_database_uri, rssUrl, publisher, topic, lang):
        self.db = create_engine(sqlalchemy_database_uri)
        self.rssUrl = rssUrl
        self.publisher = publisher
        self.topic = topic
        self.lang = lang

    def readFeed(self):
        with Session(self.db) as session:
            try:
                newsFeed = feedparser.parse(self.rssUrl)
                # commented out to not enforce timezone
                # tz = pytz.timezone('Canada/Eastern')
                # now = datetime.now(tz)
                now = datetime.now()

                sql = "SELECT url FROM articles"
                articles = session.execute(sql).fetchall()

                # CHECK TO SEE IF THESE ENTRIES ARE ALREADY IN DB
                urlsInDb = []

                for article in articles:
                    urlsInDb.append(article[0])

                urlsFromFeed = []

                for article in newsFeed.entries:
                    cleanUrl = article.link.split("?")[0]
                    urlsFromFeed.append(cleanUrl)

                remainingUrls = list(set(urlsFromFeed) - set(urlsInDb))

                count = 0

                for article in newsFeed.entries:
                    print("The title is : {}".format(article.title))
                    print("The url is : {}".format(article.link))
                    cleanUrl = article.link.split("?")[0]

                    if(cleanUrl in remainingUrls):
                        print("INSERTING INTO DATABASE")
                        body,image,publishDate = readBody(article.link)
                        print("The publishDate is {}".format(publishDate))
                        dateTimeSQL = publishDate.strftime("%Y-%m-%d %H:%M:%S")

                        try:
                            _art = Articles(title=article.title,
                                teaser= "testTeaser",
                                text = body,
                                publisher = self.publisher,
                                topic = self.topic, 
                                url = cleanUrl, 
                                date = dateTimeSQL, 
                                imageUrl = image,
                                imageFilename = "",
                                lang = self.lang)

                            result = session.add(_art)
                            session.flush()
                            lastrowid = _art.id
                            print(f"ARTICLE ID IS ={lastrowid}")
                            session.execute(f"INSERT INTO all_news (id) VALUES ({lastrowid})")
                            session.commit()
                        except Exception as err:
                            print(err)
                    else:
                        print("ALREADY IN DATABASE")
            except Exception as error:
                print("ERROR: {}".format(error))


class ImageProcessor():
    def __init__(self, sqlalchemy_database_uri):
        self.db = create_engine(Config.SQLALCHEMY_DATABASE_URI)

    def process_all(self):
        with Session(self.db) as session:
            sql = "SELECT id, imageUrl, publisher FROM articles WHERE imageFilename=''"
            images = session.execute(sql).fetchall()
        
        for image in images:
            if image[1] == "":
                continue

            try:
                response = requests.get(image[1])
            except Exception as error:
                print (error)
                continue

            try:
                img = Image.open(BytesIO(response.content))
            except Exception as error:
                print (error)
                continue

            if(img.format == "PNG"):
                ext = "png"
            else:
                ext = "jpg"
                try:
                    img = img.convert('RGB')
                except Exception as error:
                    print (error)

            if image[2] == "theguardian":
                # TODO #lowpriority make this more generalizable - theguardian needs a tighter crop, but we may want to
                # somehow make this less hard-coded here
                width, height = img.size
                # Calculate the new dimensions for cropping
                zoom = 0.6  # adjust this to control the tightness of the zoom
                crop_width = int(width * zoom)
                crop_height = int(height * zoom)
                # Calculate the coordinates for the crop
                left = int((width - crop_width) / 2)
                top = 0  # anchor the top edge to the center
                right = int(left + crop_width)
                bottom = int(top + crop_height)
                img = img.crop((left, top, right, bottom))
                # Resize the cropped image to 1280 x 720
                img = img.resize((1280, 720))
            else:    
                try:
                    img.thumbnail((1280, 720))
                except Exception as error:
                    print (error)

            newFilename = "../app/static/images/thumb_{}.{}".format(image[0],ext) 
            shortFilename = "thumb_{}.{}".format(image[0],ext)

            try:
                img.save(newFilename,img.format)
                session.execute(f'UPDATE articles SET imageFilename = "{shortFilename}" WHERE id = "{image[0]}"')
                session.commit()
            except Exception as error:
                print (error)
def main():
    configrss = ConfigParser()

    configFile = os.path.join(os.path.dirname(__file__), 'feedlist.cfg')
    configrss.read(configFile)

    # read all the rss feeds from the feedlist file

    for x in range(1, int(configrss["config"]["feedCount"]) + 1):
        feedString = "feed" + str(x)
        scraper = Scraper(Config.SQLALCHEMY_DATABASE_URI,
            configrss[feedString]["url"],
            configrss[feedString]["publisher"],
            configrss[feedString]["topic"],
            configrss[feedString]["lang"])
        scraper.readFeed()
        #readFeed(configrss[feedString]["url"],configrss[feedString]["publisher"], configrss[feedString]["topic"], configrss[feedString]["lang"], dbCursor, dbConnection)

    # download and process the images
    imageprocessor = ImageProcessor(Config.SQLALCHEMY_DATABASE_URI)
    imageprocessor.process_all()

if __name__ == "__main__":
    main()
