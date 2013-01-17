#-*- coding:utf-8 -*-
#
# Copyright (C) 2009 - Jens Knutson <jens.knutson at gmail dot com>
# This software is licensed under the GNU General Public License
# version 3 or later (see the file COPYING).
"""OH NOES."""
from __future__ import absolute_import, division, print_function


__author__ = 'Jens Knutson'


import abc
import datetime
import json
import os
import pathlib
import pickle
import shutil
import string  # IGNORE:W0402  # the string module is not deprecated!
import time

import glib
import gio
import requests

from lxml import etree
from xml.sax import saxutils

from xdg import BaseDirectory

from fluidity import app_utils
from fluidity import defs
from fluidity import dbus_misc
from fluidity import gio_fml
from fluidity import slider


INBOXES = ()
#           'sftp://luser@myserver.example.org/home/luser/Inbox')
# INBOXES MUST BE A SET OF URIs/URLs, NOT JUST PLAIN PATHS


def testimate():
    import gtk
    import gobject
    gobject.timeout_add_seconds(3, consolidate)
    gtk.main()


def consolidate():
    inboxes = []
    for ibx in INBOXES:
        if ibx.startswith('file://'):
            inboxes.append(LocalFilesystemInbox(ibx))
        else:
            inboxes.append(MountableInbox(ibx))

    inboxes.extend((
        # CONFIG FOR WHICH INBOXES GET USED AND WHICH DON'T
        # terrible place for it, but this is the kind of thing
        # that's going away when I finally get around to 
        # refactoring all this
#        RESTInbox(), 
        DropboxInbox(),
        TomboyInbox(),  # this should probably always be the last one.
    ))
    for i in inboxes:
        i.consolidate()


class Error(Exception):
    """Created because Google's Python style guidelines say to do this...  
    I'm probably misinterpreting. ;-P """
    pass


class ConsolidateInboxError(Error):

    def __init__(self, message):
        self._message = message
        super(ConsolidateInboxError, self).__init__(message)

    def __str__(self):
        return "ConsolidateInboxError: " + self._message


class Inbox(object):

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def consolidate(self):
        """Consolidate this inbox into the main inbox for this inbox type."""


class LocalFilesystemInbox(Inbox):
    """Inbox subclass for local filesystems."""

    MAIN_INBOX = gio_fml.FityFile(defs.INBOX_FOLDER)
    SLIDER_INBOX = gio_fml.FityFile(defs.NOTE_SLIDER_FOLDER)

    def __init__(self, secondary_inbox):
        """Initialize this LocalFilesystemInbox.

        Args:
            secondary_path: full path to an inbox folder to be emptied into the
                main Fity inbox.
        """
        self._this_inbox = gio_fml.FityFile(secondary_inbox)

    def consolidate(self):
        for child in self._this_inbox.get_children():
            try:
                app_utils.log_line("Moving file {0} to inbox...".format(child.path),
                               datetime.datetime.now())
                inbox = self.SLIDER_INBOX if child.ext == ".pkl" else self.MAIN_INBOX
                child.move(inbox.get_child(child.basename))
            except gio_fml.MoveError as m_err:
                app_utils.log_line(str(m_err), datetime.datetime.now())


class MountableInbox(LocalFilesystemInbox):

    def consolidate(self):
        cb_user_data = {'cb': self.consolidate}
        if self._mount_volume(user_data=cb_user_data):
            try:
                super(MountableInbox, self).consolidate()
            except (gio.Error, ConsolidateInboxError) as error:
                msg = "Unable to consolidate from {0} - message: {1}".format(
                    self._this_inbox, error)
                app_utils.log_line(msg, datetime.datetime.now())
            self._unmount_volume()

    def _mount_volume(self, obj=None, async_result=None, user_data=None):
        """Tricky crap to get around having to do proper async I/O. ;-P"""
        if async_result is None:        # i.e.: we're not being called as a callback
            try:
                self._this_inbox.find_enclosing_mount()
                return True
            except gio.Error:
                # location not mounted; let's try fixing that.
                self._this_inbox.mount_enclosing_volume(
                        callback=self._mount_volume, user_data=user_data)
                return False
        else:
            try:
                obj.mount_enclosing_volume_finish(async_result)
            except (gio.Error, glib.GError) as err:
                msg = "unable to mount: {0}.  Error: {1}".format(self._this_inbox,
                                                                 err)
                app_utils.log_line(msg, datetime.datetime.now())
                msg = "Unable to mount the requested volume: " + msg
                raise ConsolidateInboxError(msg)
            user_data['cb']()

    def _unmount_volume(self, *args):
        # FIXME: do I care about the fact that I'm not paying any additional
        # attention to unmounts?
        if not args:
            mounty = self._this_inbox._gfile.find_enclosing_mount()
            mounty.unmount(self._unmount_volume)
        else:
            try:
                args[0].unmount_finish(args[1])
            except gio.Error as err:
                msg = "Unable to UNmount: {0}.  Error: {1}".format(self._this_inbox,
                                                                   err)
                app_utils.log_line(msg, datetime.datetime.now())


class RESTInbox(Inbox):
    
    NOTE_SAVE_PATH = defs.NOTE_SLIDER_FOLDER
    
    def consolidate(self):
        for i in self._retrieve_inbox_items():
            note = {'summary': i['summary'], 
                    'details': i['details']}
            self._create_inbox_note(note, self.NOTE_SAVE_PATH)
    
    def _retrieve_inbox_items(self):
        url = 'http://anvil.solemnsilence.org:9395/fluidity_mobile/inbox/pull_all/'
        uname, pwd = self._read_auth_info()
        response = requests.post(url, auth=(uname, pwd))
        return [i['fields'] for i in json.loads(response.content)]  # IGNORE:E1103
    
    def _create_inbox_note(self, note_dict, parent_dir):
        if note_dict['summary'] is None:
            app_utils.log_line("Blank summary line in REST inbox...")
        else:
            file_name = "{0}_{1}-{2}".format(
                note_dict['summary'][:50].replace(os.sep, ''),
                time.time(),
                "note.pkl")
            file_path = os.path.join(parent_dir, file_name)
            with open(file_path, 'wb') as pickle_file:
                pickle.dump(note_dict, pickle_file, pickle.HIGHEST_PROTOCOL)

    def _read_auth_info(self):
        # TOTAL HACK.  just here for now...  (I'm saying that a lot these days.)
        with open('/home/jensck/.local/share/fluidity/anvil_auth.json', 'r') as anvil_auth_file:
            return json.load(anvil_auth_file)


class TomboyInbox(Inbox):
    #shit I might actually want to change at some point
    MAIN_INBOX = defs.INBOX_FOLDER
    TOMBOY_NOTE_FOLDER = BaseDirectory.save_data_path("tomboy")
    STARTHERE_BACKUPS = os.path.join(BaseDirectory.save_data_path("boxidate"),
                                     "start_here_backups")
    NOTE_SUFFIX = ".note"
    PADDING = "\n\n\n"
    # Tomboy "magic" - these really aren't the Right Way, but ElementTree
    # pissed me off, and seemed like overkill when this is all that's needed.
    # what to put inbetween the chunks of content grabbed from each NOTD
    #
    # Also: THE NEXT THREE LINES GET WRITTEN INTO START HERE, so don't screw with it
    # unless you know what you're doing!
    TB_CONTENT_START = "<note-content version=\"0.1\">"
    TB_CONTENT_END = "</note-content>"
    SH_CONTENT_START = TB_CONTENT_START + "Start Here"

    def __init__(self):
        super(TomboyInbox, self).__init__()
        # Set everything up - path names, mostly, a few connections to dbus, etc
        self.tbus = dbus_misc.notes_proxy

    def consolidate(self):
        # FIXME: REMOVE LATER
        if os.environ.get("USER") not in ("jensck", "jknutson"):
            return
        notelist = self.build_note_list(self.MAIN_INBOX)
        agg_xml = self.build_aggregate_note(notelist)
        self._back_up_SH()
        new_sh_xml = self.build_SH_replacement_xml(agg_xml)
        msg = "".join(("Boxidate is adding this to your Start Here note:\n",
                      new_sh_xml, "\n\n\n"))
        app_utils.log_line(msg, datetime.datetime.now(),
                       '/home/jensck/fity-data/boxidate.log')
        self.set_SH_xml(new_sh_xml)
        self.delete_notes(notelist)

    def build_aggregate_note(self, notelist):
        aggregate = self.PADDING
        el = len(self.TB_CONTENT_START)
        for n in notelist:
            n = os.path.join(self.MAIN_INBOX, n)
            opened = open(n, 'r')
            c = opened.read()
            opened.close()
            c_begin = c.find(self.TB_CONTENT_START) + el
            c_end = c.find(self.TB_CONTENT_END)
            aggregate += c[c_begin:c_end] + self.PADDING

        aggregate += self._horrible_hack_to_get_PlainText_inbox()
        aggregate += self._horrible_hack_to_get_NV_inbox()
        return aggregate

    def build_note_list(self, folder):
        notes = []
        for f in os.listdir(folder):
            if f.endswith(self.NOTE_SUFFIX):
                notes.append(f)
                print(f)
        return notes

    def build_SH_replacement_xml(self, xml):
        sh_xml = self.tbus.GetNoteContentsXml(self.sh_uri)
        marker = len(self.SH_CONTENT_START)
        return self.SH_CONTENT_START + xml + sh_xml[marker:]

    def delete_notes(self, notes):
        for n in notes:
            n = os.path.join(self.MAIN_INBOX, n)
            os.remove(n)

    def set_SH_xml(self, xml):
        # FIXME: remove this - testing only
        with open('/home/jensck/stupid_tomboy_format_changes.xml', 'w') as xmlfile:
            xmlfile.write(xml)
        self.tbus.SetNoteContentsXml(self.sh_uri, xml)

    @property
    def sh_uri(self):
        return self.tbus.FindStartHereNote()

    def _back_up_SH(self):
        sh_raw = self.tbus.FindStartHereNote()
        sh_name = sh_raw.split('/')[-1] + self.NOTE_SUFFIX
        sh_file_path = os.path.join(self.TOMBOY_NOTE_FOLDER, sh_name)
        backup_file_path = os.path.join(self.STARTHERE_BACKUPS,
                           str(datetime.date.today()) + "_" + sh_name)
        shutil.copy2(sh_file_path, backup_file_path)

    def _horrible_hack_to_get_PlainText_inbox(self):
        """Horrible, lame hack to help me for the short-term as my workflow changes..."""
        plaintext_inbox = '/home/jensck/Dropbox/PlainText/Fluidity Inbox.txt'
        with open(plaintext_inbox) as inboxfile:
            contents = inboxfile.read()

        # empty the inbox, since we're done with it
#        with open(plaintext_inbox, 'w') as inboxfile_again:
#            inboxfile_again.write("\n")

        return saxutils.escape(contents)

    def _horrible_hack_to_get_NV_inbox(self):
        """Horrible, lame hack #2 to help me for the short-term as my workflow changes..."""
        nv_inbox = '/home/jensck/Dropbox/Notational Data/Start Here.html'
        with open(nv_inbox, 'r') as inboxfile:
            contents = inboxfile.read()

        personal_header = '<b>Personal_Inbox_FTW</b></p>'
        doc_footer_base = '\n</body>\n</html>'

        personal_start = contents.find(personal_header) + len(personal_header)
        personal_end = contents.find(doc_footer_base)
        personal_content_raw = contents[personal_start:personal_end]
        # prevent annoying-albeit-correct complaints from XML libs about unclosed tags...
        personal_content = personal_content_raw.replace('<br>', '<br/>')
        # add a fake header and footer back so it can be parsed as XML (well, HTML5)
        fake_header = '<!DOCTYPE HTML><html><body>'
        personal_content = fake_header + personal_content + doc_footer_base

        # FIXME: WTF. why is this necessary?
        personal_content = "".join([c for c in personal_content if c in string.printable])
        personal_content = _convert_xml_to_text(personal_content, 'body')
        personal_content = saxutils.escape(personal_content)
        personal_content = "".join([c for c in personal_content if c in string.printable])

        new_contents = contents.replace(personal_content_raw, '') 

        # empty the inbox, since we're done with it
        with open(nv_inbox, 'w') as inboxfile_again:
            inboxfile_again.write(new_contents)

        return personal_content


class DropboxInbox(Inbox):

    NOTE_GLOB = 'inbox_note*.protobytes'

    def consolidate(self):
        for note_path in defs.DROPBOX_INBOX_PATH.glob(DropboxInbox.NOTE_GLOB):
            self._process_android_inbox_note(note_path)
        # now handle the remaining files.
        for path in defs.DROPBOX_INBOX_PATH.glob('*'):
            # leave dotfiles alone, for stuff like dropsync
            if not str(path).startswith('.'):
                self._process_android_inbox_note(note_path)
    
    def _process_regular_file(self, path):
        print("Processing regular file:", path)
        shutil.move(str(path), defs.INBOX_FOLDER)

    def _process_android_inbox_note(self, note_path):
        print("Processing note:", note_path)
        abs_path = str(note_path.absolute())
        with open(abs_path, 'r') as notefile:
            note_text = notefile.read()
        
        # the android inbox app takes no 'details' info yet.
        slider.create_inbox_note(note_text, "")
        
        # we're done with the file, ditch it.
        gf = gio.File(abs_path)
        gf.trash()


class BoxidatorOld(object):
    """Consolidate my inboxes, including content from an external Tomboy note."""

    #shit I might actually want to change at some point
    MAIN_INBOX = defs.INBOX_FOLDER
    TOMBOY_NOTE_FOLDER = BaseDirectory.save_data_path("tomboy")
    FITY_SLIDER_INBOX = defs.NOTE_SLIDER_FOLDER
    STARTHERE_BACKUPS = os.path.join(BaseDirectory.save_data_path("boxidate"),
                                     "start_here_backups")
    #Tomboy "magic" - these really aren't the Right Way, but ElementTree
    #pissed me off, and seemed like overkill when this is all that's needed.
    #Also note: THE NEXT THREE LINES GET WRITTEN INTO START HERE,
    #so don't screw with it unless you know what you're doing!
    TB_CONTENT_START = "<note-content version=\"0.1\">"
    TB_CONTENT_END = "</note-content>"
    SH_CONTENT_START = TB_CONTENT_START + "Start Here"
    NOTE_SUFFIX = ".note"
    #what to put inbetween the chunks of content grabbed from each NOTD
    PADDING = "\n\n\n"

    def __init__(self):
        # Set everything up - path names, mostly, a few connections to dbus, etc
        self.tbus = dbus_misc.notes_proxy

        #get the URI for Start Here
        self.sh_uri = self.tbus.FindStartHereNote()

    ##Tomboy - importing .note files into Start Here
    def _back_up_SH(self):
        sh_raw = self.tbus.FindStartHereNote()
        sh_name = sh_raw.split('/')[-1] + self.NOTE_SUFFIX
        sh_file_path = os.path.join(self.TOMBOY_NOTE_FOLDER, sh_name)
        backup_file_path = os.path.join(self.STARTHERE_BACKUPS,
                           str(datetime.date.today()) + "_" + sh_name)
        shutil.copy2(sh_file_path, backup_file_path)

    def build_aggregate_note(self, notelist):
        aggregate = self.PADDING
        el = len(self.TB_CONTENT_START)
        for note in notelist:
            notepath = os.path.join(self.MAIN_INBOX, note)
            with open(notepath, 'r') as notefile:
                content = notefile.read()
                content_begin = content.find(self.TB_CONTENT_START) + el
                content_end = content.find(self.TB_CONTENT_END)
                aggregate += content[content_begin:content_end] + self.PADDING
        return aggregate

    def build_note_list(self, folder):
        notes = []
        for f in os.listdir(folder):
            if f.endswith(self.NOTE_SUFFIX):
                notes.append(f)
                print(f)
        return notes

    def build_SH_replacement_xml(self, xml):
        sh_xml = self.tbus.GetNoteContentsXml(self.sh_uri)
        marker = len(self.SH_CONTENT_START)
        return self.SH_CONTENT_START + xml + sh_xml[marker:]

    def delete_notes(self, notes):
        for n in notes:
            n = os.path.join(self.MAIN_INBOX, n)
            os.remove(n)

    def set_SH_xml(self, xml):
        self.tbus.SetNoteContentsXml(self.sh_uri, xml)

    def import_sidearm_inbox(self, sidearm_inbox, main_slider_inbox, main_inbox):
        for gf_info in sidearm_inbox.enumerate_children('*'):
            file_name = gf_info.get_name()
            gfile = sidearm_inbox.get_child(file_name)
            if file_name.endswith(".pkl"):
                gfile.move(main_slider_inbox.get_child(file_name),
                           self.totally_irresponsible_callback,
                           user_data="calling irresponsible_callback from "
                                     "import_sidearm_inbox for a pickle")
            else:
                gfile.move(main_inbox.get_child(file_name),
                           self.totally_irresponsible_callback,
                           user_data="calling irresponsible_callback from "
                                     "import_sidearm_inbox for a regular file")
        try:
            sidearm_inbox.find_enclosing_mount().unmount(
                self.totally_irresponsible_callback,
                user_data="calling irresponsible_callback from "
                          "import_sidearm_inbox for unmounting sftp_inbox")
        except gio.Error as error:
            print("Problem unmounting an inbox.  Error: ", error)

    def consolidate(self):
        app_utils.log_line("Running boxidate.Boxidator.consolidate()",
                        datetime.datetime.now())
        #put us in the right folder to start off with, just in case...
        os.chdir(self.MAIN_INBOX)

        # Disabled for now
#        self.move_contents_to_main_inbox(self.FS_INBOXES, self.MAIN_INBOX)
#        print "Contents of external filesystem inboxes moved."
        notelist = self.build_note_list(self.MAIN_INBOX)
        agg_xml = self.build_aggregate_note(notelist)
        self._back_up_SH()
        new_sh_xml = self.build_SH_replacement_xml(agg_xml)
        #FIXME: still required?
        time.sleep(2)
        msg = "".join(("Boxidate is adding this to your Start Here note:\n",
                      new_sh_xml, "\n\n\n"))
        app_utils.log_line(msg, datetime.datetime.now(),
                       '/home/jensck/fity-data/boxidate.log')
        self.set_SH_xml(new_sh_xml)
        self.delete_notes(notelist)

        # handle the stuff on Sidearm
        main_slider_inbox = gio.File(self.FITY_SLIDER_INBOX)
        main_inbox = gio.File(self.MAIN_INBOX)
        sidearm_sftp_inbox = gio.File(uri=self.SIDEARM_SFTP_INBOX_URI)
        try:
#            sidearm_sftp_inbox.find_enclosing_mount()
            sidearm_sftp_inbox.mount_enclosing_volume(gio.MountOperation(),
                self.import_inbox_async_cb, user_data=(sidearm_sftp_inbox,
                                                       main_slider_inbox,
                                                       main_inbox))
        except gio.Error as error:
            print("Error while trying to mount sftp inbox: " + str(error))

    def import_inbox_async_cb(self, obj=None, result=None, user_data=None):
        if user_data is not None:
            other_inbox, main_slider_inbox, main_inbox = user_data
            self.import_sidearm_inbox(other_inbox, main_slider_inbox, main_inbox)


def _convert_xml_to_text(xml_str, content_element_name, namespaces=None):
    def _convert_xml(element):
        chunks = []
        
        if element.text:
            chunks.append(element.text)
        
        children = element.getchildren()
        if len(children) > 0:
            for child in children:
                chunks.append(_convert_xml(child))
        
        if element.tail:
            chunks.append(element.tail)
        
        return "".join(chunks)
    
    root = etree.fromstring(xml_str).getroottree().getroot()
    content_element = root.find(content_element_name)
    
    return _convert_xml(content_element)


# NONE OF THIS WORKS, IT'S JUST COPY/PASTE WORK TO SERVE AS A STUB FOR LATER ON...
#class FTPInbox(LocalFilesystemInbox):
#
#    def __init__(self):
#        ftp = self.get_ftp_conn(self.INBOX_SERVERS, self.FTP_USERNAME)
#        if ftp:
#            self.get_ftp_inbox_files(ftp, self.REMOTE_INBOX_FOLDER)
#            self.delete_ftp_files(ftp)
#            self.tear_down_ftp_conn(ftp)
#
#    def delete_ftp_files(self, ftp):
#        for f in ftp.nlst():
#            ftp.delete(f)
#
#    def get_ftp_conn(self, servers, username):
#        success = False
#        ftp_conn = None
#        for hostname in servers:
#            if not success:
#                try:
#                    ftp_conn = ftplib.FTP(hostname)
#                    password = self.get_ftp_password(hostname)
#                    ftp_conn.login(username, password)
#                    success = True
#                except socket.error as e:
#                    print(("Problem connecting to '{0}', "
#                           "error given was: {1}").format(hostname, e))
#        return ftp_conn
#
#    def get_ftp_inbox_files(self, ftp, remote_inbox):
#        ftp.cwd(remote_inbox)
#        for f in ftp.nlst():
#            print("Trying to RETR: " + f)
#            ftp.retrbinary('RETR ' + f,
#                           open(os.path.join(self.MAIN_INBOX, f), 'wb').write)
#
#    def tear_down_ftp_conn(self, ftp):
#        ftp.quit()
#
#    def get_ftp_password(self, server):
#        attrs = {"server": server, "protocol": 'ftp', 'user': 'jensck'}
#        items = gnomekeyring.find_items_sync(gnomekeyring.ITEM_NETWORK_PASSWORD,
#                                             attrs)
#        return items[0].secret


#class SSHInbox(NetworkInbox):
#
#    def __init__(self, remote_inbox, hostname, port=22, username=None, password=None):
#        """Initialize this SSHInbox.
#
#        See superclass for docstring.
#        """
#
#        # well, that interface got kinda bloaty real fast... bah.
#        import paramiko
#
#        super(SSHInbox, self).__init__(remote_inbox, hostname, port, username,
#                                       password)
#        self.pkey = None
#        self.key_filename = None
#        self.timeout = None
#        self.allow_agent = True
#        self.look_for_keys = True
#        self.connection_client = paramiko.SSHClient()
#
#        # FIXME: bad security...  bleh.
#        self.connection_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#
#    def consolidate(self):
#        self._connect()
#        self._move_files_to_inbox()
#        self._close_connection()
#
#    def _close_connection(self):
#        self.connection_client.close()
#
#    def _connect(self):
#        try:
#            self.connection_client.connect(self.hostname, self.username,
#                                           self.password)
#        except Exception as err:
#            print("Error while trying to connect to", self.hostname + ":", str(err))
#
#    def _move_files_to_inbox(self):
#        fuckyou = self.connection_client.open_sftp()
#        print(fuckyou)
##
#################===================================================================
# #        basename = os.path.basename(to_upload)
# #        print("Downloading " + basename)
# #        sftp.put(to_upload, remote_path + basename)
# #        sftp.close()
#===================================================================================


def main():
    di = DropboxInbox()
    di.consolidate()


if __name__ == '__main__':
    main()

