from flask import render_template, flash, redirect, url_for, request, make_response, session, Markup
from app import app, db, mail, recommender
from config import Config
from flask_login import current_user, login_user, logout_user, login_required
from app.models import User, News, News_sel, Category, Points_logins, Points_stories, Points_invites, Points_ratings, User_invite, Num_recommended, Show_again, Diversity, ShareData, Nudges, Scored
from werkzeug.urls import url_parse
from app.forms import RegistrationForm, ChecklisteForm, LoginForm, ReportForm,  ResetPasswordRequestForm, ResetPasswordForm, rating, ContactForm
import string
import random
import re
from app.email import send_password_reset_email, send_registration_confirmation
from datetime import datetime
from app.recommender import recommender
from sqlalchemy import desc
from flask_mail import Message
from user_agents import parse
from app.processing import paragraph_processing
from werkzeug.security import generate_password_hash
#from app.vars import host, indexName, es, list_of_sources, topics, doctype_dict, topic_list
from app.vars import num_less, num_more, num_select, num_recommender
from app.vars import topicfield, textfield, teaserfield, teaseralt, titlefield, doctypefield, classifier_dict
from app.vars import group_number
from app.vars import p1_day_min, p1_points_min, p2_day_min, p2_points_min
import webbrowser
import time
import math
import random

import mysql.connector
from mysql.connector import Error
from mysql.connector import errorcode

connection = mysql.connector.connect(host = Config.MYSQL_HOST,
                                     port=Config.MYSQL_PORT,
                                     database = Config.MYSQL_DB,
                                     user = Config.MYSQL_USER, 
                                     password = Config.MYSQL_PASSWORD)

rec = recommender()
paragraph = paragraph_processing()

@app.route('/login', methods = ['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('count_logins'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username = form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        try:
            user.panel_id(panel_id)
        except:
            pass
        user_guest = user.username
        user_invite_guest = User_invite.query.filter_by(user_guest = user_guest).first()
        if user_invite_guest is not None:
            user_invite_guest.times_logged_in = user_invite_guest.times_logged_in + 1
            db.session.commit()
        return redirect(url_for('count_logins'))
    return render_template('login.html', title='Inloggen', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('count_logins'))

@app.route('/consent', methods = ['GET', 'POST'])
def consent():
    parameter = request.args.to_dict()
    try:
        other_user = parameter['user']
    except:
        other_user = None
    if other_user is not None:
        other_user = other_user
    else:
        other_user = None
    try:
        panel_id = parameter['pid']
    except:
        try:
            panel_id = parameter['PID']
        except:
            panel_id = "noIDyet"
    return render_template('consent.html', other_user = other_user, panel_id = panel_id)

@app.route('/no_consent')
def no_consent():
    return render_template('no_consent.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('count_logins'))
    parameter = request.args.to_dict()
    try:
        panel_id = parameter['id']
    except:
        panel_id = "noIDyet"
    form = RegistrationForm()
    if form.validate_on_submit():
        group_list = list(range(1, group_number + 1))

        ### USERS ARE CURRENTLY RANDOMLY ASSIGNED TO GROUPS, THAT COULD RESULT IN INEQUAL GROUPS
        ### MAY NEED TO CHANGE THIS SO THAT THE GROUPS ARE EQUAL
        ### PERHAPS A SEPERATE SCRIPT

        # group = random.choices(population = group_list, weights = [0.25, 0.25, 0.25, 0.25], k = 1)[0]

        # start of new user group assignment

        sql = "SELECT `group` FROM user WHERE ID = (SELECT MAX(id) FROM user)"
        cursor = connection.cursor(buffered=True)
        cursor.execute(sql)
        group = cursor.fetchall()[0][0]
        connection.commit()


        if(group == 1):
            newGroup=2
        elif(group == 2):
            newGroup=3
        elif(group == 3):
            newGroup=4
        elif(group == 4):
            newGroup=1
        else:
            newGroup=1

        # end of new user group assignment

        user = User(username=form.username.data, group = newGroup, panel_id = panel_id, email_contact = form.email.data)
        user.set_password(form.password.data)
        user.set_email(form.email.data)
        db.session.add(user)
        db.session.commit()
        connection.commit()

        try:
            other_user = request.args.to_dict()['other_user']
        except:
            other_user = None
        if other_user is not None:
            other_user = other_user
            user_invite = User_invite(stories_read = 0, times_logged_in = 0, user_host = other_user, user_guest = form.username.data)
            db.session.add(user_invite)
            db.session.commit()
        send_registration_confirmation(user, form.email.data)
        flash('Congratulations, you are a registered user now!')
        return redirect(url_for('login', panel_id = panel_id))
    return render_template('register.html', title = 'Registratie', form=form)



@app.route('/activate', methods=['GET', 'POST'])
def activate():
    parameter = request.args.to_dict()
    try:
        user = parameter['user']
    except:
        user = "no_user"
    check_user = User.query.filter_by(id = user).first()
    if check_user is not None:
        if check_user.activated == 0:
            check_user.activated = 1
            db.session.commit()
            redirect_link = "".format(check_user.panel_id)
            flash('Congratulations, your account is activated now!')
            try:
                return webbrower.open_new_tab(redirect_link)
            except:
                return redirect(redirect_link)
        elif check_user.activated == 1:
            flash('Your account has already been activated, have fun on the website!')
            return redirect(url_for('login'))
    else:
        flash('Something went wrong. Did you already create an account on the website?')
        return redirect(url_for('login'))



@app.route('/', methods = ['GET', 'POST'])
@app.route('/homepage', methods = ['GET', 'POST'])
@login_required
def newspage(show_again = 'False'):

    ### start of nudge functionality

    group = current_user.group

    nudge = {}
    selectedArticle = {}
    ## only do nudges if in group 1 or 3

    if group == 1 or group==3:

        nudge["nudge"] = "no"

        ### START BY CHECKING IF THEY HAVE SHARED RECENTLY, IF NOT, AND IF THEY HAVE NOT SEEN A NUDGE IN 24 HOURS SHOW RECENCY NUDGE

        # check to see if they have shared in the last 24 hours
        sql = "SELECT * FROM share_data WHERE user_id = {} AND timestamp > DATE_SUB(NOW(), INTERVAL 24 HOUR)".format(current_user.id)

        nudge["sql"] = sql

        cursor = connection.cursor(buffered=True)
        cursor.execute(sql)

        nudgeDone = 0

        if(cursor.rowcount == 0):

            sql = "SELECT * FROM nudges WHERE user_id = {} AND nudgeType='recency' AND timestamp > DATE_SUB(NOW(), INTERVAL 36 HOUR)".format(current_user.id)
            cursor.execute(sql)

            nudge["sql"] = sql
            nudge["rowcount"] = cursor.rowcount

            if(cursor.rowcount == 0):

                nudge["nudge"] = "yes"
                nudge["type"] = "recency"

                # add nudge details to nudge table
                nudgeInfo = Nudges(user_id=current_user.id,nudgeType="recency")
                db.session.add(nudgeInfo)
                db.session.commit()
                connection.commit()

                # randomly select a story the user has not shared
                sql = "SELECT * FROM articles WHERE  date > DATE_SUB(NOW(), INTERVAL 24 HOUR) AND id NOT IN (SELECT articleId FROM share_data WHERE user_id={})".format(current_user.id)
                cursor = connection.cursor(dictionary=True)
                cursor.execute(sql)
                potentialArticles = cursor.fetchall()
                selectedArticle = potentialArticles[random.randrange(0,len(potentialArticles))]

                nudgeDone = 1

        ### NOW CHECK TO SEE IF THERE IS A TOPIC THEY HAVEN'T SHARED RECENTLY, IF THERE IS DO A NUDGE BASED ON TOPIC

        if(nudgeDone == 0):

            # get all topics of all available articles
            sql1 = "SELECT DISTINCT articles.topic FROM articles"
            cursor = connection.cursor()
            cursor.execute(sql1)
            articleTopics = cursor.fetchall()

            listArticleTopics = []

            for article in articleTopics:
                listArticleTopics.append(article[0])

            # get all topics of all the articles that the user has shared
            sql2 = "SELECT DISTINCT articles.topic FROM share_data INNER JOIN articles ON share_data.articleId = articles.id WHERE share_data.user_id={}".format(current_user.id)

            cursor = connection.cursor(buffered=True)
            cursor.execute(sql2)
            shareTopics = cursor.fetchall()

            shareArticleTopics = []

            for share in shareTopics:
                shareArticleTopics.append(share[0])

            # create a list of which topics are missing from the topics the user has shared
            notSharedTopics = list(set(listArticleTopics) - set(shareArticleTopics))

            # double check to make sure there are some not shared topics then create a nudge if they haven't receieved a topic nudge in the last 36 hours
            if(len(notSharedTopics) > 0):

                sql = "SELECT * FROM nudges WHERE user_id = {} AND nudgeType='topic' AND timestamp > DATE_SUB(NOW(), INTERVAL 36 HOUR)".format(current_user.id)
                cursor.execute(sql)

                if(cursor.rowcount == 0):

                    nudge["nudge"] = "yes"
                    nudge["type"] = "topic"

                    # add nudge details to nudge table
                    nudgeInfo = Nudges(user_id=current_user.id,nudgeType="topic")
                    db.session.add(nudgeInfo)
                    db.session.commit()
                    connection.commit()

                    removeNoneTopics = [i for i in notSharedTopics if i is not None]

                    sql3 = "SELECT * FROM articles WHERE date > DATE_SUB(NOW(), INTERVAL 24 HOUR) AND topic IN ('{}') ORDER BY RAND() LIMIT 1".format("','".join(removeNoneTopics))

                    cursor = connection.cursor(dictionary=True)
                    cursor.execute(sql3)
                    selectedArticleList = cursor.fetchall()
                    selectedArticle = selectedArticleList[0]

    else:
        nudge["nudge"] = "no"

    ### end of nudge functionality

    number_rec = Num_recommended(num_recommended = num_recommender, user_id = current_user.id)
    results = []
    parameter = request.args.to_dict()
    try:
        show_again = parameter['show_again']
    except KeyError:
        show_again = "False"
    if show_again == 'True':
        documents = last_seen()
        decision = Show_again(show_again = 1, user_id = current_user.id)
        db.session.add(decision)
    elif show_again == 'False':
        documents = which_recommender()
        decision = Show_again(show_again = 0, user_id = current_user.id)
        db.session.add(decision)

        testData = {}

        if documents == "not enough stories":
            return render_template('no_stories_error.html')

    for idx, result in enumerate(documents):

        # recommended is set to 1 if it is an actual recommended article is 0 in this case because is random
        # switched elasticsearch to id of mysql scraped article

        news_displayed = News(elasticsearch = result["id"], url = result["url"], user_id = current_user.id, recommended = 0, position = idx)
        db.session.add(news_displayed)
        db.session.commit()

        result["new_id"] = news_displayed.id
        text_clean = re.sub(r'\|','', result["title"])
        if text_clean.startswith(('artikel ', 'live ')):
            text_clean = text_clean.split(' ', 1)[1]
        elif re.match('[A-Z]*? - ', text_clean):
            text_clean = re.sub('[A-Z]*? - ', '', text_clean)
        try:
            teaser = result["teaser"]
        except KeyError:
            teaser = result["text"]
        teaser = re.sub('[A-Z]*? - ', '', teaser)
        result["teaser"] = teaser
        result["text_clean"] = text_clean

        result["position"] = idx

        currentTime = time.time()
        result["currentMs"] = int(currentTime * 1000)

        results.append(result)

    # begin leaderboard content

    sql = "SELECT points.user_id AS user_id, user.username AS username, points.totalPoints AS totalPoints FROM points INNER JOIN user ON points.user_id = user.id ORDER BY totalPoints DESC LIMIT 10"

    cursor = connection.cursor(dictionary=True)
    cursor.execute(sql)
    scores = cursor.fetchall()

    # end added leaderboard content

    # begin current user scores

    userScore={}

    sql = "SELECT totalPoints, streak FROM points WHERE user_id = {}".format(current_user.id)

    cursor.execute(sql)
    userScoreResults = cursor.fetchall()

    if(cursor.rowcount > 0):
        userScore["currentScore"] = userScoreResults[0]["totalPoints"]
        userScore["streak"] = userScoreResults[0]["streak"]
    else:
        userScore["currentScore"] = 0
        userScore["streak"] = 0

    # end current user scores

    session['start_time'] = datetime.utcnow()

    user_guest = current_user.username
    user_invite_guest = User_invite.query.filter_by(user_guest = user_guest).first()
    if user_invite_guest is not None:
        user_invite_guest.stories_read = user_invite_guest.stories_read + 1
        db.session.commit()
    different_days = days_logged_in()['different_dates']
    points = points_overview()['points']
    group = current_user.group
    href_final = "https://vuamsterdam.eu.qualtrics.com/jfe/form/SV_38UP20nB0r7wv3f?id={}&group={}&fake={}".format(current_user.panel_id, current_user.group, current_user.fake)
    message_final = 'You can now complete this study and fill in the final questionnaire - click on <a href={} class="alert-link">hier</a> - but you can also continue using our web app if you want to.'.format(href_final)
    href_first = "https://vuamsterdam.eu.qualtrics.com/jfe/form/SV_b7XIK4EZPElGJN3?id={}&group={}".format(current_user.panel_id, current_user.group)
    message_first = 'Je kunt nu de eerste deel van deze studie afsluiten door een aantal vragen te beantwoorden. Klik <a href={} class="alert-link">hier</a> om naar de vragenlijst te gaan. aan het einde van de vragenlijst vindt je een link die je terugbrengt naar de website voor het tweede deel. Om de studie succesvol af te ronden, moet je aan beide delen deelnemen.'.format(href_first)
    message_final_b = 'You can now complete this study and fill in the final questionnaire - click on <a href={} class="alert-link">hier</a> - but you can also continue using our web app if you want to.'.format(href_first)

    if different_days >= p2_day_min and points >= p2_points_min and (group == 1 or group == 2 or group == 3) and current_user.phase_completed == 2:
        flash(Markup(message_final))
    elif current_user.phase_completed == 2 and (group == 2 or group == 3):
        flash(Markup('New functions to personlize 3bij3 according to your wishes are available. Click <a href="/points" class="alert-link">here</a> or go to "My 3bij3" and try it out!'))
    elif p1_day_min <= different_days and p1_points_min <= points and current_user.phase_completed == 1 and (group == 1 or group == 2 or group == 3):
        flash(Markup(message_first))
    elif different_days >= p1_day_min and points >= p1_points_min and group == 4 and current_user.phase_completed == 1:
        flash(Markup(message_final_b))
    elif current_user.phase_completed == 3:
        flash(Markup('Thanks for finishing the study. You can keep using 3bij3 if you want to.'))
    return render_template('newspage.html', results = results, scores = scores, userScore = userScore, nudge = nudge, selectedArticle=selectedArticle, group=current_user.group)

def which_recommender():

    group = current_user.group

    if(group == 1):
        # RANDOM SELECTION WITH GAMIFICATION
        method = rec.random_selection()
    elif(group == 2):
        # RANDOM SELECTION NO GAMIFICATION
        method = rec.random_selection()
    elif(group == 3):
        # ALGORTHMIC SELECTION WITH GAMIFICATION
        method = rec.past_behavior()
    elif(group == 4):
        # ALGORTHMIC SELECTION NO GAMIFICATION
        method = rec.past_behavior()
    return(method)

def last_seen():
    news = News.query.filter_by(user_id = current_user.id).order_by(desc(News.id)).limit(9)
    news_ids = [item.elasticsearch for item in news]
    recommended = [item.recommended for item in news]
    id_rec = zip(news_ids, recommended)
    news_last_seen = []
    for item in id_rec:
        doc = es.search(index=indexName,
                  body={"query":{"term":{"_id":item[0]}}}).get('hits',{}).get('hits',[""])
        for text in doc:
                text['recommended'] = item[1]
                news_last_seen.append(text)
    return news_last_seen

@app.route('/logincount', methods = ['GET', 'POST'])
@login_required
def count_logins():
    parameter = request.args.to_dict()
    try:
        show_again = parameter['show_again']
    except KeyError:
        show_again = "False"
    try:
        user_string = request.headers.get('User-Agent')
        user_string = str(parse(user_string))
    except:
        user_string = " "
    points_logins = Points_logins.query.filter_by(user_id = current_user.id).all()
    if points_logins is None or points_logins == []:
        logins = Points_logins(points_logins = 2, user_id = current_user.id)
        db.session.add(logins)
    else:
        dates = [item.timestamp.date() for item in points_logins]
        now = datetime.utcnow()
        points_today = 0
        for date in dates:
            if date == now.date():
                points_today += 2
            else:
                pass
        try:
            date = current_user.last_visit
            if date is None:
                date = current_user.first_login
        except:
            date = datetime.utcnow()
        difference = now - date
        difference = int(difference.seconds // (60 * 60))
        if difference > 1:
            if points_today >= 4:
                logins = Points_logins(points_logins = 0, user_id = current_user.id, user_agent = user_string)
                db.session.add(logins)
            else:
                logins = Points_logins(points_logins = 2, user_id = current_user.id, user_agent = user_string)
                db.session.add(logins)
        else:
            pass
        current_user.last_visit = datetime.utcnow()
    db.session.commit()
    return redirect(url_for('newspage', show_again = show_again))

@app.route('/save/<id>/<idPosition>/<recommended>', methods = ['GET', 'POST'])
@login_required
def save_selected(id,idPosition,recommended):

    # reset current Ms to current time not time of index page load
    currentTime = time.time()
    currentMs = int(currentTime * 1000)

    query = "SELECT * FROM articles WHERE id = %s"
    values = (id,)
    cursor = connection.cursor(dictionary=True)
    cursor.execute(query,values)
    results = cursor.fetchall()
    doc = results[0]

    news_selected = News_sel(news_id = id, user_id =current_user.id, position = idPosition, recommended=recommended)
    db.session.add(news_selected)
    db.session.commit()

    points_stories = Points_stories.query.filter_by(user_id = current_user.id).all()

    if points_stories is None:
        stories = Points_stories(points_stories = 1, user_id = current_user.id)
        db.session.add(stories)
    else:
        dates = [item.timestamp.date() for item in points_stories]
        now = datetime.utcnow().date()
        points_today = 0
        for date in dates:
            if date == now:
                points_today += 1
            else:
                pass
        if points_today >= 10:
            stories = Points_stories(points_stories = 0, user_id = current_user.id)
            db.session.add(stories)
        else:
            stories = Points_stories(points_stories = 1, user_id = current_user.id)
            db.session.add(stories)
    db.session.commit()

    return redirect(url_for('show_detail', id = id, idPosition=idPosition, currentMs=currentMs,fromNudge=0))

@app.route('/detail/<id>/<currentMs>/<idPosition>/<fromNudge>', methods = ['GET', 'POST'])
@login_required
def show_detail(id, currentMs, idPosition,fromNudge):

     query = "SELECT * FROM articles WHERE id = %s"
     values = (id,)
     cursor = connection.cursor(dictionary=True)
     cursor.execute(query,values)
     results = cursor.fetchall()

     doc = results[0]

     selected = News_sel.query.filter_by(id = id).first()

     textWithBreaks = doc["text"].replace('\n', '<br />')

     return render_template('detail.html', text = textWithBreaks, teaser = doc["teaser"], title = doc["title"], url = doc["url"], time = doc["date"], source = doc["publisher"], imageFilename = doc["imageFilename"], form = "form?", id=id,currentMs=currentMs,fromNudge=fromNudge)


@app.route('/decision', methods = ['GET', 'POST'])
@login_required
def decision():
    return render_template('decision.html')


@app.route('/reset_password_request', methods= ['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('count_logins'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        email = form.email.data
        user = User.query.filter_by(email_contact = email).first()
        if user:
            send_password_reset_email(user, email)
        flash('Check your email - you got information on how to reset your password.')
        return redirect(url_for('login'))
    return render_template('reset_password_request.html', title="Reset password", form=form)

@app.route('/reset_password/<token>', methods = ['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('count_logins'))
    user = User.verify_reset_password_token(token)
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset.')
        return redirect(url_for('login'))
    return render_template('reset_password.html', form=form)


@app.context_processor
def time_logged_in():
    if current_user.is_authenticated:
        try:
            first_login = current_user.first_login
            difference_raw = datetime.utcnow() - first_login
            difference = difference_raw.days
        except:
            difference = 0
    else:
        difference = 0
    return dict(difference = difference)

@app.context_processor
def days_logged_in():
    if current_user.is_authenticated:
        points_logins = Points_logins.query.filter_by(user_id = current_user.id).all()
        if points_logins is None:
            different_dates = 0
        else:
            dates = [item.timestamp.date() for item in points_logins]
            different_dates = len(list(set(dates)))
    else:
        different_dates = 0
    return dict(different_dates = different_dates)

@app.context_processor
def number_read():
    if current_user.is_authenticated:
        try:
            selected_news = News_sel.query.filter_by(user_id = current_user.id).all()
            selected_news = len(selected_news)
        except:
            selected_news = 0
    else:
        selected_news = 0
    return dict(selected_news = selected_news)

@app.context_processor
def points_overview():
    if current_user.is_authenticated:
        user = User.query.filter_by(id = current_user.id).first()
        group = current_user.group
        phase_completed = current_user.phase_completed
        try:
            points_logins = user.sum_logins
            if points_logins is None:
                points_logins = 0
        except:
            points_logins = 0
        try:
            points_stories = user.sum_stories
            if points_stories is None:
                points_stories = 0
        except:
            points_stories = 0
        try:
            points_ratings = float(user.sum_ratings)
            if points_ratings is None:
                points_ratings = 0
        except:
            points_ratings = 0
        user_host = current_user.id
        user_invite_host = User_invite.query.filter_by(user_host = user_host).all()
        if user_invite_host is None:
            points_invites = 0
        else:
            number_invited = []
            for item in user_invite_host:
                item1 = item.__dict__
                if item1["stories_read"] >= 5 and item1["times_logged_in"] >= 2:
                    number_invited.append(item1['id'])
                    invites_points = Points_invites.query.filter_by(user_guest_new = item1['user_guest']).first()
                    if invites_points is None:
                         points_invites = Points_invites(user_guest_new = item1['user_guest'], points_invites = 5, user_id = current_user.id)
                         db.session.add(points_invites)
                         db.session.commit()
                    else:
                        points_invites = 0
                else:
                    points_invites = 0
        try:
            points_invites = user.sum_invites
            if points_invites is None:
                points_invites = 0
        except:
            points_invites = 0
        points = points_stories + points_invites + points_ratings + points_logins
        if group == 4:
            points_min = p1_points_min
        else:
            points_min = p2_points_min
        rest = points_min - (points_logins + points_stories + points_ratings)
        if rest <= 0:
            rest = 0
    else:
        points_stories = 0
        points_invites = 0
        points_ratings = 0
        points_logins = 0
        points = 0
        group = 1
        phase_completed = 0
        rest = 0

    return dict(points = points, points_ratings = points_ratings, points_stories = points_stories, points_invites = points_invites, points_logins = points_logins, group = group, phase = phase_completed, rest = rest)

@app.context_processor
def user_agent():
    user_string = request.headers.get('User-Agent')
    try:
        user_agent = parse(user_string)
        if user_agent.is_mobile == True:
            device = "mobile"
        elif user_agent.is_tablet == True:
            device = "tablet"
        else:
            device = "pc"
    except:
        user_agent = " "
        device = "pc"
    return dict(device = device)


@app.route('/decision/popup_back')
@login_required
def popup_back():
    return render_template('information_goback.html')


@app.route('/homepage/categories', methods = ['POST'])
@login_required
def get_categories():
    sel_categories = request.form.getlist('category')
    categories = []
    for category in topic_list:
        if category in sel_categories:
            categories.append(1)
        else:
            categories.append(0)
    category = Category(topic1 = categories[0], topic2 = categories[1], topic3 = categories[2], topic4 = categories[3], topic5= categories[4], \
topic6 = categories[5], topic7 = categories[6], topic8 = categories[7], topic9 = categories[8], topic10 = categories[9],  user_id = current_user.id)
    db.session.add(category)
    db.session.commit()
    return redirect(url_for('count_logins'))

@app.route('/contact', methods = ['GET', 'POST'])
@login_required
def contact():
    form = ContactForm()
    if request.method == 'POST':
        if form.validate() == False:
            return 'Vul alstublieft alle velden in <p><a href="/contact">Probeer het opnieuw!!! </a></p>'
        else:
            name =  current_user.username
            id = str(current_user.id)
            email =  form.email.data
            if not email or email == []:
                email = 'no_address_given'
            msg = Message("Message from your visitor " + name + "with ID: " + id,
                          sender= email,
                          recipients= ['felicia.loecherbach@gmail.com'])
            msg.body = """
            From: %s <%s>,
            %s
            %s
            """ % (name, email, form.lead.data, form.message.data)
            mail.send(msg)
            return redirect(url_for('count_logins'))
    elif request.method == 'GET':
        return render_template('contact.html', form=form)

@app.route('/faq', methods = ['GET'])
@login_required
def faq():
    return render_template("faq.html")

@app.route('/leaderboard', methods = ['GET'])
def leaderboard():
    return render_template("leaderboard.html")

@app.route('/share', methods = ['GET','POST'])
def share():
    if request.method == "POST":
        platformForm = request.form['platform']
        articleIdForm = request.form['articleId']
        startMs = request.form['currentMs']
        fromNudge = request.form['fromNudge']

        currentTime = time.time()
        currentTimeMili = int(currentTime * 1000)

        timeSpentMiliSeconds = currentTimeMili - int(request.form['currentMs'])
        timeSpentSecondsFloat = timeSpentMiliSeconds / 1000

        timeSpentSecondsInt = math.floor(timeSpentSecondsFloat)

        shareInfo = ShareData(platform=platformForm,user_id=current_user.id,articleId=articleIdForm,timeSpentSeconds=timeSpentSecondsInt,fromNudge=fromNudge)
        db.session.add(shareInfo)
        db.session.commit()
        return redirect('/share')
    else:
        return render_template("share.html")


@app.route('/points', methods = ['GET'])
@login_required
def get_points():
    points_stories_all = [item[0] for item in User.query.with_entities(User.sum_stories).all()]
    points_invites_all = [item[0] for item in User.query.with_entities(User.sum_invites).all()]
    points_ratings_all = [item[0] for item in User.query.with_entities(User.sum_ratings).all()]
    points_logins_all = [item[0] for item in  User.query.with_entities(User.sum_logins).all()]
    points_list = [points_stories_all, points_invites_all, points_ratings_all, points_logins_all]
    if points_stories_all is None:
        points_stories_all = [0]
    else:
        points_stories_all = [0 if x==None else x for x in points_stories_all]
    max_stories = max(points_stories_all)
    min_stories = min(points_stories_all)
    avg_stories  = round((sum(points_stories_all)/len(points_stories_all)),1)
    if points_invites_all is None:
        points_invites_all = [0]
    else:
        points_invites_all = [0 if x==None else x for x in points_invites_all]
    max_invites = max(points_invites_all)
    min_invites = min(points_invites_all)
    avg_invites  = round((sum(points_invites_all)/len(points_invites_all)), 1)
    if points_ratings_all is None:
        points_ratings_all = [0]
    else:
        points_ratings_all = [0 if x==None else x for x in points_ratings_all]
    points_ratings_all = [float(i) for i in points_ratings_all]
    max_ratings = max(points_ratings_all)
    min_ratings = min(points_ratings_all)
    avg_ratings  = round((sum(points_ratings_all)/len(points_ratings_all)), 1)
    if points_logins_all is None:
        points_logins_all = [0]
    else:
        points_logins_all = [0 if x==None else x for x in points_logins_all]
    max_logins = max(points_logins_all)
    min_logins = min(points_logins_all)
    avg_logins  = round((sum(points_logins_all)/len(points_logins_all)),1)

    points_overall = [sum(item) for item in zip(points_stories_all, points_logins_all, points_ratings_all, points_invites_all)]
    max_overall = max(points_overall)
    min_overall = min(points_overall)
    avg_overall  = round((sum(points_overall)/len(points_overall)), 2)
    group = current_user.group
    different_days = days_logged_in()['different_dates']
    points = points_overview()['points']
    rest = points_overview()['rest']
    phase = current_user.phase_completed
    if group == 4:
        points_min = p1_points_min
    else:
        points_min = p2_points_min
    try:
        num_recommended = Num_recommended.query.filter_by(user_id = current_user.id).order_by(desc(Num_recommended.id)).first().real
    except:
        num_recommended = 6
    try:
        diversity = Diversity.query.filter_by(user_id = current_user.id).order_by(desc(Diversity.id)).first().real
    except:
        diversity = 1
    return render_template("display_points.html",points_min = points_min,  max_stories = max_stories, min_stories = min_stories, avg_stories = avg_stories, max_logins = max_logins, min_logins = min_logins, avg_logins = avg_logins, max_ratings = max_ratings, min_ratings = min_ratings, avg_ratings = avg_ratings, max_invites = max_invites, min_invites = min_invites, avg_invites = avg_invites, points_overall = points_overall, max_overall = max_overall, min_overall = min_overall, avg_overall = avg_overall, phase = phase, num_recommended = num_recommended, diversity = diversity, rest = rest)


@app.route('/invite', methods = ['GET', 'POST'])
@login_required
def invite():
    id = current_user.id
    url = "https://www.3bij3.nl/consent?user={}".format(current_user.id)
    return render_template("invite.html", url = url, id = id)

@app.route('/report_article', methods = ['GET', 'POST'])
@login_required
def report_article():
    form = ReportForm()
    if request.method == 'POST':
        if form.validate() == False:
            return 'Vul alstublieft alle velden in <p><a href="/contact">Probeer het opnieuw!!! </a></p>'
        else:
            mail.send(msg)
            return redirect(url_for('count_logins'))
    elif request.method == 'GET':
        url = request.args.to_dict()['article']
        form.lead.data = "Probleem met artikel " + url
        return render_template('report_article.html', form=form, url = url)


@app.route('/phase_completed', methods = ['GET', 'POST'])
@login_required
def completed_phase():
    parameter = request.args.to_dict()
    try:
        wave_completed =int(parameter['phase_completed'])
        user_id = parameter['id']
        try:
            fake = int(parameter['fake'])
        except:
            fake = 0
        if str(user_id) == current_user.panel_id and wave_completed == 2:
            user = User.query.filter_by(id = current_user.id).first()
            user.phase_completed = wave_completed
            user.fake = fake
            db.session.commit()
        elif str(user_id) == current_user.panel_id and wave_completed == 3:
            user = User.query.filter_by(id = current_user.id).first()
            user.phase_completed = wave_completed
            db.session.commit()
    except:
        pass
    return redirect(url_for('count_logins'))

@app.route('/diversity', methods = ['POST'])
@login_required
def get_diversity():
    if current_user.fake == 0:
        div = request.form['diversity']
        real = div
    elif current_user.fake == 1:
        div = 1
        real = request.form['diversity']
    else:
        div = 1
        real = 1
    div_final  = Diversity(diversity = div,  user_id = current_user.id, real = real)
    db.session.add(div_final)
    db.session.commit()
    return redirect(url_for('get_points'))

@app.route('/num_recommended', methods = ['POST'])
@login_required
def get_num_recommended():
    if current_user.fake == 0:
        number = request.form['num_recommended']
        real = number
    elif current_user.fake == 1:
        number = num_recommender
        real = request.form['num_recommended']
    else:
        number = num_recommender
        real = num_recommender
    number_rec = Num_recommended(num_recommended = number, user_id = current_user.id, real = real)
    db.session.add(number_rec)
    db.session.commit()
    return redirect(url_for('get_points'))

@app.route('/privacy_policy', methods = ['GET', 'POST'])
def privacy_policy():
    return render_template('privacy_policy.html')
