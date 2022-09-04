import bpy
import bmesh
import mathutils
import os

class Material():
    def __init__(self, index, name, path):
        self.index = index
        self.name = name
        self.texture_path = path

class Object():
    def __init__(self, index):
        self.faces = []
        self.index = index
        self.name = "UnnamedObject_%d" % (index)

class Face():
    def __init__(self, object_index, material_index):
        self.object_index = object_index
        self.material_index = material_index
        self.vertex = []

class Influence():
    def __init__(self, index, weight):
        self.weight = weight
        self.index = index
        
class Vertex():
    def __init__(self):
        self.offset = mathutils.Vector()
        self.normal = mathutils.Vector()
        self.uv = mathutils.Vector((0, 0))
        self.influences = []
        
class Bone():
    def __init__(self, index, parent, tag):
        self.tag = tag
        self.index = index
        self.parent = parent
        self.offset = mathutils.Vector()
        self.x = mathutils.Vector()
        self.y = mathutils.Vector()
        self.z = mathutils.Vector()
        self.scale = mathutils.Vector((1, 1, 1))
        self.vertices = []

class Parser():
    
    def __init__(self):
        self.numbones = -1
        self.numfaces = -1
        self.bones = []
        self.vertices = []
        self.materials = []
        self.objects = []
        self.current_object = None
        self.current_face = None
        self.filepath = None
    
    def error(self, msg):
            raise Exception(msg)    
    
    def parse_version(self, ver):
        if ver != "6":
            self.error("Invalid version %s" % (ver))
    
    def parse_numfaces(self, nf):
        self.numfaces = int(nf)
            
    def parse_numbones(self, nb):
        self.numbones = int(nb)
        
    def parse_vert(self, vertex_index):
        if self.numfaces == -1: # vertex definition
            self.vertices.append(Vertex())
            self.current_object = self.vertices[-1]
        else:
            self.current_face.vertex.append(int(vertex_index))
            self.current_object = self.vertices[int(vertex_index)]
            #print("setting vert to %d" % (int(vertex_index)))
    
    def parse_set_current_face_index(self, object_index_str, material_index, c1, c2):
        
        obj_idx = int(object_index_str)
        
        if obj_idx >= len(self.objects):
            self.objects.append(Object(obj_idx))
        obj = self.objects[-1]
        obj.faces.append(Face(obj_idx, int(material_index)))
        self.current_face = obj.faces[-1]
    
    def parse_bone_definition(self, index, parent, tag):
        self.bones.append(Bone(int(index), int(parent), tag))
        
    def parse_set_current_bone_index(self, index):
        self.current_object = self.bones[int(index)]
        
    def parse_vector_string(self, x, y, z):
        v = mathutils.Vector((0, 0, 0))
        v[:] = float(x[0:-1]), float(y[0:-1]), float(z[0:-1])
        return v
        
    def parse_offset(self, x, y, z):
        self.current_object.offset = self.parse_vector_string(x, y, z)
        
    def parse_x(self, x, y, z):
        self.current_object.x = self.parse_vector_string(x, y, z)
        
    def parse_y(self, x, y, z):
        self.current_object.y = self.parse_vector_string(x, y, z)
        
    def parse_z(self, x, y, z):
        self.current_object.z = self.parse_vector_string(x, y, z)
    
    def parse_object(self, index, name):
        self.objects[int(index)].name = name    
    
    def parse_normal(self, x, y, z):
        if not isinstance(self.current_object, Vertex):
            self.error("Current object is not of type Vertex")
        self.current_object.normal = mathutils.Vector((float(x), float(y), float(z)))
        
    def parse_uv(self, c, u, v):
        if not isinstance(self.current_object, Vertex):
            self.error("Current object is not of type Vertex")
        uv = mathutils.Vector((float(u), float(v)))
        
        while uv.x < 0.0:
            uv.x += 1.0
        while uv.y < 1.0:
            uv.y += 1.0
            
        while uv.x > 1.0:
            uv.x -= 1.0
        while uv.y > 1.0:
            uv.y -= 1.0
        self.current_object.uv = mathutils.Vector((uv.x, 1.0 - uv.y))
        #print("setting uv to %f %f" % (float(u), float(v)))
    
    def parse_material(self, index, material, shading, image):
        name = material[1:-1]
        path = image[1:-1]
        # nvm, just manually fix the materials
        #if len(path) != 0:
        #    path = path.split("color:")[1].replace("\\\\", "/") # get path after color:
        #    path = os.path.dirname(self.filepath) + "/" + path
        #    path = path.replace("~-g", "")
        m = Material(int(index), name, path)
        self.materials.append(m)
    
    def parse_vertex_bone_weight(self, bone_index, weight):
        if not isinstance(self.current_object, Vertex):
            self.error("Current object is not of type Vertex")
        bi = int(bone_index)
        b = self.bones[bi]
        self.current_object.influences.append(Influence(bi, float(weight)))
        b.vertices.append(self.current_object)
        
    def read_file(self, path):
        self.filepath = path
        with open(path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
            
            for l in lines:
                if len(l) == 0:
                    continue
                if l[0] == '/' and l[1] == '/':
                    continue
                sp = l.split(" ")
                if len(sp) == 0:
                    continue
                
                key = sp[0]
                args = sp[1:]
                parsers = {
                    "VERSION": self.parse_version,
                    "NUMBONES": self.parse_numbones,
                    "OFFSET": self.parse_offset,
                    "X": self.parse_x,
                    "Y": self.parse_y,
                    "Z": self.parse_z,
                    "NORMAL": self.parse_normal,
                    "UV": self.parse_uv,
                    "MATERIAL": self.parse_material,
                    "TRI": self.parse_set_current_face_index,
                    "BONE": {
                        4: self.parse_bone_definition,
                        2: self.parse_set_current_bone_index,
                        3: self.parse_vertex_bone_weight,
                    },
                    "OBJECT": self.parse_object,
                    "NUMFACES": self.parse_numfaces,
                    "VERT": self.parse_vert,
                }
                if key in parsers:
                    if callable(parsers[key]):
                        parsers[key](*args)
                    else:
                        parsers[key][len(sp)](*args)