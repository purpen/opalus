# -*- coding:utf-8 -*-

import time
import base64
# 加密
import hashlib
from bson import ObjectId

def isset(v): 
   try : 
     type (eval(v)) 
   except : 
     return  False
   else : 
     return  True

def force_int(value, default=0):
    try:
        return int(value)
    except:
        return default

def force_float_2(value, default=0):
    try:
        value = float(value)
        return float("%.2f" % value)
    except:
        return default

# md5
def gen_md5(str):
    m = hashlib.md5()
    m.update(str.encode('utf8'))
    return m.hexdigest()

# sha1
def gen_sha1(str):
    m = hashlib.sha1()
    m.update(str.encode('utf8'))
    return m.hexdigest()

# 返回指定key对应值
def filter_key(keys, row):
    data = {}
    for f in keys:
        if f in row:
            data[f] = row[f]

    return data

# 随机生成BsonId
def gen_mongo_id():
    return ObjectId().__str__()
