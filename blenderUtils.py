import bpy

def addArmature(name):
    bpy.ops.object.armature_add()

    obj = bpy.context.active_object
    obj.name = name

    return obj

def addCamera(name):
    bpy.ops.object.camera_add()

    obj = bpy.context.active_object
    bpy.context.scene.camera = obj
    obj.name = name

    return obj

def get_max_keyframe_time(action):
    if action and action.fcurves:
        return max(kp.co.x for fcurve in action.fcurves for kp in fcurve.keyframe_points)
    return 0

def insertKeyframe(obj, dataPath: str, framePos: int):
    obj.keyframe_insert(data_path=dataPath, frame=framePos)

def insertLocation(obj, framePos):
    insertKeyframe(obj, "location", framePos)

def insertRotationEuler(obj, framePos):
    insertKeyframe(obj, "rotation_euler", framePos)

def insertScale(obj, framePos):
    insertKeyframe(obj, "scale", framePos)

def insertLocRotScale(obj, framePos):
    insertRotationEuler(obj, framePos)
    insertLocation(obj, framePos)
    insertScale(obj, framePos)

