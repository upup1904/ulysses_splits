import requests
import json
import base64

try:

    r = requests.get('https://api.github.com/repos/upup1904/ulysses_splits/commits/master')
    print("Got first request {}", r.status_code)
    commit=json.loads(r.text)
    print("Loadedd commit dict")
    commit_sha = commit["sha"]
    print("commit sha is {}".format(commit_sha))
    r = requests.get('https://api.github.com/repos/upup1904/ulysses_splits/git/commits/{}'.format(commit_sha))
    print("got the commit")
    repo_dict=json.loads(r.text)
    print("made repo_dict")
    tree_sha=repo_dict["tree"]["sha"]
    print ("tree_sha is {}".format(tree_sha))
    r = requests.get('https://api.github.com/repos/upup1904/ulysses_splits/git/trees/{}?recursive=1'.format(tree_sha))
    print("tree request gets {}".format(r.status_code))
    tree_dict = json.loads(r.text)
    print("made tree_dict")
    # print(tree_dict)
    for item in tree_dict['tree'] :
        if item['type'] == 'blob' :
            print(item['path'])

except:
    print("It didn't work")
