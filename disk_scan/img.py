''' Image related utils '''
from typing import List
from pathlib import Path
from PIL import Image as PILImage
import imagehash
import time

class HashComputer:
    ''' Image Hash Computer '''
    MODE = {
        'ahash': imagehash.average_hash,
        'phash': imagehash.phash,
        'dhash': imagehash.dhash,
        'color': imagehash.colorhash,
        'crop': imagehash.crop_resistant_hash,
        'default': imagehash.average_hash
    }
    def __init__(self, mode: str):
        _mode_name = mode.lower()
        if _mode_name in HashComputer.MODE:
            self.mode = HashComputer.MODE[_mode_name]
        else:
            self.mode = HashComputer.MODE['default']

    def compute(self, img: PILImage.Image) -> imagehash.ImageHash:
        ''' Sort pics and return a sorted order '''
        return self.mode(img)


class HashableImage:
    ''' Container of {Path, ImageHash}
    '''
    def __init__(self, path: Path, computer: HashComputer):
        self.path = path
        self.img = PILImage.open(path)
        self.computer = computer
        self.img_hash = computer.compute(self.img)

    def hash(self):
        return self.img_hash
    
    def get_path(self) -> Path:
        return self.path
    

def total_distance(images: List[HashableImage]) -> int:
    ''' Generate the total distance over a list of HashableImage

    Args:
        images (List[HashableImage]): The input list of HashImage(s)

    Returns:
        int: Total distance
    '''
    summary = 0
    last_idx = len(images) - 1
    for idx in range(0, len(images)):
        if idx != last_idx:
            d = abs(images[idx].hash() - images[idx+1].hash())
            summary += d
    
    return summary


def insert_to_list(images: List[HashableImage], item: HashableImage) -> List[HashableImage]:
    ''' Insert an image into a list of images, require that the total list weight is the lowest '''
    if len(images) == 0:
        return [item]
    elif len(images) == 1:
        images.append(item)
        return images
    else:
        lowest_weight = -1
        lowest_chain = None

        # position from 0 to N-1
        for idx in range(0, len(images)):
            _images = images.copy()
            _images.insert(idx, item)
            _weight = total_distance(_images)
            
            if lowest_weight == -1:
                lowest_weight = _weight
                lowest_chain = _images
            else:
                if _weight < lowest_weight:
                    lowest_weight = _weight
                    lowest_chain = _images
        
        # final position N
        _images = images.copy()
        _images.append(item)
        _weight = total_distance(_images)

        if _weight < lowest_weight:
            lowest_weight = _weight
            lowest_chain = _images
        
        return lowest_chain


def sort_list(existing: List[HashableImage]) -> List[HashableImage]:
    ''' Sort a list, make sure the total weight is the lowest '''
    _existing = existing.copy()

    return_list = []

    while True:
        try:
            return_list = insert_to_list(return_list, _existing.pop())
        except IndexError as e: # pop from empty list
            break
    
    return return_list


def sort_images(paths: List[Path], mode:str='aHash') -> List[Path]:
    ''' Sort images by a chosen mode, return the new order '''
    hash_computer = HashComputer(mode)
    t1 = time.time()
    hash_images = [HashableImage(x, hash_computer) for x in paths]
    t2 = time.time()
    print(f'image hash time: {t2-t1}s')
    sorted_hash_images = sort_list(hash_images)
    t3 = time.time()
    print(f'image sort time: {t3-t2}s')
    sorted_paths = [x.get_path() for x in sorted_hash_images]
    return sorted_paths