#!/usr/bin/env python
from __future__ import absolute_import, division, print_function

# include in this a total of the time estimates!

try:
    import cPickle as pickle
except ImportError:
    import pickle
import datetime
import operator
import os
import sys

import gtk

from fluidity import defs
from fluidity import gee_tee_dee    #pylint: disable-msg=W0611


def copy_to_clipboard(text):
    clipboard = gtk.clipboard_get()
    clipboard.set_text(text)
    clipboard.store()
    clipboard = None

def create_overall_summary(nas_completed_today):
    overall_summary = ""
    time_total = 0
    na_format = "{0} -- {1} mins\n"
    nas_completed_today.sort(key=operator.attrgetter('summary'))
    if len(nas_completed_today) > 0:
        for na in nas_completed_today:
            overall_summary += na_format.format(na.summary, na.time_est)
            time_total += na.time_est
        mins = int(time_total % 60)
        mins = "" if mins == 0 else ", {0} mins".format(mins)
        time_summary = "{0} hours{1}".format(int(time_total // 60), mins)
        overall_summary += "Total (estimated) time: " + time_summary
    else:
        overall_summary = "(No completed NAs found for this date)"
    return overall_summary

def get_nas_completed_on_date(archived_nas, completion_date):
    results = []
    for na in archived_nas:
        if na.completion_date == completion_date:
            results.append(na)
    return results

def get_parsed_date(date):
    if date in ('y', 'yest', 'yesterday'):
        return datetime.date.today() - datetime.timedelta(1)
    else:
        split = [int(x) for x in date.split('-')]
        if len(split) != 3:
            print("You screwed up, boss.  I need dates as YYYY-MM-DD.")
            sys.exit(1)
        return datetime.date(split[0], split[1], split[2])

def load_data_files(path):
    with open(path, 'r') as pkl:
        data = pickle.load(pkl)
    return data

def main():
    if len(sys.argv) == 2:
        today = get_parsed_date(sys.argv[1])
    else:
        today = datetime.date.today()

    archived_path = os.path.join(defs.USER_DATA_PATH,
                                 defs.ARCHIVED_SINGLETONS_FNAME.format(""))
    top = load_data_files(defs.USER_DATA_MAIN_FILE)
    archived = load_data_files(archived_path)

    nas_completed_today = []

    for prj in top['projects'].values():
        nas_completed_today += get_nas_completed_on_date(prj.next_actions, today)
    nas_completed_today += get_nas_completed_on_date(archived, today)

    na_summaries = create_overall_summary(nas_completed_today)

    copy_to_clipboard(na_summaries)
    #print na_summaries

if __name__ == '__main__':
    main()