#!/usr/bin/env python

from configparser import ConfigParser

# make it possible to import from parent directory
import sys, os, inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from config import Config               # for generic 3bij3 config (database access)

from datetime import datetime
from dateutil import parser
import os
import dbConnect
import feedparser
import pytz
from newspaper import Article
from io import BytesIO
from PIL import Image
import requests
from requests import ConnectionError
from mysql.connector import Error as MysqlError


def readFeed(rssUrl, publisher, topic, lang, dbCursor,dbConnection):


    try:
        newsFeed = feedparser.parse(rssUrl)

        tz = pytz.timezone('Canada/Eastern')
        now = datetime.now(tz)

        sql = "SELECT url FROM articles"
        dbCursor.execute(sql)
        articles = dbCursor.fetchall()

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

            # remove any html and leading spaces from description

            print("The title is : {}".format(article.title))
            print("The url is : {}".format(article.link))

            cleanUrl = article.link.split("?")[0]

            if(cleanUrl in remainingUrls):

                print("INSERTING INTO DATABASE")

                body,image,publishDate = readBody(article.link)

                print("The publishDate is {}".format(publishDate))

                dateTimeSQL = publishDate.strftime("%Y-%m-%d %H:%M:%S")

                sql = "INSERT INTO articles(title, teaser, text, publisher, topic, url, date, imageUrl,imageFilename,lang) VALUES (%s, %s,%s,%s,%s,%s, %s,%s,%s,%s)"
                values = (article.title, "testTeaser", body, publisher, topic, cleanUrl, dateTimeSQL, image,"",lang)

                try:
                    dbCursor.execute(sql, values)
                    dbConnection.commit()

                    sql2 = "INSERT INTO all_news (id) VALUES (%s)"
                    values = (dbCursor.lastrowid,)
                    dbCursor.execute(sql2, values)
                    dbConnection.commit()

                except MysqlError as err:
                    print(err)
                    print("Error Code:", err.errno)
                    print("SQLSTATE", err.sqlstate)
                    print("Message", err.msg)

            else:
                print("ALREADY IN DATABASE")
    except Exception as error:
        print("ERROR: {}".format(error))


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

def imageProcess(dbCursor, dbConnection):

    sql = "SELECT id, imageUrl FROM articles WHERE imageFilename=''"
    dbCursor.execute(sql)
    images = dbCursor.fetchall()

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

        try:
            img.thumbnail((1280, 720))
        except Exception as error:
            print (error)

        """

        width, height = img.size

        new_width = 800
        new_height = 400

        left = (width - new_width)/2
        top = (height - new_height)/2
        right = (width + new_width)/2
        bottom = (height + new_height)/2

        img = img.crop((left, top, right, bottom))

        """

        newFilename = "../app/static/images/thumb_{}.{}".format(image[0],ext)

        shortFilename = "thumb_{}.{}".format(image[0],ext)

        try:
            img.save(newFilename,img.format)
            sql = "UPDATE articles SET imageFilename = %s WHERE id = %s"
            values = (shortFilename, image[0])
            dbCursor.execute(sql, values)
            dbConnection.commit()
            print("Downloaded and inserted image for article : {}".format(image[0]))
        except Exception as error:
            print (error)

def main():
    configrss = ConfigParser()

    configFile = os.path.join(os.path.dirname(__file__), 'feedlist.cfg')
    configrss.read(configFile)
    dbCursor, dbConnection = dbConnect.getDbConnection(Config)

    # read all the rss feeds from the feedlist file

    for x in range(1, int(configrss["config"]["feedCount"]) + 1):
        feedString = "feed" + str(x)
        readFeed(configrss[feedString]["url"],configrss[feedString]["publisher"], configrss[feedString]["topic"], configrss[feedString]["lang"], dbCursor, dbConnection)

    # download and process the images
    imageProcess(dbCursor, dbConnection)

if __name__ == "__main__":
    main()
