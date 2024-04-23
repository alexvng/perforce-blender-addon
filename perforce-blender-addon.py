from bpy.props import (StringProperty, PointerProperty, BoolProperty)
from bpy.types import Operator
from re import split
import subprocess
import ctypes
import os
import bpy
import platform

bl_info = {
    "name": "Perforce Integration Add-on",
    "author": "Alex Vuong",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "location": "N-panel in 3D viewport",
    "category": "Generic"
}


def escape_filepath_spaces(path):
    return '"'+path+'"'


class PerforceTracking(bpy.types.PropertyGroup):
    p4IsInstalled: BoolProperty(
        name="Perforce is installed",
        default=True
    )
    insideWorkspace: BoolProperty(
        name="In a Perforce workspace",
        default=True
    )
    untracked: BoolProperty(
        name="File is untracked",
        default=False
    )
    otherOpen: BoolProperty(
        name="Someone else has file opened",
        default=False
    )
    isAdd: BoolProperty(
        name="File is marked for add locally",
        default=False
    )
    isEdit: BoolProperty(
        name="File is opened for edit locally",
        default=False
    )
    outOfDate: BoolProperty(
        name="File is out of date",
        default=False
    )
    commit_message: StringProperty(
        name="Changelog",
        description="Briefly describe what you changed in this file",
        default="Default message",
        options={'SKIP_SAVE'}
    )


class P4_OT_check_file_status(bpy.types.Operator):
    bl_label = "Status check"
    bl_idname = "p4.check_file_status"
    bl_description = "Check this file's status in the Perforce database"

    @classmethod
    def poll(cls, context):
        wm = context.window_manager
        if not wm.p4_tracking.insideWorkspace:
            cls.poll_message_set(
                "This is not a Perforce workspace.\nIf you cannot save, go to the Unlock panel to unlock this file.")
            return False
        return True

    def execute(self, context):
        wm = context.window_manager
        p4 = wm.p4_tracking
        p4.insideWorkspace = True
        p4.untracked = False
        p4.otherOpen = False
        p4.isAdd = False
        p4.isEdit = False
        p4.outOfDate = False
        p4.commit_message = "Default message"
        fstat = run_p4_command(
            "fstat", escape_filepath_spaces(bpy.data.filepath))
        print(fstat)
        wm.p4_tracking.untracked = fstat.find("no such file") != -1
        wm.p4_tracking.insideWorkspace = not (
            fstat.find("not under client's root") != -1)
        wm.p4_tracking.p4IsInstalled = not (
            fstat.find("is not recognized") != -1)

        if not wm.p4_tracking.p4IsInstalled:
            show_panel_helper(
                "Perforce is not installed.\nIf you cannot save, go to the Unlock panel to unlock this file.")
            wm.p4_tracking.insideWorkspace = False
            return {'FINISHED'}
        elif not wm.p4_tracking.insideWorkspace:
            show_panel_helper(
                "This file is not in a Perforce workspace.\nMove it to a folder in the Perforce workspace to use this addon.")
            return {'FINISHED'}
        elif wm.p4_tracking.untracked:
            pass
        else:
            arr = fstat.split('...')
            arr = [a.strip() for a in arr if a]
            fstat_dict = {}
            for a in arr:
                b = a.split(' ')
                fstat_dict[b[0]] = b[1:]

            if "action" in fstat_dict:
                wm.p4_tracking.isAdd = fstat_dict["action"] == ['add']
                wm.p4_tracking.isEdit = fstat_dict["action"] == ['edit']
            if "haveRev" in fstat_dict:
                haveRev = int(fstat_dict["haveRev"][0])
                headRev = int(fstat_dict["headRev"][0])
                if haveRev < headRev:
                    wm.p4_tracking.outOfDate = True
            wm.p4_tracking.otherOpen = fstat.find("otherOpen") != -1
            wm.p4_tracking.untracked = False

            print(fstat + " DEBUG")

        if wm.p4_tracking.untracked:
            show_panel_helper(
                "This file is not registered on the server.\nIt needs to be marked for upload.\nProceed to step 2.")
        elif wm.p4_tracking.outOfDate:
            show_panel_helper(
                "This file is out of date!\n\"Download updates\", then restart Blender.")
        elif wm.p4_tracking.otherOpen:
            show_panel_helper(
                "This file is being edited by someone else!\nYou cannot edit it until they are done.\nOpen P4V to see more details.")
        elif wm.p4_tracking.isAdd:
            show_panel_helper(
                "You created this file, and it isn't uploaded onto the server.\nUpload this file with Step 4 when ready.")
        elif wm.p4_tracking.isEdit:
            show_panel_helper(
                "You have previously reserved this file for editing.\nYou are safe to edit this file, and can upload your changes in Step 4.")
        else:
            show_panel_helper(
                "This file is not reserved by anyone.\nIf you would like to edit it, proceed to Step 3.")

        return {'FINISHED'}


class P4_OT_sync_all(bpy.types.Operator):
    bl_label = "1. Download updates (may lag)"
    bl_idname = "p4.sync_all"
    bl_description = "Download new and updated files from the Perforce server"

    @classmethod
    def poll(cls, context):
        wm = context.window_manager
        if not wm.p4_tracking.insideWorkspace:
            cls.poll_message_set(
                "This is not a Perforce workspace. Addon is disabled.")
            return False
        return True

    def execute(self, context):
        show_panel_helper(run_p4_command(
            "sync"))
        return {'FINISHED'}


class P4_OT_reload_file(bpy.types.Operator):
    bl_label = "2. Reload (erases unsaved changes)"
    bl_description = "Load the latest version of this file from Perforce (or do nothing, if already up-to-date.)\nA backup of this file will be stored in this folder as a .blend2 file"
    bl_idname = "p4.reload_file"
    bl_options = {'INTERNAL'}

    @classmethod
    def poll(cls, context):
        wm = context.window_manager
        if wm.p4_tracking.untracked or wm.p4_tracking.isAdd or wm.p4_tracking.isEdit:
            cls.poll_message_set("No need to reload - you are editing the latest version.")
            return False
        if not wm.p4_tracking.insideWorkspace:
            cls.poll_message_set(
                "This is not a Perforce workspace. Addon is disabled.")
            return False
        else:
            return True

    def execute(self, context):
        bpy.ops.wm.save_as_mainfile(
            copy=True, filepath=bpy.data.filepath+"2", check_existing=False)
        bpy.ops.wm.revert_mainfile()
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)


class P4_OT_manual_unlock(bpy.types.Operator):
    bl_label = "Fix un-save-able file"
    bl_description = "If this file cannot be saved (error \"is not writable\"),\nuse this button to enable saving"
    bl_idname = "p4.manual_unlock"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        cmd = "attrib -R " + escape_filepath_spaces(bpy.data.filepath)
        val = os.system(cmd)
        if not val:
            show_panel_helper("File should be unlocked, try saving.")
            return {'FINISHED'}
        else:
            show_panel_helper("An error occurred:\n" + os.popen(cmd).read())
            return {'CANCELLED'}


class P4_OT_overwrite_local_changes(bpy.types.Operator):
    bl_label = "1. Restore last uploaded version"
    bl_description = "DISCARD ALL CHANGES to this file since your last upload.\nA backup copy will be stored in this folder as a .blend2 file"
    bl_idname = "p4.overwrite_local_changes"
    bl_options = {'INTERNAL'}

    @classmethod
    def poll(cls, context):
        wm = context.window_manager
        if not wm.p4_tracking.insideWorkspace:
            cls.poll_message_set(
                "This is not a Perforce workspace. Addon is disabled.")
            return False
        return True

    def execute(self, context):
        bpy.ops.wm.save_as_mainfile(
            copy=True, filepath=bpy.data.filepath+"2", check_existing=False)
        print(run_p4_command("revert", escape_filepath_spaces(bpy.data.filepath)))
        context.window_manager.p4_tracking.commit_message = "Default message"
        show_panel_helper(
            f"All changes since last backup have been DISCARDED.\nA single backup has been saved to this folder as:\n{bpy.data.filepath+'2'}")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)


class P4_OT_release_edit_lock(bpy.types.Operator):
    bl_label = "3. Release editing lock"
    bl_description = "Forfeit your edit lock (reservation) on this file,\nallowing other team members to edit it"
    bl_idname = "p4.release_edit_lock"
    bl_options = {'INTERNAL'}

    @classmethod
    def poll(cls, context):
        wm = context.window_manager
        if not wm.p4_tracking.insideWorkspace:
            cls.poll_message_set(
                "This is not a Perforce workspace. Addon is disabled.")
            return False
        return True

    def execute(self, context):
        context.window_manager.p4_tracking.commit_message = "Default message"
        show_panel_helper(
            "Your edit lock (reservation) has been released.\nOther team members can now edit this file.")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)


class P4_OT_add_file(bpy.types.Operator):
    bl_label = "Mark this file for future upload"
    bl_idname = "p4.add_file"
    bl_description = "Mark this file to be uploaded to Perforce in Step 4"

    @classmethod
    def poll(cls, context):
        wm = context.window_manager
        if not wm.p4_tracking.insideWorkspace:
            cls.poll_message_set(
                "This is not a Perforce workspace. Addon is disabled.")
            return False
        if wm.p4_tracking.untracked:
            return True
        elif wm.p4_tracking.isAdd:
            cls.poll_message_set("This file is already marked for add.")
            return False
        else:
            cls.poll_message_set(
                "File is already tracked in server. Skip this step.")
            return False

    def execute(self, context):
        output_str = run_p4_command(
            "add", escape_filepath_spaces(bpy.data.filepath))
        if output_str.find("opened for add") != -1:
            show_panel_helper(
                "Success: File is marked for add. Upload in Step 4.")
            context.window_manager.p4_tracking.isAdd = True
            context.window_manager.p4_tracking.untracked = False
        else:
            show_panel_helper("Error:\n" + output_str)

        return {'FINISHED'}


class P4_OT_open_p4v(bpy.types.Operator):
    bl_label = "Open P4V program"
    bl_description = "Opens the P4V program, which has more features than this addon."
    bl_idname = "p4.open_p4v"

    def execute(self, context):
        subprocess.Popen("p4v")
        show_panel_helper("Starting P4V, please wait...")
        return {'FINISHED'}


class P4_OT_checkout(bpy.types.Operator):
    bl_label = "Enable editing in this file"
    bl_idname = "p4.checkout"
    bl_description = "Reserve (lock) this file for editing, allowing you to save.\nThis prevents other people from editing this file"

    @classmethod
    def poll(cls, context):
        wm = context.window_manager
        if not wm.p4_tracking.insideWorkspace:
            cls.poll_message_set(
                "This is not a Perforce workspace. Addon is disabled.")
            return False
        if wm.p4_tracking.otherOpen:
            cls.poll_message_set(
                "Someone else has this file reserved. You cannot edit it.")
            return False
        if wm.p4_tracking.outOfDate:
            cls.poll_message_set(
                "This file is out of date.\n\"Sync files from server\" before trying to edit it.")
        if wm.p4_tracking.isAdd:
            cls.poll_message_set(
                "File is marked for add, and does not need an edit lock.")
            return False
        elif wm.p4_tracking.untracked:
            cls.poll_message_set(
                "File is not tracked by server, and cannot be reserved.")
            return False
        elif wm.p4_tracking.isEdit == False:
            return True
        else:
            cls.poll_message_set("File is already enabled for editing.")
            return False

    def execute(self, context):
        run_p4_command("edit", escape_filepath_spaces(bpy.data.filepath))
        show_panel_helper("You have reserved (locked) this file.\nWhile you have this file reserved, only you can edit it.\nTo allow others to edit, upload your changes in Step 4.\nIf you'd like to cancel your lock without uploading, go to\n\"DANGER: Discard all changes\".")
        context.window_manager.p4_tracking.isEdit = True
        return {'FINISHED'}


class P4_OT_submit(bpy.types.Operator):
    bl_label = "2. Upload new version (may lag)"
    bl_idname = "p4.submit"
    bl_description = "Upload a new version of this file to the server.\nYour edit locks will release, allowing others to edit this file"

    @classmethod
    def poll(cls, context):
        wm = context.window_manager
        if not wm.p4_tracking.insideWorkspace:
            cls.poll_message_set(
                "This is not a Perforce workspace. Addon is disabled.")
            return False
        if wm.p4_tracking.outOfDate:
            cls.poll_message_set(
                "This file is out of date and has no changes. Go to Step 1.")
            return False
        if wm.p4_tracking.untracked:
            cls.poll_message_set(
                "This file is not tracked by the server. Go to Step 2.")
            return False
        if wm.p4_tracking.isAdd or wm.p4_tracking.isEdit:
            return True
        # else
        cls.poll_message_set(
            "This file isn't reserved for editing, and can't be saved. Run a status check.")
        return False

    def execute(self, context):
        wm = context.window_manager
        bpy.ops.wm.save_mainfile()
        commit_message = wm.p4_tracking.commit_message
        wm.p4_tracking.commit_message = "Default message"
        output_str = run_p4_command(
            "submit", "-d", '"' + commit_message + '"', escape_filepath_spaces(bpy.data.filepath))
        if output_str.find("submitted") != -1:
            wm.p4_tracking.isEdit = False
            wm.p4_tracking.isAdd = False
        show_panel_helper(output_str)
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)


class P4_OT_popup(bpy.types.Operator):
    bl_label = "Perforce addon message box"
    bl_idname = "p4.debug_popup"

    message: StringProperty(default="empty message")
    icon_type: StringProperty(default="INFO")

    def draw(self, context):
        layout = self.layout
        split_message = split("\n| - ", self.message)
        print(split_message)
        if split_message[-1] == "":
            split_message.pop()
        for i, line in enumerate(split_message):
            if i == 0:
                layout.label(text=line, icon=self.icon_type)
            else:
                layout.label(text=line)

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=500)


class OBJECT_PT_P4UnlockWizard(bpy.types.Panel):
    bl_label = "Manually Unlock Files"
    bl_idname = "OBJECT_PT_P4UnlockWizard"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Perforce"

    @classmethod
    def poll(cls, context):
        wm = context.window_manager
        return not (wm.p4_tracking.p4IsInstalled and wm.p4_tracking.insideWorkspace)

    def draw(self, context):
        layout = self.layout
        # p4_tracking = context.window_manager.p4_tracking
        layout.label(icon='INFO', text="Fix files that can't be saved")
        layout.operator("p4.manual_unlock", icon="UNLOCKED")


class OBJECT_PT_P4Debug(bpy.types.Panel):
    bl_label = "Debug"
    bl_idname = "OBJECT_PT_P4Debug"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Perforce"
    # bl_context = "objectmode"

    @classmethod
    def poll(cls, context):
        return bpy.data.is_saved

    def draw(self, context):
        layout = self.layout
        p4_tracking = context.window_manager.p4_tracking

        row = layout.row()
        row.prop(p4_tracking, "insideWorkspace",
                 emboss=True, text="Inside workspace?")
        row.enabled = False
        row = layout.row()
        row.prop(p4_tracking, "untracked", emboss=True, text="Untracked")
        row.enabled = False
        row = layout.row()
        row.prop(p4_tracking, "isAdd", emboss=True, text="Marked for add")
        row.enabled = False
        row = layout.row()
        row.prop(p4_tracking, "isEdit", emboss=True, text="Marked for edit")
        row.enabled = False
        row = layout.row()
        row.prop(p4_tracking, "otherOpen", emboss=True,
                 text="!! Opened by someone else")
        row.enabled = False
        row = layout.row()
        row.prop(p4_tracking, "outOfDate", emboss=True, text="!! Out of date")
        row.enabled = False
        row = layout.row()
        row.prop(p4_tracking, "p4IsInstalled", emboss=True, text="p4 working?")
        row.enabled = False


class OBJECT_PT_P4Panel(bpy.types.Panel):
    bl_label = "Perforce"
    bl_idname = "OBJECT_PT_P4Panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Perforce"
    # bl_context = "objectmode"

    @classmethod
    def poll(cls, context):
        return bpy.data.is_saved

    def draw(self, context):
        layout = self.layout
        p4_tracking = context.window_manager.p4_tracking

        layout.label(text="Before you start working:")
        layout.operator("p4.sync_all", icon='UV_SYNC_SELECT')
        layout.operator("p4.reload_file", icon='FILE_REFRESH')
        layout.separator()
        layout.label(text="1. Check status of this file")
        layout.operator("p4.check_file_status", icon='INFO')
        layout.separator()
        layout.label(text="2. Track new file on server")
        # add a disable flag here
        layout.operator("p4.add_file", icon='FILE_NEW')
        layout.separator()
        layout.label(text="3. Reserve editing rights")
        layout.operator("p4.checkout", icon='GREASEPENCIL')
        layout.separator()
        layout.label(text="4. Upload changes to server")
        layout.prop(p4_tracking, "commit_message")
        layout.operator("file.pack_all",
                        text="1. Pack resources", icon='FILE_TICK')
        layout.operator("p4.submit", icon='EXPORT')
        layout.separator()
        layout.label(text="DANGER: Discard all changes")
        layout.operator("p4.overwrite_local_changes", icon='ERROR')
        layout.operator("wm.revert_mainfile",
                        text="2. Discard current changes", icon='TRASH')
        layout.operator("p4.release_edit_lock", icon='UNLOCKED')
        layout.separator()
        layout.label(text="Having any issues?")
        layout.operator("p4.open_p4v", icon="FULLSCREEN_ENTER")


def run_p4_command(*args):
    command = "p4 "
    for arg in args:
        command += str(arg) + " "
    command += "2>&1"
    output = os.popen(command).read()
    print(output)
    return output


def show_panel_helper(text):
    bpy.ops.p4.debug_popup('INVOKE_DEFAULT', message=text, icon_type='INFO')
    print(text)


classes = (
    PerforceTracking,
    P4_OT_checkout,
    P4_OT_submit,
    P4_OT_overwrite_local_changes,
    P4_OT_sync_all,
    P4_OT_popup,
    OBJECT_PT_P4Panel,
    P4_OT_add_file,
    P4_OT_open_p4v,
    P4_OT_check_file_status,
    P4_OT_release_edit_lock,
    OBJECT_PT_P4Debug,
    P4_OT_reload_file,
    P4_OT_manual_unlock,
    OBJECT_PT_P4UnlockWizard
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    bpy.types.WindowManager.p4_tracking = PointerProperty(
        type=PerforceTracking)


def unregister():
    wm = bpy.context.window_manager
    if platform.system() == 'Windows' and wm.p4_tracking.insideWorkspace:
        warnOnExit = False
        if wm.p4_tracking.isEdit:
            warnOnExit = True
            windowTitle = "Blender Perforce: File was not uploaded"
            message = """Warning: You are closing a blender file that is still **reserved for editing**.
Your saved changes have NOT been uploaded.

No one else can edit this file until you upload or revert your changes.
Please do this in the Perforce tab in the N-hotkey panel."""

        if wm.p4_tracking.isAdd or wm.p4_tracking.untracked:
            warnOnExit = True
            windowTitle = "Blender Perforce: File is not known to server"
            message = """Note: This file has not been uploaded to Perforce yet.

It is not accessible to other people.
Please upload this file using the Perforce tab, located in the N-hotkey panel."""

        if warnOnExit:
            ctypes.windll.user32.MessageBoxExW(
                None, message, windowTitle, 0x40000)

    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    del bpy.types.WindowManager.p4_tracking


if __name__ == "__main__":
    register()
