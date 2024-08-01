#!/usr/bin/env python3
# An interactive remover of duplicate files.
# Specify a '.json' file for it to start processing.
import json
from pathlib import Path
from typing import List
from disk_scan import utils
import click

DRY_RUN = False
EXCLUDE = ['.lrprev']

def _exclude(paths: List[str]) -> List[str]:
    ''' Filter the paths, remove the excluded files '''
    a = [Path(x) for x in paths]
    b = utils.filter_by_suffixes(a, None, EXCLUDE)
    c = [str(x) for x in b]
    return c

def _exists(paths: List[str]) -> List[str]:
    ''' Filter the paths, keep only exist paths '''
    a = [Path(x) for x in paths]
    b = [x for x in a if x.exists()]
    c = [str(x) for x in b]
    return c

@click.group()
def cli():
    pass

@click.command()
@click.option('--long', 'long_', is_flag=True, default=False, help='Keep the file with longest parent path')
@click.option('--json', 'json_', type=str, required=False, default=None, prompt='Feed me the json file that describes the duplicated files: ', help='Feed me the json file that describes the duplicated files: ')
def automatic(json_, long_):
    ''' Automatic duplicate remover.
        Keeps the first occurrence, removes the rest.
        If '--long' flag is set, keep the longest "parent" path, removes files under shorter parent paths.
    '''
    location = json_

    with open(location, 'r') as f:
        data = json.load(f)
        print(f'Successfully loaded json file: {location}\n')

        total_keys = len(data)
        processed_keys = 0

        for hash_key in data:
            # mark progress
            processed_keys += 1

            # pre-process the items of the same hash key
            items = utils.sort_path_naturally(data[hash_key])
            items = _exclude(items)
            items = _exists(items)
            if len(items) <= 1:
                continue

            print(f'Progress: {processed_keys}/{total_keys}, Hash: {hash_key}')
            for idx, item in enumerate(items):
                print(f'{idx}) {item}')
            
            # Which one to keep? Fill in the answer
            answer = 0
            if long_:
                # Find out the longest path to keep
                _top_len = 0
                for idx, item in enumerate(items):
                    parental_len = utils.get_root(item)
                    if len(parental_len) > _top_len:
                        answer = idx
                        _top_len = len(parental_len)
            else:
                # Keep the 0 position item
                answer = 0

            # Make the remove
            for idx, item in enumerate(items):
                if idx != int(answer):
                    print(f'Remove: {item}')
                    utils.remove_file(Path(item), DRY_RUN)
            print('\n')

@click.command()
@click.option('--json', 'json_', type=str, required=False, default=None, prompt='Feed me the json file that describes the duplicated files: ', help='Feed me the json file that describes the duplicated files: ')
def interactive(json_):
    ''' Interactive duplicate remover (Asks you which one to keep) '''
    location = json_

    with open(location, 'r') as f:
        data = json.load(f)
        print(f'Successfully loaded json file: {location}\n')

        total_keys = len(data)
        processed_keys = 0

        for hash_key in data:
            # mark progress
            processed_keys += 1

            # pre-process the items of the same hash key
            items = utils.sort_path_naturally(data[hash_key])
            items = _exclude(items)
            items = _exists(items)
            if len(items) <= 1:
                continue

            print(f'Progress: {processed_keys}/{total_keys}, Hash: {hash_key}')
            for idx, item in enumerate(items):
                print(f'{idx}) {item}')
            answer = input(f'Which one to KEEP? Choose [0-{len(items)-1}], or ENTER to skip: ')
            if len(answer) == 0:
                print('Skip.')
                continue
            if int(answer) > (len(items) - 1):
                print(f'Number {int(answer)} out of range, skip.')
                continue
            
            for idx, item in enumerate(items):
                if idx == int(answer):
                    continue
                else:
                    print(f'Remove: {item}')
                    utils.remove_file(Path(item), DRY_RUN)
            print('\n')


@click.command()
@click.option('--json', 'json_', type=str, required=False, default=None, prompt='Feed me the json file that describes the dirs you want to remove: ', help='Feed me the json file that describes the dirs you want to remove: ')
@click.option('--recursive', 'recursive_', is_flag=True, default=False, help='If specified, recursively remove sub folders')
def automatic_dirs(json_, recursive_):
    '''Automatically remove dirs.

    Args:
        json_ (str): location of a json file that describes dirs to remove. {'paths': []}
    '''

    meta_key = 'paths'

    location = json_

    with open(location, 'r') as f:
        data = json.load(f)
        data = data[meta_key]
        print(f'Successfully loaded json file: {location}\n')

        total_keys = len(data)
        processed_keys = 0

        for each_path in data:
            # mark progress
            processed_keys += 1

            print(f'Progress: {processed_keys}/{total_keys}, Path: {each_path}')
            
            # Make the remove of folder (best effort)
            try:
                utils.remove_dir(Path(each_path), recursive=recursive_, dry_run=DRY_RUN)
            except Exception as e:
                print(e)

cli.add_command(automatic)
cli.add_command(interactive)
cli.add_command(automatic_dirs)

if __name__ == '__main__':
    cli()
