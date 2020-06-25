import psycopg2
import sqlalchemy

import pandas
from IPython.display import Audio
import time

engine = sqlalchemy.create_engine('postgresql://crm20:crm20@localhost:5433/github')
lastResult = None

def runQuery(query, mute=False):
    start = time.time()
    result = pandas.read_sql_query(query, engine)
    global lastResult
    lastResult = result
    #display(result)
    end = time.time()
    if not mute:
        print('Time used: '+str(end - start))
        display(Audio('./beep.mp3', autoplay=True))
    return result