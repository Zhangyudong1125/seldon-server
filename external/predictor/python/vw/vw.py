import random, math
import operator
from collections import defaultdict
from socket import *
import threading, Queue, subprocess

def sigmoid(x):
    return 1 / (1 + math.exp(-x))
  
def normalize( predictions ):
    s = sum( predictions )
    normalized = []
    for p in predictions:
        normalized.append( p / s )
    return normalized  

def tail_forever(fn):
    p = subprocess.Popen(["tail", "-f", fn], stdout=subprocess.PIPE)
    while 1:
        line = p.stdout.readline()
        tailq.put(line)
        if not line:
            break

def init(config):
    print "initialised"
    global tailq
    tailq = Queue.Queue(maxsize=1000) 
    vw_config = config['VW']
    # we tail the raw prediction file to get the full scores from daemon sevrer
    threading.Thread(target=tail_forever, args=(vw_config['raw_predictions'],)).start()

# simple vw precition string create
# ASSUMES ALL FEATURES HAVE NUMERIC VALUES
# this function could be extended in many ways to allow arbitrary json->vw translation to handle non numeric features and namespaces
def getVWFeatures(data,tag):
    line = "1 "+tag+"|f "
    for k in data.keys():
        line = line + k + ":" + str(data[k]) + " "
    line = line + "\n"
    return line

# Search for tag in raw_predictions file to match with out request to the vw daemon
def get_full_scores(tag):
    found = False
    l = 1
    while not found:
        l = l + 1
        if l > 1000:
            print "failed to find tag after ",l,"lines"
            return []
        rawLine = tailq.get()
        parts = rawLine.split(' ')
        tagScores = parts[len(parts)-1].rstrip() 
        if  tagScores == tag:
            found = True
            scores = []
            for score in parts:
                if score.rstrip() == tag:
                    nscores = normalize(scores)
                    fscores = []
                    c = 1
                    for nscore in nscores:
                        fscores.append((nscore,c,1.0))
                        c = c + 1
                    return fscores
                else:
                    (classId,score) = score.split(':')
                    scores.append(sigmoid(float(score)))


def score(json):
    tag = "tag"+str(random.randrange(0,9999999))
    vwRequest = getVWFeatures(json,tag)
    scores = {}

    s = socket(AF_INET, SOCK_STREAM)    # create a TCP socket
    s.connect(("localhost", 26542)) # connect to server on the port
    s.send(vwRequest)               # send the data
    data = s.recv(1028) # receive up to 1K bytes
    return get_full_scores(tag)
    

# ignores client in this example. One could direct to multiple daemons holding different models 1 for each client.
def get_predictions(client,json):
    return score(json)



