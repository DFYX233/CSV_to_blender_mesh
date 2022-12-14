
import os
import bpy
import csv
import mathutils
from collections import OrderedDict
from bpy_extras.io_utils import axis_conversion
from bpy.props import BoolProperty, StringProperty, EnumProperty,IntProperty

bl_info = {
    "name": "PIX CSV",
    "author": "SuperInvincibleUltraWatermelon & Stanislav Bobovych",
    "version": (2, 1, 0),
    "blender": (2, 80, 0),
    "location": "File > Import-Export",
    "description": "Import PIX CSV dump of mesh. Imports mesh, normals and UVs.",
    "category": "Import"}


class PIX_CSV_Operator(bpy.types.Operator):

    # Plugin definitions, such as ID, name, and file extension filters
    bl_idname = "object.pix_csv_importer"
    bl_label = "Import PIX CSV"
    filepath : StringProperty(subtype = "FILE_PATH")
    filter_glob : StringProperty(default = "*.csv", options = {'HIDDEN'})

    # Options for generation of vertices
    mirror_x : BoolProperty(
                            name = "Mirror X",
                            description = "Mirror all the vertices across X axis",
                            default = True,
                            )

    vertex_order : BoolProperty(
                                name = "Change vertex order",
                                description = "Reorder vertices in counter-clockwise order",
                                default = True,
                                )

    # Options for axis alignment
    axis_forward : EnumProperty(
                                name = "Forward",
                                items = (
                                         ('X', "X Forward", ""),
                                         ('Y', "Y Forward", ""),
                                         ('Z', "Z Forward", ""),
                                         ('-X', "-X Forward", ""),
                                         ('-Y', "-Y Forward", ""),
                                         ('-Z', "-Z Forward", ""),
                                         ),
                                default = 'Z',
                                )

    axis_up : EnumProperty(
                           name = "Up",
                           items = (
                                    ('X', "X Up", ""),
                                    ('Y', "Y Up", ""),
                                    ('Z', "Z Up", ""),
                                    ('-X', "-X Up", ""),
                                    ('-Y', "-Y Up", ""),
                                    ('-Z', "-Z Up", ""),
                                    ),
                           default = 'Y',
                           )
    normal_offset : IntProperty(
                            name = "Normal Offset",
                            description = "Offset of normal index",
                            default = 5
                            )
                           
                           
    texcoord_offset : IntProperty(
                            name = "texcoord Offset",
                            description = "Offset of texcoord index",
                            default = 12
                            )
                            


# ~~~~~~~~~~~~~~~~~~~~Operator Functions~~~~~~~~~~~~~~~~~~~~
    def execute(self, context):
        

        
        keywords = self.as_keywords(ignore = ("axis_forward", "axis_up", "filter_glob"))
        global_matrix = axis_conversion(from_forward = self.axis_forward, from_up = self.axis_up).to_4x4()

        keywords["global_matrix"] = global_matrix
        print(keywords)
        importCSV(**keywords)

        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)  #select file!!!!
        return {'RUNNING_MODAL'}

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.label(text = "Import Options")

        row = col.row()
        row.prop(self, "mirror_x")
        row = col.row()
        row.prop(self, "vertex_order")
        layout.prop(self, "axis_forward")
        layout.prop(self, "axis_up")
        layout.prop(self,"normal_offset")
        layout.prop(self,"texcoord_offset")


# ~~~~~~~~~~~~~~~~~~~~Mesh-Related Functions~~~~~~~~~~~~~~~~~~~~
def make_mesh(vertices, faces, normals, uvs, global_matrix):

    print(faces)
    # Create a new mesh from the vertices and faces
    mesh = bpy.data.meshes.new('name')
    mesh.from_pydata(vertices, [], faces)

    # Generate normals
    #index = 0
    #for vertex in mesh.vertices:
    #    vertex.normal = normals[index]
    #    index += 1

    mesh.calc_normals()

    # Generate UV data
    uv_layer = mesh.uv_layers.new(name = "UV")
    for face, uv in enumerate(uv_layer.data): uv.uv = uvs[face]

    mesh.update(calc_edges = False)

    obj = bpy.data.objects.new('fan', mesh)    # Create the mesh object for the imported mesh
    obj.matrix_world = global_matrix            # Apply transformation matrix
    bpy.context.collection.objects.link(obj)    # Link object to scene


def importCSV(filepath = None, mirror_x = False, vertex_order = True, global_matrix = None,normal_offset=5,texcoord_offset = 12):

    # Translates coordinates of things to the global space by ensuring that there's a global matrix to use
    if global_matrix is None: global_matrix = mathutils.Matrix()

    # Check if a valid filepath was given; if nothing was given, cancel the import
    if filepath == None: return

    # Dictionaries
    vertex_dict = {}
    normal_dict = {}

    # Arrays/Lists
    vertices = []
    faces = []
    normals = []
    uvs = []

    with open(filepath) as f:

        # Create the CSV reader
        reader = csv.reader(f) # Initialize the reader
        next(reader)  # Skip the CSV header

        #face_count = sum(1 for row in reader) / 3
        #print(face_count)

        #f.seek(0)
        #reader = csv.reader(f)
        #next(reader)  # skip header

        # Check if user wants vertices to be mirrored on the X-axis
        if mirror_x: x_mod = -1
        else: x_mod = 1

        # For-Loop variables
        i = 0
        current_face = []

        for row in reader:

            vertex_index = int(row[0])
            


            # X, Y, Z coordinates of vertices
            vertex_dict[vertex_index] = (
                                         x_mod * float(row[2]), # X
                                                 float(row[3]), # Y
                                                 float(row[4]), # Z
                                         )

            #TODO: How are axises really ligned up?
            normal_dict[vertex_index] = (
                                         float(row[normal_offset]), # X
                                         float(row[normal_offset+1]), # Y
                                         float(row[normal_offset+2]), # Z
                                         )

            #TODO: Add support for changing the origin of UV coords
            uv = (float(row[texcoord_offset]), 1.0 - float(row[texcoord_offset+1])) # X and Y coordinates while also modifying V

            
            if i < 2:
                # Append "current" data to list/array until a 3-vertex face is formed
                current_face.append(vertex_index)
                uvs.append(uv)
                i += 1
            else:
                # Append face and UV data to appropriate dictionary/array/list
                current_face.append(vertex_index)
                #TODO: Add option to change order of marching vertices
                if vertex_order: faces.append((current_face[2], current_face[1], current_face[0]))
                else: faces.append(current_face)
                uvs.append(uv)

                # Clear For-Loop variables for next iteration
                current_face = []
                i = 0

        # Zero out any missing vertices/normals
        for i in range(len(vertex_dict)):
            if i in vertex_dict:
                pass
            else:
                #print("missing",i)
                vertex_dict[i] = (0, 0, 0)
                normal_dict[i] = (0, 0, 0)

        # Dictionary sorted by key
        vertex_dict = OrderedDict(sorted(vertex_dict.items(), key=lambda t: t[0]))
        normal_dict = OrderedDict(sorted(normal_dict.items(), key=lambda t: t[0]))

        for key in vertex_dict: vertices.append(list(vertex_dict[key]))
        #print(key,vertex_dict[key])
        for key in normal_dict: normals.append(list(normal_dict[key]))

        #print("Vertices:\n")
        #print(vertices)
        #print("faces:\n")
        #print(faces)
        #print("normal:\n")
        #print(normals)
        #print("uv:\n")
        #print(uvs)
        make_mesh(vertices, faces, normals, uvs, global_matrix)

#UI
class ToolPanel(bpy.types.Panel):
    bl_label = "CSV to Mesh"
    bl_idname="CSV to Mesh Panel"
    bl_space_type="VIEW_3D"
    bl_region_type="UI"
    bl_category="CSV2Mesh"
    
    def draw(self,context):
        layout=self.layout
        row = layout.row() 
        row.label(text='Import',icon='MESH_CUBE')
        row.operator("object.pix_csv_importer",icon="CUBE")


# ~~~~~~~~~~~~~~~~~~~~Registration Functions~~~~~~~~~~~~~~~~~~~~
classes = (PIX_CSV_Operator,ToolPanel)

def menu_func_import(self, context):
    self.layout.operator(PIX_CSV_Operator.bl_idname, text="PIX CSV (.csv)")

def register():
    for cls in classes: bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)

def unregister():
    for cls in reversed(classes): bpy.utils.unregister_class(cls)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)






# ~~~~~~~~~~~~~~~~~~~~MAIN Block~~~~~~~~~~~~~~~~~~~~
if __name__ == "__main__":
    #register()                                             # Uncomment this to run as a plugin
    #These run the script from "Run script" button
    os.system('cls')
    bpy.utils.register_class(PIX_CSV_Operator)              # Comment this to run as a plugin
    bpy.utils.register_class(ToolPanel)
    #bpy.ops.object.pix_csv_importer('INVOKE_DEFAULT')       # Comment this to run as a plugin