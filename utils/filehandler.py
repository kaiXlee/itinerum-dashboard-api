#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Kyle Fitzsimmons, 2016
from flask import current_app
from hashids import Hashids
import math
import os
from PIL import Image
import time
from werkzeug.utils import secure_filename
import zipfile

hashids = Hashids()


def save(filedata, extensions=None):
    # check that extension is valid
    _, ext = os.path.splitext(filedata.filename)
    valid_ext = ext in extensions

    if not valid_ext:
        raise TypeError

    # create a unique hash based on timestamp
    now = int(time.time())
    time_hash = hashids.encode(now)

    # save to assets folder and return filename
    filename = secure_filename(time_hash + ext)
    filepath = os.path.join(current_app.config['ASSETS_FOLDER'], 'user', 'avatars', filename)
    filedata.save(filepath)
    return filename


def delete(uri):
    filepath = os.path.join(current_app.config['ASSETS_FOLDER'], 'user', 'avatars', os.path.basename(uri))
    if os.path.exists(filepath):
        os.remove(filepath)


def crop(image, size):
    img_format = image.format
    image = image.copy()
    old_size = image.size
    left = (old_size[0] - size[0]) / 2
    top = (old_size[1] - size[1]) / 2
    right = old_size[0] - left
    bottom = old_size[1] - top
    rect = [int(math.ceil(x)) for x in (left, top, right, bottom)]
    left, top, right, bottom = rect
    crop = image.crop((left, top, right, bottom))
    crop.format = img_format
    return crop


# resizes existing edge (width or length) to given size and reduces
# other dimension by existing aspect ratio. Crops excess length evenly from
# each side to create a square centered thumbnail
def make_thumbnail(img_file, size=[200., 200.]):
    img = None
    with Image.open(img_file) as image:
        img_format = image.format
        img = image.copy()
        img.format = img_format
        img_size = img.size

        img_too_large = (img_size[0] > size[0]) or (img_size[1] > size[1])
        if img_too_large:
            ratio = max(size[0] / img_size[0], size[1] / img_size[1])
            new_size = [
                int(math.ceil(img_size[0] * ratio)),
                int(math.ceil(img_size[1] * ratio))
            ]
            img = img.resize((new_size[0], new_size[1]), Image.LANCZOS)
            img = crop(img, size)

    img.filename = img_file.filename
    return img


# Takes a dictionary object of BytesIO memory file objects
# and writes a zip containing these files with the dictionary
# keys as filenames
def save_zip(basepath, basename, data):
    zip_filename = '{base}-{time}.zip'.format(base=basename.encode('utf-8'),
                                              time=int(time.time()))
    zip_filepath = os.path.join(current_app.config['ASSETS_FOLDER'],
                                basepath, zip_filename)
    with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zip_f:
        for csv_filename, csv_data in data.items():
            zip_f.writestr(csv_filename, csv_data.getvalue())
    return zip_filename
