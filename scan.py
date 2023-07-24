#!/usr/bin/env python3
''' Command line interface to disk scan '''
from typing import Set
from pathlib import Path
from disk_scan import (utils, common)
import click
import json


class Cache:
    def __init__(self):
        self.a = None
    
    def get(self):
        return self.a

    def populate(self, a):
        self.a = a


def progress(p: Path, show_progress=True) -> Cache:
    cache = Cache()
    for counter in utils.scan_2(p, cache.populate):
        if show_progress:
            print(f'\rScan: {str(p)} {counter}', end='')
    print()
    return cache


def d_progress(nodes: Set[Path], show_progress=True) -> Cache:
    cache = Cache()
    for current in utils.find_duplicates_2(nodes, cache.populate):
        if show_progress:
            show = utils.pretty_line(str(current))
            print(f'\rReading: {show}', end='')
    print('')
    return cache


@click.group()
def cli():
    pass


@click.command()
@click.argument('dir', type=click.Path(exists=True, dir_okay=True, resolve_path=True), required=True)
@click.option('--json', 'json_', type=str, default=None, help='File name to save the result in json')
@click.option('--include-sys', is_flag=True, default=False, help='Include system files in scan.')
def duplicate(dir, json_, include_sys):
    '''
    Find duplicated files.
    '''
    p = Path(str(dir))
    cache = progress(p)
    nodes = cache.get()
    if not include_sys:
        nodes = utils.exclude_os_files(nodes)

    cache = d_progress(nodes)
    result = cache.get()

    if not json_:
        for md5_hash, paths in result.items():
            click.echo(md5_hash.hex())
            for x in paths:
                click.echo(str(x))
            click.echo('-' * 32)
    else:
        with open(json_, 'w', encoding='utf8') as f:
            r = {md5_hash.hex(): [str(x) for x in paths] for md5_hash, paths in result.items()}
            json.dump(r, f, indent=2, ensure_ascii=False)


@click.command()
@click.argument('dir', type=click.Path(exists=True, dir_okay=True, resolve_path=True), required=True)
@click.option('-s', '--size', type=int, required=True, prompt="Bigger than () MB?", help='Filter bigger than ? MB.')
@click.option('--json', 'json_', type=str, default=None, help='File name to save the result in json')
def bigfiles(dir, size, json_):
    '''
    Find big files.
    '''
    click.echo(f'> {size} mb.')
    p = Path(str(dir))
    cache = progress(p)
    nodes = cache.get()

    result = utils.filter_by_size(nodes, more_than=size * (1024 * 1024))
    temp = sorted(list(result))
    if not json_:
        for each in temp:
            click.echo(each)
    else:
        with open(json_, 'w', encoding='utf8') as f:
            r = {'paths': [str(x) for x in temp]}
            json.dump(r, f, indent=2, ensure_ascii=False)


@click.command()
@click.argument('dir', type=click.Path(exists=True, dir_okay=True, resolve_path=True), required=True)
@click.option('-s', '--suffix', multiple=True, default=[], required=True, help="eg. mp4, png, jpg")
@click.option('--json', 'json_', type=str, default=None, help='File name to save the result in json')
@click.option('--include-sys', is_flag=True, default=False, help='Include system files in scan.')
def bysuffix(dir, suffix, json_, include_sys):
    '''
    Filter out files with suffixes.
    
    You can supply multiple suffixes with multiple '-s' switch.
    '''
    _suffixes = ['.'+str(x).lower() for x in suffix if len(x.strip()) > 0]
    if len(_suffixes) == 0:
        click.echo('The suffixes provided cannot be white spaces!')
        return

    p = Path(str(dir))
    cache = progress(p)
    nodes = cache.get()
    if not include_sys:
        nodes = utils.exclude_os_files(nodes)

    result = utils.filter_by_suffixes(nodes, _suffixes)
    temp = sorted(list(result), key=lambda p: len(str(p.parent)))
    if not json_:
        for each in temp:
            click.echo(each)
    else:
        with open(json_, 'w', encoding='utf8') as f:
            r = {'paths': [str(x) for x in temp]}
            json.dump(r, f, indent=2, ensure_ascii=False)


@click.command()
@click.argument('dir', type=click.Path(exists=True, dir_okay=True, resolve_path=True), required=True)
@click.option('--force', is_flag=True, help='Perform real actions. (NOT dry run)')
@click.option('--old', 'old_', required=True, type=str, default=None, help='Old name')
@click.option('--new', 'new_', required=True, type=str, default=None, help='New name')
@click.option('--json', 'json_', type=str, default=None, help='File name to save the result in json')
def renamedirs(dir, force, old_, new_, json_):
    '''
    Replace old string in dir name with new.

    Note: This is recursive.
    '''
    p = Path(str(dir))
    cache = progress(p)
    nodes = cache.get()

    # Get dirs
    dirs = utils.filter_dir(nodes)
    # Get wanted dirs
    dirs = {x for x in dirs if utils.name_has_str(x, old_)}

    dirs = sorted(dirs, key=lambda dir: len(str(dir)), reverse=True)

    if not json_:
        click.echo('-' * 32)
        for each in dirs:
            oldName, newName = utils.rename_name(each, old_, new_, True)
            click.echo(f'old: {oldName}')
            click.echo(f'new: {newName}')
            click.echo('-' * 16)
    else:
        with open(json_, 'w', encoding='utf8') as f:
            r = {'paths': []}
            for each in dirs:
                oldName, newName = utils.rename_name(each, old_, new_, True)
                r['paths'].append({
                    'old': str(oldName),
                    'new': str(newName)
                })
            json.dump(r, f, indent=2, ensure_ascii=False)
    
    if force:
        for each in dirs:
            utils.rename_name(each, old_, new_, False)
    else:
        click.echo("Warning: This is a dry run, use --force to perform actual rename action.")

@click.command()
@click.argument('dir', type=click.Path(exists=True, dir_okay=True, resolve_path=True), required=True)
@click.option('--force', is_flag=True, default=False, help='Perform real actions. (NOT dry run)')
@click.option('--regex', 'regex_', required=False, type=str, default=None, help='Regex to match the source file names')
@click.option('--only-media', 'only_media', is_flag=True, show_default=True, default=False, help='Filter only common media files')
@click.option('--separator', 'separator_', required=False, type=str, default='_', show_default=True, help='Separator for final file name')
@click.option('--prefix', 'prefix_', required=False, type=str, default='', help='Prefix for final file name')
@click.option('--keep', 'keep_folder_name', is_flag=True, show_default=True, default=False, help='Keep folder name as part of file name')
@click.option('--json', 'json_', type=str, default=None, help='Save the operation result in a json file')
def normalize(dir, force, regex_, only_media, prefix_, separator_:str, keep_folder_name, json_):
    ''' Normalize file names under a directory.
        1) Recursive (automatic goes into sub folders)
        2) Match files. User needs to either use regex to match file names or turn on only_media flag.
        3) (Optional) User can have a prefix prepended to each file.
        4) (Optional) User can keep folder name prepended to each file.
        5) File names are automatically incremental (001, 002, ...).
    '''

    if (not regex_) and (not only_media):
        click.echo('One of --regex or --only-media shall be specified.')
        return
    
    if (regex_) and (only_media):
        click.echo('One of --regex or --only-media shall be specified.')
        return
    
    p = Path(str(dir))
    cache = progress(p)
    nodes = cache.get()

    # only files not directories
    output = utils.filter_file(nodes)

    # only normal files not os files or hidden files
    output = utils.exclude_os_files(output)
    
    # filter the correct files with regex or media
    if regex_:
        output = {x for x in output if utils.name_matches_str(x, regex_)}
    elif only_media:
        o_1 = utils.filter_by_suffixes(output, include=common.IMAGE_SUFFIX)
        o_2 = utils.filter_by_suffixes(output, include=common.VIDEO_SUFFIX)
        output = o_1.union(o_2)
    else:
        click.echo("Unknown filter operation, abort")
        return
    
    # Steps:
    # 0. Make a safe prefix.
    # 1. Old names to a hashed safe middle name.
    # 2. Middle name to final name.
    # 3. Depends on json or not, and dry run or not, do the output.

    total_number = len(output) # How many files needs to be renamed
    digits = len(str(total_number)) # How many digits reserved for file names

    # Make it a list
    output = list(output)

    # Order the list with path prefix
    output = sorted(output)

    # Loop over the paths, decide how to rename, make a plan
    plans = [] # Plans to be executed in the future
    for idx, each in enumerate(output):
        stem_parts = []
        _folder_name = utils.get_parent(each)
    
        _old_stem = each.stem
        _middle_stem = utils.get_random_string(7)
        
        _old_path, _middle_path = utils.rename_stem(each, _old_stem, _middle_stem, True)

        if prefix_:
            stem_parts.append(prefix_)
        if keep_folder_name:
            stem_parts.append(_folder_name)
        
        stem_parts.append(str(idx+1).zfill(digits))

        _new_stem = utils.filter_safe_os_name(separator_.join(stem_parts).lstrip(separator_).rstrip(separator_))
        
        _middle_path_2, _new_path = utils.rename_stem(Path(_middle_path), _middle_stem, _new_stem, True)

        assert _middle_path == _middle_path_2

        plans.append({
            'old_path': _old_path,
            'middle_path': _middle_path,
            'new_path': _new_path,
            'old_stem': _old_stem,
            'middle_stem': _middle_stem,
            'new_stem': _new_stem
        })

    if not json_:
        click.echo('-' * 32)
        for each in plans:
            click.echo(f"{each['old_stem']} => {each['middle_stem']} => {each['new_stem']}")
            click.echo(f"{each['old_path']}")
            click.echo(f"{each['middle_path']}")
            click.echo(f"{each['new_path']}")
            click.echo('-' * 16)
    else:
        with open(json_, 'w', encoding='utf8') as f:
            r = {'paths': plans}
            json.dump(r, f, indent=2, ensure_ascii=False)
    
    if force:
        for each in plans:
            utils.rename_stem(Path(each['old_path']), each['old_stem'], each['middle_stem'], False)
        for each in plans:
            utils.rename_stem(Path(each['middle_path']), each['middle_stem'], each['new_stem'], False)
    else:
        click.echo("Warning: This is a dry run, use --force to perform actual rename action.")

@click.command()
@click.argument('dir', type=click.Path(exists=True, dir_okay=True, resolve_path=True), required=True)
@click.option('--force', is_flag=True, help='Perform real actions. (NOT dry run)')
@click.option('--old', 'old_', required=True, type=str, default=None, help='Old name')
@click.option('--new', 'new_', required=True, type=str, default=None, help='New name')
@click.option('--json', 'json_', type=str, default=None, help='File name to save the result in json')
def renamefiles(dir, force, old_, new_, json_):
    '''
    Replace old string in file names with new.

    Note: This is recursive.
    '''
    p = Path(str(dir))
    cache = progress(p)
    nodes = cache.get()

    # Get only files not directories
    output = utils.filter_file(nodes)
    # Get targeted files
    output = {x for x in output if utils.name_has_str(x, old_)}

    if not json_:
        click.echo('-' * 32)
        for each in output:
            oldName, newName = utils.rename_name(each, old_, new_, True)
            click.echo(f'old: {oldName}')
            click.echo(f'new: {newName}')
            click.echo('-' * 16)
    else:
        with open(json_, 'w', encoding='utf8') as f:
            r = {'paths': []}
            for each in output:
                oldName, newName = utils.rename_name(each, old_, new_, True)
                r['paths'].append({
                    'old': str(oldName),
                    'new': str(newName)
                })
            json.dump(r, f, indent=2, ensure_ascii=False)
    
    if force:
        for each in output:
            utils.rename_name(each, old_, new_, False)
    else:
        click.echo("Warning: This is a dry run, use --force to perform actual rename action.")


@click.command()
@click.argument('dir', type=click.Path(exists=True, dir_okay=True, resolve_path=True), required=True)
@click.option('--include-sys', is_flag=True, default=False, help='Hidden system files are considered in scan.')
@click.option('--json', 'json_', type=str, default=None, help='File name to save the result in json')
def emptydirs(dir, include_sys, json_):
    '''
    Find empty directories.
    '''
    p = Path(str(dir))
    cache = progress(p)
    nodes = cache.get()
    # Get dirs
    dirs = utils.filter_dir(nodes)

    output = set()
    if include_sys:
        output = {x for x in dirs if utils.is_empty_dir(x)}
    else:
        output = {x for x in dirs if utils.is_almost_empty_dir(x)}
    
    
    if not json_:
        click.echo('-' * 32)
        for each in output:
            click.echo(each)
    else:
        with open(json_, 'w', encoding='utf8') as f:
            temp = sorted(list(output))
            r = {'paths': [str(x) for x in temp]}
            json.dump(r, f, indent=2, ensure_ascii=False)


@click.command()
@click.argument('dir', type=click.Path(exists=True, dir_okay=True, resolve_path=True), required=True)
@click.option('-n', '--name', multiple=True, default=[], required=True, help="eg. From Russia with Love")
@click.option('--json', 'json_', type=str, default=None, help='File name to save the result in json')
@click.option('--include-sys', is_flag=True, default=False, help='Include system files in scan.')
@click.option('--only-dir', is_flag=True, default=False, help='Only show directories.')
def byname(dir, name, json_, include_sys, only_dir):
    ''' Find files with names.'''
    _names = [str(x).lower() for x in name if len(x.strip()) > 0]
    if len(_names) == 0:
        click.echo('The names provided cannot be white spaces!')
        return
    
    p = Path(str(dir))
    cache = progress(p)
    nodes = cache.get()
    if not include_sys:
        nodes = utils.exclude_os_files(nodes)

    result = utils.filter_by_name(nodes, _names)

    if only_dir:
        result = utils.filter_dir(result)

    temp = sorted(list(result))
    if not json_:
        for each in temp:
            click.echo(each)
    else:
        with open(json_, 'w', encoding='utf8') as f:
            r = {'paths': [str(x) for x in temp]}
            json.dump(r, f, indent=2, ensure_ascii=False)


cli.add_command(bigfiles)
cli.add_command(duplicate)
cli.add_command(bysuffix)
cli.add_command(byname)
cli.add_command(renamedirs)
cli.add_command(renamefiles)
cli.add_command(emptydirs)
cli.add_command(normalize)


if __name__ == '__main__':
    cli()
