# -*- coding: utf-8 -*-
'''Compile page showing simulations for ARCUS from various input directories.
'''
from __future__ import print_function

import argparse
from glob import glob
import os
from os.path import join as pjoin
import shutil
import json
import yaml
from copy import copy

from jinja2 import Environment, FileSystemLoader, select_autoescape


parser = argparse.ArgumentParser(description='Generate website to bundle all Lynx simulations in one place with both Jupiter notebooks rendered to html and x3d output.')
parser.add_argument('outpath',
                    help='base directory for output')
parser.add_argument('x3dpath',
                    help='directory where x3d files are found')
parser.add_argument('notebookpath',
                    help='directory where html rendered notebooks are found')


args = parser.parse_args()

# Generate html
env = Environment(loader=FileSystemLoader(['htmltemplates']),
                  autoescape=select_autoescape(['html']))

if not os.path.exists(args.outpath):
    os.makedirs(args.outpath)

with open('toc.yaml', 'r') as f:
    pagelist = yaml.load(f)


# The page list is nested to represent the structure of the menu.
# Make a flattened copy that can be iterated over:
def add_children(flatlist, page):
    flatlist.append(page)
    if 'children' in page:
        for p in page['children']:
            add_children(flatlist, p)

flatlist = []
add_children(flatlist, pagelist)

for page in flatlist:
    if 'title' not in page:
        continue
    print("Working on {0}".format(page['title']))
    kwargs = copy(page)
    if page['type'] == 'included':
        template = env.get_template(page['href'] + '.html')
    else:
        template = env.get_template(page['type'] + '.html')
        if page['type'] == 'x3d':
            with open(pjoin(args.x3dpath, page['href'] + '.json'), 'r') as f:
                kwargs['x3d'] = json.load(f)
            kwargs['x3d']['path'] = pjoin('x3d', page['href'])
            outdir = pjoin(args.outpath, 'x3d')
            if not os.path.exists(outdir):
                os.makedirs(outdir)
            shutil.copy(pjoin(args.x3dpath, page['href'] + '.x3d'),
                        pjoin(outdir, page['href'] + '.x3d'))
        elif page['type'] == 'notebook':
            outdir = pjoin(args.outpath, 'notebooks')
            if not os.path.exists(outdir):
                os.makedirs(outdir)
            shutil.copy(pjoin(args.notebookpath, page['href'] + '.html'),
                        pjoin(outdir, page['href'] + '.html'))
            kwargs['path'] = pjoin('notebooks', page['href'])

    with open(pjoin(args.outpath, page['href'] + '.html'), "w") as f:
        f.write(template.render(pages=pagelist['children'],
                                active_page=page['href'],
                                **kwargs))


# copy several directories verbatim
for d in ['css', 'images']:
    outdir = pjoin(args.outpath, d)
    if not os.path.exists(outdir):
        os.makedirs(outdir)

    filelist = glob(pjoin(d, '*'))
    for f in filelist:
        shutil.copy(f, outdir)

print("Done. Website is in directory: {}.".format(args.outpath))
print("If this version is meant for publication, take the following steps:")
print(" cd {}".format(args.outpath))
print(" git add any_new_files")
print(" git commit -am'My message here'")
print(" scp -r * space:/space/web/home/guenther/Lynx")
