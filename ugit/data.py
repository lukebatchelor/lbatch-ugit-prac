import hashlib
import os

GIT_DIR='.ugit'

def init():
    # use makedirs instead of mkdir to create if it doesn't exist
    os.makedirs(GIT_DIR)
    os.makedirs(f'{GIT_DIR}/objects')

def set_HEAD(oid):
    with open(f'{GIT_DIR}/HEAD', 'w') as f:
        f.write(oid)
    
def get_HEAD():
    if os.path.isfile(f'{GIT_DIR}/HEAD'):
        with open(f'{GIT_DIR}/HEAD', 'r') as f:
            return f.read().strip()

def hash_object(data, type_='blob'):
    obj = type_.encode() + b'\x00' + data
    oid = hashlib.sha1(obj).hexdigest()
    # 'wb' is write binary mode
    with open(f'{GIT_DIR}/objects/{oid}', 'wb') as out:
        out.write(obj)
    
    return oid

def get_object(oid, expected_type='blob'):
    with open(f'{GIT_DIR}/objects/{oid}', 'rb') as f:
        obj =  f.read()
    first_null = obj.index(b'\x00')
    type_ = obj[:first_null].decode()
    content = obj[first_null + 1:]

    if expected_type is not None:
        assert type_ == expected_type, f'expected object to be type {expected_type}, got {type_}'
    return content