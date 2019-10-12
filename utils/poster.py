import requests
import json
import base64
import re
import random # for choosing titles

# Overview: get the last episode, upup (filename), and last reddit id
# from a configuration file.  Post the next upup to r/jamesjoyce

# From github, get all the upups in the episode
# if the next upup is in the episode, get its text and title
# Else, get the next episode, and get the text for the first
# upup and title from  there.
# form a last episode link from last reddit id (planned) and add to text
# Post to reddit using current text and title
# capture the new reddit id (planned)
# save episode, upup, and reddit id (planned) to configuration file

# reddit functions adapted from https://github.com/SkullTech/reddit-auto-poster.py


from inspect import currentframe, getframeinfo
import praw
import configparser
import getpass
import time


repo_base = "https://api.github.com/repos/upup1904/ulysses_splits/"
dotfile = "/home/pa/.upup_last_post"
personal_token = 'see below'

# personal_token used for req_headers, below.  Only needed for testing/
# dev; if you do need it you have to make your own and uncomment in
# headers below.  If you don't have personal token, reddit throttles
# how frequently you post.


episode_dict = {
    "telemachus" : {"next" : "nestor",},
    "nestor" : {"next" : "proteus",},
    "proteus" : {"next" : "calypso",},
    "calypso" : {"next" : "hades",},
    "hades" : {"next" : "aeolus",},
    "aeolus" : {"next" : "lestrygonians",},
    "lestrygonians" : {"next" : "sylla_and_charybdis",},
    "sylla_and_charybdis" : {"next" : "wandering_rocks",},
    "wandering_rocks" : {"next" : "sirens",},
    "sirens" : {"next" : "cyclops",},
    "cyclops" : {"next" : "nausicaa",},
    "nausicaa" : {"next" : "oxen_of_the_sun",},
    "oxen_of_the_sun" : {"next" : "circe",},
    "circe" : {"next" : "eumaeus",},
    "eumaeus" : {"next" : "ithaca",},
    "ithaca" : {"next" : "telemachus" },
}


####### GITHUB Functions #####################3


req_headers = {
#    'Authorization' : "token " + personal_token,
    'Accept' : 'application/vnd.github.v3.raw'
}

# Headers:
# personal_token is for github.  
# To run more that 60 queries an hour, you have to have a github
# personal token.   The Accept: header is needed for the use-case; 
# the markup version is "raw", without the Accept:  you get rendered text.

def get_tree_for_episode(episode) :
    if episode not in episode_dict.keys() :
        return "that is not an episode"
    
    r = requests.get(repo_base+"commits/master", headers=req_headers)
    print(r.status_code)
    commit=json.loads(r.text)  #most recent commit
    commit_sha = commit["sha"]
    r = requests.get(repo_base+'git/commits/{}'.format(commit_sha), headers=req_headers)
    print("got the commit")
    repo_dict = json.loads(r.text)
    print("made repo_dict")
    tree_sha=repo_dict["tree"]["sha"]
    r = requests.get(repo_base+"git/trees/{}".format(tree_sha), headers=req_headers)
    print("tree request gets {}".format(r.status_code))
    tree_dict = json.loads(r.text)
    root_directory_list = tree_dict["tree"]
    for i in root_directory_list :
        if i["type"] == "tree" :
            if (i["path"]) == episode  :
                return i["sha"]
    print("get_tree_for_episode failed to find episode {}".format(episode))
    return None

def get_title_for_episode(episode_tree, upup_to_persist) :
    print("matching {}".format(upup_to_persist))
    m= re.match(r'^(UPUP_[0-9]+)', upup_to_persist)
    title_file = m.group(1) + '_titles.txt'
    r = requests.get(repo_base+"git/trees/{}".format(episode_tree), headers=req_headers)
    tree_dict = json.loads(r.text)
    print("looking for " + title_file)
    title_sha = None
    for i in tree_dict["tree"] :
        if i["path"] == title_file :
            title_sha = i["sha"]
            break
    if title_sha :
        titles=get_text_from_blob(title_sha)
        title_array=titles.splitlines()
        if len(title_array) > 1 :
            random.seed()
            k  = random.randrange(len(title_array))
        else:
            k = 0
        return "[{}] {}".format(m.group(1), title_array[k])
    else:
        print("Can't find {}".format(title_file))
        return "[{}]".format(m.group(1))


def get_episodes_from_tree(tree_sha) :
    r = requests.get(repo_base+'git/trees/{}'.format(tree_sha), headers=req_headers)
    print(r.status_code)
    
    episode_tree = json.loads( r.text)
    if (episode_tree["truncated"]) :
        frameinfo = getframeinfo(currentframe())
        print (frameinfo.filename, frameinfo.lineno)
        print("get_episodes_from_tree for  was truncated, script needs rewrite")
        return None
    upups = {}
    for i in episode_tree["tree"] :
        if i["type"] == "blob" :
            if i["path"].startswith("UPUP_") :
                # print("adding {}, {}".format(i["path"], i["sha"]))
                upups[i["path"]] = i["sha"]
    return upups

def get_text_from_blob(blob_sha) :
    r  = requests.get(repo_base+'git/blobs/{}'.format(blob_sha), headers=req_headers)
    return r.text

def get_next_from_dict(d, prev, get_first=False) :
    if prev not in d and not get_first :
        raise ValueError("error in get_next_from_dict: tried to get item after {} from list not containing that value".format(prev))
    candidates = []
    for n in d.keys() :
        if re.match(r'^UPUP_[0-9]+\.md', n) :
            candidates.append(n)
    #following is a helper funtion used only in this function, gets the integer value of the upup name.  Needed so 100 comes after 99, etc.  Call sort with key-=intpart          
    def intpart(string):
        m= re.match(r'^UPUP_([0-9]+)', string)
        return int(m.group(1))
    candidates.sort(key=intpart)
    if get_first :
        return(candidates[0])
    if candidates[-1] == prev :
        return None # last one was listed, caller has to look in next episode
    i = candidates.index(prev)
    return candidates[i+1]

##### Reddit - PRAW functions ##############

## adapted from https://github.com/SkullTech/reddit-auto-poster.py
class Golem:
    def __init__(self, config):
        self.reddit = praw.Reddit(client_id=config['CONFIG']['CLIENT_ID'], 
                                  client_secret=config['CONFIG']['CLIENT_SECRET'],
                                  username=config['CONFIG']['USERNAME'],
                                  password=config['CONFIG']['PASSWORD'],
                                  user_agent='upupaway, contact /u/earthsophagus')

    def post(self, subreddit, title,  text=''): 
            submission = self.reddit.subreddit(subreddit).submit(title=title, selftext=text)
            return submission

def reddit_submit(golem, sr, post):
    sub = golem.post(sr, post['Title'], text=post['Text'])
    return sub

#### Scriptus Beginnus ##############

#get reddit credentials
config = configparser.ConfigParser()
config.read('config.ini')

with open(dotfile, 'r+') as dotfile:
    upup_to_persist = None
    episode_to_persist = None
    line = dotfile.readline()
    (last_episode, upup) = line.split()
    print("starting with ", last_episode, ' ', upup)

    episode_tree =  get_tree_for_episode(last_episode)
    upup_dict =  get_episodes_from_tree(episode_tree) # markdup file name is key, the sha is the value

    print("call get_next_from_d")
    next_upup = get_next_from_dict(upup_dict, upup )
    
    print("Prev was {}, next is {}".format(upup, next_upup))
    if next_upup is not None :
        upup_to_persist = next_upup
        episode_to_persist = last_episode
    else:
        episode_to_persist = episode_dict[last_episode]["next"]
        episode_tree = get_tree_for_episode(episode_to_persist)
        upup_dict = get_episodes_from_tree(episode_tree)
        next_upup = get_next_from_dict(upup_dict, 'dummy', True) # True gets last episode
        print ("Changed edpisodes, new one is {}".format(episode_to_persist))
        print("Next upup is {}".format(next_upup))
        upup_to_persist = next_upup

    reddit_body = get_text_from_blob(upup_dict[upup_to_persist])
    reddit_body = reddit_body + """

-------

^Posted ^with ^https://github.com/upup1904/ulysses_splits/blob/master/utils/poster.py
"""

    reddit_title = get_title_for_episode(episode_tree, upup_to_persist)
    print(reddit_title)

    try:
        config['CONFIG']['PASSWORD']
    except KeyError:
        config['CONFIG']['PASSWORD'] = getpass.getpass('[*] Password for Reddit account {}: '.format(config['CONFIG']['USERNAME']))
    try:
        WAIT = int(config['CONFIG']['WAIT'])
    except KeyError:
        WAIT = 1000

    try: 
        golem = Golem(config)
        post = {"Title" : reddit_title, "Text": reddit_body}
        reddit_result = reddit_submit(golem, "jamesjoyce", post)
    except Exception as exp:
        print('[*] Exception: {}'.format(exp))
    else:
        print('[*] Posted "{}..." on {}. Post ID: {}'.format(post['Title'][:10].rstrip(), "JamesJoyce", reddit_result.id))

    dotfile.truncate(0)
    dotfile.seek(0)
    dotfile.write("{} {}\n".format(episode_to_persist, upup_to_persist))

    
