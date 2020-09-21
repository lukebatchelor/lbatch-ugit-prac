import hashlib
import os

GIT_DIR='.ugit'

def init():
    # use makedirs instead of mkdir to create if it doesn't exist
    os.makedirs(GIT_DIR)
    os.makedirs(f'{GIT_DIR}/objects')

def hash_object(data):
    oid = hashlib.sha1(data).hexdigest()
    # 'wb' is write binary mode
    with open(f'{GIT_DIR}/objects/{oid}', 'wb') as out:
        out.write(data)
    
    return oid

def get_object(oid):
    with open(f'{GIT_DIR}/objects/{oid}', 'rb') as f:
        return f.read()