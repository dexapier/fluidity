#!/usr/bin/python -O
#-*- coding:utf-8 -*-
# ZOMG, a time when -O might not be total rice!
from __future__ import absolute_import, division, print_function, unicode_literals

__author__ = "Jens Knutson"


try:
    import cPickle as pickle
except ImportError:
    import pickle
import os
import sys


QUERY_STRINGS = ['.', 'nvr', 'doug', 'mcc', 'jason', 'parking', 'camera']
RESULTS_REPORT_PATH = "data_hunter_report.txt"


def find_pickles(root):
    for i in os.walk(root):
        for filename in i[2]:
            if '.pkl' in filename and not "singletons" in filename:
                yield os.path.join(i[0], filename)

def pull_notes_from_pickle(pkl_path):
    with open(pkl_path, 'r') as pkl:
        notes = pickle.load(pkl)['single_notes']
    # SOOOOooo not in the mood for case sensitivity issues
    return (n['summary'].lower().strip('.') for n in notes)

def search_notes(notes, queries):
    found = set()
    for n in notes:
        for q in queries:
            if q in n:
                found.add(n)
                print("|", end="")
    return found


def main(search_root):
    pickles_to_search = []
    basenames = []
    print("Finding pkl files")
    for pklpath in find_pickles(search_root):
        base = os.path.basename(pklpath)
        if base not in basenames:
            pickles_to_search.append(pklpath)
            basenames.append(base)
            print(".", end="")

    print("\nReading in data from pkl files...")
    notes = set()
    for search_pickle in pickles_to_search:
        print(".", end="")
        for pnote in pull_notes_from_pickle(search_pickle):
            notes.add(pnote)

    print("\nNow searching notes...\nMatches found: ", end="")
    results = search_notes(notes, QUERY_STRINGS)

    print("\nDone -- writing report.")
    with open(RESULTS_REPORT_PATH, 'w') as report:
        report.write("\n".join(sorted(results)))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("fity_data_hunter.py takes 1 and only 1 argument: a root "
                 "path to be searched for pkl files.")
    else:
#        import cProfile
#        cProfile.run("main(sys.argv[1])", 'profile.out')
        main(sys.argv[1])