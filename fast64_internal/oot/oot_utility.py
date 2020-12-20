from ..utility import *
import bpy
from bpy.utils import register_class, unregister_class

class BoxEmpty:
	def __init__(self, position, scale, emptyScale):
		# The scale ordering is due to the fact that scaling happens AFTER rotation.
		# Thus the translation uses Y-up, while the scale uses Z-up.
		self.low = (position[0] - scale[0] * emptyScale, position[2] - scale[1] * emptyScale)
		self.high = (position[0] + scale[0] * emptyScale, position[2] + scale[1] * emptyScale)
		self.height = position[1] + scale[2] * emptyScale

def drawEnumWithCustom(panel, data, attribute, name, customName):
	prop_split(panel, data, attribute, name)
	if getattr(data, attribute) == "Custom":
		prop_split(panel, data, attribute + "Custom", customName)

def clampShort(value):
	return min(max(round(value), -2**15), 2**15 - 1)

def convertNormalizedFloatToShort(value):
	value *= 2**15
	value = clampShort(value)
	
	return int(value.to_bytes(2, 'big', signed = True))

def convertNormalizedVectorToShort(value):
	return (
		convertNormalizedFloatToShort(value[0]),
		convertNormalizedFloatToShort(value[1]),
		convertNormalizedFloatToShort(value[2]),
	)

# Operators cannot store mutable references (?), so to reuse PropertyCollection modification code we do this.
# Save a string identifier in the operator, then choose the member variable based on that.
# subIndex is for a collection within a collection element
def getCollection(obj, collectionType, subIndex):

	if collectionType == "Actor":	
		collection = obj.ootActorProperty.headerSettings.cutsceneHeaders
	elif collectionType == "Room":
		collection = obj.ootAlternateRoomHeaders.cutsceneHeaders
	elif collectionType == "Scene":
		collection = obj.ootAlternateSceneHeaders.cutsceneHeaders
	elif collectionType == "Light":
		if subIndex < 0:
			raise PluginError("Alternate scene header index too low: " + str(subIndex))
		elif subIndex == 0:		
			collection = obj.ootSceneHeader.lightList
		elif subIndex == 1:
			collection = obj.ootAlternateSceneHeaders.childNightHeader.lightList
		elif subIndex == 2:
			collection = obj.ootAlternateSceneHeaders.adultDayHeader.lightList
		elif subIndex == 3:
			collection = obj.ootAlternateSceneHeaders.adultNightHeader.lightList
		else:
			collection = obj.ootAlternateSceneHeaders.cutsceneHeaders[subIndex - 4].lightList
	elif collectionType == "Object":
		if subIndex < 0:
			raise PluginError("Alternate scene header index too low: " + str(subIndex))
		elif subIndex == 0:		
			collection = obj.ootRoomHeader.objectList
		elif subIndex == 1:
			collection = obj.ootAlternateRoomHeaders.childNightHeader.objectList
		elif subIndex == 2:
			collection = obj.ootAlternateRoomHeaders.adultDayHeader.objectList
		elif subIndex == 3:
			collection = obj.ootAlternateRoomHeaders.adultNightHeader.objectList
		else:
			collection = obj.ootAlternateRoomHeaders.cutsceneHeaders[subIndex - 4].objectList
	else:
		raise PluginError("Invalid collection type: " + collectionType)

	return collection

def drawAddButton(layout, index, collectionType, subIndex):
	if subIndex is None:
		subIndex = 0
	addOp = layout.operator(OOTCollectionAdd.bl_idname)
	addOp.option = index
	addOp.collectionType = collectionType
	addOp.subIndex = subIndex

def drawCollectionOps(layout, index, collectionType, subIndex):
	if subIndex is None:
		subIndex = 0

	buttons = layout.row(align = True)

	addOp = buttons.operator(OOTCollectionAdd.bl_idname, text = 'Add', icon = "ADD")
	addOp.option = index + 1
	addOp.collectionType = collectionType
	addOp.subIndex = subIndex

	removeOp = buttons.operator(OOTCollectionRemove.bl_idname, text = 'Delete', icon = "REMOVE")
	removeOp.option = index
	removeOp.collectionType = collectionType
	removeOp.subIndex = subIndex
	
	#moveButtons = layout.row(align = True)
	moveButtons = buttons

	moveUp = moveButtons.operator(OOTCollectionMove.bl_idname, text = 'Up', icon = "TRIA_UP")
	moveUp.option = index
	moveUp.offset = -1
	moveUp.collectionType = collectionType
	moveUp.subIndex = subIndex

	moveDown = moveButtons.operator(OOTCollectionMove.bl_idname, text = 'Down', icon = "TRIA_DOWN")
	moveDown.option = index
	moveDown.offset = 1
	moveDown.collectionType = collectionType
	moveDown.subIndex = subIndex

class OOTCollectionAdd(bpy.types.Operator):
	bl_idname = 'object.oot_collection_add'
	bl_label = 'Add Item'
	bl_options = {'REGISTER', 'UNDO'} 

	option : bpy.props.IntProperty()
	collectionType : bpy.props.StringProperty(default = "Actor")
	subIndex : bpy.props.IntProperty(default = 0)

	def execute(self, context):
		obj = context.object
		collection = getCollection(obj, self.collectionType, self.subIndex)

		collection.add()
		collection.move(len(collection)-1, self.option)
		self.report({'INFO'}, 'Success!')
		return {'FINISHED'} 

class OOTCollectionRemove(bpy.types.Operator):
	bl_idname = 'object.oot_collection_remove'
	bl_label = 'Remove Item'
	bl_options = {'REGISTER', 'UNDO'} 

	option : bpy.props.IntProperty()
	collectionType : bpy.props.StringProperty(default = "Actor")
	subIndex : bpy.props.IntProperty(default = 0)

	def execute(self, context):
		collection = getCollection(context.object, self.collectionType, self.subIndex)
		collection.remove(self.option)
		self.report({'INFO'}, 'Success!')
		return {'FINISHED'} 

class OOTCollectionMove(bpy.types.Operator):
	bl_idname = 'object.oot_collection_move'
	bl_label = 'Move Item'
	bl_options = {'REGISTER', 'UNDO'} 

	option : bpy.props.IntProperty()
	offset : bpy.props.IntProperty()
	subIndex : bpy.props.IntProperty(default = 0)

	collectionType : bpy.props.StringProperty(default = "Actor")
	def execute(self, context):
		obj = context.object
		collection = getCollection(obj, self.collectionType, self.subIndex)
		collection.move(self.option, self.option + self.offset)
		self.report({'INFO'}, 'Success!')
		return {'FINISHED'} 

oot_utility_classes = (
	OOTCollectionAdd,
	OOTCollectionRemove,
	OOTCollectionMove,
)

def oot_utility_register():
	for cls in oot_utility_classes:
		register_class(cls)

def oot_utility_unregister():
	for cls in reversed(oot_utility_classes):
		unregister_class(cls)