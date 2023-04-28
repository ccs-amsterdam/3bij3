 3bij3 - A framework for testing recommender systems and their effects 

3bij3 allows you to set up social-science experiments with news recommender systems. You set up the recommender system, deploy it, and participants use it in their web browser - just like any news site.

If you use it, please cite the original publication that describes the first version of 3bij3:

```
@article{3bij3,
  title = {{3bij3}: {D}eveloping a framework for researching recommender systems and their effects},
  author = {Felicia Loecherbach and Damian Trilling},
  year = {2020},
  volume = {2},
  issue = {1},
  pages = {53--79},
  doi = {10.5117/CCR2020.1.003.LOEC},
  journal = {Computational Communication Research}
}
```

An example of an empirical study that used 3bij3 is:

```
@inproceedings{Loecherbach2021,
  address = {New York, NY},
  author = {Loecherbach, Felicia and Welbers, Kasper and Moeller, Judith and Trilling, Damian and {Van Atteveldt}, Wouter},
  booktitle = {13th ACM Web Science Conference (WebSci 2021)},
  doi = {10.1145/3447535.3462506},
  isbn = {978-1-4503-8330-1},
  pages = {282--290},
  publisher = {ACM},
  title = {{Is this a click towards diversity? Explaining when and why news users make diverse choices}},
  year = {2021}
}
```

Please note that while 3bij3 aims at making it (relatively) easy to set up your own news recommender website, including participant management tasks, such things are not plug and play. The instructions below should make it relatively straightforward to run your own 3bij3 - but still, you probably do need at least some knowledge of Python and (if you want to run 3bij3 not only on your local computer) some Linux server admin stuff. If you want to dive really into the backend, also some SQL knowledge won't hurt. 3bij3 uses the Flask microframework, which you may want to have a look at if you aren't familiar with it and want to dig deeper into the code.

Because in almost all scenarios, 3bij3 will be ultimately deployed on a Linux server, these instructions assume that you work on Linux. If you use MacOS, it's probably 99% identical -- for Windows, you may have to improvise a bit more.

 Installation

To get started, let us first assume that you want to install 3bij3 locally. You probably want to do this anyway first for testing purposes, and to configure everything such that it fits your needs.

1. Clone the repository

```
git clone https://github.com/ccs-amsterdam/3bij3
cd 3bij3
```

2. Create a virtual environment and activate it:

```
python3 -m venv venv
source venv/bin/activate
```

3. Install requirements with 

```
pip install -r requirements.txt
```

You may get an error saying sth about `wheels`. If so, just run the command again, the second time should fix it.

There is some dependency error that I haven't had the time to figure out - there are incompatible ways of installing flask bootstrap. To be sure, do:

```
pip uninstall flask-bootstrap bootstrap-flask
pip install bootstrap-flask
```


4. Set up a MySQL database to store both the news articles as well as the user data. You can do this with docker:
Note that you need to modify the full path after the `src` arguments. These are the folders where the mysql data are stored. You can leave both lines starting with `--mount` away, but then your database isn't persistent: If docker stops, everything is lost. )
```
docker run \
--mount type=bind,src=/home/damian/onderzoek-github/3bij3/data/,dst=/var/lib/mysql \
--mount type=bind,src=/home/damian/onderzoek-github/3bij3/databackup,dst=/data/backups \
-p 3307:3306 \
--name 3bij3 \
-e MYSQL_ROOT_PASSWORD=somepassword \
-d mysql/mysql-server
```
We chose here to bind to port 3307 on the host machine (instead of 3306 as inside the container) to avoid collusions with a potentially running local instance of mysql on the host machine.

**(of course, choose a different password than `somepassword`!)**

You can check whether it is running via `docker ps`. Y


Now log into mysql with `docker exec -it 3bij3 mysql -u root -p`. Enter the root password that you just chose.

Then, create a new user and a database for your project. Note that you can (and should) choose the username and password freely.

```
CREATE USER 'driebijdrie'@'%' IDENTIFIED BY 'testpassword!';
GRANT ALL PRIVILEGES ON * . * TO 'driebijdrie'@'%';
FLUSH PRIVILEGES;
CREATE DATABASE 3bij3;
exit;

```
The SQL code above will create a user `driebijdrie` with the password `'testpassword!'`. You will later use these to let 3bij3 connect to the database. It also creates a database called `3bij3`. You could potentially have multiple databases for multiple projects, but for now, let's just assume there is one.

Check whether you can now log on with your new (non-root) user:
```docker exec -it 3bij3 mysql -u driebijdrie -p```

You can exit with `exit;`, don't forget the semicolon.

If you have a local mysql client, you should also be able to connect like this:
```mysql --host=172.17.0.1 --port=3307 -u driebijdrie -p```
(you don't have to have this, though, to run 3bij3.)





5. Initialise the database with the following commands:

```bash
flask db init
flask db migrate
flask db upgrade
```


6. Add some articles to the database. To get started, maybe just run the RSS scraper once.

```
./runReadRSS.sh
```



6. Set up your credentials

You pass your credentials using environment variables.
Alternatively, you can store them in a file called `.env` that you create in the 3bij3 folder:
```
MYSQLHOST=172.17.0.1
MYSQLPORT=3307
MYSQLDB=3bij3
MYSQLUSER=driebijdrie
MYSQLPASSWORD="testpassword!"
```

3bij3 will also run without email functionality, and that can be fine for local and small-scale experiments. However, you most likely want to have the possibility to send users remiders, or to allow them to reset there passwords. In that case, also add the following variables to your environment (depending on your mail-provider):
```
MAIL_SERVER="smtp.somedomain.com"
MAIL_USERNAME="bla@bla"
MAIL_PASSWORD="blabla"
ADMINS=['bla@bla.com','bla2@bla3.eu']
```

 Filling the database

Before you can get started, you first need to fill your database with some articles:

```bash
./runReadRSS.sh
```

When ``really'' using the app, make sure to run this script regularly (e.g., a few times per hour).

Simiarily, you need to run these two scripts regularly to calculate document similarities:


```bash
./runGetSims.sh
```

However, you don't have to necessarily do this before the first run.



 First steps using

First, make sure that your SQL database backend is running. If you followed this tutorial, you can check this with `docker ps`, and if the container has not been started (for example, because you rebooted your machine), you can restart it with `docker restart 3bij3`


Then, run a local flask server with (make sure the virtual environment you used before is activated):

```
FLASK_APP=3bij3.py flask run
```

If you want to see more debugging logs, you could do this instead:
```
flask --app 3bij3 --debug run
```

You can then create a user, log in, and start browsing.


 Customizing 3bij3 for your experiment

(to be added - which files to change etc.)


 Deploying 3bij3 for a ``real'' experiment

There is a great tutorial on how to deploy Flask apps on a production server available at https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-uswgi-and-nginx-on-ubuntu-18-04.

We assume that you use `nginx` as a web server, and we use `gunicorn` as WSGI server.

We advise to take a look, also for the prerequisits etc. Broadly speaking, the steps you need to take are:

1. Create a file `/etc/systemd/system/3bij3.service` with the following cotent:

```
[Unit]
Description=Gunicorn instance to serve 3bij3
After=network.target

[Service]
User=stuart
Group=www-data
WorkingDirectory=/home/stuart/3bij3
Environment="PATH=/home/stuart/3bij3/venv/bin"
Environment="SCRIPT_NAME=/3bij3"
ExecStart=/home/stuart/3bij3/venv/bin/gunicorn --workers 3 --limit-request-line 8190 --bind unix:3bij3.sock -m 007 wsgi:app

[Install]
WantedBy=multi-user.target
```
Of course, change `/home/stauart/3bij3` to the correct location of your 3bij3 folder. Also, depending on the scale of your experiment, you may want to change the number of workers. Also, make sure that `User` and `Group` are defined correctly. Set the group of the 3bij3 directory to `www-data`.

2. Tell NGINX to serve 3bij3

Add the following `location` to `/etc/nginx/sites-enabled` (in case you want to serve 3bij3 at /3bij3/). Again, adapt accordingly.

```
location /3bij3/ {
  include proxy_params;
  proxy_pass http://unix:/home/stuart/3bij3/3bij3.sock;
  proxy_buffers 4 512k;
  proxy_buffer_size 256k;
  proxy_busy_buffers_size 512k;
    }
```

3. Create a socks file 

e.g., like this:

```
touch /home/stuart/3bij3/3bij3.sock
```

4. Make sure to configure NGINX to use http

You really shoud allow nginx only to listen to port 443 (SSL). You could use letsencrypt if necessary. In any case, make sure that people cannot address 3bij3 using http and have to use https.

5. Make sure 3bij3 is running

Make sure that your environment variables are set or that you have a working `.env` file .

```
systemctl daemon-reload
service 3bij3 restart
service 3bij3 status
```

6. Create crontab jobs

Add jobs to your crontab for re-occuring jobs, more or less like this:

```
*/5 * * * * /home/damian/github/3bij3/runReadRSS.sh >> /home/damian/github/3bij3/logs/readRSS.log 2>&1
*/5 * * * * /home/damian/github/3bij3/runGetSims.sh >> /home/damian/github/3bij3/logs/getsims.log 2>&1
```

Also adapt the shell scripts (`run....sh`) to your needs