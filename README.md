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

4. Set up a MySQL database to store both the news articles as well as the user data. You can do this with docker:

```
docker run -p 127.0.0.1:3307:3306 --name 3bij3 -e MYSQL_ROOT_PASSWORD=somepassword -d mysql/mysql-server
```
We chose here to bind to port 3307 on the host machine (instead of 3306 as inside the container) to avoid collusions with a potentially running local instance of mysql on the host machine.

**(of course, choose a different password than `somepassword`!)**


5. Add data to the elasticsearch database. To get started, you can use the [add_example_data.py](add_example_data.py) script to add some wikinews articles:

```
python add_example_data.py
```

(depending on you settings, you might need to run the first command as administrator, e.g. `sudo docker ...`)

5. Initialise the database with the following commands:

```python3
flask db init
flask db migrate
flask db upgrade
```


## Usage

Run a local server with:

```
FLASK_APP=3bij3.py flask run
```

You can then create a user, log in, and start browsing.
