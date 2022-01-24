import bpy
import math

from mathutils import Euler, Matrix, Vector
from .blenderUtils import *
from .errors import *

class Parser():
    dynamicFOV = True
    metaIndex = "information"
    cameraIndex = "camera_tracking"
    entityIndex = "entity_tracking"
    morphIndex = "morph_tracking"

    def __init__(self, data, camera, jsonImporter):
        self.data = data
        self.camera = camera
        self.frameOffset = jsonImporter.properties.frameOffsetPanel
        self.locationOffset = (jsonImporter.properties.deltaLocationX, jsonImporter.properties.deltaLocationY, jsonImporter.properties.deltaLocationZ)
        self.useEulerFilter = jsonImporter.properties.eulerFilterButton
        self.ignoreKeyframeTrackers = jsonImporter.properties.ignoreKeyframeTrackers
        self.yAxis = '-Y'

    def parseMetaInformation(self, version_no):
        renderInfo = self.data[self.metaIndex]

        if version_no < renderInfo["required_import_version"]:
            raise VersionError("The version of the import script is not compatible with the data!")

        fps = int(renderInfo["fps"])
        motionblurfps = round(renderInfo["motionblur_fps"])
        
        bpy.context.scene.render.fps = fps
        bpy.context.scene.render.resolution_x = renderInfo["resolution"][0]
        bpy.context.scene.render.resolution_y = renderInfo["resolution"][1]

        #motionblurfps != fps: #motionblur equivalent settings to ffmpeg's motionblur
        bpy.context.scene.cycles.motion_blur_position = 'START'
        bpy.context.scene.render.motion_blur_shutter = 1
                        
        bpy.context.scene.eevee.motion_blur_position = 'START'
        bpy.context.scene.eevee.motion_blur_shutter = 1

        self.ignoreFrame = motionblurfps / fps
        self.dynamicFOV = renderInfo["dynamic_fov"]

    def parseCamera(self):
        self.camera.rotation_mode = 'XYZ'
        self.camera.data.sensor_fit = 'VERTICAL'

        #iterate through frames of camera
        for frame in range(len(self.data[self.cameraIndex])):
            ignoreFrame = self.ignoreFrameTest(self.ignoreFrame, frame)

            if ignoreFrame == "continue": 
                continue

            frameData = self.data[self.cameraIndex][frame]
            keyframePos = ignoreFrame + self.frameOffset
            
            #NyanLi https://github.com/NyaNLI helped a lot to figure out how to convert Minecraft FOV to Blender's FOV
            fovFactor = 1
            
            #fov*1.1 because of specator mode and dynamic fov - ignores whether other fov effects take place
            if self.dynamicFOV:
                fovFactor = 1.1

            self.camera.data.lens = 0.5 / (math.tan(fovFactor * math.radians(frameData["angle"][0]) / 2)) * self.camera.data.sensor_height

            self.camera.delta_location = self.locationOffset
            self.camera.location = self.getPosition(frameData["position"]) #matches default orientation when you import mineways world.
            self.camera.delta_rotation_euler  = Euler((math.radians(90 - frameData["angle"][3]), 0, math.radians(-frameData["angle"][2] - 180)), 'XYZ')
            self.camera.rotation_euler = Euler((0, 0, -math.radians(frameData["angle"][1])), 'XYZ')

            #insert the keyframes
            insertLocation(self.camera, keyframePos)
            insertRotationEuler(self.camera, keyframePos)
            insertKeyframe(self.camera, "delta_rotation_euler", keyframePos)
            insertKeyframe(self.camera.data, "lens", keyframePos)

        #make the camera the only selected active object
        if bpy.context.view_layer.objects.active is not None:
            bpy.context.view_layer.objects.active.select_set(False)
        
        bpy.context.view_layer.objects.active = self.camera
        self.camera.select_set(True)

        if len(self.data[self.cameraIndex]) > 1:
            self.eulerFilter()

    def parseEntities(self):
        if self.entityIndex not in self.data:
            return
        
        entities = self.data[self.entityIndex]
        keyset = entities.keys()

        #iterate through entities
        for entityKey in keyset:
            entityData = entities[entityKey]

            if len(entityData) <= self.ignoreKeyframeTrackers:
                continue

            obj = addArmature(entityKey)

            startFrame = 0

            #iterate through frames of entity
            for frame in range(len(entityData)):
                ignoreFrame = self.ignoreFrameTest(self.ignoreFrame, frame)

                if ignoreFrame == "continue": 
                    continue
                
                frameData = entityData[frame]

                if frame == 0 and "frame" in frameData:
                    startFrame = int(int(frameData["frame"]) // self.ignoreFrame)

                keyframePos = ignoreFrame + self.frameOffset + startFrame

                if "body_rotation" in frameData:
                    obj.delta_rotation_euler  = Euler((math.radians(90-frameData["body_rotation"][2]), 0, -math.radians(frameData["body_rotation"][1])), 'XYZ')
                    insertKeyframe(obj, "delta_rotation_euler", keyframePos)
                        
                obj.delta_location = self.locationOffset
                obj.location = self.getPosition(frameData["position"])
                insertLocation(obj, keyframePos)

            if len(entityData) > 1:
                self.eulerFilter()

    def parseMorphs(self):
        morphs = self.data[self.morphIndex]
        keyset = morphs.keys()

        #iterate through morphs
        for morphKey in keyset:
            morphData = morphs[morphKey]

            if len(morphData) <= self.ignoreKeyframeTrackers:
                continue

            obj = addArmature(morphKey)
                    
            startFrame = 0

            #iterate through frames of morph
            for frame in range(len(morphData)):
                ignoreFrame = self.ignoreFrameTest(self.ignoreFrame, frame)

                if ignoreFrame == "continue": 
                    continue 
                        
                frameData = morphData[frame]

                if frame == 0:
                    startFrame = int(int(frameData["frame"]) // self.ignoreFrame)

                keyframePos = ignoreFrame + self.frameOffset + startFrame

                rotmatrixdata = frameData["rotation"]
                delta_rotation = Euler((math.radians(90), 0, 0), 'XYZ').to_matrix().to_4x4()
                        
                rotation_matrix = Matrix((
                Vector((rotmatrixdata[0][0], rotmatrixdata[1][0], rotmatrixdata[2][0], 0)),
                Vector((rotmatrixdata[0][1], rotmatrixdata[1][1], rotmatrixdata[2][1], 0)),
                Vector((rotmatrixdata[0][2], rotmatrixdata[1][2], rotmatrixdata[2][2], 0)),
                Vector((0, 0, 0, 1))))
                        
                rotation_matrix = delta_rotation @ rotation_matrix
                        
                translation_matrix = Matrix((
                Vector((1, 0, 0, self.getPosition(frameData["position"])[0])),
                Vector((0, 1, 0, self.getPosition(frameData["position"])[1])),
                Vector((0, 0, 1, self.getPosition(frameData["position"])[2])),
                Vector((0, 0, 0, 1))))
                        
                scale_matrix = Matrix((
                Vector((frameData["scale"][0], 0, 0, 0)),
                Vector((0, frameData["scale"][1], 0, 0)),
                Vector((0, 0, frameData["scale"][2], 0)),
                Vector((0, 0, 0, 1))))

                obj.matrix_world = translation_matrix @ rotation_matrix @ scale_matrix
                obj.delta_location = self.locationOffset

                insertLocRotScale(obj, keyframePos)

            if len(morphData) > 1:
                try:
                    self.eulerFilter()
                except:
                    print(len(morphData))


    def eulerFilter(self):
        if self.useEulerFilter is True:
            window = bpy.context.window
            screen = window.screen

            #avoid TOPBAR - for some reason it caused problems
            for area in screen.areas:
                if area.type != 'TOPBAR':
                    oldtype = area.type
                    area.type = 'GRAPH_EDITOR'
                    override = {'window': window, 'screen': screen, 'area': area}

                    bpy.ops.graph.euler_filter(override)
                    area.type = oldtype

                    break

    def ignoreFrameTest(self, ignoreFrame : int, frame : int):
        if int(frame) % int(ignoreFrame) != 0:
            return "continue"
        return int(int(frame) // ignoreFrame)

    def getPosition(self, position):
        if self.yAxis == '-Y':
            return (position[0], -position[2], position[1])
        elif self.yAxis == 'Y':
            return (position[0], position[2], position[1])