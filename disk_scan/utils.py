'''
    Utils dealing with <Path>
    These functions are stateless

    name:
        The final path component, excluding the drive and root, if any.
        eg. setup.py
    stem:
        The final path component, without its suffix
        eg. setup
    suffix:
        The file extension of the final component, if any.
        eg. .py or ''
'''

from typing import Iterable, Set, Dict, List, Callable, Tuple, Union
from pathlib import Path
import hashlib
import os
import re
import multiprocessing
from multiprocessing import Pool
from .common import MAC_FORBIDDEN, LINUX_FORBIDDEN, WINDOWS_FORBIDDEN

# MD5 hash, we pick up head, tail, and total size of file
MD5_HEAD_SIZE = 10 * 1024 * 1024
MD5_TAIL_SIZE = 10 * 1024 * 1024
MD5_FILE_SIZE = MD5_HEAD_SIZE + MD5_TAIL_SIZE

def pretty_line(content:str, max:int=79):
    ''' Given a line truncate or fill it until 79 characters '''
    if len(content) <= max:
        suffix = (max - len(content)) * '.'
        return content + suffix
    else:
        return content[:max]


def max_process_count(MIN:int=2):
    ''' Decide the max number of processes on this machine '''
    try:
        x = multiprocessing.cpu_count()
        return max([int(x) - 1, MIN])
    except:
        return MIN


def is_mac_os_file(p: Path) -> bool:
    ''' Judge if a file is mac os hidden file '''
    if str(p.stem).startswith('._'): # Mac OS shadow files.
        return True
        
    if str(p.stem) == ".DS_Store": # Mac OS system files.
        return True
        
    return False


def pretty_str(p: Path, only_path=True) -> str:
    ''' Pretty string of the path '''
    buffer = [p]
    if not only_path:
        buffer.append(p.stat().st_size)
        buffer.append(p.suffix)
        buffer.append(p.stem)
        buffer.append(p.name)

    return '\n'.join(buffer)


def remove_file(p: Path, dry_run=True) -> None:
    ''' Remove a file, if file not found, won't fail '''
    if p.is_dir():
        raise Exception(f'{p} is not a file')

    if dry_run:
        print(f'Dry run remove: {p}')
    else:
        try:
            p.unlink()
        except FileNotFoundError:
            pass


def remove_dir(p: Path, recursive=False, dry_run=True) -> None:
    '''
    Remove a directory.

    Note: If not recursive, and the directory isn't empty, will raise error.
    '''
    if not p.is_dir():
        raise Exception(f'{p} is not a directory')

    if ( not is_empty_dir(p) ) and ( not recursive ):
        raise Exception(f"{p} not empty, use recurisve=True to force remove.")
    
    # First, remove any content inside it.
    for x in p.iterdir():
        if x.is_dir():
            remove_dir(x, recursive, dry_run)
        else:
            remove_file(x, dry_run)

    # Then, remove the dir.
    if is_empty_dir(p):
        if dry_run:
            print(f'Remove: {p}')
        else:
            try:
                p.rmdir()
            except FileNotFoundError:
                pass


def is_empty_dir(p: Path) -> bool:
    ''' Test if directory is empty '''
    if not p.is_dir():
        raise Exception(f'{p} is not a directory')

    return not any(p.iterdir())


def is_almost_empty_dir(p: Path) -> bool:
    '''
    If directory only contains os hidden files, then it is almost empty.
    '''
    if not p.is_dir():
        raise Exception(f'{p} is not a directory')
    
    if is_empty_dir(p):
        return True
    
    input = {x for x in p.iterdir()}
    output = exclude_os_files(input)

    return not (len(output) != 0)


def exclude_os_files(nodes: Set[Path]) -> Set[Path]:
    ''' Filter out mac os files from the set '''
    return {x for x in nodes if not is_mac_os_file(x)}


def filter_by_size(nodes: Set[Path], more_than:int=None, less_than:int=None) -> Set[Path]:
    ''' Filter nodes with size requirement
         
        more_than/less_than: how many bytes
    '''
    if more_than == None and less_than == None:
        raise Exception("Need one of: more_than/less_than")

    if more_than != None and less_than == None:
        return {x for x in nodes if x.stat().st_size > more_than}
    
    if more_than == None and less_than != None:
        return {x for x in nodes if x.stat().st_size < less_than}
    
    if more_than != None and less_than != None:
        if more_than >= less_than:
            raise Exception("more_than shall < less_than if both specified.")

        return {x for x in nodes if (x.stat().st_size < less_than) and (x.stat().st_size > more_than)}


def filter_by_suffixes(nodes: Set[Path], include: List[str]=None, exclude: List[str]=None) -> Set[Path]:
    ''' Filter nodes, include some, exclude some.
    
    Note: '.mp4' and '.MP4' are treated equally as '.mp4'
    '''
    if include == None and exclude == None:
        raise Exception("Need one of: include / exclude")
    
    if include != None and exclude != None:
        raise Exception("Can only fill in one of: include / exclude")

    if include:
        _include = [x.lower() for x in include]
        return {x for x in nodes if (not x.is_dir() and (x.suffix.lower() in _include))}

    if exclude:
        _exclude = [x.lower() for x in exclude]
        return {x for x in nodes if (not x.is_dir() and (x.suffix.lower() not in _exclude))}


def filter_by_name(nodes: Set[Path], include: List[str]=None, exclude: List[str]=None) -> Set[Path]:
    ''' Filter nodes, include some with partial name matching, case insensitive '''
    _include = []
    if include:
        _include = [str(x).lower() for x in include]
    
    _exclude = []
    if exclude:
        _exclude = [str(x).lower() for x in exclude]
    
    output = set()
    for x in nodes:
        should_add = False
        _x = str(x.name).lower()
        for each in _include:
            if each in _x:
                should_add = True
                break
        
        for each in _exclude:
            if each in _x:
                should_add = False
                break
        if should_add:
            output.add(x)
    
    return output


def count_suffixes(nodes: Set[Path]) -> Dict:
    '''
    Go through the nodes, count the suffixes and their frequencies.

    Note: '.mp4' and '.MP4' are treated equally.

    Args:
        nodes (Set[Path]): A set of paths.

    Returns:
        Dict: {'.mp4': 345, '.avi': 456, ...}
    '''
    output = {}
    for x in nodes:
        if x.is_dir():
            continue
        current = str(x.suffix).lower()
        if current in output:
            output[current] += 1
        else:
            output[current] = 1
    
    return output


def _scan_dir(current: Path) -> Tuple[List[Path], List[Path]]:
    ''' Scan the dir, get immediate children. Classify as list of files and list of dirs '''
    files_list = []
    dirs_list = []
    
    # If encounter "permission" error (can't list the dir),
    # jump over it.
    try:
        for x in current.iterdir():
            if x.is_file():
                files_list.append(x)
            elif x.is_dir():
                dirs_list.append(x)
            else:
                pass
    except:
        pass

    return files_list, dirs_list


def scan_2(root: Path, call_back: Callable):
    ''' Multi-thread version of scan() '''

    unresolved_dirs = []
    unresolved_dirs.append(root.resolve())

    resolved_files = []
    resolved_dirs = []

    total_sum = 0
    n_of_cores = max_process_count()
    with Pool(n_of_cores) as pool:
        while len(unresolved_dirs) > 0:
            # Read in unresolved dirs to prepare args
            args = [(p) for p in unresolved_dirs]
            # Mark above dirs as "resolved"
            for p in unresolved_dirs:
                resolved_dirs.append(p)
            # Clean up unresolved dirs
            unresolved_dirs.clear()
            # Do the multi-thread magic
            results = pool.map(_scan_dir, args)
            # Feed the scan result back
            for result in results:
                new_files, new_dirs = result
                for item in new_files:
                    resolved_files.append(item)
                for item in new_dirs:
                    unresolved_dirs.append(item)
            
            total_sum = len(resolved_files) + len(resolved_dirs)
            yield total_sum

    all_nodes = set()
    for i in resolved_dirs:
        all_nodes.add(i)
    for i in resolved_files:
        all_nodes.add(i)
    
    call_back(all_nodes)


def scan(root: Path, call_back: Callable):
    '''
    Scan from root, get all dirs and files.

    When finished, call the 'call_back' with a set of paths.
    When processing, yeild total number (int) of scanned files.

    Args:
        root (Path): from path start to scan
        call_back (Callable): Accepts (Set[Path]) as only argument.

    Raises:
        Exception: If scanning path is not file nor dir.
    '''
    total_sum = 0
    all_nodes = set()
    unresolved = []
    unresolved.append(root.resolve())

    while len(unresolved):
        total_sum += 1
        # Yield progress, if hits every 100
        if total_sum % 100 == 0:
            yield total_sum

        current = unresolved.pop(0)
        # File? Mark it.
        if current.is_file():
            all_nodes.add(current)
            continue
        
        # Directory? Go deeper.
        if current.is_dir():
            all_nodes.add(current)
            # If encounter "permission" error (can't list),
            # jump over it.
            try:
                for x in current.iterdir():
                    unresolved.append(x)
            except:
                pass
            continue

        # raise Exception(f"{current} is not file, nor dir")
    
    yield total_sum
    
    call_back(all_nodes)


def sort_nodes(nodes: Iterable[Path]) -> Iterable[Path]:
    ''' Sort a list of nodes.
    
    Shorter path: comes first.
    Shorter stem: comes first.

    Keep original if above rules doesn't apply.
    '''
    l = [len(str(node)) for node in nodes]
    if not (min(l) == max(l)):
        return sorted(nodes, key=lambda node: len(str(node)))  # path short first.
    
    s = [len(str(node.stem)) for node in nodes]
    if not (min(s) == max(s)):
        return sorted(nodes, key=lambda node: len(str(node.stem)))  # stem short first.

    return nodes


def has_str(p: Path, old: str) -> bool:
    ''' Path has string? '''
    x = str(p)
    return old in x


def stem_has_str(p: Path, old: str) -> bool:
    return old in p.stem


def name_has_str(p: Path, old: str) -> bool:
    ''' path.name contains the string '''
    return old in p.name


def name_matches_str(p: Path, regex_: str) -> bool:
    ''' If path.name matches the regular expression '''
    pattern = re.compile(regex_)
    if pattern.match(p.name):
        return True
    else:
        return False


def rename_str(p: Path, old: str, new: str, dry_run=True) -> Tuple[str, str]:
    '''
    Replace part of the name of the path.

    Return:
        Tuple(old, new)
    '''
    x = str(p)
    if old in x:
        y = x.replace(old, new)
        b = Path(y)
        if not dry_run:
            p = p.rename(b)
        return (x, y)
    return (None, None)


def rename_stem(p: Path, old: str, new: str, dry_run=True) -> Tuple[str, str]:
    ''' Change the path.stem, replace old with new.
        return (old_path, new_path)
    '''
    if not stem_has_str(p, old):
        return None, None
    
    x = str(p)
    newStem = p.stem.replace(old, new)
    newPath = p.with_name(newStem.rstrip('/') + p.suffix.lstrip('/'))
    y = str(newPath)
    if not dry_run:
        p.rename(newPath)
    
    return x, y


def rename_name(p: Path, old: str, new: str, dry_run=True) -> Tuple[str, str]:
    ''' Change the path.name, replace old with new '''
    if not name_has_str(p, old):
        return None, None
    x = str(p)
    newName = p.name.replace(old, new)
    newPath = p.with_name(newName.strip('/'))
    y = str(newPath)
    if not dry_run:
        p.rename(newPath)
    return x, y


def filter_dir(nodes: Set[Path]):
    ''' Filter nodes, return only directories '''
    return {x for x in nodes if x.is_dir()}


def filter_file(nodes: Set[Path]):
    ''' Filter nodes, return only files '''
    return {x for x in nodes if x.is_file()}


def read_file_size(node: Path, _ignore_stem:List[str]=None, _ignore_suffix:List[str]=None) -> Union[int, None]:
    ''' Return the file size in bytes unit, or None, if included in stem or suffix '''
    skip_me = False
    if node.is_dir():
        skip_me = True
    if _ignore_stem and node.stem.lower() in _ignore_stem:
        skip_me = True
    if _ignore_suffix and node.suffix.lower() in _ignore_suffix:
        skip_me = True

    if skip_me:
        return None
    else:
        how_big = node.stat().st_size # size of file in bytes
        return how_big


def calc_file_md5(node: Path, secure=False) -> bytes:
    ''' Calculate the MD5 of file, if secure, read all file, if not, use head and tail section '''
    b = None
    if secure:
        b = node.read_bytes()
    else:
        with open(node, 'rb') as f:
            if node.stat().st_size > MD5_FILE_SIZE:
                # Read head section
                b = f.read(MD5_HEAD_SIZE)
                # Jump to end, read tail section
                f.seek((-1) * MD5_TAIL_SIZE, os.SEEK_END)
                b += f.read()
            else:
                b = node.read_bytes()
    
    # Calculate the md5 hash value: k
    m = hashlib.md5()
    m.update(b)
    k = m.digest()

    return k


def find_duplicates(nodes: Set[Path], call_back: Callable, ignore_stem: List[str]=None, ignore_suffix: List[str]=None, secure=False):
    '''
    Given a dict of nodes, find duplicated files within it.
    Using MD5 hashing to determine if file are the same.

    During the process, it will yield current reading path.

    Args:
        call_back (Callable): Accepts (dict) as only argument.
        secure (bool): If secure, then md5 scan the whole file, otherwise scan first and last 30MB of the file.

    The call_back shall accept the only argument:
    {
        b'md5_hash': [Path, Path, ...],
        ...
    }
    '''
    _ignore_stem = None 
    if ignore_stem:
        _ignore_stem = [str(x).lower() for x in ignore_stem]
    
    _ignore_suffix = None
    if ignore_suffix:
        _ignore_suffix = [str(x).lower() for x in ignore_suffix]

    # Firstly, create a big map of file size and file paths
    # key: size
    # value: [] of paths 
    big = {}
    for node in nodes:
        how_big = read_file_size(node, _ignore_stem, _ignore_suffix)
        
        if how_big == None:
            continue

        if big.get(how_big) == None:
            big[how_big] = [node]
        else:
            big[how_big].append(node)
    
    # Secondly, filter the big map, keep only entries with size duplicates (wait for MD5 hash).
    filtered_big = {key:value for key, value in big.items() if len(value) > 1}
    
    # Thirdly, create a new map.
    # key: md5_hash
    # valu: [] of paths
    md5_big = {}
    for _size, _paths in filtered_big.items():
        # Single thread approach
        for node in _paths:
            yield f'r{node}'
            k = calc_file_md5(node, secure)
            # Fill in the big table of md5_big
            if md5_big.get(k) == None:
                md5_big[k] = [node]
            else:
                md5_big[k].append(node)
    
    # Lastly, now we have a exact duplicate table,
    # We trun only that md5 is duplicated.
    r_md5_big = {key: value for key, value in md5_big.items() if len(value) > 1}

    call_back(r_md5_big)


def find_duplicates_2(nodes: Set[Path], call_back: Callable, ignore_stem: List[str]=None, ignore_suffix: List[str]=None, secure=False):
    '''
        Given a dict of nodes, find duplicated files within it.
        Using MD5 hashing to determine if file are the same.

        During the process, it will yield current reading path.

        Args:
            call_back (Callable): Accepts (dict) as only argument.
            secure (bool): If secure, then md5 scan the whole file, otherwise scan first and last 30MB of the file.

        The call_back shall accept the only argument:
        {
            b'md5_hash': [Path, Path, ...],
            ...
        }
    '''
    _ignore_stem = None 
    if ignore_stem:
        _ignore_stem = [str(x).lower() for x in ignore_stem]
    
    _ignore_suffix = None
    if ignore_suffix:
        _ignore_suffix = [str(x).lower() for x in ignore_suffix]

    # Firstly, create a big map of file size and file paths
    # key: size
    # value: [] of paths 
    big = {}
    n_of_cores = max_process_count()
    with Pool(n_of_cores) as pool:
        args = [(node, _ignore_stem, _ignore_suffix) for node in nodes]
        node_sizes = pool.starmap(read_file_size, args)
        for _node, _size in zip(nodes, node_sizes):
            if _size == None: # Skip the nodes with None as size
                continue
            if big.get(_size) == None:
                big[_size] = [_node]
            else:
                big[_size].append(_node)
    
    # Secondly, filter the big map, keep only entries with size duplicates (wait for MD5 hash).
    filtered_big = {key:value for key, value in big.items() if len(value) > 1}
    
    # Thirdly, create a new map.
    # key: md5_hash
    # value: [] of paths
    md5_big = {}
    n_of_cores = max_process_count()
    with Pool(n_of_cores) as pool:
        bag_counter = 100
        for _size, _paths in filtered_big.items():
            # Multi thread approach
            # Yield progress every 100 count
            if bag_counter > 0:
                bag_counter -= 1
            else:
                yield f'bytes {_size}'
                bag_counter = 100
            
            args = [(x, secure) for x in _paths]
            k_list = pool.starmap(calc_file_md5, args)

            for _node, _k in zip(_paths, k_list):
                if md5_big.get(_k) == None:
                    md5_big[_k] = [_node]
                else:
                    md5_big[_k].append(_node)
    
    # Lastly, now we have a exact duplicate table,
    # We turn only that md5 is duplicated.
    r_md5_big = {key: value for key, value in md5_big.items() if len(value) > 1}

    call_back(r_md5_big)


def get_random_string(size: int = 7) -> str:
    '''
    Random string, up to size (how many bytes)

    Parameters
    ----------
    size : int
        how many bytes of random

    Returns
    -------
    str
        a hex string of generated random number (no 0x prefix)
    '''
    a = os.urandom(size)
    return a.hex()


def get_full_parent(p: Path) -> str:
    '''
    Return the full path of parent of this file or folder.

    Parameters
    ----------
    p : Path
        The path in question

    Returns
    -------
    str
        the full path  or ''
    '''
    try:
        return str(os.path.dirname(p))
    except:
        return ''


def get_parent(p: Path) -> str:
    '''
    Return the immediate parent of this file.

    Parameters
    ----------
    p : Path
        Path in question

    Returns
    -------
    str
        the parent folder name or ''
    '''
    parent = os.path.dirname(p)
    parts = Path(parent).parts
    try:
        return parts[-1]
    except:
        return ''


def filter_safe_os_name(s: str) -> str:
    ''' Remove unsafe characters in string'''
    bag = []
    for c in s:
        if c in MAC_FORBIDDEN or c in LINUX_FORBIDDEN or c in WINDOWS_FORBIDDEN:
            continue
        else:
            bag.append(c)
    return ''.join(bag)


def atoi(text: str):
    ''' Return int of text is int, else return text itself '''
    return int(text) if text.isdigit() else text


def natural_keys(text: str):
    ''' Given a string, return a list as keys.
        All the numbers will be turned to int.
        Text remains
    '''
    return [atoi(c) for c in re.split(r'(\d+)', text)]


def sort_stem_naturally(paths: List[Path]) -> List[Path]:
    ''' Return the paths with natural sorting by stem name '''
    stems = [x.stem for x in paths]
    aparted_stems = [natural_keys(x) for x in stems]
    to_be_sorted = list(zip(aparted_stems, paths))
    sorted_list = sorted(to_be_sorted, key=lambda x: x[0])
    return [x[1] for x in sorted_list]