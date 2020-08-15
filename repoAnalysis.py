'''
This module is the heart of this repository. It includes the functions that are used to analyze sets of repositories fast.
It can be structured as follows:
- The first part includes the regexes and wrapping metric functions that are used to analyze the contents of single source files. 
    All metric functions return numbers of occurences of structures in code, which can later be divided by loc to get unweighted density metrics
- The second and third part include functions to analyze a set of metrics for all files of a repository. The two parts use different approaches:
    a) Calculating absolute metrics each commit (which means that all files are analyzed) (decently fast)
    b) Calculating only deltas for each commit (starkly fast)
- The last part includes methods to run the metrics on a given set of repos and write the results to table; 
    the `runFullAnalysis` method uses all functionality of the parts above (apart from approach a))
'''

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

# ===== Regexes & Metric functions ===== 
'''String and comment regex are used globally for in this file for removal of strings and comments'''
stringRemoveRegex = re.compile(r"\".*?\"")
commentRegex = re.compile(r"//.*?\n|/\*.*?\*/", re.S)


def safeDivision(a,b):
    '''Allows division by zero, usefull e.g. when number of methods is zero in lines of code per method metric'''
    return a/b if b > 0 else 0

def identity(x,*y):
    '''Only returns first argument, usefull e.g. when ignoring secondary values in aggregation'''
    return x

def removeHeader(contentWithHeader):
    '''Used when imports and class doc are irrelevant for further analysis. Uses heuristic to cut them off: The first bracket will at the latest occur at class definition'''
    content = contentWithHeader.split('{', 1)
    content = content[1] if len(content) > 1 else ''
    return content

def occurencesOf(regex, content):
    '''Utility as many metrics are based on counting occurences of certain regexes'''
    return len(regex.findall(content))
    
def loc(contentWithHeader, **kwargs):
    '''Lines of code metric, takes full class source (as opposed to cloc)'''
    return len(contentWithHeader.split('\n'))

def cloc(content, **kwargs):
    '''Class lines of code metric, takes class without imports, inaccurate in that in might calculate some of class documentation in'''
    return len(content.split('\n'))

def file_count(contentWithHeader, **kwargs):
    '''Number of files metric, empty string indicates no file (usually when the file has been deleted), so no file is counted'''
    return 1 if contentWithHeader else 0

methodRegex = re.compile(r"(public|protected|private|static|\s) +[\w\<\>\[\]]+\s+(\w+) *\([^\)]*\) *(\{?|[^;])")
def num_methods(content, **kwargs):
    '''Number of methods metric, identified by method header'''
    num_methods = occurencesOf(methodRegex, content)
    return num_methods

lambdaRegex = re.compile(r"->|::")
def num_lambdas(content, **kwargs):
    '''Number of lambdas metric. Lambdas are counted when using the `::` or `->` operator. This is more limited, as it does not count usages of function objects when they come from a library or framework or are from a class that implements (not extends) a functional interface. However, static type checking is way out of scope of this project. '''
    num_lambdas = occurencesOf(lambdaRegex, content) 
    return num_lambdas
    
def num_comment_lines(content, **kwargs):
    '''Number of comment lines metric. Comments in Java can be oneline, which starts with `//` and always counts as one comment line because there can never be two in one line, or multiline, (between `/*` and `*/`), which counts as as many lines that there are in, so it's ok to just split along line breaks).'''
    matches = commentRegex.findall(stringRemoveRegex.sub("\"...\"", content))
    # Trailing newlines indicate that the regex match ends with the newline (indicating a oneline comment) and are therefore stripped
    commentLines = sum(map(lambda x: len(x.rstrip().split("\n")), matches))
    return commentLines

def num_reflection(contentWithoutComments, **kwargs):
    '''Number of reflection uses. Only counted by accessing objects of class Class<T> or using instanceof; can be extended in future'''
    return (contentWithoutComments.count('instanceof') + contentWithoutComments.count('.class.') + contentWithoutComments.count('Class<'))

snakeRegex = re.compile(r"\w_\w")
def num_snakes(contentWithoutComments, **kwargs):
    '''Snake usage. Expected to deviate for python users'''
    return len(snakeRegex.findall(contentWithoutComments))

def total_indent(content, **kwargs):
    '''Calculates indent summed up for all lines metric. Assumes one tab or 4 spaces for one indentation depth. See `Lab for new metrics` in RepoAnalysis_Historical notebook for details'''
    indentOfLine = lambda line: len(line[:(len(line)-len(line.lstrip()))].replace('\t', '    ')) / 4 
    indents = list(map(indentOfLine, content.split('\n')))
    indentSum = sum(indents)
    return indentSum

'''
The metric suite is a set of metric functions that can be applied together to repositories. 
Function names should be in snake case as they are later used to determine column names.
Functions should accept **kwargs and are passed contents of files in different formats (full, without header, without header, strings and comments)
'''
metricSuite = [loc, cloc, file_count, num_methods, num_lambdas, num_comment_lines, num_reflection, num_snakes, total_indent]
   

# ===== a) Absolute occurences approach - Analysis code for Iteration #1 ===== 
def calculateMetrics(repoTuple, metricSuite=metricSuite):
    '''
    Calculates a set of given metrics for a repository. 
    Returns commit information and full project metric results for each commit in form of a Pandas Dataframe.
    Metricfunctions should fulfill the limitations described for `metricSuite`
    '''
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
    '''Calculates a set of given metrics for all files of a single commit and sums them up.'''
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
    

# ===== b) Delta occurences approach Analysis code for iteration #2 and #3 (and future iterations) ===== 
def safeToInt(string):
    '''Used to safely interpret removed files in git logs'''
    return 0 if string == '-' else int(string)

def block_to_stats(block):
    '''Splits one block of commit data into diff information of each changed file, assumes a git log numstat format'''
    lines = block.split('\n')
    header = lines[0]
    lines = filter(lambda line: line.endswith('.java'), lines)
    changed_files = list(map(lambda line: line.split('\t'), lines))
    additions = sum(map(lambda file: safeToInt(file[0]), changed_files))
    deletions = sum(map(lambda file: safeToInt(file[1]), changed_files))
    return (header, (changed_files, additions, deletions))

def file_contents(tree, path):
    '''Safely gets file contents in a git tree, if the file is not existent, it has been deleted'''
    try: 
        obj = tree / path
        return obj.data_stream.read().decode("CP437")
    except KeyError:
        return ''
    
def addMetricsOfTo(metricSuite, contentWithHeader, resultTuple, factor=1):
    '''
    Calls all functions of a metric suite on full file content, without header, and without comments and weightedly adds the occurences to an existing sum 
    Used to aggregate for each file of a commit, weighting can be used to subtract the parent commit data, thus effectively calculating delta.
    '''
    content = removeHeader(contentWithHeader)
    contentWithoutStrings = stringRemoveRegex.sub("\"...\"", content)
    contentWithoutComments = commentRegex.sub("/*...*/", contentWithoutStrings)
    for metricFunction in metricSuite:
        metric = metricFunction(content=content, contentWithHeader=contentWithHeader, contentWithoutComments=contentWithoutComments)
        resultTuple[metricFunction.__name__] = resultTuple[metricFunction.__name__] + metric * factor

def deltaMetricsForCommit(commit, metricSuite, repoId, change):
    '''
    Sums up all change of one commit by subtracting occurence metrics in that commit from those of the parent commit
    '''
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
    '''
    Calculates deltas of occurence metrics for all commits of one repository 
    Passed metric functions should fulfill the limitations described for `metricSuite`
    Commit iterator is created with git log, as delta information can addtionally derived on the fly
    '''
    (user, project, repoId) = repoTuple
    repo = repoLibrarian.getRepo(user, project)
    columns = ['sha', 'parent', 'timestamp', 'repo_id', 'additions', 'deletions'] + list(map(lambda fun: fun.__name__, metricSuite))
    results = []
    try:
        start = time.time()
        log = repo.git.log('--numstat', '--format=//%H', '--all')# note the `//%H`, `//` is a safe delimiter as it cannot occur in file paths on unix, macos, or windows 
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
    
# ===== Suite running code for future iterations ===== 
def runFullAnalysis(repos, tableName, repoFolder, logfile='log.txt', suite=metricSuite):
    '''
    Fully runs all functions of a metric suite for all repositories and writes the results to database (parallelizes mutliple runs of `runDeltaSuite`)
    Uses the delta approach for each commit of each repo.
    Creates a log file because of the large run time
    '''
    createResultTable(tableName, suite)
    repoLibrarian.setReposFolder(repoFolder)
    start = time.time()
    with Pool(int(multiprocessing.cpu_count()*3/4)) as pool:
        allMetrics = pool.map(functools.partial(runDeltaSuite, tableName=tableName, logfile=logfile, suite=suite), repos)
    end = time.time()
    dbUtils.log('Total Time used: '+str(end - start))
    
def runDeltaSuite(repo, tableName, logfile='log.txt', suite=metricSuite):
    '''
    Runs all functions of a metric suite for a single repository and writes the results to database
    '''
    with io.capture_output() as output:
        data = calculateDeltaMetrics(repo, suite)
        dbUtils.writeDataToDb(data, tableName)
    dbUtils.log(output, logfile)
    return len(data) > 0

def createResultTable(tableName, suite=metricSuite):
    '''Creates a new database for a given metric suite, column names are chosen by metric function names'''
    columns = [Column('sha', String), Column('parent', String), Column('timestamp', Integer), Column('repo_id', Integer), Column('additions', Integer), Column('deletions', Integer)]
    columns = columns + list(map(lambda func: Column(func.__name__, Integer), suite))
    dbUtils.createTable(tableName, columns)