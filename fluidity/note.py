#-*- coding:utf-8 -*-
#
# Copyright (C) 2009 - Jens Knutson <jens.knutson at gmail dot com>
# This software is licensed under the GNU General Public License
# version 3 or later (see the file COPYING).
"""Miscellaneous classes for Fluidity's needs

...and OMG, look: it's code I'm not totally ashamed of, huzzah!
"""
from __future__ import absolute_import, division, print_function


__author__ = 'Jens Knutson'


from xml.sax import saxutils

from fluidity import dbus_misc
from fluidity import defs


class Error(Exception):

    def __init__(self, value):
        super(Error, self).__init__()
        self.value = value
        self.message = "Undefined error: "

    def __str__(self):
        return self.message + self.value


class NoteAlreadyExistsError(Error):

    def __init__(self, note_title):
        super(NoteAlreadyExistsError, self).__init__(note_title)
        self.message = "Note with this title already exists: "


class NoUriSetError(Error):

    def __init__(self, value=""):
        super(NoUriSetError, self).__init__(value)
        self.message = "No URI set; a uri must be specified."


class NoteNotFoundError(Error):

    def __init__(self, value):
        super(NoteNotFoundError, self).__init__(value)
        self.message = "Could not find note with uri: "


class Note(object):
    """Tomboy Note object representation."""

    # This is REALLY not the right way to do this, but I didn't understand how
    # to do it with ElementTree until /after/ I created this hack.  I'll fix
    # it later.
    BULLET_LIST_SINGLE_ITEM = '<list><list-item dir="ltr">{0}\n</list-item></list>'
    BULLET_LIST_WITH_SUB_ITEM = ('<list><list-item dir="ltr">{0}\n<list>'
                                 '<list-item dir="ltr">{1}</list-item></list>'
                                 '</list-item></list>')
    # NOTE: THE NEXT THREE LINES GET WRITTEN INTO YOUR NOTE,
    # so don't screw with it unless you know what you're doing!
    CONTENT_START_MARKER_NO_NS = """<note-content version="0.1">"""
    TB_NAMESPACE = 'http://beatniksoftware.com/tomboy'
    CONTENT_START_MARKER_WITH_NS = \
        '<note-content xmlns="' + TB_NAMESPACE + '" version="0.1">'
    CONTENT_END_MARKER = "</note-content>"
    NOTE_SUFFIX = ".note"

    def __init__(self, title=None, uri=None):
        """Initializes the Note object.

        One, and only one, in (uri, title) must be specified.

        Args:
            uri: complete URI of the note
            title: title of the note
        """
        super(Note, self).__init__()
        specify_msg = "'title' or 'uri' must be specified."
        assert (title or uri) and not (title and uri), specify_msg
        if uri:
            assert "://" in uri, "URI format is wrong -- received: " + uri

        remote = self._get_note_remote()
        if uri:
            title = remote.GetNoteTitle(uri)
        elif title:
            uri = remote.FindNote(title)
        self.uri = uri
        self.title = title

    def delete(self):
        """Delete note from Tomboy/Gnote... PERMANENTLY.  There is undo!"""
        remote = self._get_note_remote()
        remote.DeleteNote(self.uri)

    def insert_xml_content(self, new_content, start_marker=None):
        """Insert new_content into note's XML content.

        Args:
            new_content: string with the Tomboy-formatted XML to be inserted
            start_marker: string containing Tomboy-formatted XML to use as a
                marker for the insertion point for new_content

        If start_marker is not specified, new_content will be inserted at the
        beginning of the note, immediately following the newline after the
        note's title.

        Returns: (nothing - method acts directly on the note's content)
        """
        remote = self._get_note_remote()
        note_xml = remote.GetNoteContentsXml(self.uri)

        if self.CONTENT_START_MARKER_WITH_NS in note_xml:
            content_start_marker = self.CONTENT_START_MARKER_WITH_NS
        elif self.CONTENT_START_MARKER_NO_NS in note_xml:
            content_start_marker = self.CONTENT_START_MARKER_NO_NS
        else:
            fail_msg = ("TOMBOY FAIL: they changed the note contents tag "
                        "format... AGAIN.")
            raise Exception(fail_msg)
        if not start_marker:
            start_marker = "".join(content_start_marker,
                                   saxutils.escape(self.title), "\n")
        start_index = note_xml.find(start_marker)
        if start_index != -1:
            insertion_point = start_index + len(start_marker)
            new_xml = (note_xml[:insertion_point] +
                       new_content +
                       note_xml[insertion_point:])
            remote.SetNoteContentsXml(self.uri, new_xml)
        else:
            raise Exception("FAIL. Somehow we had another problem with "
                            "the <note content> tag.  Again.")

    def show(self):
        """Display this Note."""
        if self.uri:
            if not self._get_note_remote().DisplayNote(self.uri):
                raise NoteNotFoundError(self.uri)
        else:
            raise NoUriSetError()

    def create_note(self):
        """Create a new Tomboy note with self.title as the title"""
        remote = self._get_note_remote()
        if remote.FindNote(self.title):
            raise NoteAlreadyExistsError(self.title)
        self.uri = remote.CreateNamedNote(self.title)
        return self.uri

#    def set_note_dimensions(self, width, height):
#        """Set note XML width and height values to `width` and `height`."""
#        remote = self._get_note_remote()
#        dimensions = {'width': str(width), 'height': str(height)}
#        # all this fucking around with unicode and the document header is to get
#        # lxml to STFU.  Yeah, this is probably The Wrong Way(TM), once again,
#        # but that's how I roll, y0: ghetto-tastic shitball code.  If you want
#        # to understand why each of these changes was made, remove this
#        # jiggery pokery and you'll see what I mean. ;-P
#        note_xml = remote.GetNoteCompleteXml(self.uri).encode('utf-8').split('\n')
#        if note_xml[0].startswith('<?xml'):
#            doc_header = note_xml[0:2] + '\n' #.replace("utf-16", "utf-8") + '\n'
#        note_xml = "\n".join(note_xml[1:])
##        # fix up the xml so lxml.etree doesn't bitch about the content being
##        # unicode with an encoding declaration, or that the declaration is wrong
##        note_xml = str(note_xml.replace('<?xml version="1.0" encoding="utf-16"?>',
##                                        '<?xml version="1.0" encoding="utf-8"?>'))
#        with open('/home/jensck/pre_processing.xml', 'w') as prefile:
#            prefile.write(note_xml)
#        ntree = etree.fromstring(note_xml)
#        for dim in dimensions:
#            dimension_element = ntree.findall('.//{%s}%s' % (self.TB_NAMESPACE,
#                                                             dim))[0]
#            dimension_element.text = dimensions[dim]
#        removeme = doc_header + etree.tostring(ntree)
#        remote.SetNoteCompleteXml(self.uri, removeme)
#        with open('/home/jensck/post_processing.xml', 'w') as postfile:
#            postfile.write(removeme)
#        removeme = remote.GetNoteCompleteXml(self.uri)
#        with open('/home/jensck/post_change.xml', 'w') as changefile:
#            changefile.write(removeme)
#        remote = self._get_note_remote()
#        old_width_tags = "<width>450</width>"
#        new_width_tags = "<width>{0}</width>".format(width)
#        fuck_you_all = remote.GetNoteCompleteXml(self.uri)
#        removeme = fuck_you_all.replace(old_width_tags, new_width_tags)
#        removeme = unicode(removeme.replace("utf-16", "utf-8"))
#        removeme.replace('<note-content version="0.1">Ya mamma smokes crack!',
#                         '<note-content version="0.1">Ya mamma smokes crack!\n'
#                         'She got a burnin yearnin and theres no goin back!')
#        remote.SetNoteCompleteXml(self.uri, removeme)
#        with open('/home/jensck/post_change.xml', 'w') as changefile:
#            changefile.write(removeme)

    def _build_bullets(self, stuff):
        """Returns a Tomboy XML-formatted bullet list from a str."""
        stuff = saxutils.escape(stuff)
        return self.BULLET_LIST_SINGLE_ITEM.format(stuff.replace("\n", "&#x2028;"))

    def _get_note_remote(self):
        """Return a dbus "RemoteControl" proxy for talking to Tomboy/GNote.

        This is a method instead of just an attribute to avoid any possible
        pickling issues.
        """
        return dbus_misc.notes_proxy


class ProjectNote(Note):

    NOTES_FROM_INBOX_HEADER = ("<bold><size:huge>Raw/Unprocessed notes"
                               "</size:huge></bold>\n")
    PROJECT_NOTE_TITLE_TEMPLATE = "Prj: "

    def __init__(self, uri=None, title=None, prj=None, notes_for_new_prj=None):
        """Initializes the ProjectNote object.

        One of (uri, title, prj) must be specified.

        Args:
            uri: complete URI of the requested note.
            title: title of the note to open - NOTE: title will automatically
                have ProjectNote.PROJECT_NOTE_TITLE_TEMPLATE pre-pended to it.
            prj: a Project.
            notes_for_new_prj: Optional; used as the note contents for a new
                Project, to be initially inserted into the new note.  Can be
                either as Tomboy XML or plain text.
        """
#       The prefix added to the note title is to prevent note name collisions
#       with pre-existing notes.
        if prj:
            title = self.PROJECT_NOTE_TITLE_TEMPLATE + prj.summary
            self.prj = prj
        elif title and not title.startswith(self.PROJECT_NOTE_TITLE_TEMPLATE):
            title = self.PROJECT_NOTE_TITLE_TEMPLATE + title
            # FIXME: I've no idea where this problem is being introduced, but I
            # have approximately zero desire to figure it out right now.  bah!
        if title:
            title = title.replace("  ", " ")

        try:
            if uri:
                super(ProjectNote, self).__init__(uri=uri)
            else:
                super(ProjectNote, self).__init__(title=title)            
        except AssertionError:
            msg = "One of: 'title', 'uri', or 'prj' must be specified."
            assert prj is not None, msg

        remote = self._get_note_remote()
        self._new_prj_note_template_uri = \
            remote.FindNote(defs.NEW_PROJECT_NOTE_TEMPLATE_NOTE_TITLE)

        if notes_for_new_prj:
            assert prj is not None, ("To use `notes_for_new_prj`, a Project object "
                                     "must be passed to ProjectNote.__init__ ")
            self.title = title
            self.create_note()
            remote.AddTagToNote(self.uri,
                                self._get_prj_status_tags(prj.status)[0])
            # newline padding added just to make it look a bit nicer.
            self.add_stuff(notes_for_new_prj)

    def add_stuff(self, stuff):
        """Add content from an InboxStuff object to the note, as bullets.

        Creates a new note with self.title if a note w/that title can't be found.

        Args:
            stuff: any inbox_stuff.InboxStuff object (or anything with
                string 'summary' and 'details' attributes).
        """
        remote = self._get_note_remote()
        if not remote.FindNote(self.title):
            self.create_note()
        stuff_bullets = self._build_bullets(stuff)
        note_xml = remote.GetNoteContentsXml(self.uri)
        if note_xml.find(self.NOTES_FROM_INBOX_HEADER) == -1:
            # we didn't find the header, so add it to the content before
            # handing it down to be inserted.
            # make it the starting marker as an arg
            stuff_bullets = ("\n" + self.NOTES_FROM_INBOX_HEADER +
                             stuff_bullets + "\n")
            self.insert_xml_content(stuff_bullets)
        else:
            # we already have the header, so don't insert it, but do pass it
            # as the start marker.
            self.insert_xml_content(stuff_bullets, self.NOTES_FROM_INBOX_HEADER)

    def change_prj_status(self, new_status):
        """Move Note to the correct notebook based on new_status."""
        remote = self._get_note_remote()
        old_tag, new_tag = self._get_prj_status_tags(self.prj.status, new_status)
        remote.RemoveTagFromNote(self.uri, old_tag)
        remote.AddTagToNote(self.uri, new_tag)

    def create_note(self, use_template=True):
        self.uri = super(ProjectNote, self).create_note()
        if use_template:
            self._replace_note_contents_with_prj_template()
        return self.uri

    def show(self):
        """Display the note; if not found, create new note using self.title."""
        # Explicitly NOT making this recursive -- if something fails here, I
        # don't want storms of exceptions or floods of dbus traffic.
        try:
            super(ProjectNote, self).show()
        except (NoteNotFoundError, NoUriSetError):
            self.uri = self.create_note()
            super(ProjectNote, self).show()

    def _build_bullets(self, stuff):
        """Returns a Tomboy XML-formatted bullet list from a Stuff note or str."""
        if not hasattr(stuff, 'summary'):
            bullets_xml = super(ProjectNote, self)._build_bullets(stuff)
        else:
            stuff.summary = saxutils.escape(stuff.summary)
            stuff.details = saxutils.escape(stuff.details)
            if stuff.details:
                stuff.summary = stuff.summary.replace("\n", "&#x2028;")
                stuff.details = stuff.details.replace("\n", "&#x2028;")
                bullets_xml = self.BULLET_LIST_WITH_SUB_ITEM.format(stuff.summary,
                                                                    stuff.details)
            else:
                stuff.summary = stuff.summary.replace("\n", "&#x2028;")
                bullets_xml = self.BULLET_LIST_SINGLE_ITEM.format(stuff.summary)
        return bullets_xml

    def _get_prj_status_tags(self, *statuses):
        """Return notebook tags for project status(es)."""
        tag_results = []
        tags = {"active": "system:notebook:Projects - active",
                "queued": "system:notebook:Projects - queued",
                "incubating": "system:notebook:Projects - incubating",
                "waiting_for": "system:notebook:Projects - waiting for",
                "completed": "system:notebook:Projects - completed"}
        for status in statuses:
            tag_results.append(tags[status])
        return tag_results

    def _replace_note_contents_with_prj_template(self):
        """REPLACES a note's contents with the Project template note's contents.

        USE WITH CARE: when called, this method will *replace* the
        contents of your note without any notice or warning.
        """
        remote = self._get_note_remote()
        template_content = \
            remote.GetNoteContentsXml(self._new_prj_note_template_uri)
        note_contents = template_content.replace(
                                 defs.NEW_PROJECT_NOTE_TEMPLATE_NOTE_TITLE,
                                 saxutils.escape(self.title))
        remote.SetNoteContentsXml(self.uri, note_contents)
