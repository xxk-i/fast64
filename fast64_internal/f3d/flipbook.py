import bpy, re
from typing import List, Any, Callable
from bpy.utils import register_class, unregister_class
from bpy.app.handlers import persistent
from .f3d_material import all_combiner_uses, update_tex_values_manual, iter_tex_nodes, TextureProperty
from ..utility import prop_split


def flipbook_to_c(flipbook, isStatic):
    newArrayData = "void* " if not isStatic else "static void* "
    newArrayData += f"{flipbook.name}[] = {{ \n"
    newArrayData += flipbook_data_to_c(flipbook)
    newArrayData += "};"
    return newArrayData


def flipbook_2d_to_c(flipbook, isStatic, count):
    newArrayData = "void* " if not isStatic else "static void* "
    newArrayData += f"{flipbook.name}[][{count}] = {{ \n"
    for i in range(count):
        newArrayData += "{\n" + flipbook_data_to_c(flipbook) + "},\n"
    newArrayData += "};"
    return newArrayData


def flipbook_data_to_c(flipbook):
    newArrayData = ""
    for textureName in flipbook.textureNames:
        newArrayData += "\t" + textureName + ",\n"
    return newArrayData


class TextureFlipbook:
    def __init__(self, name: str, exportMode: str, textureNames: List[str]):
        self.name = name
        self.exportMode = exportMode
        self.textureNames = textureNames


def usesFlipbook(
    material: bpy.types.Material,
    flipbookProperty: Any,
    index: int,
    checkEnable: bool,
    checkFlipbookReference: Callable[[str], bool],
) -> bool:
    texProp = getattr(material.f3d_mat, "tex" + str(index))
    if all_combiner_uses(material.f3d_mat)["Texture " + str(index)] and texProp.use_tex_reference:
        return (
            checkFlipbookReference is not None
            and checkFlipbookReference(texProp.tex_reference)
            and (not checkEnable or flipbookProperty.enable)
        )
    else:
        return False


class ImagePointerProperty(bpy.types.PropertyGroup):
    image: bpy.props.PointerProperty(type=bpy.types.Image)
    name: bpy.props.StringProperty(name="Name", default="gImage")


def drawTextureArray(
    layout: bpy.types.UILayout, textureArray: bpy.types.CollectionProperty, index: int, exportMode: str
):
    for i in range(len(textureArray)):
        drawTextureArrayProperty(layout, textureArray[i], i, index, exportMode)

    addOp = layout.operator(AddFlipbookTexture.bl_idname, text="Add Texture")
    addOp.combinerTexIndex = index
    addOp.arrayIndex = len(textureArray)


def drawTextureArrayProperty(
    layout: bpy.types.UILayout, texturePointer: ImagePointerProperty, arrayIndex: int, texNum: int, exportMode: str
):
    col = layout.column()

    box = col.box().column()
    if exportMode == "Individual":
        prop_split(box, texturePointer, "name", "Texture Name")

    box.template_ID(texturePointer, "image", new="image.new", open="image.open")

    row = box.row()
    buttons = row.row(align=True)
    visualizeOp = buttons.operator(VisualizeFlipbookTexture.bl_idname, text="Visualize", icon="VIEW_CAMERA")
    visualizeOp.arrayIndex = arrayIndex
    visualizeOp.combinerTexIndex = texNum

    addOp = buttons.operator(AddFlipbookTexture.bl_idname, text="", icon="ADD")
    addOp.arrayIndex = arrayIndex + 1
    addOp.combinerTexIndex = texNum

    removeOp = buttons.operator(RemoveFlipbookTexture.bl_idname, text="", icon="REMOVE")
    removeOp.arrayIndex = arrayIndex
    removeOp.combinerTexIndex = texNum

    moveUp = buttons.operator(MoveFlipbookTexture.bl_idname, text="", icon="TRIA_UP")
    moveUp.arrayIndex = arrayIndex
    moveUp.offset = -1
    moveUp.combinerTexIndex = texNum

    moveDown = buttons.operator(MoveFlipbookTexture.bl_idname, text="", icon="TRIA_DOWN")
    moveDown.arrayIndex = arrayIndex
    moveDown.offset = 1
    moveUp.combinerTexIndex = texNum


class AddFlipbookTexture(bpy.types.Operator):
    bl_idname = "material.add_flipbook_texture"
    bl_label = "Add Flipbook Texture"
    bl_options = {"REGISTER", "UNDO"}
    arrayIndex: bpy.props.IntProperty()
    combinerTexIndex: bpy.props.IntProperty()

    def execute(self, context):
        material = context.material
        flipbook = getattr(material.flipbookGroup, "flipbook" + str(self.combinerTexIndex))
        flipbook.textures.add()
        flipbook.textures.move(len(flipbook.textures) - 1, self.arrayIndex)
        self.report({"INFO"}, "Success!")
        return {"FINISHED"}


class RemoveFlipbookTexture(bpy.types.Operator):
    bl_idname = "material.remove_flipbook_texture"
    bl_label = "Remove Flipbook Texture"
    bl_options = {"REGISTER", "UNDO"}
    arrayIndex: bpy.props.IntProperty()
    combinerTexIndex: bpy.props.IntProperty()

    def execute(self, context):
        material = context.material
        flipbook = getattr(material.flipbookGroup, "flipbook" + str(self.combinerTexIndex))
        flipbook.textures.remove(self.arrayIndex)
        self.report({"INFO"}, "Success!")
        return {"FINISHED"}


class MoveFlipbookTexture(bpy.types.Operator):
    bl_idname = "material.move_flipbook_texture"
    bl_label = "Move Flipbook Texture"
    bl_options = {"REGISTER", "UNDO"}
    combinerTexIndex: bpy.props.IntProperty()
    arrayIndex: bpy.props.IntProperty()
    offset: bpy.props.IntProperty()

    def execute(self, context):
        material = context.material
        flipbook = getattr(material.flipbookGroup, "flipbook" + str(self.combinerTexIndex))
        flipbook.textures.move(self.arrayIndex, self.arrayIndex + self.offset)
        self.report({"INFO"}, "Success!")
        return {"FINISHED"}


class VisualizeFlipbookTexture(bpy.types.Operator):
    bl_idname = "material.visualize_flipbook_texture"
    bl_label = "Visualize Flipbook Texture"
    bl_options = {"REGISTER", "UNDO"}
    combinerTexIndex: bpy.props.IntProperty()
    arrayIndex: bpy.props.IntProperty()

    def execute(self, context):
        material = context.material
        flipbook = getattr(material.flipbookGroup, "flipbook" + str(self.combinerTexIndex))
        texProp = getattr(material.f3d_mat, "tex" + str(self.combinerTexIndex))

        setTexNodeImage(context.material, self.combinerTexIndex, self.arrayIndex)

        self.report({"INFO"}, "Success!")
        return {"FINISHED"}


enumFlipbookExportMode = [
    ("Array", "Array", "Array"),
    ("Individual", "Individual", "Individual"),
]


class FlipbookProperty(bpy.types.PropertyGroup):
    enable: bpy.props.BoolProperty()
    name: bpy.props.StringProperty(default="sFlipbookTextures")
    exportMode: bpy.props.EnumProperty(default="Array", items=enumFlipbookExportMode)
    textures: bpy.props.CollectionProperty(type=ImagePointerProperty)


# The reason these are separate is for the case when the user changes the material draw layer, but not the
# dynamic material calls. This could cause crashes which would be hard to detect.
class FlipbookGroupProperty(bpy.types.PropertyGroup):
    flipbook0: bpy.props.PointerProperty(type=FlipbookProperty)
    flipbook1: bpy.props.PointerProperty(type=FlipbookProperty)


def drawFlipbookProperty(layout: bpy.types.UILayout, flipbookProp: FlipbookProperty, index: int):
    box = layout.box().column()
    box.prop(flipbookProp, "enable", text="Export Flipbook Textures " + str(index))
    if flipbookProp.enable:
        prop_split(box, flipbookProp, "exportMode", "Export Mode")
        if flipbookProp.exportMode == "Array":
            prop_split(box, flipbookProp, "name", "Array Name")
        drawTextureArray(box.column(), flipbookProp.textures, index, flipbookProp.exportMode)


def drawFlipbookGroupProperty(
    layout: bpy.types.UILayout,
    material: bpy.types.Material,
    checkFlipbookReference: Callable[[str], bool],
    flipbookRequirementMessage: Callable[[bpy.types.UILayout], None],
):
    layout.box().column().label(text="Flipbook Properties")
    if flipbookRequirementMessage is not None:
        flipbookRequirementMessage(layout)
    for i in range(2):
        flipbook = getattr(material.flipbookGroup, "flipbook" + str(i))
        if usesFlipbook(material, flipbook, i, False, checkFlipbookReference):
            drawFlipbookProperty(layout.column(), flipbook, i)
            if getattr(material.f3d_mat, "tex" + str(i)).tex_format[:2] == "CI":
                layout.label(text="New shared CI palette will be generated.", icon="ERROR")


# START GAME SPECIFIC CALLBACKS
def ootFlipbookReferenceIsValid(texReference: str) -> bool:
    return re.search(f"0x0([0-9A-F])000000", texReference) is not None


def ootFlipbookRequirementMessage(layout: bpy.types.UILayout):
    layout.label(text="To use this, material must use a texture ")
    layout.label(text="reference with name = 0x0?000000.")


def ootFlipbookAnimUpdate(self, armatureObj: bpy.types.Object, segment: str, index: int):
    for child in [child for child in armatureObj.children if isinstance(child.data, bpy.types.Mesh)]:
        for material in child.data.materials:
            for i in range(2):
                flipbook = getattr(material.flipbookGroup, "flipbook" + str(i))
                texProp = getattr(material.f3d_mat, "tex" + str(i))
                if usesFlipbook(material, flipbook, i, True, ootFlipbookReferenceIsValid):
                    match = re.search(f"0x0([0-9A-F])000000", texProp.tex_reference)
                    if match is None:
                        return
                    if match.group(1) == segment:
                        # Remember that index 0 = auto, and keyframed values start at 1
                        flipbookIndex = min((index - 1 if index > 0 else 0), len(flipbook.textures) - 1)
                        setTexNodeImage(material, i, flipbookIndex)


# END GAME SPECIFIC CALLBACKS

# we use a handler since update functions are not called when a property is animated.
@persistent
def flipbookAnimHandler(dummy):
    if bpy.context.scene.gameEditorMode == "OOT":
        for obj in bpy.data.objects:
            if isinstance(obj.data, bpy.types.Armature):
                # we only want to update texture on keyframed armatures.
                # this somewhat mitigates the issue of two skeletons using the same flipbook material.
                if obj.animation_data is None or obj.animation_data.action is None:
                    return
                action = obj.animation_data.action
                if not (
                    action.fcurves.find("ootLinkTextureAnim.eyes") is None
                    or action.fcurves.find("ootLinkTextureAnim.mouth") is None
                ):
                    ootFlipbookAnimUpdate(obj.data, obj, "8", obj.ootLinkTextureAnim.eyes)
                    ootFlipbookAnimUpdate(obj.data, obj, "9", obj.ootLinkTextureAnim.mouth)
    else:
        pass


class Flipbook_MaterialPanel(bpy.types.Panel):
    bl_label = "Flipbook Material"
    bl_idname = "MATERIAL_PT_Flipbook_Material_Inspector"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "material"
    bl_options = {"HIDE_HEADER"}

    @classmethod
    def poll(cls, context):
        return (
            context.material is not None
            and context.scene.gameEditorMode in ["OOT"]
            and not (context.object is not None and context.object.ootGeometryType == "Actor Collider")
        )

    def draw(self, context):
        layout = self.layout
        mat = context.material
        col = layout.column()

        if context.scene.gameEditorMode == "OOT":
            checkFlipbookReference = ootFlipbookReferenceIsValid
            flipbookRequirementMessage = ootFlipbookRequirementMessage
        else:
            checkFlipbookReference = None
            flipbookRequirementMessage = None

        drawFlipbookGroupProperty(col.box().column(), mat, checkFlipbookReference, flipbookRequirementMessage)


def setTexNodeImage(material: bpy.types.Material, texIndex: int, flipbookIndex: int):
    flipbook = getattr(material.flipbookGroup, "flipbook" + str(texIndex))
    for texNode in iter_tex_nodes(material.node_tree, texIndex):
        if texNode.image is not flipbook.textures[flipbookIndex].image:
            texNode.image = flipbook.textures[flipbookIndex].image


flipbook_classes = [
    ImagePointerProperty,
    AddFlipbookTexture,
    RemoveFlipbookTexture,
    MoveFlipbookTexture,
    VisualizeFlipbookTexture,
    FlipbookProperty,
    FlipbookGroupProperty,
    Flipbook_MaterialPanel,
]


def flipbook_register():
    for cls in flipbook_classes:
        register_class(cls)

    bpy.app.handlers.frame_change_pre.append(flipbookAnimHandler)
    bpy.types.Material.flipbookGroup = bpy.props.PointerProperty(type=FlipbookGroupProperty)


def flipbook_unregister():
    for cls in reversed(flipbook_classes):
        unregister_class(cls)

    del bpy.types.Material.flipbookGroup
