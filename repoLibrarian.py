'''
This module aims at curating large sets of repositories.
It provides utility to clone, delete, access, and classify repositories.
For a demonstration of usage, refer to the RepoLibrarian notebook
'''

from git import Repo 
import os
import shutil
from git.db import GitDB
from git.db import GitCmdObjectDB
from git import GitCommandError

'''The current folder where repositories are saved. Can be changed with accessors which allows to managing different sets of repositories'''
reposFolder = '/mnt/brick/crm20/repos/'
#reposFolder = './repos/'

def setReposFolder(path):
    '''Accessor to set repos folder, allows to switch to a different repository working set'''
    global reposFolder
    reposFolder = path
    if not path.endswith('/'):
        reposFolder = reposFolder+'/'
    return reposFolder


def getReposFolder():
    '''The current folder where repositories are saved, forms a current working set of repositories'''
    return reposFolder
    
def pathFor(user, project):
    '''Path where a repository would be saved if managed by this module'''
    if not project.endswith('.git'):
        project = project + '.git'
    return reposFolder+user+'/'+project

def knownRepos(path=''):
    '''Deeply searches the current repos directory for repositories; Takes a path parameter for recursion or to descend into a subfolder'''
    fullPath = reposFolder+path
    for file in os.listdir(fullPath):
        if file.endswith('.git'):
            yield path+file
        elif os.path.isdir(fullPath+file):
            for element in knownRepos(path+file+'/'):
                yield element

def managedRepos():
    '''Wrapper for knownRepos that returns them in format (user,project) which is usefull to pass this tuples to other functions'''
    def splitPath(path):
        split = path.split('/')
        user = split[-2]
        project = split[-1]
        return (user, project)
    return list(map(splitPath, knownRepos()))

def splitUrl(url):
    '''Utility to extract user and project name from a github url'''
    split = url.split('/')
    user = split[-2]
    project = split[-1]
    return (user, project)

def hasRepo(user, project):
    '''Checks if a repository is managed by this module'''
    return os.path.isdir(pathFor(user, project))


def deleteRepo(user, project):
    '''Removes a repository from management by deleting it from disk'''
    if not hasRepo(user, project):
        print('Repo "'+user+'/'+project+'" does not exist locally')
    else:
        shutil.rmtree(pathFor(user, project))
        print('Deleted repo "'+user+'/'+project+'"')
        

def downloadRepo(user, project, override=False):
    '''Downloads a repo into management, allows to override existing checkouts by flag. Downloading might not always be possible due to urls being invalid due to renames'''
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
        print('Could not download repo "'+user+'/'+project)
        raise err
        

def getRepo(user, project):
    '''Utility that gives a repository handle and downloads if necessary, takes responsibility of checking whether a repository is already managed from user'''
    if not hasRepo(user, project):
        downloadRepo(user, project)
    return Repo.init(pathFor(user, project), bare=True, odbt=GitCmdObjectDB)


def isJavaFile(gitObject):
    '''Checks if gitpython gitobject is a java source code file'''
    return gitObject.type == 'blob' and gitObject.name.endswith('.java')

def isJavaRepo(user, project, *args):
    '''Checks if a repository is a java repository, downloads repository if necessary and returns false if errors occur'''
    try:
        repo = getRepo(user, project)
    except Exception as e:
        print('Failed to download '+str((user, project))+': '+str(e))
        return False
    
    try:
        return next(filter(lambda x: x.endswith('.java'), repo.git.ls_tree('--full-tree', '--name-only', '-r', 'HEAD').split('\n')), None) != None
    except Exception as e:
        print('Failed to check '+str((user, project))+': '+str(e))
        return False