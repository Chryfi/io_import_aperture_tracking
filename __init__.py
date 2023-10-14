bl_info = {
    "name": "Aperture JSON tracking import",
    "author": "Christian F. (known as Chryfi)",
    "version": (1, 6, 1),
    "blender": (2, 80, 0),
    "location": "File > Import",
    "description": "Import tracking data from a json file generated by the Aperture Mod.",
    "warning": "",
    "category": "Import"
}
version_no = 161

import bpy
import json
import traceback
import os

from math import sqrt
from .blenderUtils import *
from .errors import *
from .trackingDataParser import Parser

from mathutils import Euler, Matrix, Vector
from bpy.props import (BoolProperty, IntProperty, StringProperty, EnumProperty, CollectionProperty)
from bpy_extras.io_utils import (ImportHelper, path_reference_mode)

class ImportJSON(bpy.types.Operator, ImportHelper):
    """Load an Aperture tracking data file"""
    bl_idname = "import_scene.trackjson"
    bl_label = 'Import Aperture JSON'
    bl_options = {'PRESET'}

    # for multi file import
    files: CollectionProperty(
            type=bpy.types.OperatorFileListElement,
            options={'HIDDEN', 'SKIP_SAVE'},
        )
    directory: StringProperty(
        subtype='DIR_PATH',
    )

    # Panel's properties
    filename_ext = ".json"
    filter_glob = StringProperty(default="*.json", options={'HIDDEN'})
    use_selection = BoolProperty(name="Selection only", description="Import selected json only", default=False)
    path_mode = path_reference_mode
    check_extension = True
    frameOffsetPanel: IntProperty(name="Frame offset", default=1)
    cameraImport: BoolProperty(name="Import Camera", default=True)
    entityImport: BoolProperty(name="Import Entities", default=True)
    morphImport: BoolProperty(name="Import Morph-trackers", default=True)
    eulerFilterButton: BoolProperty(name="Use Discontinuity (Euler) Filter", default=True)
    deltaLocationX: IntProperty(name="", description = "X", default=0)
    deltaLocationY: IntProperty(name="", description = "Y", default=0)
    deltaLocationZ: IntProperty(name="", description = "Z", default=0)
    morphRotationX: IntProperty(name="", description = "X", default=0)
    morphRotationY: IntProperty(name="", description = "Y", default=0)
    morphRotationZ: IntProperty(name="", description = "Z", default=0)
    ignoreErrors: BoolProperty(name="Ignore errors", default=False)
    ignoreKeyframeTrackers: IntProperty(name="Ignore trackers with keyframe amount", description = "Ignore trackers if the amount of keyframes is less or equal than the given amount.", default=1)
    #yAxis: EnumProperty(name="Axis", items=[('-Y', '-Y', 'Equals mineways world orientation.'), ('Y', 'Y', 'No conversion.')], default='-Y',)

    defaultErrorEnd = "Read the console for further information."

    def execute(self, context):
        frameOffset = 0
        files = self.files.values()

        #sort alphabetically because it does not seem like selection order gets recognised
        files.sort(key=lambda file : file.name)

        for trackingFile in files:
            file = open(os.path.join(self.directory, trackingFile.name),)
            data = json.load(file)
            camera = bpy.context.scene.camera

            file.close()
            
            if camera is None:
                camera = addCamera("Camera")

            parser = Parser(data, camera, self)
            
            #parsing meta information
            try:
                parser.parseMetaInformation(version_no)
                parser.frameOffset += frameOffset
            except VersionError as e:
                self.report({"WARNING"}, str(e) + "\nDownload the newest version of the script at https://github.com/Chryfi/io_import_aperture_tracking/releases.")

                return {"CANCELLED"}
            except:
                self.defaultDataError("information data", "", self.defaultErrorEnd)

                if not self.properties.ignoreErrors:
                    return {"CANCELLED"}
            
            #parsing camera
            if self.properties.cameraImport is True:
                try:
                    parser.parseCamera()
                    frameOffset += parser.cameraFrames
                except:
                    self.defaultReportError("camera data", "", self.defaultErrorEnd)

                    if not self.properties.ignoreErrors:
                        return {"CANCELLED"}

            #parsing entities
            if self.properties.entityImport is True:
                try:
                    parser.parseEntities()
                except:
                    self.defaultReportError("entities data", "", self.defaultErrorEnd)

                    if not self.properties.ignoreErrors:
                        return {"CANCELLED"}
            
            if self.properties.morphImport is True:
                try:
                    parser.parseMorphs()
                except:
                    self.defaultReportError("morphs data", "", self.defaultErrorEnd)

                    if not self.properties.ignoreErrors:
                        return {"CANCELLED"}

        return{'FINISHED'}

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        sfile = context.space_data
        operator = sfile.active_operator

        layout.prop(operator, 'frameOffsetPanel')
        layout.prop(operator, 'cameraImport')
        layout.prop(operator, 'entityImport')
        layout.prop(operator, 'morphImport')
        layout.prop(operator, 'eulerFilterButton')

        #morph tracker rotation offset row
        layout.label(text="Morph tracker rotation offset")

        row = layout.row()

        row.prop(operator, 'morphRotationX')
        row.prop(operator, 'morphRotationY')
        row.prop(operator, 'morphRotationZ')

        #delta location row
        layout.label(text="Delta location")

        row = layout.row()

        row.prop(operator, 'deltaLocationX')
        row.prop(operator, 'deltaLocationY')
        row.prop(operator, 'deltaLocationZ')

        
        layout.prop(operator, 'ignoreErrors')
        layout.prop(operator, 'ignoreKeyframeTrackers')

        
        #layout.prop(operator, 'yAxis')

    def defaultReportError(self, dataMessage: str, start: str, end: str):
        self.report({"WARNING"}, start + " Something went wrong while parsing the " + dataMessage + "! " + end)
        traceback.print_exc()

# Register and stuff
def menu_func_import(self, context):
    self.layout.operator(ImportJSON.bl_idname, text="JSON trackingdata (.json)")

classes = (
    ImportJSON, 
)

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)

    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
