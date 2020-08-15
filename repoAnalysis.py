import re
import repoLibrarian
import time
import pandas

from git.util import hex_to_bin
from git import Commit

import functools
import dbUtils
from sqlalchemy import Column, Integer, String
import multiprocessing
from multiprocessing import Pool
from IPython.utils import io

stringRemoveRegex = re.compile(r"\".*?\"")
commentRegex = re.compile(r"//.*?\n|/\*.*?\*/", re.S)

def safeDivision(a,b):
    return a/b if b > 0 else 0

def removeHeader(contentWithHeader):
    content = contentWithHeader.split('{', 1)
    content = content[1] if len(content) > 1 else ''
    return content

def occurencesOf(regex, content):
    return len(regex.findall(content))
    
def loc(contentWithHeader, **kwargs):
    return len(contentWithHeader.split('\n'))

def cloc(content, **kwargs):
    return len(content.split('\n'))

def file_count(contentWithHeader, **kwargs):
    return 1 if contentWithHeader else 0

methodRegex = re.compile(r"(public|protected|private|static|\s) +[\w\<\>\[\]]+\s+(\w+) *\([^\)]*\) *(\{?|[^;])")
def num_methods(content, **kwargs):
    num_methods = occurencesOf(methodRegex, content)
    return num_methods

lambdaRegex = re.compile(r"->|::")
def num_lambdas(content, **kwargs):
    num_lambdas = occurencesOf(lambdaRegex, content) 
    return num_lambdas
    
def num_comment_lines(content, **kwargs):
    matches = commentRegex.findall(stringRemoveRegex.sub("\"...\"", content))
    # Lines of comment; trailing newlines indicate that comment ends with the newline (indicating a oneline comment) and are therefore stripped
    commentLines = sum(map(lambda x: len(x.rstrip().split("\n")), matches))
    return commentLines

def num_reflection(contentWithoutComments, **kwargs):
    return (contentWithoutComments.count('instanceof') + contentWithoutComments.count('.class.') + contentWithoutComments.count('Class<'))

snakeRegex = re.compile(r"\w_\w")
def num_snakes(contentWithoutComments, **kwargs):
    return len(snakeRegex.findall(contentWithoutComments))

# Can be divided by loc to get average indent
def total_indent(content, **kwargs):
    indentOfLine = lambda line: len(line[:(len(line)-len(line.lstrip()))].replace('\t', '    ')) / 4 
    indents = list(map(indentOfLine, content.split('\n')))
    indentSum = sum(indents)
    return indentSum

def identity(x,*y):
    return x


metricSuite = [loc, cloc, file_count, num_methods, num_lambdas, num_comment_lines, num_reflection, num_snakes, total_indent]
   
# Analysis code for Iteration #1
def calculateMetrics(repoTuple, metricSuite=metricSuite):
    (user, project, repoId) = repoTuple
    repo = repoLibrarian.getRepo(user, project)
    columns = ['sha', 'parent', 'timestamp', 'repo_id'] + list(map(lambda fun: fun.__name__, metricSuite))
    results = []
    try:
        start = time.time()
        for commit in repo.iter_commits('--all'):
            results.append(metricsForCommit(commit, metricSuite, repoId))
        df = pandas.DataFrame(results, columns=columns)
        end = time.time()
        print('Time used for '+str(repoTuple)+': '+str(end - start))
        return df
    except Exception as e:
        print('Failed to analyze '+str(repoTuple)+': '+str(e))
        return []
    
def metricsForCommit(commit, metricSuite, repoId):
    resultTuple = {
        'sha' : commit.hexsha,
        'parent' : commit.parents[-1].hexsha if len(commit.parents) == 1 else None,
        'timestamp' : commit.committed_date,
        'repo_id' : repoId
    }
    for metricFunction in metricSuite:
        resultTuple[metricFunction.__name__] = 0
    for obj in commit.tree.traverse():
        if obj.type == 'blob' and obj.name.endswith('.java'):
            contentWithHeader = obj.data_stream.read().decode("CP437")#.decode("utf-8")
            content = removeHeader(contentWithHeader)
            contentWithoutStrings = stringRemoveRegex.sub("\"...\"", content)
            contentWithoutComments = commentRegex.sub("/*...*/", contentWithoutStrings)
            for metricFunction in metricSuite:
                metric = metricFunction(content=content, contentWithHeader=contentWithHeader, contentWithoutComments=contentWithoutComments)
                resultTuple[metricFunction.__name__] = resultTuple[metricFunction.__name__] + metric
    return resultTuple
    

# Analysis code for iteration #2 and #3 (and future iterations)
def safeToInt(string):
    return 0 if string == '-' else int(string)

def block_to_stats(block):
    lines = block.split('\n')
    header = lines[0]
    lines = filter(lambda line: line.endswith('.java'), lines)
    changed_files = list(map(lambda line: line.split('\t'), lines))
    additions = sum(map(lambda file: safeToInt(file[0]), changed_files))
    deletions = sum(map(lambda file: safeToInt(file[1]), changed_files))
    return (header, (changed_files, additions, deletions))

def file_contents(tree, path):
    try: 
        obj = tree / path
        return obj.data_stream.read().decode("CP437")
    except KeyError:
        return ''
    
def addMetricsOfTo(metricSuite, contentWithHeader, resultTuple, factor=1):
    content = removeHeader(contentWithHeader)
    contentWithoutStrings = stringRemoveRegex.sub("\"...\"", content)
    contentWithoutComments = commentRegex.sub("/*...*/", contentWithoutStrings)
    for metricFunction in metricSuite:
        metric = metricFunction(content=content, contentWithHeader=contentWithHeader, contentWithoutComments=contentWithoutComments)
        resultTuple[metricFunction.__name__] = resultTuple[metricFunction.__name__] + metric * factor

def deltaMetricsForCommit(commit, metricSuite, repoId, change):
    changed_files, additions, deletions = change
    
    resultTuple = {
        'sha' : commit.hexsha,
        'parent' : commit.parents[-1].hexsha if len(commit.parents) == 1 else None,
        'timestamp' : commit.committed_date,
        'repo_id' : repoId,
        'additions' : additions,
        'deletions' : deletions
    }    
    for metricFunction in metricSuite:
        resultTuple[metricFunction.__name__] = 0
        
    for added, removed, file in changed_files:
        addMetricsOfTo(metricSuite, file_contents(commit.tree,            file), resultTuple    )
        addMetricsOfTo(metricSuite, file_contents(commit.parents[0].tree, file), resultTuple, -1)
            
    return resultTuple
    

def calculateDeltaMetrics(repoTuple, metricSuite=metricSuite):
    (user, project, repoId) = repoTuple
    repo = repoLibrarian.getRepo(user, project)
    columns = ['sha', 'parent', 'timestamp', 'repo_id', 'additions', 'deletions'] + list(map(lambda fun: fun.__name__, metricSuite))
    results = []
    try:
        start = time.time()
        log = repo.git.log('--numstat', '--format=//%H', '--all')
        commits = log.split('//')[1:]#First 'part' is empty string before the first commit
        changes = map(block_to_stats, commits)

        for hexsha, change in changes:
            commit = Commit(repo, hex_to_bin(hexsha))
            if len(commit.parents) == 1:
                results.append(deltaMetricsForCommit(commit, metricSuite, repoId, change))
                
        df = pandas.DataFrame(results, columns=columns)
        end = time.time()
        print('Time used for '+str(repoTuple)+': '+str(end - start))
        return df
    except Exception as e:
        print('Failed to analyze '+str(repoTuple)+': '+str(e))
        return []
    
# Suite running code for future iterations
def runFullAnalysis(repos, tableName, repoFolder, logfile='log.txt', suite=metricSuite):
    createResultTable(tableName, suite)
    repoLibrarian.setReposFolder(repoFolder)
    start = time.time()
    with Pool(int(multiprocessing.cpu_count()*3/4)) as pool:
        allMetrics = pool.map(functools.partial(runDeltaSuite, tableName=tableName, logfile=logfile, suite=suite), repos)
    end = time.time()
    dbUtils.log('Total Time used: '+str(end - start))
    
def runDeltaSuite(repo, tableName, logfile='log.txt', suite=metricSuite):
    with io.capture_output() as output:
        data = calculateDeltaMetrics(repo, suite)
        dbUtils.writeDataToDb(data, tableName)
    dbUtils.log(output, logfile)
    return len(data) > 0

def createResultTable(tableName, suite=metricSuite):
    columns = [Column('sha', String), Column('parent', String), Column('timestamp', Integer), Column('repo_id', Integer), Column('additions', Integer), Column('deletions', Integer)]
    columns = columns + list(map(lambda func: Column(func.__name__, Integer), suite))
    dbUtils.createTable(tableName, columns)