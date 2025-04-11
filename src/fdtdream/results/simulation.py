# # from .. import structures
# # from .. import sources
# # from .. import monitors
# # from ..fdtd import FDTDRegion
# # from ..mesh import Mesh
# from typing import Any, TypedDict
# from src.fdtdream.structures.scripted_structures import *
# from src.fdtdream.interfaces import SimulationInterface
# import re
#
# # _type_to_class_map: dict[str, type] = {
# #
# #     # Structure types
# #     "Rectangle": structures.Rectangle,
# #     "Circle": structures.Circle,
# #     "Sphere": structures.Sphere,
# #     "Ring": structures.Ring,
# #     "Pyramid": structures.Pyramid,
# #     "Polygon": structures.Polygon,
# #
# #     # Source types
# #     "GaussianSource": sources.GaussianBeam,
# #     "Cauchy-Lorentzian": sources.CauchyLorentzianBeam,
# #     "PlaneSource": sources.PlaneWave,
# #
# #     # Monitor Types
# #     "IndexMonitor": monitors.IndexMonitor,
# #     "DFTMonitor": monitors.FreqDomainFieldAndPowerMonitor,
# #
# #     # FDTD Types
# #     "FDTD": FDTDRegion,
# #     "Mesh": Mesh,
# #
# #     # Group types:
# #
# # }
#
#
# class Obj(TypedDict, total=False):
#     name: str
#     obj_type: str
#     parent_hierarchy: list[str]
#     child_hierarchy: list[str]
#
#
# creation_lines = ["addrect();", "addcircle();", "addsphere();", "addring();", "addpyramid();" "addpoly();"]
#
#
# def extract_effective_lines(code_str: str) -> list[str]:
#     """Takes in Lumerical Scripting language and returns a list with each line of code that actually does anything."""
#
#     effective_lines = []
#     current_statement = ""
#
#     # Process the code line by line
#     for line in code_str.splitlines():
#
#         # Remove any comment (anything after '#' is ignored)
#         code_without_comment = line.split('#', 1)[0].strip()
#         if not code_without_comment:
#             continue  # skip empty lines
#
#         # Accumulate the code, adding a space for separation if needed
#         current_statement += code_without_comment + " "
#
#         # Process the accumulated code until all effective lines (terminated by ;) are extracted
#         while ';' in current_statement:
#             # Split on the first semicolon
#             statement, remainder = current_statement.split(';', 1)
#             if statement.strip():
#                 effective_lines.append(statement.strip())
#             current_statement = remainder.strip()
#
#         # Add back the ; separators.
#     effective_lines = [line + ";" for line in effective_lines]
#
#     return effective_lines

#
# def read_construction_code(line: str, sim: SimulationInterface, current_object: ScriptedStructure | None,
#                            objects: list) -> ScriptedStructure:
#
#     if line == "addrect();":
#         current_object = ScriptedRectangle(sim)
#         objects.append(current_object)
#     elif line == "addcircle();":
#         current_object = ScriptedCircle(sim)
#         objects.append(current_object)
#     elif line == "addsphere();":
#         current_object = ScriptedSphere(sim)
#         objects.append(current_object)
#     elif line == "addring();":
#         current_object = ScriptedRing(sim)
#         objects.append(current_object)
#     elif line == "addpyramid();":
#         current_object = ScriptedPyramid(sim)
#         objects.append(current_object)
#     elif line == "addpoly();":
#         current_object = ScriptedPolygon(sim)
#         objects.append(current_object)
#
#     return current_object
#
#
# def read_set_line(line, current_object: ScriptedStructure | None) -> None:
#
#     if current_object is None:
#         #TODO implement catching
#         ...
#
#     # This regex captures the entire quoted string (including quotes) for each argument.
#     pattern = r"set\(\s*((['\"]).*?\2)\s*,\s*(((['\"]).*?\5)|([^'\"\)]+))\s*\);"
#
#     match = re.search(pattern, line)
#     if match:
#         left_arg = match.group(1)  # always a quoted string (with quotes)
#         right_arg = match.group(3)  # either a quoted string (with quotes) or a non-quoted value
#
#         left_arg = left_arg.strip("'").strip('"')
#         if "'" in right_arg or '"' in right_arg:
#             right_arg = right_arg.strip("'").strip('"')
#         elif right_arg == "true":
#             right_arg = True
#         elif right_arg == "false":
#             right_arg = False
#         else:
#             right_arg = float(right_arg)
#
#         current_object._set(left_arg, right_arg)
#
#
# def read_setnamed_line(line, objects: list[ScriptedStructure]) -> None:
#     pattern = r"""
#     setnamed\(\s*                             # Match "setnamed(" with optional whitespace
#       ( (["']).*?\2 )\s*,\s*                    # Group 1: first argument (quoted); Group 2: its quote
#       ( (["']).*?\4 )\s*,\s*                    # Group 3: second argument (quoted); Group 4: its quote
#       (                                        # Group 5: third argument (either quoted or unquoted)
#         (                                      # Group 6: quoted alternative
#           (["']).*?\7                         # Group 7: captures the opening quote and content up to matching quote
#         )
#         |                                      # OR
#         (                                      # Group 8: unquoted alternative
#           [^'"\)]+
#         )
#       )
#     \s*\);                                    # Match closing parenthesis, semicolon, and optional whitespace
#     """
#
#     match = re.search(pattern, line, re.VERBOSE)
#     if match:
#         first_arg = match.group(1)  # Contains quotes, e.g. "rect"
#         second_arg = match.group(3)  # Contains quotes, e.g. 'material'
#         third_arg = match.group(5)  # Contains quotes if quoted, or the raw token if unquoted
#
#         first_arg = first_arg.strip("'").strip('"')
#         second_arg = second_arg.strip("'").strip('"')
#         if "'" in third_arg or '"' in third_arg:
#             third_arg = third_arg.strip("'").strip('"')
#         elif third_arg == "true":
#             third_arg = True
#         elif third_arg == "false":
#             third_arg = False
#         else:
#             third_arg = float(third_arg)
#
#         for obj in objects:
#             raise_exception = False  # Raise exception if
#             if obj._name == first_arg:
#                 try:
#                     obj._set(second_arg, third_arg)
#                 except:
#
#
#     else:
#         #TODO implement catching
#         ...
#     return None
#
#
# def read_construction_group(script: str, sim: SimulationInterface) -> list[Obj] | None:
#
#     # Separate the script into lines
#     code_lines = extract_effective_lines(script)
#
#     objects = []
#     current_object = None
#
#     if not code_lines:
#         return None
#     elif code_lines[0] == "deleteall;":
#         if len(code_lines) > 1:
#             code_lines = code_lines[1:]
#         else:
#             return None
#
#     for line in code_lines:
#
#         if line in creation_lines:
#             current_object = read_construction_code(line, sim, current_object, objects)
#
#         elif line.startswith("set("):
#
#             read_set_line(line, current_object)
#
#         elif line.startswith("setnamed("):
#             read_setnamed_line(line, objects)
#
#     return objects
#
# def read_lattice(script: str, sim: SimulationInterface) -> Any:
#     ...
#
# def _get_sim_objects_in_scope(sim, lumapi, scope: str, iterated: list[dict[str, str]] = None) -> Any:
#
#     # Initialize a list with objects if it is not provided
#     if not iterated:
#         iterated: list[dict[str, str]] = []
#
#     # Select all objects in scope and get how many objects are selected.
#     lumapi.groupscope(scope)  # Select scope.
#     lumapi.selectall()  # Select all objects in scope.
#     nr_objects = int(lumapi.getnumber())  # Fetch number of objects selected.
#
#     # Iterate through the selected objects.
#     for i in range(1, nr_objects + 1):
#
#         # Fetch name, type, and parents.
#         obj_dict: Obj = {
#             "name": lumapi.get("name", i).replace(" ", "_"),
#             "obj_type": lumapi.get("type", i),
#             "parent_hierarchy": scope.split("::")[::-1],
#             "child_hierarchy": []
#         }
#
#         # Handle cases where the object is a group of some sorts.
#         if obj_dict["obj_type"] == "Structure Group":
#
#             # Handle cases where it is a construction group.
#             is_construction_group: bool = bool(lumapi.get("construction group", i))
#             if is_construction_group:
#                 script: str = lumapi.get("script", i)
#
#                 if "type = 'Lattice';" in script:
#                     objects = read_lattice(script, sim)
#                 else:
#                     objects = read_construction_group(script, sim)
#             else:
#
#
#
#             # If not fetch the contained obejcts and add it to the list of already iterated objects.
#             iterated = _get_sim_objects_in_scope(lumapi, scope + "::" + name, iterated)
#
#             # Reset the groupscope to the current one and reselect all objects.
#             lumapi.groupscope(scope)
#             lumapi.selectall()
#
# #
# #
# # def _get_simulation_objects_in_scope(self, groupscope: str, autoset_new_unique_names: bool,
# #                                      iterated: list[dict[str, str]] = None) -> list[dict[str, str]]:
# #
# #     if iterated is None:
# #         iterated = []
# #
# #     # Fetch reference to the lumerical API for reuse
# #     lumapi = self._lumapi()
# #
# #     # Select the provided group as the groupscope and select all objects in it
# #     lumapi.groupscope(groupscope)
# #     lumapi.selectall()
# #     num_objects = int(lumapi.getnumber())
# #
# #     # Iterate through all the objects in the group
# #     for i in range(num_objects):
# #
# #         name = lumapi.get("name", i + 1).replace(" ", "_")
# #         sim_object_type = lumapi.get("type", i + 1)
# #
# #         used_names = [sim_object["name"].replace(" ", "_") for sim_object in iterated]
# #
# #         if autoset_new_unique_names and sim_object_type != "FDTD":
# #
# #             unique_name = get_unique_name(name, used_names)
# #
# #             lumapi.set("name", unique_name, i + 1)
# #
# #         else:
# #             unique_name = name
# #
# #         iterated.append(
# #             {"name": unique_name, "type": sim_object_type, "scope": groupscope.split("::")[-1]})
# #
# #         # Check if the object is another group, run this method recursively
# #         if (sim_object_type == "Layout Group" or
# #                 (sim_object_type == "Structure Group" and
# #                  lumapi.getnamed(name, "construction group") == 0.0)):
# #             new_groupscope = groupscope + "::" + unique_name
# #             iterated = self._get_simulation_objects_in_scope(new_groupscope, autoset_new_unique_names,
# #                                                              iterated)
# #             lumapi.groupscope(groupscope)
# #
# #         lumapi.selectall()
# #
# #     return iterated
#
# script = \
#     """deleteall;
#     # This should not be included
#     addrect();
#     set('name', 'rect_1');
#     set('x', 0);
#     set('y', 0);
#     set('z', true);
#     set('x span', 4e-07);
#     set('y span', 4e-07);
#     set('z span', 1e-07);
#     set('material', 'Au (Gold) - Johnson and Christy');
#     addcircle();
#     set('name', 'rect_2');
#     set('x', -6e-07);
#     set('y', 0);
#     set('z', 0);
#     set('radius', 4e-07);
#     set('material', 'Au (Gold) - Johnson and Christy');
#     setnamed("rect_1", "x", -111e-7);
#     """
#
# obj = read_construction_group(script, "sim")
# print(obj)
# for ob in obj:
#     print(ob._x)
