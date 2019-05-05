#!/usr/bin/python3

# split an org-formated file to indidual files
# filename might bee like cyclops_splits.org for a whole chapter
# expect [UPUP #xx] as chunk delimeters, and form name from xx

import sys
import re

CHUNK_RE=re.compile('\[UPUP[^0-9]+(?P<chunkno>[0-9]+)')
line=0
x=0
orgfile = sys.argv[1]
capturefile = ""
outfile=None
with open(orgfile) as f :
    for line in f.readlines() :
        m = CHUNK_RE.search(line)
        if m :
            capturefile = "./UPUP_{}.md".format( m.group('chunkno'))
            outfile=open(capturefile, "w")
        else:
            if outfile is not None :
                outfile.write(line)


