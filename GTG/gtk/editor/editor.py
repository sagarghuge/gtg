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
"""
This is the TaskEditor

It's the window you see when you double-click on a Task
The main text widget is a home-made TextView called TaskView (see taskview.py)
The rest is the logic of the widget: date changing widgets, buttons, ...
"""
import time

from gi.repository import Gtk, Gdk, Pango

from GTG import _, ngettext
from GTG.gtk.editor import GnomeConfig
from GTG.gtk.editor.taskview import TaskView
from GTG.core.plugins.engine import PluginEngine
from GTG.core.plugins.api import PluginAPI
from GTG.core.task import Task
from GTG.tools.dates import Date
from GTG.gtk.editor.calendar import GTGCalendar
from GTG.gtk.help import add_help_shortcut
from GTG.gtk.editor.notify_dialog import NotifyCloseUI
import uuid


class TaskEditor(object):

    def __init__(self,
                 requester,
                 vmanager,
                 task,
                 taskconfig=None,
                 thisisnew=False,
                 clipboard=None):
        '''
        req is the requester
        vmanager is the view manager
        taskconfig is a ConfigParser to save infos about tasks
        thisisnew is True when a new task is created and opened
        '''
        self.req = requester
        self.browser_config = self.req.get_config('browser')
        self.vmanager = vmanager
        self.config = taskconfig
        self.time = None
        self.thisisnew = thisisnew
        self.clipboard = clipboard
        self.edit_event = True
        self.clone_task = None
        self.builder = Gtk.Builder()
        self.builder.add_from_file(GnomeConfig.EDITOR_UI_FILE)
        self.donebutton = self.builder.get_object("mark_as_done_editor")
        self.dismissbutton = self.builder.get_object("dismiss_editor")
        self.deletebutton = self.builder.get_object("delete_editor")
        self.deletebutton.set_tooltip_text(GnomeConfig.DELETE_TOOLTIP)
        self.subtask_button = self.builder.get_object("insert_subtask")
        self.subtask_button.set_tooltip_text(GnomeConfig.SUBTASK_TOOLTIP)
        self.inserttag_button = self.builder.get_object("inserttag")
        self.inserttag_button.set_tooltip_text(GnomeConfig.TAG_TOOLTIP)
        self.open_parents_button = self.builder.get_object("open_parents")
        self.repeattask_button = self.builder.get_object("toggle_repeattask")
        self.repeattask_button.set_tooltip_text(
            GnomeConfig.REPEAT_TASK_TOOLTIP)

        # Get spinbutton and set ranges
        self.endafter_spinbutton = self.builder.get_object(
            "endafter_spinbutton")
        self.every_spinbutton = self.builder.get_object(
            "every_spinbutton")
        self.every_spinbutton.set_range(1, 30)
        self.every_spinbutton.set_wrap(True)
        # TODO Decide the range MAX range for endafter_spinbutton

        # Create our dictionary and connect it
        dic = {
            "mark_as_done_clicked": self.change_status,
            "on_dismiss": self.dismiss,
            "delete_clicked": self.delete_task,
            "on_duedate_pressed": lambda w: self.on_date_pressed(
                w, GTGCalendar.DATE_KIND_DUE),
            "on_startdate_pressed": lambda w: self.on_date_pressed(
                w, GTGCalendar.DATE_KIND_START),
            "on_closeddate_pressed": lambda w: self.on_date_pressed(
                w, GTGCalendar.DATE_KIND_CLOSED),
            "on_endondate_pressed": lambda w: self.on_date_pressed(
                w, GTGCalendar.DATE_KIND_ENDON),
            "close_clicked": self.close,
            "duedate_changed": lambda w: self.date_changed(
                w, GTGCalendar.DATE_KIND_DUE),
            "duedate_focus_out": lambda w, e: self.date_focus_out(
                w, e, GTGCalendar.DATE_KIND_DUE),
            "startingdate_changed": lambda w: self.date_changed(
                w, GTGCalendar.DATE_KIND_START),
            "startdate_focus_out": lambda w, e: self.date_focus_out(
                w, e, GTGCalendar.DATE_KIND_START),
            "closeddate_changed": lambda w: self.date_changed(
                w, GTGCalendar.DATE_KIND_CLOSED),
            "closeddate_focus_out": lambda w, e: self.date_focus_out(
                w, e, GTGCalendar.DATE_KIND_CLOSED),
            "endondate_changed": lambda w: self.date_changed(
                w, GTGCalendar.DATE_KIND_ENDON),
            "endondate_focus_out": lambda w, e: self.date_focus_out(
                w, e, GTGCalendar.DATE_KIND_ENDON),
            "on_insert_subtask_clicked": self.insert_subtask,
            "on_inserttag_clicked": self.inserttag_clicked,
            "on_repeattask_toggled": self.repeattask_toggled,
            "on_repeats_combobox_value_changed":
            self.repeats_combobox_value_changed,
            "on_end_combobox_value_changed": self.end_combobox_value_changed,
            "on_every_spinbutton_value_changed":
            self.every_spinbutton_value_changed,
            "on_endafter_spinbutton_value_changed":
            self.endafter_spinbutton_value_changed,
            "on_checkbuttons_toggled": self.weekdays_toggled,
            "on_days_combobox_changed": self.days_combobox_value_changed,
            "on_sequence_combobox_changed":
            self.sequence_combobox_value_changed,
            "on_all_instances_toggled": self.all_instance_toggled,
            "on_current_instance_toggled": self.current_instance_toggled,
            "on_open_parent_clicked": self.open_parent_clicked,
            "on_move": self.on_move,
        }
        self.builder.connect_signals(dic)
        self.window = self.builder.get_object("TaskEditor")
        # Removing the Normal textview to replace it by our own
        # So don't try to change anything with glade, this is a home-made
        # widget
        textview = self.builder.get_object("textview")
        scrolled = self.builder.get_object("scrolledtask")
        scrolled.remove(textview)
        self.textview = TaskView(self.req, self.clipboard)
        self.textview.show()
        self.textview.set_subtask_callback(self.new_subtask)
        self.textview.open_task_callback(self.vmanager.open_task)
        self.textview.set_left_margin(7)
        self.textview.set_right_margin(5)
        scrolled.add(self.textview)
        conf_font_value = self.browser_config.get("font_name")
        if conf_font_value != "":
            self.textview.override_font(Pango.FontDescription(conf_font_value))
        # Voila! it's done
        self.calendar = GTGCalendar()
        self.calendar.set_transient_for(self.window)
        self.calendar.set_decorated(False)
        self.duedate_widget = self.builder.get_object("duedate_entry")
        self.startdate_widget = self.builder.get_object("startdate_entry")
        self.closeddate_widget = self.builder.get_object("closeddate_entry")
        self.endondate_widget = self.builder.get_object("endondate_entry")
        self.dayleft_label = self.builder.get_object("dayleft")
        self.tasksidebar = self.builder.get_object("tasksidebar")
        # Define accelerator keys
        self.init_accelerators()

        self.task = task
        tags = task.get_tags()
        self.textview.subtasks_callback(task.get_children)
        self.textview.removesubtask_callback(task.remove_child)
        self.textview.set_get_tagslist_callback(task.get_tags_name)
        self.textview.set_add_tag_callback(task.add_tag)
        self.textview.set_remove_tag_callback(task.remove_tag)
        self.textview.save_task_callback(self.light_save)

        texte = self.task.get_text()
        title = self.task.get_title()
        # the first line is the title
        self.textview.set_text("%s\n" % title)
        # we insert the rest of the task
        if texte:
            self.textview.insert("%s" % texte)
        else:
            # If not text, we insert tags
            if tags:
                for t in tags:
                    self.textview.insert_text("%s, " % t.get_name())
                self.textview.insert_text("\n")
            # If we don't have text, we still need to insert subtasks if any
            subtasks = task.get_children()
            if subtasks:
                self.textview.insert_subtasks(subtasks)
        # We select the title if it's a new task
        if thisisnew:
            self.textview.select_title()
        else:
            self.task.set_to_keep()
        self.textview.modified(full=True)
        self.window.connect("destroy", self.destruction)
        self.window.connect("delete-event", self.quit)
        self.calendar.connect("date-changed", self.on_date_changed)

        # plugins
        self.pengine = PluginEngine()
        self.plugin_api = PluginAPI(self.req, self.vmanager, self)
        self.pengine.register_api(self.plugin_api)
        self.pengine.onTaskLoad(self.plugin_api)

        # Putting the refresh callback at the end make the start a lot faster
        self.textview.refresh_callback(self.refresh_editor)
        self.refresh_editor()
        self.textview.grab_focus()

        # restoring size and position, spatial tasks
        if self.config is not None:
            tid = self.task.get_id()
            if self.config.has_section(tid):
                if self.config.has_option(tid, "position"):
                    pos_x, pos_y = self.config.get(tid, "position")
                    self.move(int(pos_x), int(pos_y))
                if self.config.has_option(tid, "size"):
                    width, height = self.config.get(tid, "size")
                    self.window.resize(int(width), int(height))

        self.textview.set_editable(True)
        self.window.show()

        #Set initial values of recurring task
        self.init_recurring_task_attributes()

        # check if task is recurring and opened for editing then
        # as we follow 'past can not be changed' rule, we only
        # allow user to affect the current or future instances
        # which task has the recurring rule, By default we set
        # all instances option
        if self.task.get_is_recurring() == 'True':
            if not self.thisisnew and \
                    self.task.get_due_date() >= self.task.get_current_date():
                self.builder.get_object("box16").show()
                self.builder.get_object("all_instances").set_active(True)
                self.clone_recurring_task()
            self.repeattask_button.set_active(True)
            self.read_recurrence_info()

    def clone_recurring_task(self):
        self.clone_task = self.req.new_task()
        self.req.clone_recurring_task(self.clone_task, self.task)
        self.clone_task.set_status(self.clone_task.STA_HIDDEN)

    def init_recurring_task_attributes(self):
        """
        Need to initialize the recurring task attribute
        to some initial value so that if user didn't change
        the value in widget we pick up the active values
        """
        if self.task.repeats is None:
            self.task.repeats = self.builder.get_object(
                "repeats_combobox").get_active_text()
        if self.task.recur_frequency is None:
            self.task.recur_frequency = \
                self.every_spinbutton.get_value_as_int()
        if self.task.onthe is None:
            self.task.onthe = self.builder.get_object(
                "sequence_combobox").get_active_text()
        if self.task.onday is None:
            self.task.onday = self.builder.get_object(
                "days_combobox").get_active_text()
        if self.task.recur_days is None:
            self.task.recur_days = self.weekdays_summary()
        if self.task.endson is None:
            self.task.endson = self.builder.get_object(
                "end_combobox").get_active_text().lower()
        if self.task.occurrences == 0:
            self.task.occurrences = \
                self.endafter_spinbutton.get_value_as_int()

    # Define accelerator-keys for this dialog
    # TODO: undo/redo
    def init_accelerators(self):
        agr = Gtk.AccelGroup()
        self.window.add_accel_group(agr)

        # Escape and Ctrl-W close the dialog. It's faster to call close
        # directly, rather than use the close button widget
        key, modifier = Gtk.accelerator_parse('Escape')
        agr.connect(key, modifier, Gtk.AccelFlags.VISIBLE, self.close)

        key, modifier = Gtk.accelerator_parse('<Control>w')
        agr.connect(key, modifier, Gtk.AccelFlags.VISIBLE, self.close)

        # F1 shows help
        add_help_shortcut(self.window, "editor")

        # Ctrl-N creates a new task
        key, modifier = Gtk.accelerator_parse('<Control>n')
        agr.connect(key, modifier, Gtk.AccelFlags.VISIBLE, self.new_task)

        # Ctrl-Shift-N creates a new subtask
        insert_subtask = self.builder.get_object("insert_subtask")
        key, mod = Gtk.accelerator_parse("<Control><Shift>n")
        insert_subtask.add_accelerator('clicked', agr, key, mod,
                                       Gtk.AccelFlags.VISIBLE)

        # Ctrl-D marks task as done
        mark_as_done_editor = self.builder.get_object('mark_as_done_editor')
        key, mod = Gtk.accelerator_parse('<Control>d')
        mark_as_done_editor.add_accelerator('clicked', agr, key, mod,
                                            Gtk.AccelFlags.VISIBLE)

        # Ctrl-I marks task as dismissed
        dismiss_editor = self.builder.get_object('dismiss_editor')
        key, mod = Gtk.accelerator_parse('<Control>i')
        dismiss_editor.add_accelerator('clicked', agr, key, mod,
                                       Gtk.AccelFlags.VISIBLE)

        # Ctrl+R makes task recurring
        toggle_repeattask = self.builder.get_object("toggle_repeattask")
        key, mod = Gtk.accelerator_parse('<Control>r')
        toggle_repeattask.add_accelerator('clicked', agr, key, mod,
                                          Gtk.AccelFlags.VISIBLE)

    # Can be called at any time to reflect the status of the Task
    # Refresh should never interfere with the TaskView.
    # If a title is passed as a parameter, it will become
    # the new window title. If not, we will look for the task title.
    # Refreshtext is whether or not we should refresh the TaskView
    #(doing it all the time is dangerous if the task is empty)
    def refresh_editor(self, title=None, refreshtext=False):
        if self.window is None:
            return
        to_save = False
        # title of the window
        if title:
            self.window.set_title(title)
            to_save = True
        else:
            self.window.set_title(self.task.get_title())

        status = self.task.get_status()
        dismiss_tooltip = GnomeConfig.MARK_DISMISS_TOOLTIP
        undismiss_tooltip = GnomeConfig.MARK_UNDISMISS_TOOLTIP
        if status == Task.STA_DISMISSED:
            self.donebutton.set_label(GnomeConfig.MARK_DONE)
            self.donebutton.set_tooltip_text(GnomeConfig.MARK_DONE_TOOLTIP)
            self.donebutton.set_icon_name("gtg-task-done")
            self.dismissbutton.set_label(GnomeConfig.MARK_UNDISMISS)
            self.dismissbutton.set_tooltip_text(undismiss_tooltip)
            self.dismissbutton.set_icon_name("gtg-task-undismiss")
        elif status == Task.STA_DONE:
            self.donebutton.set_label(GnomeConfig.MARK_UNDONE)
            self.donebutton.set_tooltip_text(GnomeConfig.MARK_UNDONE_TOOLTIP)
            self.donebutton.set_icon_name("gtg-task-undone")
            self.dismissbutton.set_label(GnomeConfig.MARK_DISMISS)
            self.dismissbutton.set_tooltip_text(dismiss_tooltip)
            self.dismissbutton.set_icon_name("gtg-task-dismiss")
        else:
            self.donebutton.set_label(GnomeConfig.MARK_DONE)
            self.donebutton.set_tooltip_text(GnomeConfig.MARK_DONE_TOOLTIP)
            self.donebutton.set_icon_name("gtg-task-done")
            self.dismissbutton.set_label(GnomeConfig.MARK_DISMISS)
            self.dismissbutton.set_tooltip_text(dismiss_tooltip)
            self.dismissbutton.set_icon_name("gtg-task-dismiss")
        self.donebutton.show()
        self.tasksidebar.show()

        # Refreshing the status bar labels and date boxes
        if status in [Task.STA_DISMISSED, Task.STA_DONE]:
            self.builder.get_object("label2").hide()
            self.builder.get_object("box1").hide()
            self.builder.get_object("label4").show()
            self.builder.get_object("box4").show()
        else:
            self.builder.get_object("label4").hide()
            self.builder.get_object("box4").hide()
            self.builder.get_object("label2").show()
            self.builder.get_object("box1").show()

        # refreshing the start date field
        startdate = self.task.get_start_date()
        self.refresh_date_field(startdate, self.startdate_widget)

        # refreshing the due date field
        duedate = self.task.get_due_date()
        self.refresh_date_field(duedate, self.duedate_widget)

        # refreshing the endon date field
        endondate = self.task.get_endon_date()
        self.refresh_date_field(endondate, self.endondate_widget)

        # refreshing the closed date field
        closeddate = self.task.get_closed_date()
        self.refresh_date_field(closeddate, self.closeddate_widget)

        # refreshing the day left label
        # If the task is marked as done, we display the delay between the
        # due date and the actual closing date. If the task isn't marked
        # as done, we display the number of days left.
        if status in [Task.STA_DISMISSED, Task.STA_DONE]:
            delay = self.task.get_days_late()
            if delay is None:
                txt = ""
            elif delay == 0:
                txt = "Completed on time"
            elif delay >= 1:
                txt = ngettext("Completed %(days)d day late",
                               "Completed %(days)d days late", delay) % \
                    {'days': delay}
            elif delay <= -1:
                abs_delay = abs(delay)
                txt = ngettext("Completed %(days)d day early",
                               "Completed %(days)d days early", abs_delay) % \
                    {'days': abs_delay}
        else:
            due_date = self.task.get_due_date()
            result = due_date.days_left()
            if due_date.is_fuzzy():
                txt = ""
            elif result > 0:
                txt = ngettext("Due tomorrow!", "%(days)d days left", result) \
                    % {'days': result}
            elif result == 0:
                txt = _("Due today!")
            elif result < 0:
                abs_result = abs(result)
                txt = ngettext("Due yesterday!", "Was %(days)d days ago",
                               abs_result) % {'days': abs_result}

        style_context = self.window.get_style_context()
        color = style_context.get_color(Gtk.StateFlags.INSENSITIVE).to_color()
        self.dayleft_label.set_markup(
            "<span color='%s'>%s</span>" % (color.to_string(), txt))

        # Refreshing the tag list in the insert tag button
        taglist = self.req.get_used_tags()
        menu = Gtk.Menu()
        tag_count = 0
        for tagname in taglist:
            tag_object = self.req.get_tag(tagname)
            if not tag_object.is_special() and \
                    not self.task.has_tags(tag_list=[tagname]):
                tag_count += 1
                mi = Gtk.MenuItem(label=tagname, use_underline=False)
                mi.connect("activate", self.inserttag, tagname)
                mi.show()
                menu.append(mi)
        if tag_count > 0:
            self.inserttag_button.set_menu(menu)

        # Refreshing the parent list in open_parent_button
        menu = Gtk.Menu()
        parents = self.task.get_parents()
        if len(parents) > 0:
            for parent in self.task.get_parents():
                task = self.req.get_task(parent)
                mi = Gtk.MenuItem(label=task.get_title(), use_underline=False)
                mi.connect("activate", self.open_parent, parent)
                mi.show()
                menu.append(mi)
            self.open_parents_button.set_menu(menu)
        else:
            self.open_parents_button.set_sensitive(False)

        if refreshtext:
            self.textview.modified(refresheditor=False)
        if to_save:
            self.light_save()

    def refresh_date_field(self, date, field):
        try:
            prevdate = Date.parse(field.get_text())
            update_date = date != prevdate
        except ValueError:
            update_date = True
        if update_date:
            field.set_text(str(date))

    def date_changed(self, widget, data):
        try:
            if data == GTGCalendar.DATE_KIND_ENDON:
                parsed_date = Date.parse(widget.get_text())
                if self.startdate_widget.get_text() != "":
                    if Date.parse(self.startdate_widget.get_text()).__gt__(
                            parsed_date):
                        valid = False
                    else:
                        valid = True
                else:
                    valid = True
            else:
                Date.parse(widget.get_text())
                valid = True
        except ValueError:
            valid = False

        if valid:
            # If the date is valid, we write with default color in the widget
            # "none" will set the default color.
            widget.override_color(Gtk.StateType.NORMAL, None)
            widget.override_background_color(Gtk.StateType.NORMAL, None)
        else:
            #We should write in red in the entry if the date is not valid
            text_color = Gdk.RGBA()
            text_color.parse("#F00")
            widget.override_color(Gtk.StateType.NORMAL, text_color)

            bg_color = Gdk.RGBA()
            bg_color.parse("#F88")
            widget.override_background_color(Gtk.StateType.NORMAL, bg_color)

    def date_focus_out(self, widget, event, date_kind):
        try:
            datetoset = Date.parse(widget.get_text())
        except ValueError:
            datetoset = None

        if datetoset is not None:
            if date_kind == GTGCalendar.DATE_KIND_START:
                self.task.set_start_date(datetoset)
            elif date_kind == GTGCalendar.DATE_KIND_DUE:
                self.task.set_due_date(datetoset)
            elif date_kind == GTGCalendar.DATE_KIND_CLOSED:
                self.task.set_closed_date(datetoset)
            elif date_kind == GTGCalendar.DATE_KIND_ENDON:
                self.task.set_due_date(datetoset)
            self.refresh_editor()
            self.update_summary()

    def on_date_pressed(self, widget, date_kind):
        """Called when a date-changing button is clicked."""
        if date_kind == GTGCalendar.DATE_KIND_DUE:
            if not self.task.get_due_date():
                date = self.task.get_start_date()
            else:
                date = self.task.get_due_date()
        elif date_kind == GTGCalendar.DATE_KIND_START:
            date = self.task.get_start_date()
        elif date_kind == GTGCalendar.DATE_KIND_CLOSED:
            date = self.task.get_closed_date()
        if date_kind == GTGCalendar.DATE_KIND_ENDON:
            if not self.task.get_endon_date():
                date = self.task.get_start_date()
            else:
                date = self.task.get_endon_date()
        self.update_summary()
        self.calendar.set_date(date, date_kind)
        # we show the calendar at the right position
        rect = widget.get_allocation()
        result, x, y = widget.get_window().get_origin()
        self.calendar.show_at_position(x + rect.x + rect.width,
                                       y + rect.y)

    def on_date_changed(self, calendar):
        date, date_kind = calendar.get_selected_date()
        if date_kind == GTGCalendar.DATE_KIND_DUE:
            self.task.set_due_date(date)
        elif date_kind == GTGCalendar.DATE_KIND_START:
            self.task.set_start_date(date)
        elif date_kind == GTGCalendar.DATE_KIND_CLOSED:
            self.task.set_closed_date(date)
        elif date_kind == GTGCalendar.DATE_KIND_ENDON:
            self.task.set_endon_date(date)
        self.refresh_editor()
        self.update_summary()

    def close_all_subtasks(self):
        all_subtasks = []

        def trace_subtasks(root):
            for i in root.get_subtasks():
                if i not in all_subtasks:
                    all_subtasks.append(i)
                    trace_subtasks(i)

        trace_subtasks(self.task)

        for task in all_subtasks:
            self.vmanager.close_task(task.get_id())

    def dismiss(self, widget):
        stat = self.task.get_status()
        if stat == Task.STA_DISMISSED:
            self.vmanager.ask_set_task_status(self.task, Task.STA_ACTIVE)
            self.refresh_editor()
        else:
            self.vmanager.ask_set_task_status(self.task, Task.STA_DISMISSED)
            self.close_all_subtasks()
            self.close(None)

    def change_status(self, widget):
        stat = self.task.get_status()
        if stat == Task.STA_DONE:
            self.vmanager.ask_set_task_status(self.task, Task.STA_ACTIVE)
            self.refresh_editor()
        else:
            self.vmanager.ask_set_task_status(self.task, Task.STA_DONE)
            self.close_all_subtasks()
            self.close(None)

    def delete_task(self, widget):
        # this triggers the closing of the window in the view manager
        if self.task.is_new():
#            self.req.delete_task(self.task.get_id())
            self.vmanager.close_task(self.task.get_id())
        else:
            self.vmanager.ask_delete_tasks([self.task.get_id()])

    # Take the title as argument and return the subtask ID
    def new_subtask(self, title=None, tid=None):
        if tid:
            self.task.add_child(tid)
        elif title:
            subt = self.task.new_subtask()
            subt.set_title(title)
            tid = subt.get_id()
        return tid

    # Create a new task
    def new_task(self, *args):
        task = self.req.new_task(newtask=True)
        task_id = task.get_id()
        self.vmanager.open_task(task_id)

    def insert_subtask(self, widget):
        self.textview.insert_newtask()
        self.textview.grab_focus()

    def inserttag_clicked(self, widget):
        itera = self.textview.get_insert()
        if itera.starts_line():
            self.textview.insert_text("@", itera)
        else:
            self.textview.insert_text(" @", itera)
        self.textview.grab_focus()

    def read_recurrence_info(self):
        # Read the recurrence info and enabled the widgets with
        # proper item
        repeat_dict = {self.task.REP_DAILY: 0,
                       self.task.REP_WEEKLY: 1,
                       self.task.REP_MONTHLY: 2,
                       self.task.REP_YEARLY: 3}
        weekdays_dict = {"Sunday": 0,
                         "Monday": 1,
                         "Tuesday": 2,
                         "Wednesday": 3,
                         "Thursday": 4,
                         "Friday": 5,
                         "Saturday": 6}
        seq_dict = {"First": 0, "Second": 1, "Third": 2,
                    "Fourth": 3, "Fifth": 4, "Last": 5}

        self.builder.get_object(
            "repeats_combobox").set_active(repeat_dict[self.task.repeats])
        self.every_spinbutton.set_value(int(self.task.recur_frequency))

        if self.task.endson == self.task.REC_DATE:
            self.builder.get_object(
                "end_combobox").set_active(1)
            self.builder.get_object(
                "endondate_entry").set_text(str(self.task.get_endon_date()))
        elif self.task.endson == self.task.REC_NEVER:
            self.builder.get_object(
                "end_combobox").set_active(2)
        else:
            self.builder.get_object(
                "end_combobox").set_active(0)
            self.endafter_spinbutton.set_value(int(self.task.occurrences))

        if self.task.repeats == self.task.REP_WEEKLY:
            if self.task.recur_days.__contains__(","):
                daysL = self.task.recur_days.split(",")
                for days in daysL:
                    checkbutton_no = weekdays_dict[days.strip()] + 1
                    self.builder.get_object(
                        "checkbutton"+str(checkbutton_no)).set_active(True)
            else:
                if self.task.recur_days == "all days":
                    for key, val in weekdays_dict.items():
                        self.builder.get_object(
                            "checkbutton"+str(val+1)).set_active(True)
                else:
                    checkbutton_no = weekdays_dict[self.task.recur_days] + 1
                    self.builder.get_object(
                        "checkbutton"+str(checkbutton_no)).set_active(True)

        elif self.task.repeats == self.task.REP_MONTHLY:
            self.builder.get_object(
                "days_combobox").set_active(weekdays_dict[self.task.onday])
            self.builder.get_object(
                "sequence_combobox").set_active(seq_dict[self.task.onthe])

    def update_summary(self):
        """
        Method shows the summary of recurrence
        """
        summary = None
        repeats = self.builder.get_object(
            "repeats_combobox").get_active_text()
        frequency = self.every_spinbutton.get_value_as_int()
        end_txt = self.builder.get_object(
            "end_combobox").get_active_text()

        if frequency <= 1:
            if repeats == self.task.REP_DAILY:
                summary = repeats
            elif repeats == self.task.REP_YEARLY:
                if self.startdate_widget.get_text() == "":
                    summary = "Annually on " + str(
                        self.task.get_current_date())
                else:
                    summary = "Annually on " + self.startdate_widget.get_text()
            else:
                summary = repeats
        else:
            summary = "Every " + str(frequency) + " " +\
                self.builder.get_object(
                    "common_label").get_text()

        if repeats == self.task.REP_WEEKLY:
            weekdays = self.weekdays_summary()
            summary += " on " + weekdays
        elif repeats == self.task.REP_MONTHLY:
            sequence = self.builder.get_object(
                "sequence_combobox").get_active_text()
            days = self.builder.get_object(
                "days_combobox").get_active_text()
            summary += " on " + sequence + " " + days

        if end_txt == "After":
            occurrences = self.endafter_spinbutton.get_value_as_int()
            if occurrences > 1:
                summary = summary + ", " + str(occurrences) + " times"
        elif end_txt == "On":
            endondate = self.builder.get_object(
                "endondate_entry").get_text()
            if endondate != "":
                summary = summary + ", until " + str(endondate)

        self.builder.get_object(
            "show_summary_label").set_text(summary)

    def all_instance_toggled(self, widget):
        self.edit_event = True

    def current_instance_toggled(self, widget):
        self.edit_event = False

    def weekdays_summary(self):
        """
        Return summary of weekdays which are selected
        """
        weekdays = ["Sunday", "Monday", "Tuesday",
                    "Wednesday", "Thursday", "Friday",
                    "Saturday"]
        days = []
        days_summary = ""

        if self.builder.get_object("checkbutton1").get_active():
            days += [weekdays[0]]
        if self.builder.get_object("checkbutton2").get_active():
            days += [weekdays[1]]
        if self.builder.get_object("checkbutton3").get_active():
            days += [weekdays[2]]
        if self.builder.get_object("checkbutton4").get_active():
            days += [weekdays[3]]
        if self.builder.get_object("checkbutton5").get_active():
            days += [weekdays[4]]
        if self.builder.get_object("checkbutton6").get_active():
            days += [weekdays[5]]
        if self.builder.get_object("checkbutton7").get_active():
            days += [weekdays[6]]

        length = len(days)

        if length == 0:
            #TODO select the current day
            # Toggle the checkbutton according to current day
            # and if no value is selected then by default current day
            # toggled
            cur_day = time.strftime('%A')
            index = weekdays.index(cur_day) + 1
            self.builder.get_object("checkbutton"+str(index)).set_active(True)
            days_summary = cur_day
        elif length == 1:
            days_summary = days[0]
        elif length > 1:
            if length == 7:
                days_summary = "all days"
            else:
                for day in days[:-1]:
                    days_summary += day + ", "
                days_summary += days[-1]

        return days_summary

    def weekdays_toggled(self, widget):
        self.task.recur_days = self.weekdays_summary()
        self.update_summary()

    def days_combobox_value_changed(self, widget):
        self.task.onday = widget.get_active_text()
        self.update_summary()

    def sequence_combobox_value_changed(self, widget):
        self.task.onthe = widget.get_active_text()
        self.update_summary()

    def end_combobox_value_changed(self, widget):
        index = widget.get_active()
        if index == 0:
            self.builder.get_object("box11").show()
            self.endafter_spinbutton.show()
            self.builder.get_object("endonbox").hide()
            self.builder.get_object("occurrence_label").show()
            self.task.endson = self.builder.get_object(
                "occurrence_label").get_text()
        elif index == 1:
            self.builder.get_object("box11").show()
            self.endafter_spinbutton.hide()
            self.builder.get_object("endonbox").show()
            self.builder.get_object("occurrence_label").hide()
            self.task.endson = self.task.REC_DATE
        elif index == 2:
            self.builder.get_object("box11").hide()
            self.task.endson = self.task.REC_NEVER
        self.update_summary()

    def every_spinbutton_value_changed(self, widget):
        label = self.builder.get_object("common_label")
        self.task.recur_frequency = self.every_spinbutton.get_value_as_int()
        self.set_label_value(label, self.every_spinbutton)
        self.update_summary()

    def endafter_spinbutton_value_changed(self, widget):
        label = self.builder.get_object("occurrence_label")
        self.task.occurrences = self.endafter_spinbutton.get_value_as_int()
        self.task.left_occurrences = self.task.occurrences - 1
        self.set_label_value(label, self.endafter_spinbutton)
        self.task.endson = self.builder.get_object(
            "occurrence_label").get_text()
        self.update_summary()

    def set_label_value(self, label, spinbutton):
        """
        @param label: lable which needs to be processed
        @param spinbutton: spinbutton object
        Makes label plural/singular depend on the spinbutton value
        """
        label_text = label.get_text()
        if spinbutton.get_value_as_int() > 1:
            if label_text.__contains__("s"):
                return
            label.set_text(label_text+"s")
        else:
            label.set_text(label_text.strip("s"))

    def repeats_combobox_value_changed(self, widget):
        index = widget.get_active()
        self.task.repeats = widget.get_active_text()
        label = self.builder.get_object("common_label")

        if index == 0:
            self.builder.get_object("box8").hide()
            self.builder.get_object("box13").hide()
            self.builder.get_object("common_label").set_text("day")
        elif index == 1:
            self.builder.get_object("box8").show()
            self.builder.get_object("box13").hide()
            self.builder.get_object("common_label").set_text("week")
        elif index == 2:
            self.builder.get_object("box8").hide()
            self.builder.get_object("box13").show()
            self.builder.get_object("common_label").set_text("month")
        elif index == 3:
            self.builder.get_object("box8").hide()
            self.builder.get_object("box13").hide()
            self.builder.get_object("common_label").set_text("year")

        self.set_label_value(label, self.every_spinbutton)
        self.update_summary()

    def repeattask_toggled(self, widget):
        if widget.get_active():
            if self.task.is_recurring is None:
                self.task.rid = str(uuid.uuid4())
            self.task.is_recurring = 'True'
            self.builder.get_object("repeattaskbox").show()
            #self.builder.get_object("end_combobox").set_row_span_column(0)
            self.builder.get_object("box6").show()
            self.builder.get_object("box12").show()
            self.update_summary()
        else:
            self.task.is_recurring = 'False'
            self.task.rid = None
            self.builder.get_object("repeattaskbox").hide()
            self.builder.get_object("box6").hide()
            self.builder.get_object("box8").hide()
            self.builder.get_object("box12").hide()

    def inserttag(self, widget, tag):
        self.textview.insert_tags([tag])
        self.textview.grab_focus()

    def open_parent_clicked(self, widget):
        self.vmanager.open_task(self.task.get_parents()[0])

    # On click handler for open_parent_button's menu items
    def open_parent(self, widget, tid):
        self.vmanager.open_task(tid)

    def save(self):
        self.task.set_title(self.textview.get_title())
        self.task.set_text(self.textview.get_text())
        self.task.sync()
        if self.config is not None:
            self.config.save()
        self.time = time.time()
    # light_save save the task without refreshing every 30seconds
    # We will reduce the time when the get_text will be in another thread

    def light_save(self):
        # if self.time is none, we never called any save
        if self.time:
            diff = time.time() - self.time
            tosave = diff > GnomeConfig.SAVETIME
        else:
            # we don't want to save a task while opening it
            tosave = self.textview.get_editable()
            diff = None
        if tosave:
            self.save()

    # This will bring the Task Editor to front
    def present(self):
        self.window.present()

    def move(self, x, y):
        try:
            xx = int(x)
            yy = int(y)
            self.window.move(xx, yy)
        except:
            pass

    def get_position(self):
        return self.window.get_position()

    def on_move(self, widget, event):
        # saving the position
        if self.config is not None:
            tid = self.task.get_id()
            if not self.config.has_section(tid):
                self.config.add_section(tid)
            self.config.set(tid, "position", self.get_position())
            self.config.set(tid, "size", self.window.get_size())

    # We define dummy variable for when close is called from a callback
    def close(self, window=None, a=None, b=None, c=None):

        # We should also destroy the whole taskeditor object.
        if self.window:
            self.window.destroy()
            self.window = None

    # The destroy signal is linked to the "close" button. So if we call
    # destroy in the close function, this will cause the close to be called
    # twice
    # To solve that, close will just call "destroy" and the destroy signal
    # Will be linked to this destruction method that will save the task
    def destruction(self, a=None):
        # Save should be also called when buffer is modified
        self.pengine.onTaskClose(self.plugin_api)
        self.pengine.remove_api(self.plugin_api)
        tid = self.task.get_id()
        if self.task.is_new():
            self.req.delete_task(tid)
        else:
            self.save()
            for i in self.task.get_subtasks():
                if i:
                    i.set_to_keep()
        self.vmanager.close_task(tid)
        if not self.task.has_parent():
            if self.task.is_recurring == 'True':
                if self.task.get_days_left() < 0:
                    self.task.check_overdue_tasks()
                    self.task.sync()

    def edit_instances(self):
        # If task is actually modified set_modify_task to true
        # if all_occurrences == True then simply delete a clone task
        # as the future instances gets created according to current task
        # if current_occurrnece is True then set it to normal task
        # and make a clone task as recurring task(future instances should
        # get created depend on the past task before making changes)
        modify_list = self.check_modified()
        if any(modify_list):
            self.task.set_modify_task("True")
            if self.edit_event:
                self.req.delete_task(self.clone_task.get_id())
            else:
                self.task.reset_to_normal_task()
                self.clone_task.set_status(self.clone_task.STA_ACTIVE)
        else:
            self.req.delete_task(self.clone_task.get_id())

    def check_modified(self):
        """
        Return list which contains actual attribute changed
        check across the cloned task
        """
        modify_list = list()
        if self.clone_task.get_title() != self.task.get_title():
            modify_list.append("get_title")
        if self.clone_task.get_text() != self.task.get_text():
            modify_list.append("get_text")
        if self.clone_task.get_start_date() != self.task.get_start_date():
            modify_list.append("get_start_date")
        if self.clone_task.get_due_date() != self.task.get_due_date():
            modify_list.append("get_due_date")
        if self.clone_task.get_endon_date().__ne__(self.task.get_endon_date()):
            modify_list.append("get_endon_date")
        if self.clone_task.get_recurrence_repeats() != \
                self.task.get_recurrence_repeats():
            modify_list.append("get_recurrence_repeats")
        if self.clone_task.get_recurrence_frequency() != \
                self.task.get_recurrence_frequency():
            modify_list.append("get_recurrence_frequency")
        if self.clone_task.get_recurrence_onthe() != \
                self.task.get_recurrence_onthe():
            modify_list.append("get_recurrence_onthe")
        if self.clone_task.get_recurrence_onday() != \
                self.task.get_recurrence_onday():
            modify_list.append("get_recurrence_onday")
        if self.clone_task.get_recurrence_endson() != \
                self.task.get_recurrence_endson():
            modify_list.append("get_recurrence_endson")
        if self.clone_task.get_recurrence_days() != \
                self.task.get_recurrence_days():
            modify_list.append("get_recurrence_days")

        return modify_list

    def quit(self, widget, data=None):
        # Before closing the taskbrowser check if due date is set
        # or if not then notify user to set it
        if self.task.is_recurring == 'True':
            if not self.thisisnew:
                if self.clone_task is None:
                    self.clone_recurring_task()
                self.edit_instances()
            if self.duedate_widget.get_text() == "":
                notify_dialog = NotifyCloseUI()
                notify_dialog.notifyclose()
                return True

    def get_builder(self):
        return self.builder

    def get_task(self):
        return self.task

    def get_textview(self):
        return self.textview

    def get_window(self):
        return self.window

# -----------------------------------------------------------------------------
