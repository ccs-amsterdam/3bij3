from flask import render_template, flash, redirect, url_for, request, make_response, session
from app import app, db, mail
from flask_login import current_user, login_user, logout_user, login_required
from app.models import User, News, News_sel, Category, Points_logins, Points_stories, Points_invites, Points_ratings, User_invite
from werkzeug.urls import url_parse
from app.forms import RegistrationForm, ChecklisteForm, LoginForm, SurveyForm,  ResetPasswordRequestForm, ResetPasswordForm, rating, ContactForm
from elasticsearch import Elasticsearch
import string
import random
import re
from app.email import send_password_reset_email
from datetime import datetime
from app.recommender import recommender
from sqlalchemy import desc
from flask_mail import Message
from user_agents import parse

host = "http://localhost:9200"
indexName = "inca"
es = Elasticsearch(host)
rec = recommender()
day_min = 10
points_min = 100
classifier_dict = {'Binnenland':['13','14','20', '3', '4', '5', '6'], 'Buitenland':['16', '19', '2'], 'Economie':['1','15'], 'Milieu':['8', '7'],  'Wetenschap':['17'], 'Immigratie':['9'],  'Justitie':['12'], 'Sport':['29'], 'Entertainment':['23'], 'Anders':['10','99']}

@app.route('/login', methods = ['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('newspage'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username = form.username.data).first()
        if user is None or not user.check_password(form.password.data): 
            flash('Ongeldige gebruikersnaam of wachtwoord')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        points_logins = Points_logins.query.filter_by(user_id = current_user.id).all()
        if points_logins is None:
            logins = Points_logins(points_logins = 2, user_id = current_user.id)
            db.session.add(logins)
        else:
            dates = [item.timestamp.date() for item in points_logins]
            now = datetime.utcnow().date()
            points_today = 0
            for date in dates:
                if date == now:
                    points_today += 2
                else:
                    pass
            if points_today >= 4:
                logins = Points_logins(points_logins = 0, user_id = current_user.id)
                db.session.add(logins)
            else:
                logins = Points_logins(points_logins = 2, user_id = current_user.id)
                db.session.add(logins)
        db.session.commit()
        user_guest = user.username
        user_invite_guest = User_invite.query.filter_by(user_guest = user_guest).first()
        if user_invite_guest is not None:
            user_invite_guest.times_logged_in = user_invite_guest.times_logged_in + 1
            db.session.commit()
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('newspage')
        return redirect(next_page)
    return render_template('login.html', title='Inloggen', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('newspage'))

@app.route('/consent', methods = ['GET', 'POST'])
def consent():
    other_user = request.args.to_dict()
    if other_user is not None:
        other_user = other_user
    else:
        other_user = None
    return render_template('consent.html', other_user = other_user)

@app.route('/no_consent')
def no_consent():
    return render_template('no_consent.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('newspage'))
    form = RegistrationForm()
    if form.validate_on_submit():
        group = random.randint(1,4)
        user = User(username=form.username.data, email=form.email.data, group = group)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        other_user = request.args.to_dict()['other_user']
        if other_user is not None:
            other_user = other_user
            user_invite = User_invite(stories_read = 0, times_logged_in = 0, user_host = other_user, user_guest = form.username.data)
            db.session.add(user_invite)
            db.session.commit()
        flash('Gefeliciteerd, u bent nu een ingeschreven gebruiker!')
        return redirect(url_for('login'))
    return render_template('register.html', title = 'Registratie', form=form)
                       
@app.route('/', methods = ['GET', 'POST'])
@app.route('/homepage', methods = ['GET', 'POST'])
@login_required 
def newspage(show_again = 'False'):
    results = []
    parameter = request.args.to_dict()
    try:
        show_again = parameter['show_again']
    except KeyError:
        show_again = "False"
    if show_again == 'True':
        documents = last_seen()
    elif show_again == 'False':
        documents = which_recommender()
        if documents == "not enough stories":
            return render_template('no_stories_error.html')
    for result in documents:
        news_displayed = News(elasticsearch = result["_id"], user_id = current_user.id, recommended = result['recommended'])
        db.session.add(news_displayed)
        db.session.commit()
        result["new_id"] = news_displayed.id
        text_clean = re.sub(r'\|','', result["_source"]["text"])
        if text_clean.startswith(('artikel ', 'live ')):
            text_clean = text_clean.split(' ', 1)[1]
        elif re.match('[A-Z]*? - ', text_clean):
            text_clean = re.sub('[A-Z]*? - ', '', text_clean)
        try:
            teaser = result["_source"]["teaser"]
        except:
            teaser = result["_source"]["teaser_rss"]
        teaser = re.sub('[A-Z]*? - ', '', teaser)
        result["_source"]["teaser"] = teaser    
        result["_source"]["text_clean"] = text_clean
        for key, value in classifier_dict.items():
            if result["_source"]["topic"] in value:
                result["_source"]["topic_string"] = key
            else:
                pass
        results.append(result) 
    session['start_time'] = datetime.utcnow()
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
        if points_today >= 5:
            stories = Points_stories(points_stories = 0, user_id = current_user.id)
            db.session.add(stories)
        else:
            stories = Points_stories(points_stories = 1, user_id = current_user.id)
            db.session.add(stories)
    db.session.commit()

    user_guest = current_user.username
    user_invite_guest = User_invite.query.filter_by(user_guest = user_guest).first()
    if user_invite_guest is not None:
        user_invite_guest.stories_read = user_invite_guest.stories_read + 1
        db.session.commit()
    different_days = days_logged_in()['different_dates']
    points = points_overview()['points']
    if different_days >= day_min and points >= points_min:
        flash('U kunt deze studie nu afsluiten en een finale vragenlijst invullen (link links in de menu) - maar u kunt de webapp ook nog wel verder gebruiken.')   
    return render_template('newspage.html', results = results)

def which_recommender():
    group = current_user.group
    if group == 1:
        categories = Category.query.filter_by(user_id = current_user.id).order_by(desc(Category.id)).first()
        if categories == None:
            method  = rec.random_selection()
        else:
            method = rec.category_selection_classifier()
    elif group == 2:
        selected_news = number_read()['selected_news']
        if selected_news < 3:
            method = rec.random_selection()
        else:
            method = rec.past_behavior()
    elif group == 3:
        selected_news = number_read()['selected_news']
        if selected_news == 0:
            method = rec.random_selection()
        else:
            method = rec.past_behavior_topic()
    elif group == 4:
        method = rec.random_selection()
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

@app.route('/save/<id>', methods = ['GET', 'POST'])
def save_selected(id):
    selected = News.query.filter_by(id = id).first()
    es_id = selected.elasticsearch
    news_selected = News_sel(news_id = selected.elasticsearch, user_id =current_user.id)
    db.session.add(news_selected)
    db.session.commit()
    selected_id = News_sel.query.filter_by(user_id = current_user.id).order_by(desc(News_sel.id)).first().__dict__['id']
    return redirect(url_for('show_detail', id = selected_id))
    
@app.route('/detail/<id>', methods = ['GET', 'POST'])
@login_required
def show_detail(id):
     selected = News_sel.query.filter_by(id = id).first()
     es_id = selected.news_id
     doc = es.search(index=indexName,
                  body={"query":{"term":{"_id":es_id}}}).get('hits',{}).get('hits',[""])
     for item in doc:
         text = item['_source']['text']
         if "||" in text:
             text = re.split(r'\|\|\.\|\|', text)
             text = re.split(r'\|\|\|', text[0])
             text = re.split(r'\|\|', text[1])
         else:
             text = [text]
         try: 
             teaser = item['_source']['teaser']
         except KeyError:
            teaser = item['_source']['teaser_rss']
            teaser = re.sub(r'<.*?>',' ', teaser)
         title = item['_source']['title']
         url = item['_source']['url']
         publication_date = item['_source']['publication_date']
         publication_date = datetime.strptime(publication_date, '%Y-%m-%dT%H:%M:%S') 
         try:
             for image in item['_source']['images']:
                 image_url = image['url']
         except KeyError:
             image_url = []
             image_caption = []
     form = rating()
     if request.method == 'POST' and form.validate():
         selected.starttime = session.pop('start_time', None)
         selected.endtime =  datetime.utcnow()
         selected.time_spent = selected.endtime - selected.starttime
         selected.rating = request.form['rating']
         db.session.commit()
         points_ratings = Points_ratings.query.filter_by(user_id = current_user.id).all()
         if points_ratings is None:
             ratings = Points_ratings(points_ratings = 0.5, user_id = current_user.id)
             db.session.add(ratings)
         else:
             dates = [item.timestamp.date() for item in points_ratings]
             points = [item.points_ratings for item in points_ratings]
             points_dict = dict(zip(dates, points))
             now = datetime.utcnow().date()
             points_today = 0
             for key, value in points_dict.items():
                 if key == now:
                     points_today += value
                 else:
                     pass
             if points_today >= 5:
                 ratings = Points_ratings(points_ratings = 0, user_id = current_user.id)
                 db.session.add(ratings)
             else:
                 ratings = Points_ratings(points_ratings = 0.5, user_id = current_user.id)
                 db.session.add(ratings)
         db.session.commit()
         return redirect(url_for('decision'))

     session['start_time'] = datetime.utcnow()
         
     return render_template('detail.html', text = text, teaser = teaser, title = title, url = url, image = image_url, time = publication_date, form = form)


@app.route('/decision', methods = ['GET', 'POST'])
@login_required
def decision():
    return render_template('decision.html')


@app.route('/reset_password_request', methods= ['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('newspage'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
        flash('Controleer uw email, u hebt informatie ontvangen hoe u uw wachtwoord opnieuw kunt instellen.')
        return redirect(url_for('login'))
    return render_template('reset_password_request.html', title="Wachtwoord opnieuw instellen", form=form)

@app.route('/reset_password/<token>', methods = ['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('newspage'))
    user = User.verify_reset_password_token(token)
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Uw wachtwoord is opnieuw ingesteld worden.')
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
        try:
            points_logins = user.sum_logins
        except:
            points_logins = 0
        try:
            points_stories = user.sum_stories
        except:
            points_stories = 0
        try:
            points_ratings = user.sum_ratings
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
                if item.stories_read >= 5 and item.times_logged_in >= 2:
                    number_invited.append(item.id)
                    invites_points = Points_invites.query.filter_by(user_guest = item.user_guest).first()
                    if invites_points is None:
                         points_invites = Points_invites(user_guest_new = item.user_guest, points_invites = 5, user_id = current_user.id)
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
    else:
        points_stories = 0
        points_invites = 0
        points_ratings = 0
        points_logins = 0
        points = 0
    return dict(points = points, points_ratings = points_ratings, points_stories = points_stories, points_invites = points_invites, points_logins = points_logins)

@app.context_processor
def points_all_users():
    points_stories_all = [item[0] for item in User.query.with_entities(User.sum_stories).all()]
    points_invites_all = [item[0] for item in User.query.with_entities(User.sum_invites).all()]
    points_ratings_all = [item[0] for item in User.query.with_entities(User.sum_ratings).all()]
    points_logins_all = [item[0] for item in  User.query.with_entities(User.sum_logins).all()]
    return dict(points_stories_all = points_stories_all, points_invites_all = points_invites_all, points_ratings_all = points_ratings_all, points_logins_all = points_logins_all) 
    
@app.context_processor
def user_agent():
    user_string = request.headers.get('User-Agent')
    user_agent = parse(user_string)
    if user_agent.is_mobile == True:
        device = "mobile"
    elif user_agent.is_tablet == True:
        device = "tablet"
    else:
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
    all_categories = ["Binnenland", "Buitenland", "Economie", "Milieu", "Wetenschap", "Immigratie", "Justitie", "Sport", "Entertainment", "Anders"]
    categories = []
    for category in all_categories: 
        if category in sel_categories: 
            categories.append(1)
        else:
            categories.append(0)
    category = Category(Binnenland = categories[0], Buitenland = categories[1], Economie = categories[2], Milieu = categories[3], Wetenschap = categories[4], \
Immigratie = categories[5], Justitie = categories[6], Sport = categories[7], Entertainment = categories[8], Anders = categories[9],  user_id = current_user.id)
    db.session.add(category)
    db.session.commit()  
    return redirect(url_for('newspage')) 

@app.route('/contact', methods = ['GET', 'POST'])
@login_required
def contact():
    form = ContactForm()
    if request.method == 'POST':
        if form.validate() == False:
            return 'Please fill in all fields <p><a href="/contact">Try Again!!! </a></p>'
        else:
            name =  current_user.username
            email =  current_user.email
            msg = Message("Message from your visitor" + name,
                          sender= email,
                          recipients=app.config['ADMINS'])
            msg.body = """
            From: %s <%s>,
            %s
            """ % (name, email, form.message.data)
            mail.send(msg)
            return "Successfully  sent message!"
    elif request.method == 'GET':
        return render_template('contact.html', form=form)

@app.route('/faq', methods = ['GET'])
def faq():
    return render_template("faq.html")

@app.route('/points', methods = ['GET'])
def get_points():
    return render_template("display_points.html")
    

@app.route('/invite', methods = ['GET', 'POST'])
def invite():
    url = "www.3bij3.nl/consent?{}".format(current_user.id)
    return render_template("invite.html", url = url)
