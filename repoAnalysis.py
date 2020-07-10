import re
import repoLibrarian
import time
import pandas

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

def timedMetricPerFileForRepo(repoTuple, metricFunction, fileCountConsumer = safeDivision):
    (user, project) = repoTuple
    repo = getRepo(user, project)
    timestamps = []
    metrics = []
    try:
        start = time.time()
        for commit in repo.iter_commits():
            fileCount = 0
            aggregatedMetric = 0
            for obj in commit.tree.traverse():
                if obj.type == 'blob' and obj.name.endswith('.java'):
                    fileCount = fileCount + 1
                    content = obj.data_stream.read().decode("CP437")#.decode("utf-8")
                    metric = metricFunction(content)
                    aggregatedMetric = aggregatedMetric + metric
            metrics.append(fileCountConsumer(aggregatedMetric, fileCount))
            timestamps.append(commit.committed_date)

        end = time.time()
        print('Time used for '+str(repoTuple)+': '+str(end - start))
#        while len(metrics) > 0 and metrics[-1] < 1:
#            metrics.pop()
#            timestamps.pop()
        return (timestamps, metrics)
    except Exception as e:
        print('Failed to analyze '+str(repoTuple)+': '+str(e))
        return ([],[])
    
def loc(contentWithHeader, **kwargs):
    return len(contentWithHeader.split('\n'))

def cloc(content, **kwargs):
    return len(content.split('\n'))

def fileCount(contentWithHeader, **kwargs):
    return 1

methodRegex = re.compile(r"(public|protected|private|static|\s) +[\w\<\>\[\]]+\s+(\w+) *\([^\)]*\) *(\{?|[^;])")
def numMethods(content, **kwargs):
    numMethods = occurencesOf(methodRegex, content)
    return numMethods

lambdaRegex = re.compile(r"->|::")
def numLambdas(content, **kwargs):
    numLambdas = occurencesOf(lambdaRegex, content) 
    return numLambdas
    
def numCommentLines(content, **kwargs):
    matches = commentRegex.findall(stringRemoveRegex.sub("\"...\"", content))
    # Lines of comment; trailing newlines indicate that comment ends with the newline and are therefore stripped
    commentLines = sum(map(lambda x: len(x.rstrip().split("\n")), matches))
    return commentLines

def numReflection(contentWithoutComments, **kwargs):
    return (contentWithoutComments.count('instanceof') + contentWithoutComments.count('.class.') + contentWithoutComments.count('Class<'))

snakeRegex = re.compile(r"\w_\w")
def numSnakes(contentWithoutComments, **kwargs):
    return len(snakeRegex.findall(contentWithoutComments))

# Can be divided by loc to get average indent
def totalIndent(content, **kwargs):
    indentOfLine = lambda line: len(line[:(len(line)-len(line.lstrip()))].replace('\t', '    ')) / 4 
    indents = list(map(indentOfLine, content.split('\n')))
    indentSum = sum(indents)
    return indentSum

def identity(x,*y):
    return x


metricSuite = [loc, cloc, fileCount, numMethods, numLambdas, numCommentLines, numReflection, numSnakes, totalIndent]
    
def calculateMetrics(repoTuple, metricSuite=metricSuite):
    (user, project, repoId) = repoTuple
    repo = repoLibrarian.getRepo(user, project)
    columns = ['sha', 'parent', 'timestamp', 'repoId'] + list(map(lambda fun: fun.__name__, metricSuite))
    results = []
    try:
        start = time.time()
        for commit in repo.iter_commits():
            resultTuple = {
                'sha' : commit.hexsha,
                'parent' : commit.parents[-1].hexsha if len(commit.parents) == 1 else None,
                'timestamp' : commit.committed_date,
                'repoId' : repoId
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
            results.append(resultTuple)
        df = pandas.DataFrame(results, columns=columns)
        end = time.time()
        print('Time used for '+str(repoTuple)+': '+str(end - start))
        return df
    except Exception as e:
        print('Failed to analyze '+str(repoTuple)+': '+str(e))
        return []