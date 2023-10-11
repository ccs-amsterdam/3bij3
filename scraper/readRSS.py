#!/usr/bin/env python

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
import json

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

from bs4 import BeautifulSoup


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
                        except Exception as err:
                            print(err)
                    else:
                        print("ALREADY IN DATABASE")
            except Exception as error:
                print("ERROR: {}".format(error))


class CurlyScraper(Scraper):
    '''Custom scraper for curly.nl'''

    def readFeed(self):
        with Session(self.db) as session:
            #try:
                # GET ALL INDIVIDUAL RECIPE PAGE URLS FROM THE RECIPE INDEX PAGE
                website_url = 'https://www.culy.nl/recepten/menugang/'
                response = requests.get(website_url)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                primary_div = soup.find('div', id='primary')
                urls = []
                
                for anchor in primary_div.find_all('a'):
                    url = anchor.get('href')

                # CHECK TO SEE IF RECEPTEN IS IN THE URL STRING INDICATING THAT IT IS A RECIPE URL               
                    if url and 'recepten' in url and 'page' not in url:
                        urls.append(url)
                
                # ELIMINATE ANY DUPLICATE RECIPE PAGES FROM THE LIST
                unique_urls = list(set(urls))

                # CHECK TO SEE IF URLS ARE ALREADY IN DB
                sql = "SELECT url FROM articles"
                articles = session.execute(sql).fetchall()
                urlsInDb = []

                for article in articles:
                    urlsInDb.append(article[0])

                remainingUrls = list(set(unique_urls) - set(urlsInDb))

                # DO SCRAPING ON NEW RECIPE PAGE URLS

                for recipePageUrl in remainingUrls:
                    # GET THE INGREDIENTS LIST
                    response = requests.get(recipePageUrl)
                    soup = BeautifulSoup(response.content, 'html.parser')
                    ingredients_container = soup.find('div', class_='ingredients-container')
                    if ingredients_container:
                        ingredients_html = str(ingredients_container)
                    else:
                        ingredients_html = "No ingredients container found on the page."
                    # Remove any content within <script> tags
                    soup = BeautifulSoup(ingredients_html, 'html.parser')
                    for script_tag in soup.find_all('script'):
                        script_tag.extract()
                    # Remove any content within <style> tags
                    for style_tag in soup.find_all('style'):
                        style_tag.extract() 
                    recipe_rating_div = soup.find('div', class_='recipe-rating')
                    # Remove the div tag with the class 'recipe-rating' and its content
                    if recipe_rating_div:
                        recipe_rating_div.extract()       
                    wake_lock_label = soup.find('label', class_='wake-lock')
                    # Remove the label tag with the class 'wake-lock' and its content
                    if wake_lock_label:
                        wake_lock_label.extract()
                    # Get the cleaned HTML content
                    cleaned_ingredients_html = str(soup)

                    # INSERTING INTO DATABASE
                    body,image,publishDate = readBody(recipePageUrl)
                    _tmp = body.split('\n')
                    title = _tmp[0]
                    body = '\n'.join( _tmp[1:])

                    fullRecipeText = "{} <br> {}".format(body, cleaned_ingredients_html)
                    dateTimeSQL = publishDate.strftime("%Y-%m-%d %H:%M:%S")

                    #try:
                    _art = Articles(title=title,
                        teaser= "testTeaser",
                        text = fullRecipeText,
                        publisher = self.publisher,
                        topic = self.topic, 
                        url = recipePageUrl, 
                        date = dateTimeSQL, 
                        imageUrl = image,
                        imageFilename = "",
                        lang = self.lang)

                    result = session.add(_art)
                    session.flush()


            #except Exception as error:
                #print("ERROR: {}".format(error))
    




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

            if "guardian" in image[2].lower():
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
    with open(os.path.join(os.path.dirname(__file__), 'feedlist.json')) as f:
        feeds = json.load(f)

    for feed in feeds:
        print(f"Processing {feed['publisher']} - {feed['topic']}...")
        if not feed['active']:
            print("Feed not marked as active, skipping...")
            continue
        if feed["publisher"] == 'culy':
            scraper = Scraper(Config.SQLALCHEMY_DATABASE_URI,
                feed["url"],
                feed["publisher"],
                feed["topic"],
                feed["lang"])
        else:
            scraper = Scraper(Config.SQLALCHEMY_DATABASE_URI,
                feed["url"],
                feed["publisher"],
                feed["topic"],
                feed["lang"])
        scraper.readFeed()

    imageprocessor = ImageProcessor(Config.SQLALCHEMY_DATABASE_URI)
    imageprocessor.process_all()

if __name__ == "__main__":
    main()
