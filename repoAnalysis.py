import re


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

methodRegex = re.compile(r"(public|protected|private|static|\s) +[\w\<\>\[\]]+\s+(\w+) *\([^\)]*\) *(\{?|[^;])")
def locmOf(contentWithHeader, **kwargs):
    content = removeHeader(contentWithHeader)
    numMethods = occurencesOf(methodRegex, content)
    loc = len(content.split('\n'))
    locm = safeDivision(loc, numMethods)
    return locm

lambdaRegex = re.compile(r"->|::")
def lambdaDensity(content, loc, **kwargs):
    numLambdas = occurencesOf(lambdaRegex, content) 
    return numLambdas * 1000 / loc
    
stringRemoveRegex = re.compile(r"\".*?\"")
commentRegex = re.compile(r"//.*?\n|/\*.*?\*/", re.S)
def commentDensity(content, loc, **kwargs):
    matches = pattern.findall(stringRemoveRegex.sub("\"...\"", x))
    # Lines of comment; trailing newlines indicate that comment ends with the newline and are therefore removed
    commentLines = sum(map(lambda x: len(x.rstrip().split("\n")), matches))
    return commentLines * 1000 / loc

def reflectionDensity(content, loc, **kwargs):
    contentWithoutStrings = stringRemoveRegex.sub("\"...\"", content)
    contentWithoutComments = commentRegex.sub("/*...*/", contentWithoutStrings)
    return (contentWithoutComments.count('instanceof') + contentWithoutComments.count('.class.') + contentWithoutComments.count('Class<')) * 1000 / loc

snakeRegex = re.compile(r"\w_\w")
def snakeDensity(content, loc, **kwargs):
    contentWithoutStrings = stringRemoveRegex.sub("\"...\"", content)
    contentWithoutComments = commentRegex.sub("/*...*/", contentWithoutStrings)
    return len(snakeRegex.findall(contentWithoutComments)) * 1000 / loc

def indentPerLoc(contentWithHeader, loc, **kwargs):
    content = removeHeader(contentWithHeader)
    indents = list(map(lambda line: len(line[:(len(line)-len(line.lstrip()))].replace('\t', '    ')) / 4, content.split('\n')))
    avg = sum(indents)/len(indents)
    return avg

def loc(content):
    return len(content.split('\n'))

def identity(x,*y):
    return x