
from __future__ import print_function
import os
import sys
import ast
import json

import re
import string
import requests
import matplotlib.pyplot as plt
import threading
import Queue
import time
import requests_oauthlib
#import cartopy.crs as ccrs
from mpl_toolkits.basemap import Basemap
import matplotlib.pyplot as plt
from pylab import rcParams
import numpy as np
import multiprocessing

# Path for spark source folder
os.environ['SPARK_HOME']="/usr/local/Cellar/apache-spark/1.5.2/"
# Append the python dir to PYTHONPATH so that pyspark could be found
sys.path.append('/usr/local/Cellar/apache-spark/1.5.2/python/')
# Append the python/build to PYTHONPATH so that py4j could be found
sys.path.append('/usr/local/Cellar/apache-spark/1.5.2/python/lib/py4j-0.8.2.1-src.zip')
from pyspark import SparkContext
from pyspark import SQLContext,Row
from pyspark.streaming import StreamingContext
from pyspark.streaming.kafka import KafkaUtils
from pyspark.ml.feature import HashingTF,IDF, Tokenizer
from pyspark.mllib.linalg import Vectors
from pyspark.mllib.regression import LabeledPoint
from pyspark.mllib.clustering import StreamingKMeans
from pyspark.mllib.feature import StandardScaler
from pyspark.mllib.feature import Word2Vec
from pyspark.mllib.feature import Word2VecModel

access_token = ""
access_token_secret = ""
consumer_key = ""
consumer_secret =""
auth = requests_oauthlib.OAuth1(consumer_key, consumer_secret,access_token, access_token_secret)

BATCH_INTERVAL = 10  # How frequently to update (seconds)
clusterNum=15



def data_plotting(q):
    plt.ion() # Interactive mode
    llon = -130
    ulon = 100
    llat = -30
    ulat = 60
    rcParams['figure.figsize'] = (14,10)
    my_map = Basemap(projection='merc',
                resolution = 'l', area_thresh = 1000.0,
                llcrnrlon=llon, llcrnrlat=llat, #min longitude (llcrnrlon) and latitude (llcrnrlat)
                urcrnrlon=ulon, urcrnrlat=ulat) #max longitude (urcrnrlon) and latitude (urcrnrlat)

    my_map.drawcoastlines()
    my_map.drawcountries()
    my_map.drawmapboundary()
    my_map.fillcontinents(color = 'white', alpha = 0.3)
    my_map.shadedrelief()
    plt.pause(0.0001)
    plt.show()


    colors = plt.get_cmap('jet')(np.linspace(0.0, 1.0, clusterNum))

    while True:
        if q.empty():
            time.sleep(5)

        else:
            obj=q.get()
            d=[x[0][0] for x in obj]
            c=[x[1] for x in obj]
            data = np.array(d)
            pcolor=np.array(c)
            print(c)
            try:
                xs,ys = my_map(data[:, 0], data[:, 1])
                my_map.scatter(xs, ys,  marker='o', alpha = 0.5,color=colors[pcolor])
                plt.pause(0.0001)
                plt.draw()
                time.sleep(5)
            except IndexError: # Empty array
                pass




def get_coord2(post):
    coord = tuple()
    try:
        if post['coordinates'] == None:
            coord = post['place']['bounding_box']['coordinates']
            coord = reduce(lambda agg, nxt: [agg[0] + nxt[0], agg[1] + nxt[1]], coord[0])
            coord = tuple(map(lambda t: t / 4.0, coord))
        else:
            coord = tuple(post['coordinates']['coordinates'])
    except TypeError:
        #print ('error get_coord')
        coord=(0,0)
    return coord



def get_json(myjson):
  try:
    json_object = json.loads(myjson)
  except ValueError, e:
    return False
  return json_object


def doc2vec(document):
    doc_vec = np.zeros(100)
    tot_words = 0

    for word in document:
        try:
            vec = np.array(lookup_bd.value.get(word))
            if vec!= None:
                doc_vec +=  vec
                tot_words += 1
        except:
            continue

    #return(tot_words)
    return doc_vec / float(tot_words)

remove_spl_char_regex = re.compile('[%s]' % re.escape(string.punctuation)) # regex to remove special characters
stopwords=[u'i', u'me', u'my', u'myself', u'we', u'our', u'ours', u'ourselves', u'you', u'your', u'yours', u'yourself', u'yourselves', u'he', u'him', u'his', u'himself', u'she', u'her', u'hers', u'herself', u'it', u'its', u'itself', u'they', u'them', u'their', u'theirs', u'themselves', u'what', u'which', u'who', u'whom', u'this', u'that', u'these', u'those', u'am', u'is', u'are', u'was', u'were', u'be', u'been', u'being', u'have', u'has', u'had', u'having', u'do', u'does', u'did', u'doing', u'a', u'an', u'the', u'and', u'but', u'if', u'or', u'because', u'as', u'until', u'while', u'of', u'at', u'by', u'for', u'with', u'about', u'against', u'between', u'into', u'through', u'during', u'before', u'after', u'above', u'below', u'to', u'from', u'up', u'down', u'in', u'out', u'on', u'off', u'over', u'under', u'again', u'further', u'then', u'once', u'here', u'there', u'when', u'where', u'why', u'how', u'all', u'any', u'both', u'each', u'few', u'more', u'most', u'other', u'some', u'such', u'no', u'nor', u'not', u'only', u'own', u'same', u'so', u'than', u'too', u'very', u's', u't', u'can', u'will', u'just', u'don', u'should', u'now']
def tokenize(text):
    tokens = []
    text = text.encode('ascii', 'ignore') #to decode
    text=re.sub('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text) # to replace url with ''
    text = remove_spl_char_regex.sub(" ",text)  # Remove special characters
    text=text.lower()


    for word in text.split():
        if word not in stopwords \
            and word not in string.punctuation \
            and len(word)>1 \
            and word != '``':
                tokens.append(word)
    return tokens

from collections import Counter
def freqcount(terms_all):
    count_all = Counter()
    count_all.update(terms_all)
    return count_all.most_common(5)

if __name__ == '__main__':
    q = multiprocessing.Queue()
    job_for_another_core2 = multiprocessing.Process(target=data_plotting,args=(q,))
    job_for_another_core2.start()
    # Set up spark objects and run
    #sc  = SparkContext('local[*]', 'Social Panic Analysis')
    sc  = SparkContext('local[*]', 'Twitter Analysis')

    sqlContext=SQLContext(sc)
    lookup = sqlContext.read.parquet("word2vecModel/data").alias("lookup")
    lookup.printSchema()
    lookup_bd = sc.broadcast(lookup.rdd.collectAsMap())

    ssc = StreamingContext(sc, BATCH_INTERVAL)
    #ssc.checkpoint("checkpoint")

    # Create a DStream that will connect to hostname:port, like localhost:9999
    dstream = ssc.socketTextStream("localhost", 9999)
    #dstream_tweets.count().pprint()
    #
    dstream_tweets=dstream.map(lambda post: get_json(post))\
         .filter(lambda post: post != False)\
         .filter(lambda post: 'created_at' in post)\
         .map(lambda post: (get_coord2(post)[0],get_coord2(post)[1],post["text"]))\
         .filter(lambda tpl: tpl[0] != 0)\
         .filter(lambda tpl: tpl[2] != '')\
         .map(lambda tpl: (tpl[0],tpl[1],tokenize(tpl[2])))\
         .map(lambda tpl:(tpl[0],tpl[1],tpl[2],doc2vec(tpl[2])))
    #dstream_tweets.pprint()



    trainingData=dstream_tweets.map(lambda tpl: [tpl[0],tpl[1]]+tpl[3].tolist())
    #trainingData.pprint()
    testdata=dstream_tweets.map(lambda tpl: (([tpl[0],tpl[1]],tpl[2]),[tpl[0],tpl[1]]+tpl[3].tolist()))
    #testdata.pprint()
    #
    model = StreamingKMeans(k=clusterNum, decayFactor=0.6).setRandomCenters(102, 1.0, 3)
    model.trainOn(trainingData)
    clust=model.predictOnValues(testdata)
    #clust.pprint()
    #words = lines.flatMap(lambda line: line.split(" "))
    topic=clust.map(lambda x: (x[1],x[0][1]))
    #topic.pprint()
    topicAgg = topic.reduceByKey(lambda x,y: x+y)
    #wordCollect.pprint()
    topicAgg.map(lambda x: (x[0],freqcount(x[1]))).pprint()

    clust.foreachRDD(lambda time, rdd: q.put(rdd.collect()))

    # Run!
    ssc.start()
    ssc.awaitTermination()
