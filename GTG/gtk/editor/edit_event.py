# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2013 - Lionel Dricot & Bertrand Rousseau
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.
# -----------------------------------------------------------------------------


from gi.repository import Gtk

from GTG import ngettext
from GTG.gtk.editor import GnomeConfig


class EditEventUI():

    def __init__(self):
        # Load window tree
        self.builder = Gtk.Builder()
        self.builder.add_from_file(GnomeConfig.EDITEVENT_UI_FILE)
        signals = {"on_following_event_activate": self.on_following_pressed,
                    "on_only_this_event_activate": self.on_only_pressed,
                    "on_all_event_activate": self.on_all_pressed,
                   "on_cancel_activate": lambda x: x.hide, }
        self.builder.connect_signals(signals)

    def on_following_pressed(self, widget):
        pass

    def on_only_pressed(self, widget):
        pass

    def on_all_pressed(self, widget):
        pass

    def editevent(self):
        cdlabel2 = self.builder.get_object("cdr-label2")
        cdlabel2.set_label(ngettext(
            "Would you like to change",
            "Would you like to change",
            0))
        cdlabel3 = self.builder.get_object("cdr-label3")
        cdlabel3.set_label(ngettext(
            "Cancel this change",
            "Cancel this change",
            0))
        cdlabel4 = self.builder.get_object("cdr-label4")
        cdlabel3.set_label(ngettext(
            "Only this event",
            "Only this event",
            0))
        cdlabel4 = self.builder.get_object("cdr-label5")
        cdlabel3.set_label(ngettext(
            "All events",
            "All events",
            0))
        cdlabel4 = self.builder.get_object("cdr-label6")
        cdlabel3.set_label(ngettext(
            "Following events",
            "Following events",
            0))

        editevent_dialog = self.builder.get_object("confirm_editevent")
        editevent_dialog.resize(1, 1)
        cancel_button = self.builder.get_object("cancel")
        cancel_button.grab_focus()

        if editevent_dialog.run() != 1:
            pass
        editevent_dialog.hide()
