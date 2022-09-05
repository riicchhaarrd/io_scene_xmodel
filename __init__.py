bl_info = {
    "name": "XModel Importer/Exporter (.xmodel_export)",
    "author": "riicchhaarrd",
    "blender": (2, 80, 0),
    "category": "Import-Export",
    "location": "File > Import-Export",
}

from . import parser
from . import export
    
import bpy
import bmesh
import mathutils
import os
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator

# https://blender.stackexchange.com/questions/153746/apply-image-on-mesh-surface
def add_texture(texture_path, obj):
    mat = bpy.data.materials.new(name='texture')
    mat.use_nodes = True
    nodes = mat.node_tree.nodes

    texImage = nodes.new('ShaderNodeTexImage')
    texImage.image = bpy.data.images.load(texture_path)

    principled = nodes['Principled BSDF']

    # What to link here?
    # mat.node_tree.links.new()
    mat.node_tree.links.new( texImage.outputs[0], principled.inputs[0] )

    # Assign it to object
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)
        
class XModelExporter(Operator, ExportHelper):
    """XModelExporter""" # Use this as a tooltip for menu items and buttons.
    bl_idname = "export_scene.xmodel_export" # Unique identifier for buttons and menu items to reference.
    bl_label = "Export XModel" # Display name in the interface.
    
    filename_ext = ".xmodel_export"
    filter_glob: StringProperty(
        default="*.xmodel_export",
        options={'HIDDEN'},
        maxlen=255,
    )
    
    def execute(self, context): # execute() is called when running the operator.
        exp = export.Exporter()
        try:
            exp.export_file(self.filepath)
        except Exception as e:
            print("Error exporting file. Error: %s" % (str(e)))
        return {'FINISHED'} # Lets Blender know the operator finished successfully.
        
class XModelImporter(Operator, ExportHelper):
    """XModelImporter""" # Use this as a tooltip for menu items and buttons.
    bl_idname = "import_scene.xmodel_export" # Unique identifier for buttons and menu items to reference.
    bl_label = "Import XModel" # Display name in the interface.
    
    filename_ext = ".xmodel_export"
    filter_glob: StringProperty(
        default="*.xmodel_export",
        options={'HIDDEN'},
        maxlen=255,
    )
    #import_materials: BoolProperty(
    #    name="Import materials",
    #    description=(
    #        "Import materials"
    #    ),
    #    default=True,
    #)
    
    def execute(self, context): # execute() is called when running the operator.
        imp = parser.Parser()
        try:
            imp.read_file(self.filepath)
            
            # create rig
            amt = bpy.data.armatures.new("Rig")
            amt_ob = bpy.data.objects.new("Rig", amt)

            bpy.context.collection.objects.link(amt_ob)
            bpy.context.view_layer.objects.active = amt_ob

            bpy.ops.object.mode_set(mode='EDIT')
            for b in imp.bones:
                bone = amt.edit_bones.new(b.tag)
                bone.tail = (0,0,1)
                bone.use_deform = True
                bone.use_connect = True
                bone.matrix = (
                    (b.x.x, b.x.y, b.x.z, 0.0),
                    (b.y.x, b.y.y, b.y.z, 0.0),
                    (b.z.x, b.z.y, b.z.z, 0.0),
                    (b.offset.x, b.offset.y, b.offset.z, 1.0),
                )
                bone.parent = None
                if b.parent != -1:
                    parent = imp.bones[b.parent]
                    bone.parent = amt.edit_bones[parent.tag]
            bpy.ops.object.mode_set(mode='OBJECT')

            for o in imp.objects:
                mesh = bpy.data.meshes.new(o.name)
                
                faces = []
                verts = []
                uvs = []
                normals = []
                
                fv = []
                
                face_index = 0
                
                mat_index = -1
                
                for f in o.faces:
                    mat_index = f.material_index # TODO FIXME
                    if len(f.vertex) != 3:
                        raise Exception("Only triangular faces are supported.")
                    
                    for i in range(3):
                        verts.append(imp.vertices[f.vertex[i]].offset)
                        uvs.append(imp.vertices[f.vertex[i]].uv)
                        normals.append(imp.vertices[f.vertex[i]].normal)
                        fv.append(imp.vertices[f.vertex[i]])
                        
                    faces.append([face_index, face_index + 1, face_index + 2])
                    face_index += 3
                    
                mesh.from_pydata(verts, [], faces)
                obj = bpy.data.objects.new(o.name, mesh)
                obj.parent = amt_ob
                
                for b in imp.bones:
                    vg = obj.vertex_groups.new(name=b.tag)
                    for v_idx, v in enumerate(fv):
                        for inf in v.influences:
                            if inf.index == b.index:
                                vg.add([v_idx], inf.weight, 'ADD')
                                
                mod = obj.modifiers.new("Rig", "ARMATURE")
                mod.object = amt_ob

                bpy.context.collection.objects.link(obj)
                
                #if self.import_materials and os.path.exists(imp.materials[mat_index].texture_path):
                #    add_texture(imp.materials[mat_index].texture_path, obj)
                
                bm = bmesh.new()
                bm.from_mesh(mesh)
                
                layer = bm.loops.layers.uv.new()
                
                for f in bm.faces:
                    for l in f.loops:
                        v = l.vert
                        l[layer].uv = uvs[v.index]
                        #l[layer].uv = (v.co[0] * .001, v.co[1] * .001)
                
                bm.to_mesh(mesh)
                
                mesh.normals_split_custom_set_from_vertices(normals)
                mesh.use_auto_smooth = True
                
                mesh.update()
                bm.free()
            
        except Exception as e:
            print("Error importing file. Error: %s" % (str(e)))
        
        return {'FINISHED'} # Lets Blender know the operator finished successfully.
    

__classes__ = (
    XModelImporter,
    XModelExporter,
)

def menu_func_import(self, context):
    self.layout.operator(XModelImporter.bl_idname, text="Import XModel (.xmodel_export)")
def menu_func_export(self, context):
    self.layout.operator(XModelExporter.bl_idname, text="Export XModel (.xmodel_export)")

def register():
    for c in __classes__:
        bpy.utils.register_class(c)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
def unregister():
    for c in reversed(__classes__):
        bpy.utils.unregister_class(c)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


# This allows you to run the script directly from Blender's Text editor
# to test the add-on without having to install it.
if __name__ == "__main__":
    register()