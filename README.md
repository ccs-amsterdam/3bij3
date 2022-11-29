# 3bij3 - A framework for testing recommender systems and their effects 

## Installation

1. Clone the repository

```
git clone https://github.com/nickma101/3bij3
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

# TODO ADD ISTRUCTION TO ADD EXAMPLE ARTICLES FIRST


## Usage

First, make sure that your SQL database backend is running. If you followed this tutorial, you can check this with `docker ps`, and if the container has not been started (for example, because you rebooted your machine), you can restart it with `docker restart 3bij3`


Then, run a local flask server with:

```
FLASK_APP=3bij3.py flask run
```

You can then create a user, log in, and start browsing.
