'''
This small module contains utility functions to run database queries and other long calculations. Its roots lay in the DataExplorer notebook.
'''

import psycopg2
import sqlalchemy
from sqlalchemy import MetaData, Table

import pandas
from IPython.display import Audio
import time
import multiprocessing
from datetime import datetime

defaultSchema = 'crm20'
engine = sqlalchemy.create_engine('postgresql://crm20:crm20@localhost:5433/github')
lastResult = None

'''
The `runQuery` method provides several features:
- It acts as wrapper to run queries against the database
- It (optionally) beeps at the end of a database run, which helped a lot in development, as I could focus on other things while waiting for queries to end, without having to look if the query finished every time
- It can save the last result to memory, as a fallback if the display session crashed while running the query (or the query just took too long to keep the session up)
- It wraps a pandas.read, which enforces each query to have a return type; this strongly encourages a exploratory way of developing
'''
def runQuery(query, mute=False):
    start = time.time()
    result = pandas.read_sql_query(query, engine)
    global lastResult
    lastResult = result
    end = time.time()
    print('Time used: '+str(end - start))
    if not mute:
        display(Audio('./beep.mp3', autoplay=True))
    return result

'''
The `log` function is meant to run very long running calculation. For those, it is impossible to keep up a single display session, which is why the output has to be redirected. Timestamps additionally show when progress has been made.
'''
logSemaphore = multiprocessing.Semaphore()
def log(text, file='log.txt'):
    with logSemaphore:
        with open(file, 'a') as file:
            file.write('========= '+str(datetime.now())+' ==========\n'+str(text)+'\n')
            
'''
Wraps table creation (for modularity); originates from the RepoAnalysis notebook
'''       
def createTable(tableName, columns):
    meta = MetaData(schema=defaultSchema)
    table = Table(
        tableName, meta,
        *columns
    )
    meta.create_all(engine)
    engine.dispose()

'''
Wraps table deletion, exception handling catches error that is thrown because the query does not return data; originates from the RepoAnalysis notebook
'''
def deleteTable(tableName):
    try:
        runQuery('''
            DROP TABLE '''+defaultSchema+'''.'''+tableName+'''
        ''')
    except:
        pass

'''
Safely writes a pandas dataframe to a given table; originates from the RepoAnalysis notebook
'''
dataBaseSemaphore = multiprocessing.Semaphore()
def writeDataToDb(data, tableName):
    with dataBaseSemaphore:
        data.to_sql(tableName, schema=defaultSchema, con=engine, if_exists='append', index=False)
        engine.dispose()