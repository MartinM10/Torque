# Torque
## Install
cd Torque\
python -m venv venv\
source /venv/bin/activate\
pip install -r requirements.txt\

If you get an error installing cartopy. Probably you can fix the error with this\
sudo apt-get install libproj-dev proj-data proj-bin  
sudo apt-get install libgeos-dev 

If you want to run in localhost, you must uncomment in settings.py the following section: \
'''\
DATABASES = { \
    'default': { \
        'ENGINE': 'django.db.backends.sqlite3', \
        'NAME': 'torque_db',\
    }\
}\
'''

You can uncomment and use mysql as the database, but the database must be previously created\ 

For load schema to database: \
python manage.py migrate

## Test
python manage.py runserver

