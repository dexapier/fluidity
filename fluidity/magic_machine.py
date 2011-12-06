#-*- coding:utf-8 -*-
# 'relevance' code:
#
# Copyright (C) 2009  Ulrik Sverdrup <ulrik.sverdrup@gmail.com>
#               2008  Christian Hergert <chris@dronelabs.com>
#               2007  Chris Halse Rogers, DR Colkitt
#                     David Siegel, James Walker
#                     Jason Smith, Miguel de Icaza
#                     Rick Harding, Thomsen Anders
#                     Volker Braun, Jonathon Anderson
#
# All the rest:
# Copyright (C) 2009 - Jens Knutson <jens.knutson at gmail dot com>
# This software is licensed under the GNU General Public License
# version 3 or later (see the file COPYING).
"""This module provides Fluidity "magic", including smart(ish) text parsing for rapid
input fields, as well as matching/formatting of related strings
based on relevance.  The code originates from Gnome-Do (in C#).

 * Python port by Christian Hergert
 * Module updated by Ulrik Sverdrup to clean up and dramatically speed up
   the code, by using more pythonic constructs as well as doing less work.
 * Lots of spazzy PEP8 fixes by Jens Knutson

Compatibility: Python 2.4 and later, including Python 3
"""
from __future__ import absolute_import, division, print_function


__author__ = 'Jens Knutson'


import datetime
import string #pylint: disable-msg=W0402
import time

from parsedatetime import parsedatetime as pdt

# Py3k compat
try:
    range = xrange  #pylint: disable-msg=W0622
except NameError:
    pass


def format_common_substrings(s, query, format_clean=None, format_match=None):
    """Creates a new string highlighting matching substrings.

    Returns: a formatted string

    >>> format_common_substrings('hi there dude', 'hidude',
    ...                        format_match=lambda m: "<b>%s</b>" % m)
    '<b>hi</b> there <b>dude</b>'

    >>> format_common_substrings('parallelism', 'lsm', format_match=str.upper)
    'paralleLiSM'
    """
    format_clean = format_clean or (lambda x: x)
    format_match = format_match or (lambda x: x)
    format_me = lambda x: x and format_clean(x)

    if not query:
        return format_me(s)

    ls = s.lower()

    # find overall range of match
    first, last = _find_best_match(ls, query)

    if first == -1:
        return format_me(s)

    # find longest perfect match, put in slc
    for slc in range(len(query), 0, -1):
        if query[:slc] == ls[first:first + slc]:
            break
    nextkey = query[slc:]

    head = s[:first]
    match = s[first: first + slc]
    matchtail = s[first + slc: last]
    tail = s[last:]

    # we use s[0:0], which is "" or u""
    result = s[0:0].join((format_me(head), format_match(match),
                          format_common_substrings(matchtail, nextkey,
                                                   format_clean, format_match),
                          format_me(tail)))

    result = result.replace("&", "&amp;").replace("&amp;amp;", "&amp;")

    return result


def score(s, query):
    """A relevance score for the string ranging from 0 to 1

    @s: a string to be scored
    @query: a string query to score against

    `s' is treated case-insensitively while `query' is interpreted literally,
    including case and whitespace.

    Returns: a float between 0 and 1

    >>> print(score('terminal', 'trml'))
    0.735098684211
    >>> print(score('terminal', 'term'))
    0.992302631579
    >>> print(score('terminal', 'try'))
    0.0
    >>> print(score('terminal', ''))
    1.0
    """
    if not query:
        return 1.0

    lower = s.lower()

    # Find the shortest possible substring that matches the query
    # and get the ration of their lengths for a base score
    first, last = _find_best_match(lower, query)
    if first == -1:
        return .0

    skore = len(query) / (last - first)  # don't re-use the name 'score'...

    # Now we weight by string length so shorter strings are better
    skore *= .7 + len(query) / len(s) * .3

    # Bonus points if the characters start words
    good = 0
    bad = 1
    first_count = 0
    for i in range(first, last - 1):
        if lower[i] in " -":
            if lower[i + 1] in query:
                first_count += 1
            else:
                bad += 1

    # A first character match counts extra
    if query[0] == lower[0]:
        first_count += 2

    # The longer the acronym, the better it scores
    good += first_count * first_count * 4

    # Better yet if the match itself started there
    if first == 0:
        good += 2

    # Super duper bonus if it is a perfect match
    if query == lower:
        good += last * 2 + 4
    skore = (skore + 3 * good / (good + bad)) / 4

    # This fix makes sure that perfect matches always rank higher
    # than split matches.  Perfect matches get the .9 - 1.0 range
    # everything else lower
    if last - first == len(query):
        skore = .9 + .1 * skore
    else:
        skore = .9 * skore

    return skore


def _find_best_match(s, query):
    """Find the shortest substring of @s containing all the characters
    of the query, in order.

    @s: a string to be searched
    @query: a string query to search for in @s

    Returns: a two-item tuple containing the start and end indicies of
             the match.  No match returns (-1,-1).

    >>> _find_best_match('terminal', 'trml')
    (0, 8)
    >>> _find_best_match('total told', 'tl')
    (2, 5)
    >>> _find_best_match('terminal', 'yl')
    (-1, -1)
    """
    best_match = -1, -1

    # Find the last instance of the last character of the query
    # since we never need to search beyond that
    last_char = s.rfind(query[-1])

    # No instance of the character?
    if last_char == -1:
        return best_match

    # Loop through each instance of the first character in query
    index = s.find(query[0])

    query_length = len(query)
    last_index = last_char - len(query) + 1
    while 0 <= index <= last_index:
        # See if we can fit the whole query in the tail
        # We know the first char matches, so we don't check it.
        cur = index + 1
        qcur = 1
        while qcur < query_length:
            # find where in the string the next query character is
            # if not found, we are done
            cur = s.find(query[qcur], cur, last_char + 1)
            if cur == -1:
                return best_match
            cur += 1
            qcur += 1

        # Take match if it is shorter.  If it's a perfect match, we are done.
        if best_match[0] == -1 or (cur - index) < (best_match[1] -
                                                   best_match[0]):
            best_match = (index, cur)
            if cur - index == query_length:
                break

        index = s.find(query[0], index + 1)

    return best_match


class MagicMachine(object):
# because it makes the magics!
# (later addition) ...and it makes it from the blood of my labors!  YAY

    def __init__(self, datamgr=None):
        self.pdtCal = pdt.Calendar()
        if datamgr:
            self.data_lumbergh = datamgr

    def get_magic_date(self, muggle_text):
        if muggle_text != "":
            parse_results = self.pdtCal.parse(muggle_text)
            #pdtCal.parse returns a tuple: the second item is an int, 1 or 0,
            #indicating if it could make sense of the input it was fed
            if parse_results[1]:
                ts = time.mktime(parse_results[0])
                magic_date = datetime.date.fromtimestamp(ts)
                return magic_date
        return None

    def get_magic_context(self, text):
        if text == "":
            return text
        t_cmp = self._prepare_for_context_comparison(text)
        contexts = self.data_lumbergh.get_contexts()
        for c in contexts:
            c_cmp = self._prepare_for_context_comparison(c)
            if c_cmp.startswith(t_cmp):
                return c
        # nothing matched...
        text = '@' + t_cmp.capitalize()
        return text

    def get_magic_task(self, muggle_text):
        if not muggle_text:
            return None
        else:
            magic_task = {}
            token_marker = None
            muggle_text = self._strip_dupe_spaces(muggle_text)
            # NOTE: the order below is important!  don't change it unless you
            # understand what you're doing!
            method_list = (self._set_energy_est, self._set_time_est,
                           self._set_high_priority, self._set_context,
                           self._set_due_date, self._set_low_priority,
                           self._set_url)
            for method in method_list:
                muggle_text = self._strip_dupe_spaces(muggle_text)
                muggle_text, token_marker = method(muggle_text, magic_task,
                                                   token_marker)
            # FIXME: this is probably stupid somehow - should probably make this
            # part of setting the context in the first place...
            if 'context' in magic_task:
                magic_task['context'] = self.get_magic_context(magic_task['context'])
            # set summary with what's left
            magic_task['summary'] = muggle_text
            return magic_task

    def _prepare_for_context_comparison(self, text):
        text = text.replace('@', '')
        return text.lower()

    def _strip_dupe_spaces(self, dirty_string):
        d_list = dirty_string.split()
        while True:
            try:
                d_list.remove('')
            except ValueError:
                break
        clean_string = " ".join(d_list)
        return clean_string

    def _set_due_date(self, text, task, marker):
        #print "*** entering _set_due_date ", text
        dmark = " due "
        if marker != None:
            m = text.rfind(dmark, marker - 1)
        else:
            m = text.rfind(dmark)
        if m > 0:
            date_text = text[m + len(dmark):]
            magic_date = self.get_magic_date(date_text)
            if magic_date:
                text = text[:m]
                task['due_date'] = magic_date
        return text, marker

    def _set_energy_est(self, text, task, marker):
        """' e[!-]' - mark the position of this token if it's lower than the
        previous, then process, then remove it"""
        temp_text = text.lower()
        if " e!" in temp_text:
            new_marker = temp_text.rfind(' e!')
            task['energy_est'] = 2
            text = text[:new_marker] + text[new_marker + 3:]
        # first test is so we don't catch "e-mail", etc
        elif text.endswith(" e-") or " e- " in temp_text:
            new_marker = temp_text.rfind(' e-')
            task['energy_est'] = 0
            text = text[:new_marker] + text[new_marker + 3:]
        if marker:
            if - 1 < new_marker < marker:
                marker = new_marker
        return text, marker

    def _set_time_est(self, text, task, marker):
        """' [0-1]m' - mark the position of this token into "global" var, then
         process it, then remove it"""
        #print "*** entering _set_time_est ", text
        time_token = None
        #apparently single quotes fuck things up??
        tlist = text.split()
        for w in tlist:
            if w.endswith("m"):
                for c in w[:-1]:
                    if c not in string.digits:
                        break
                    time_token = w
        if time_token:
            task['time_est'] = float(time_token[:-1])
            new_marker = text.rfind(time_token)
            tlen = len(time_token)
            text = text[:new_marker] + text[new_marker + tlen:]
            if marker:
                if - 1 < new_marker < marker:
                    marker = new_marker
        return text, marker

    def _set_high_priority(self, text, task, marker):
        """This is separate from low priority because low priority is much more
        difficult to parse.  If we can just get this one out of the way, it
        makes things much easier."""
        #print "*** entering _set_high_priority ", text
        if " !" in text:
            new_marker = text.rfind(' !')
            task['priority'] = 1
            text = text[:new_marker] + text[new_marker + 2:]
        if marker:
            if - 1 < new_marker < marker:
                marker = new_marker
        return text, marker

    def _set_low_priority(self, text, task, marker):
        """This is separate from high priority because... see comments re:
        setting high priority."""
        #print "*** entering _set_low_priority ", text
        # FIXME: make it actually work for " - "
        if 'priority' not in task:
            if text.endswith(" -") or text.endswith(" - "):
                task['priority'] = 3
                text = text[:-2]
        return text, marker

    def _set_url(self, text, task, marker):
        #print "*** entering _set_url ", text
        tlist = text.split()
        for i in tlist:
            if "://" in i:
                task['url'] = i
        return text, marker

    # sweet twitching fuck this needs cleaning up...  ew.
    def _set_context(self, text, task, marker):
        #print "*** entering _set_context ", text
        #context - the last instance of a substring that starts with ' @[a-z]'
        #first, find our best candidate - if we don't find one, just bail out
        candidate = None
        urls = []
        for w in text.split():
            if w.startswith('@'):
                candidate = w
            if "://" in w:
                urls.append(w)
        # is the candidate also the last item in the list?  if so, we have to
        # assume that this is the correct item
        # FIXME: bah.  don't do this.
        # UPDATE: disabling the try/except so I can find out what exceptions
        # actually get thrown, ffs
#        try:
        if candidate == text.split()[-1]:
            task['context'] = text.split()[-1]
            marker = text.rfind(candidate)
            text = text[:marker]
            return text, marker
#        except:
#            print "your awesome maintainer is not, in fact, awesome."
        # and if we have nothing, or if we end in a punctuation character:
        if not candidate or candidate[-1] in ['!', '?', '.']:
            return text, marker

        # context not yet found..
        candidate_index = text.rfind(candidate)
        # if we came after another marker at this point, we know we're safe
        if marker:
            if candidate_index >= marker:
                marker = candidate_index
                right = text.find(' ', marker)
                context = text[marker:right]
                task['context'] = context
                text = text.replace(context, marker, 1)
                return text, marker
        # context still not found yet, moving on...
        # strip URLs, we don't want to consider them for this
        temp_text = text
        for u in urls:
            temp_text = temp_text.replace(u, '')
        # don't accidentally pick up low priority for the later "between due
        # and us" test
        temp_text.replace(" - ", "")
        due_index = text.rfind(" due ")
        if due_index > candidate_index:
            if candidate_index + len(candidate) != due_index:
                # at this point we should never have anything between us and
                # the due_index
                return text, marker
        right = candidate_index + len(candidate)
        remaining_after_due = text[candidate_index:right]
        if remaining_after_due == "":
            # candidate can't be a context
            return text, marker
        # FINALLY.  christ...  we have to assume we're a context here
        tlist = text.split()
        tlist.reverse()
        tlist.remove(candidate)
        tlist.reverse()
        text = " ".join(tlist)
        task['context'] = candidate
        marker = candidate_index
        return text, marker

