import hashlib
import os

from collections import namedtuple

GIT_DIR='.ugit'

def init():
    # use makedirs instead of mkdir to create if it doesn't exist
    os.makedirs(GIT_DIR)
    os.makedirs(f'{GIT_DIR}/objects')

RefValue = namedtuple('RefValue', ['symbolic', 'value'])

def update_ref(ref_name, value, deref=True):
    # dereference ref if required
    ref_name = _get_ref_internal(ref_name, deref)[0]

    # check if writing a symbolic value
    assert value.value
    if value.symbolic:
        value = f'ref: {value.value}'
    else:
        value = value.value

    ref_path = f'{GIT_DIR}/{ref_name}'
    os.makedirs(os.path.dirname(ref_path), exist_ok=True)
    with open(ref_path, 'w') as f:
        f.write(value)

def get_ref(ref_name, deref=True):
    return _get_ref_internal(ref_name, deref)[1]

# recursively de-reference ref until we reach a non-symbolic ref
def _get_ref_internal(ref_name, deref=True):
    ref_path = f'{GIT_DIR}/{ref_name}'
    value = None
    if os.path.isfile(ref_path):
        with open(ref_path) as f:
            value = f.read().strip()
    symbolic = bool(value) and value.startswith('ref:')
    if symbolic:
        value = value.split(':', 1)[1].strip()
        if deref:
            return _get_ref_internal(value, deref=True)

    return ref_name, RefValue(symbolic=symbolic, value=value)

def iter_refs(deref=True):
    refs = ['HEAD']

    for root, _, filenames in os.walk(f'{GIT_DIR}/refs'):
        root = os.path.relpath(root, GIT_DIR)
        refs.extend(f'{root}/{name}' for name in filenames)

    for ref_name in refs:
        yield ref_name, get_ref(ref_name, deref=deref)

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