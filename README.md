## Augur

Augur is a webapp for tracking reference desk statistics for libraries, inspired by libstats. It was written in Python and Javascript.
Python version 2.7.2+ required.

In Ubuntu/Debian:

sudo apt-get install python-pip python-dev build-essential

sudo pip install --upgrade pip

sudo pip install --upgrade virtualenv

sudo apt-get install git

sudo apt-get install mysql-server

sudo apt-get install python-mysqldb

mysql -u root -p

create database augurdb;

git clone https://github.com/szweibel/Augur.git

pip install -r requirements.txt

Change 'settings.cfg.template' to 'settings.cfg'

In settings.cfg, change the secret key to whatever you'd like, and replace <USER> and <PASSWORD> with the root username and password you use for MySQL.

python manage.py restart_db

gunicorn -w 4 -b 0.0.0.0:5000 augur:app

Now Augur is running on port 5000. Default username and password in manage.py line 16.
