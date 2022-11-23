import bpy
import os
import mathutils
import bmesh

def get_selected_objects():
    selected_objects = [o for o in bpy.context.scene.objects if o.select_get()]
    return selected_objects
    
def find_armature():
    sel = get_selected_objects()
    for o in sel:
        if o.type == "ARMATURE":
            return o
    return None

def get_meshes():
    sel = get_selected_objects()
    #sel = bpy.context.scene.objects
    meshes = []
    for o in sel:
        if o.type != "MESH":
            continue
        meshes.append(o)
    return meshes

class Exporter():
    def __init__(self):
        pass
    def export_file(self, path):
        meshes = get_meshes()
        amt_ob = find_armature()

        # deselect all
        for obj in bpy.data.objects:
            obj.select_set(False)

        # add armature if there's none
        if amt_ob is None:
            bpy.ops.object.armature_add()
            amt_ob = bpy.context.scene.objects['Armature']
            
            for m in meshes:
                m.select_set(True)
                
            amt_ob.select_set(True)
            bpy.ops.object.parent_set(type='ARMATURE_AUTO')
            #raise Exception("No armature found")
        amt = amt_ob.data
        
        with open(path, "w", encoding="utf-8") as f:
            
            f.write("MODEL\n")
            f.write("VERSION 6\n\n")
            f.write("NUMBONES %d\n" % ( len(amt.bones) ))
            
            table = {}
            
            for index, b in enumerate(amt.bones):
                parent_index = -1
                if b.parent is not None:
                    parent_index = table[b.parent.name]
                f.write("BONE %d %d \"%s\"\n" % (index, parent_index, b.name))
                table[b.name] = index
            
            f.write("\n")
            
            for index, b in enumerate(amt.bones):
                f.write("BONE %d\n" % (index))
                m = b.matrix_local
                f.write("OFFSET %f, %f, %f\n" % (m[0][3], m[1][3], m[2][3]))
                f.write("SCALE 1.000000, 1.000000, 1.000000\n")
                f.write("X %f, %f, %f\n" % (m[0][0], m[1][0], m[2][0]))
                f.write("Y %f, %f, %f\n" % (m[0][1], m[1][1], m[2][1]))
                f.write("Z %f, %f, %f\n" % (m[0][2], m[1][2], m[2][2]))
                f.write("\n")
            
            numverts = 0
            numfaces = 0
            for mesh in meshes:
                numverts += len(mesh.data.vertices)
                numfaces += len(mesh.data.polygons)
            f.write("NUMVERTS %d\n" % (numverts))
            
            # TODO FIXME: if the vertex group name doesn't match the bone name
            total = 0
            for mesh in meshes:
                vgtable = {}
                for gr in mesh.vertex_groups:
                    vgtable[gr.index] = gr.name
                for index, v in enumerate(mesh.data.vertices):
                    f.write("VERT %d\n" % (index + total))
                    f.write("OFFSET %f, %f, %f\n" % (v.co.x, v.co.y, v.co.z))
                    
                    vgroupnames = []
                    for vg in v.groups:
                        group_name = vgtable[vg.group]
                        if not group_name in table:
                            continue
                        vgroupnames.append(group_name)
                    if len(vgroupnames) == 0:
                        raise Exception("Empty vgroupnames for %s" % (mesh))
                        
                    f.write("BONES %d\n" % (len(vgroupnames)))
                    for group_name in vgroupnames:
                        f.write("BONE %d %f\n" % (table[group_name], vg.weight))
                    f.write("\n")
                total += len(mesh.data.vertices)
                
            total = 0
                    
            f.write("NUMFACES %d\n" % (numfaces))
            for mesh_index, mesh in enumerate(meshes):
                for face in mesh.data.polygons:
                    f.write("TRI %d %d 0 0\n" % (mesh_index, mesh_index))
                    for v, l in zip(face.vertices, face.loop_indices):
                        f.write("VERT %d\n" % (v + total))
                        n = mesh.data.vertices[v].normal
                        uv = mesh.data.uv_layers.active.data[l].uv
                        f.write("NORMAL %f %f %f\n" % (n.x, n.y, n.z))
                        f.write("COLOR 1.000000 1.000000 1.000000 1.000000\n")
                        f.write("UV 1 %f %f\n" % (uv.x, 1.0 - uv.y))
                total += len(mesh.data.vertices)
            
            f.write("\n")
            f.write("NUMOBJECTS %d\n" % (len(meshes)))
            for mesh_index, mesh in enumerate(meshes):
                f.write("OBJECT %d \"%s\"\n" % (mesh_index, mesh.name))
            f.write("\n")
            
            # https://blender.stackexchange.com/questions/80773/how-to-get-the-name-of-image-of-image-texture-with-python
            def get_image_for_object(obj):
                for s in obj.material_slots:
                    if s.material and s.material.use_nodes:
                        for n in s.material.node_tree.nodes:
                            if n.type == 'TEX_IMAGE':
                                return (s.material, n.image.name, n.image.filepath)
                return None
            
            # TODO FIXME don't write them based off of objects/meshes and don't write duplicates
            f.write("NUMMATERIALS %d\n" % (len(meshes)))
            for mesh_index, mesh in enumerate(meshes):
                img = get_image_for_object(mesh)
                if img is None:
                    f.write("MATERIAL %d \"material_%d\" \"Phong\" \"%s\"\n" % (mesh_index, mesh_index, ""))
                else:
                    f.write("MATERIAL %d \"%s\" \"Phong\" \"%s\"\n" % (mesh_index, img[0].name, img[1]))
                f.write("COLOR 0.000000 0.000000 0.000000 1.000000\n")
                f.write("TRANSPARENCY 0.000000 0.000000 0.000000 1.000000\n")
                f.write("AMBIENTCOLOR 0.000000 0.000000 0.000000 1.000000\n")
                f.write("INCANDESCENCE 0.000000 0.000000 0.000000 1.000000\n")
                f.write("COEFFS 0.800000 0.000000\n")
                f.write("GLOW 0.000000 0\n")
                f.write("REFRACTIVE 6 1.000000\n")
                f.write("SPECULARCOLOR -1.000000 -1.000000 -1.000000 1.000000\n")
                f.write("REFLECTIVECOLOR -1.000000 -1.000000 -1.000000 1.000000\n")
                f.write("REFLECTIVE -1 -1.000000\n")
                f.write("BLINN -1.000000 -1.000000\n")
                f.write("PHONG -1.000000\n")
            f.write("\n")
            
            f.close()