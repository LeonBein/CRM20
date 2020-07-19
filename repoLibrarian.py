from git import Repo 
import os
import shutil
from git.db import GitDB
from git.db import GitCmdObjectDB
from git import GitCommandError

reposFolder = '/mnt/brick/crm20/repos/'
#reposFolder = './repos/'

def setReposFolder(path):
    global reposFolder
    reposFolder = path
    if not path.endswith('/'):
        reposFolder = reposFolder+'/'
    return reposFolder


def getReposFolder():
    return reposFolder
    
def pathFor(user, project):
    if not project.endswith('.git'):
        project = project + '.git'
    return reposFolder+user+'/'+project

# Parameter for recursion or to descend into subfolder
def knownRepos(path=''):
    fullPath = reposFolder+path
    for file in os.listdir(fullPath):
        if file.endswith('.git'):
            yield path+file
        elif os.path.isdir(fullPath+file):
            for element in knownRepos(path+file+'/'):
                yield element

def managedRepos():
    def splitPath(path):
        split = path.split('/')
        user = split[-2]
        project = split[-1]
        return (user, project)
    return list(map(splitPath, knownRepos()))

def hasRepo(user, project):
    return os.path.isdir(pathFor(user, project))


def deleteRepo(user, project):
    if not hasRepo(user, project):
        print('Repo "'+user+'/'+project+'" does not exist locally')
    else:
        shutil.rmtree(pathFor(user, project))
        print('Deleted repo "'+user+'/'+project+'"')
        

def downloadRepo(user, project, override=False):
    if hasRepo(user, project):
        print('Repo "'+user+'/'+project+'" already exists locally')
        if override:
            print('Overriding ...')
            deleteRepo(user, project)
        else:
            return
    try:
        repo = Repo.clone_from(url=f'https://github.com/{user}/{project}.git', to_path=reposFolder+user+'/'+project+'.git', bare=True) 
        print('Cloned repo "'+user+'/'+project+'"')
        return repo        
    except GitCommandError as err:
        print('Could not download repo "'+user+'/'+project+'": {0}'.format(err))
        

def getRepo(user, project):
    if not hasRepo(user, project):
        downloadRepo(user, project)
    return Repo.init(pathFor(user, project), bare=True, odbt=GitCmdObjectDB)


def isJavaFile(gitObject):
    return gitObject.type == 'blob' and gitObject.name.endswith('.java')

def isJavaRepo(user, project):
    try:
        repo = getRepo(user, project)
        commit = list(repo.iter_commits())[0]
        return any(isJavaFile(obj) for obj in commit.tree.traverse())
    except Exception as e:
        print('Failed to check '+str((user, project))+': '+str(e))
        return False