from bpy.props import (StringProperty, PointerProperty, BoolProperty)
from bpy.types import Operator
from re import split
import bpy

bl_info = {
    "name": "WEAVER Render Settings Manager",
    "author": "Alex Vuong",
    "version": (1, 0, 1),
    "blender": (4, 0, 0),
    "location": "N-panel in 3D viewport",
    "category": "Generic"
}

class WEAVER_OT_popup(bpy.types.Operator):
    bl_label = "WEAVER render manager message box"
    bl_idname = "weaver.debug_popup"

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

class OBJECT_PT_weaver_panel_ui(bpy.types.Panel):
    bl_label = "WEAVER"
    bl_idname = "OBJECT_PT_weaver_panel_ui"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "WEAVER"

    def draw(self, context):
        layout = self.layout
        layout.operator("weaver.set_render_settings")
        layout.operator("weaver.set_playblast_settings")

class WEAVER_OT_set_playblast_settings(bpy.types.Operator):
    bl_label = "Set playblast settings"
    bl_idname = "weaver.set_playblast_settings"
    bl_description = "Set render to playblast WEBM settings"

    def execute(self, context):
        bpy.ops.weaver.set_render_settings()
        bpy.context.scene.render.ffmpeg.format = 'WEBM'
        bpy.context.scene.render.ffmpeg.codec = 'WEBM'
        bpy.context.scene.render.ffmpeg.constant_rate_factor = 'LOWEST'
        bpy.context.scene.render.ffmpeg.ffmpeg_preset = 'BEST'
        return {'FINISHED'}

class WEAVER_OT_set_render_settings(bpy.types.Operator):
    bl_label = "Set render settings"
    bl_idname = "weaver.set_render_settings"
    bl_description = "Set render to Quicktime MOV settings, set output path to //../../../Renders/ShotNumber/ViewLayer_"

    def execute(self, context):
        filename = bpy.path.basename(bpy.context.blend_data.filepath)
        filename = filename.split('_')
        shotname = filename[1].split('.')
        shotname = shotname[0]
        viewlayername = bpy.context.view_layer.name
        bpy.context.scene.render.filepath = f"//../../../Renders/{shotname}/{viewlayername}_"

        if "ALL" in viewlayername or "_editing" in viewlayername:
            show_panel_helper(f"Are you sure you want to render \"{viewlayername}\"?")

        if "ALL" in viewlayername or "GP" in viewlayername:
            bpy.context.view_layer.use_pass_z = True
        else:
            bpy.context.view_layer.use_pass_z = False

        bpy.context.scene.render.image_settings.file_format = 'FFMPEG'
        bpy.context.scene.render.use_render_cache = False
        bpy.context.scene.render.use_file_extension = True
        bpy.context.scene.render.ffmpeg.format = 'QUICKTIME'
        bpy.context.scene.render.ffmpeg.codec = 'QTRLE'
        bpy.context.scene.render.ffmpeg.ffmpeg_preset = 'BEST'
        bpy.context.scene.render.use_compositing = False
        bpy.context.scene.render.use_sequencer = False
        bpy.context.scene.render.image_settings.color_mode = 'RGBA'
        bpy.context.scene.render.film_transparent = True
        bpy.context.view_layer.use = True
        bpy.context.scene.render.use_single_layer = True
        bpy.context.scene.eevee.use_bloom = True

        return {'FINISHED'}

class WEAVER_OT_playblast_current_viewlayer(bpy.types.Operator):
    bl_label = "Playblast this layer"
    bl_idname = "weaver.playblast_active_layer"
    bl_description = "Runs \"Viewport Render Animation\""

    def execute(self, context):
        bpy.ops.wm.save_mainfile()
        bpy.ops.render.opengl(animation=True)
        return {'FINISHED'}

classes = (
    OBJECT_PT_weaver_panel_ui,
    WEAVER_OT_set_render_settings,
    WEAVER_OT_playblast_current_viewlayer,
    WEAVER_OT_popup,
    WEAVER_OT_set_playblast_settings
)

def show_panel_helper(text):
    bpy.ops.weaver.debug_popup('INVOKE_DEFAULT', message=text, icon_type='INFO')
    print(text)

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    # bpy.types.WindowManager.p4_tracking = PointerProperty(
    #     type=PerforceTracking)
    
def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    # del bpy.types.WindowManager.p4_tracking

if __name__ == "__main__":
    register()
