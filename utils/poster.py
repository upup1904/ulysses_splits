import requests
import json
import base64
import re


from inspect import currentframe, getframeinfo
#frameinfo = getframeinfo(currentframe())
#    print frameinfo.filename, frameinfo.lineno


personal_token = 'normally not needded'

# normally you can just leave "auth" as an empty dictionary.  However,
# to run more that 60 queries an hour, you have to have a github
# personal token, and you'd have to clone the repo to one you could
# grant access to.  Script needs it to be the Accept: header to
# get postable text

req_headers = {
    #'Authorization' : "token " + personal_token,
    'Accept' : 'application/vnd.github.v3.raw'
}

# try:


repo_base = "https://api.github.com/repos/upup1904/ulysses_splits/"
dotfile = "/home/pa/.upup_last_post"
episode_names = [ "telemachus", "nestor", "proteus",
                  "calypso", "hades", "aeolus",
                  "lestrygonians", "sylla_and_charybdis", "wandering_rocks",
                  "sirens", "cyclops", "naussicaa", "oxen_of_the_sun",
                  "circe", "eumaeus", "ithaca" ]
                  

def get_tree_for_episode(episode) :
    if episode not in episode_names :
        return "that is not an episode"
    
    r = requests.get(repo_base+"commits/master", headers=req_headers)
    print(r.status_code)
    commit=json.loads(r.text)  #most recent commit
    commit_sha = commit["sha"]
    r = requests.get(repo_base+'git/commits/{}'.format(commit_sha), headers=req_headers)
    print("got the commit")
    repo_dict=json.loads(r.text)
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

def get_episodes_from_tree(tree_sha) :
    r = requests.get(repo_base+'git/trees/{}'.format(tree_sha), headers=req_headers)
    print(r.status_code)
    
    episode_tree = json.loads( r.text)
    if (episode_tree["truncated"]) :
        frameinfo = getframeinfo(currentframe())
        print frameinfo.filename, frameinfo.lineno
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

#### Scriptus Beginnus ##############

with open(dotfile) as dotfile:
    line = dotfile.readline()
    (last_episode, upup) = line.split()
    print(last_episode, ',', upup)

    x = get_tree_for_episode(last_episode)
    upup_dict =  get_episodes_from_tree(x) # markdup file name is key, the sha is the value

    print("call get_next_from_d")
    next_upup = get_next_from_dict(upup_dict, upup )
    
    print("Prev was {}, next is {}".format(upup, next_upup))
    

#t = get_text_from_blob(upup_dict[upup])
#print(t)

    
