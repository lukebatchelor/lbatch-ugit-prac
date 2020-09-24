# pylint: disable=relative-beyond-top-level
import os
import itertools
import operator
import string

from collections import namedtuple, deque

from . import data

def write_tree(directory='.'):
    entries = []
    with os.scandir(directory) as files:
        for entry in files:
            full_path = f'{directory}/{entry.name}'
            if is_ignored(full_path):
                continue
            if entry.is_file(follow_symlinks=False):
                type_='blob'
                with open(full_path, 'rb') as f:
                    oid = data.hash_object(f.read())
            elif entry.is_dir(follow_symlinks=False):
                type_='tree'
                oid=write_tree(full_path)
            entries.append((entry.name, oid, type_))
    tree = ''.join(f'{type_} {oid} {name}\n' for name, oid, type_ in sorted(entries))
    return data.hash_object(tree.encode(), type_='tree')

def _iter_tree_entries(oid):
    if not oid:
        return
    tree = data.get_object(oid, 'tree')
    for entry in tree.decode().splitlines():
        type_, oid, name = entry.split(' ', 2)
        yield type_, oid, name

def get_tree(oid, base_path=''):
    result = {}
    for type_, oid, name in _iter_tree_entries(oid):
        assert '/' not in name
        assert name not in ('..', '.')
        path = base_path + name
        if type_ == 'blob':
            result[path] = oid
        elif type_ == 'tree':
            result.update(get_tree(oid, f'{path}/'))
        else:
            assert False, f'Unknown tree entry {type_} {oid}'
    return result

def empty_current_directory():
    for root, _, filenames in os.walk(''):
        for filename in filenames:
            path = os.path.relpath(f'{root}/{filename}')
            if is_ignored(path) or os.path.isfile(path):
                continue
            os.remove(path)

def read_tree(tree_oid):
    empty_current_directory()
    tree = get_tree(tree_oid, base_path='./')
    for path, oid in tree.items():
        dir_name = os.path.dirname(path)
        os.makedirs(dir_name, exist_ok=True)
        with open(path, 'wb') as f:
            f.write(data.get_object(oid))

def commit(message):
    tree = write_tree()
    commit_str = f'tree {tree}\n'

    HEAD = data.get_ref('HEAD').value
    if HEAD:
        commit_str += f'parent {HEAD}\n'

    commit_str += '\n'
    commit_str += f'{message}\n'

    oid = data.hash_object(commit_str.encode(), type_='commit')

    data.update_ref('HEAD', data.RefValue(symbolic=False, value=oid))

    return oid

def checkout(name):
    oid = get_oid(name)
    commit = get_commit(oid)
    read_tree(commit.tree)
    
    if is_branch(name):
        HEAD = data.RefValue(symbolic=True, value=f'refs/heads/{name}')
    else:
        HEAD = data.RefValue(symbolic=False, value=oid)
    
    data.update_ref('HEAD', HEAD, deref=False)

def create_tag(tag_name, oid):
    data.update_ref(f'refs/tags/{tag_name}', data.RefValue(symbolic=False, value=oid))

def create_branch(branch_name, oid):
    data.update_ref(f'refs/heads/{branch_name}', data.RefValue(symbolic=False, value=oid))

def is_branch(branch_name):
    return data.get_ref(f'refs/heads/{branch_name}').value is not None

Commit = namedtuple('Commit', ['tree', 'parent', 'message'])

def get_commit(oid):
    parent = None

    commit_str = data.get_object(oid, 'commit').decode()
    lines = iter(commit_str.splitlines())
    for line in itertools.takewhile(operator.truth, lines):
        key, value = line.split(' ', 1)
        if key == 'tree':
            tree = value
        elif key == 'parent':
            parent = value
        else:
            assert False, f'Unknown field {key}'
    message = '\n'.join(lines)
    
    return Commit(tree = tree, parent = parent, message = message)

def iter_commits_and_parents(oids):
    oids = deque(oids)
    visted = set()

    while oids:
        oid = oids.popleft()
        if not oid or oid in visted:
            continue
        visted.add(oid)
        yield oid

        commit = get_commit(oid)
        oids.appendleft(commit.parent)

# given a name or oid, return the corresponding oid
def get_oid(name_or_oid):
    if name_or_oid == '@':
        name_or_oid = 'HEAD'

    refs_to_try = [
        f'{name_or_oid}',
        f'refs/{name_or_oid}',
        f'refs/tags/{name_or_oid}',
        f'refs/heads/{name_or_oid}'
    ]
    for ref in refs_to_try:
        if data.get_ref(ref).value:
            return data.get_ref(ref).value
    # check name is a SHA1 hash
    is_hash = all(c in string.hexdigits for c in name_or_oid)
    if len(name_or_oid) and is_hash:
        return name_or_oid

    assert False, f'Unknown name {name_or_oid}'

def is_ignored(path):
    return '.ugit' in path.split('/')