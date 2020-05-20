import bpy
import json
import time
from enum import Enum
from math import radians
from random import randint
from random import uniform
import sys

bpy.context.user_preferences.addons['cycles'].preferences.compute_device_type = 'CUDA'
bpy.context.user_preferences.addons['cycles'].preferences.devices[0].use= True

bpy.context.scene.cycles.device = 'GPU'

bpy.context.scene.render.tile_x = 256
bpy.context.scene.render.tile_y = 256

bpy.ops.render.render(write_still=True)

sys.setrecursionlimit(10000)

#####################################################################################################################################################


# debug functions

class Verbosity(Enum):
	NONE = 0
	ERROR = 1
	WARNING = 2

verbosity = Verbosity.WARNING

def print_debug(message, verbosity_level):
	if verbosity.value >= verbosity_level.value:
		print(message)

print_debug('DEBUG: system recurrent limit is ' + str(sys.getrecursionlimit()), Verbosity.NONE)

# edit these to point to the correct folders / files when integrating the algorythm

workspace = bpy.path.abspath('//')

components_dir = 'Models//'

materials_dir = 'Materials//'

output_dir = 'Renderings\\\\'

json_file = 'avril.training.json'

product_root_name = 'Product_Root'

camera_root_name = 'Camera_Root'

mask_suffix = '_m'

landmarks_suffix = '_l'

renderings = 3

samples = 256

#####################################################################################################################################################

# class that represents a color of a material
# init sets the default value
# import_value sets the value according to the parameter passed
# apply sets the material nodes according to the type of attribute

# to support a new color, extend the most appropriate color class and implement those methods

class Color:

	def __init__(self, new_name, new_value):
		new_value = self._expand_hex_code(new_value.lstrip('#'))

		if (self._is_hex_code(new_value)):
			self._name = new_name
			self._value = new_value

	def __str__(self):
		s = '' + self._name + ': ' + str(self._value)
		return s

	def _is_hex_code(self, code):
		if not len(code) == 6:
			return False

		chars = {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "A", "B", "C", "D", "E", "F"}

		for i in range(len(code)):
			if code[i] not in chars:
				return False

		return True

	def _expand_hex_code(self, code):
		if len(code) == 3:
			return ('' + str(code[:1]) + str(code[:1]) + str(code[1:2]) + str(code[1:2]) + str(code[-1:]) + str(code[-1:]))

		return code

	def _to_RGB(self, hex_code):
		length = len(hex_code)
		return tuple(float(int(hex_code[i:i + length // 3], 16) / 255.0) for i in range(0, length, length // 3))

	def _apply(self, color_object):
		rgb = self._to_RGB(self._value)

		color_object.default_value[0] = rgb[0]
		color_object.default_value[1] = rgb[1]
		color_object.default_value[2] = rgb[2]

	def generate(self, color_object):
		self._apply(color_object)

#####################################################################################################################################################

# class that represents a material

# it can have multiple colors which are stored in a list called _colors

# init loads the material and creates all its colors according to json
# apply sets the material on the node and calls the color apply method

class Material:

	def __init__(self, new_name, material_filepath, new_colors):
		self._name = new_name
		self._colors = []

		# create the material only if there is no instance of the material yet
		# there should be 1 instance of a material for each component otherwise
		# setting the color for one component will set the color for all of the
		# materials of that type

		try:
			self._value = bpy.data.materials[self._name].copy()
		except KeyError:
			try:
				bpy.ops.wm.append(filepath = material_filepath + '\\Material\\' + self._name, filename = self._name, directory= material_filepath + '\\Material\\')
				self._value = bpy.data.materials[self._name]
			except KeyError:
				print_debug('ERROR: material \"' + str(self._name) + '\" could not be imported', Verbosity.ERROR)
				raise KeyboardInterrupt()

		for new_color in new_colors:
			try:
				self._colors.append(Color(new_color['name'], new_color['code']))
			except KeyError:
				print_debug('ERROR: malformed color \"' + str(new_color) + '\"', Verbosity.ERROR)
				raise KeyboardInterrupt()

	def __str__(self):
		s = '' + self._name.upper() + ': '

		for _color in self._colors:
			s += ' [' + str(_color) + ']'

		return s

	def _apply(self, material_object, color_index):
		material_object.material = self._value

		try:
			#print_debug('DEBUG: generating color \"' + str(self._colors[color_index]._name) + '\" for material \"' + str(self._name) + '\"', Verbosity.NONE)
			self._colors[color_index].generate(material_object.material.node_tree.nodes['RGB'].outputs[0])
		except KeyError:
			print_debug('WARNING: could not find RGB node for \"' + str(self._name) + '\" material', Verbosity.WARNING)
		except IndexError:
			print_debug('WARNING: color index ' + str(color_index) + ' for material \"' + str(self._name) + '\" is out of bounds', Verbosity.WARNING)

	def generate(self, material_object):
		self._apply(material_object, randint(0, max(0, len(self._colors) - 1)))


#####################################################################################################################################################

# class that represents a concrete variant

# it can have multiple materials which are stored in a list called _materials

# init creates all the materials and passes their json data to them
# apply applies a specified material and a specified color

class Variant:

	def __init__(self, new_name, variant_filepath, new_materials):
		self._name = new_name
		self._materials = []

		try:
			bpy.ops.wm.append(filepath = workspace + components_dir + variant_filepath + '\\Object\\' + self._name, filename = self._name, directory = workspace + components_dir + variant_filepath + '\\Object\\')
			self._value = bpy.data.objects[self._name]
		except KeyError:
			print_debug('ERROR: object \"' + _name + '\" could not be imported', Verbosity.ERROR)
		
		if new_materials is not None:
			for new_material in new_materials:
				try:
					self._materials.append(Material(new_material['name'], workspace + materials_dir + new_material['file'],  new_material['colors']))
				except KeyError:
					print_debug('ERROR: malformed material \"' + str(new_material) + '\"', Verbosity.ERROR)
					raise KeyboardInterrupt()
		else:
			self._materials.append(None)

	def __str__(self):
		s = '' + self._name.upper() + '\n\n'

		for _material in self._materials:
			s += str(_material) + '\n'

		s += '\n'
		return s

	def _apply(self, material):
		for _slot in self._value.material_slots:
			try:
				#print_debug('DEBUG: generating material \"' + str(self._materials[material_index]._name) + '\" for part \"' + str(self._name) + '\"', Verbosity.NONE)
				if material is not None:
					material.generate(_slot)
			except IndexError:
				print_debug('ERROR: material index ' + str(material_index) + ' for part \"' + str(self._name) + '\" is out of bounds', Verbosity.ERROR)
				raise KeyboardInterrupt()

	def parent(self, new_parent):
		try:
			self._value.parent = new_parent
		except IndexError:
			print_debug('ERROR: couldn\'t set parent to ' + str(new_parent) + ' for part \"' + str(self._name) + '\"', Verbosity.ERROR)
			raise KeyboardInterrupt()

	def set_visibility(self, visible):
		try:
			self._value.hide_render = not visible
		except IndexError:
			print_debug('ERROR: couldn\'t set visibility to ' + str(visible) + ' for part \"' + str(self._name) + '\"', Verbosity.ERROR)
			raise KeyboardInterrupt()


	def generate(self):
		if (len(self._materials) > 0):
			self._apply(self._materials[randint(0, max(0, len(self._materials) - 1))])

	def mask(self, mask_material):
		self._apply(mask_material)

	def landmarks(self, landmark_material):
		self._apply(landmark_material)

#####################################################################################################################################################

# class that represents a concrete part

# it can have multiple materials which are stored in a list called _variants

# init creates all the variants and passes their json data to them
# apply applies a specified variant, with a specified material and a specified color

class Part:

	def __init__(self, new_name, new_variants, new_mask_material, new_landmark_material):
		self._name = new_name
		self._variants = []
		self._active_variant = 0

		for new_variant in new_variants:
			try:
				self._variants.append(Variant(new_variant['name'], new_variant['file'], new_variant['materials']))
			except KeyError:
				print_debug('ERROR: part \"' + str(self._name) + '\" contains malformed variant', Verbosity.ERROR)

		if new_mask_material is not None:
			try:
				self._mask_material = Material(new_mask_material['name'], workspace + materials_dir + new_mask_material['file'],  new_mask_material['colors'])
			except KeyError:
				print_debug('ERROR: malformed material \"' + str(new_mask_material) + '\"', Verbosity.ERROR)
				raise KeyboardInterrupt()
		else:
			self._mask_material = None

		if new_landmark_material is not None:
			try:
				self._landmark_material = Material(new_landmark_material['name'], workspace + materials_dir + new_landmark_material['file'],  new_landmark_material['colors'])
			except KeyError:
				print_debug('ERROR: malformed material \"' + str(new_landmark_material) + '\"', Verbosity.ERROR)
				raise KeyboardInterrupt()
		else:
			self._landmark_material = None

	def __str__(self):
		s = '' + self._name.upper() + '\n\n'

		for _variant in self._variants:
			s = '' + str(variant) + '\n\n'

		s += str(self._mask_material) + '\n\n'

		s += str(self._landmark_material) + '\n\n'

		s += '\n'
		return s

	def parent(self, new_parent):
		for _variant in self._variants:
			try:
				_variant.parent(new_parent)
			except IndexError:
				print_debug('ERROR: couldn\'t set parent to ' + str(new_parent) + ' for part \"' + str(self._name) + '\"' + ', variant \"' + str(_variant) + '\"', Verbosity.ERROR)
				raise KeyboardInterrupt()

	def set_visibility(self, visible):
		for i in range(len(self._variants)):
			try:
				self._variants[i].set_visibility(visible and (i == self._active_variant))
			except IndexError:
				print_debug('ERROR: couldn\'t set visibility to ' + str(visible) + ' for part \"' + str(self._name) + '\"' + ', variant \"' + str(_variant) + '\"', Verbosity.ERROR)
				raise KeyboardInterrupt()

	def generate_variant(self):
		self._active_variant = randint(0, max(0, len(self._variants) - 1))

	def generate(self):
		self._variants[self._active_variant].generate()

	def mask(self):
		self._variants[self._active_variant].mask(self._mask_material)

	def landmarks(self):
		self._variants[self._active_variant].landmarks(self._landmark_material)

#####################################################################################################################################################

# class that represents a product configuration

# it can have multiple components which are stored in a list called _components

# init creates all the components and passes their json data to them
# apply applies to a specified component a specified material and a specified color

class Configuration:

	def __init__(self, new_name, new_root, new_components, new_landmarks):
		self._name = new_name
		self._root = new_root
		self._components = []
		self._landmarks = []

		for new_component in new_components:
			self._components.append(Part(new_component['name'], new_component['variants'],  new_component['mask_material'], new_component['landmark_material']))

		for _component in self._components:
			_component.parent(self._root)

		for new_landmark in new_landmarks:
			self._landmarks.append(Part(new_landmark['name'], new_landmark['variants'], None, new_landmark['landmark_material']))

		for _landmark in self._landmarks:
			_landmark.parent(self._root)

	def __str__(self):
		s = '' + self._name.upper() + '\n----------\n\n'
		s += 'ROOT: ' + self._root.name + '\n' 
		s += '' + self._name.upper() + '\n----------\n\n'
		s += 'COMPONENTS\n\n'

		for _component in self._components:
			s += str(_component) + '\n\n'

		s += '\n----------\n\n'
		s += 'LANDMARKS\n\n'

		for _landmark in self._landmarks:
			s += str(_landmark) + '\n\n'

		s += '\n----------\n\n'
		return s

	def _generate_variants(self):
		for _component in self._components:
			_component.generate_variant()
		for _landmark in self._landmarks:
			_landmark.generate_variant()

	def _set_components_visibility(self, visible):
		for _component in self._components:
			_component.set_visibility(visible)

	def _set_landmarks_visibility(self, visible):
		for _landmark in self._landmarks:
			_landmark.set_visibility(visible)

	def generate(self):
		self._generate_variants()
		self._set_components_visibility(True)
		self._set_landmarks_visibility(False)

		for _component in self._components:
			_component.generate()

	def mask(self):
		self._set_components_visibility(True)
		self._set_landmarks_visibility(False)

		for _component in self._components:
			_component.mask()

	def landmarks(self):
		self._set_components_visibility(True)
		self._set_landmarks_visibility(True)

		for _component in self._components:
			_component.landmarks()

		for _landmark in self._landmarks:
			_landmark.landmarks()

#####################################################################################################################################################

class RootUpdater:

	def __init__(self, new_root):
		self._root = new_root

	def update(self):
		pass
		# root.rotation_euler[2] = radians(randint(0, rotation) - (rotation / 2))

#####################################################################################################################################################

class CameraAngle:

	def __init__(self, new_angle_name, new_value, new_offset):
		self._name = new_angle_name
		self._value = new_value % 360.0
		self._offset = abs(new_offset)

	def update(self, camera_root):
		camera_root.rotation_euler[2] = radians(self._value + (uniform(0.0, self._offset * 2) - self._offset))

#####################################################################################################################################################

class CameraRootUpdater:

	def __init__(self, new_root, new_camera_angles):
		self._root = new_root
		self._angles = []
		
		for new_camera_angle in new_camera_angles:
			try:
				self._angles.append(CameraAngle(new_camera_angle['name'], new_camera_angle['value'], new_camera_angle['offset']))
			except KeyError:
				print_debug('ERROR: malformed camera_angle', Verbosity.ERROR)
				raise KeyboardInterrupt()

	def update(self):
		self._angles[randint(0, len(self._angles) - 1)].update(self._root)

#####################################################################################################################################################

class ConfigurationRenderer:

	def __init__(self, new_scene_name, new_max_renders, new_samples, new_product_updater, new_camera_updater, new_configuration):
		self._pass = -1
		self._index = 0
		self._scene_name = new_scene_name 
		self._max_renders = max(self._index, new_max_renders)
		self._samples = max(0, new_samples)
		self._product_updater = new_product_updater
		self._camera_updater = new_camera_updater
		self._configuration = new_configuration
		bpy.app.handlers.render_complete.append(self._save)

	def start(self):
		self._index = 0
		print_debug('DEBUG: starting rendering \n\n', Verbosity.NONE)
		bpy.data.scenes["Scene"].cycles.samples = self._samples
		self._render()

	def _update(self):
		bpy.context.scene.frame_set(self._index)
		self._product_updater.update()
		self._camera_updater.update()

	def _render(self):
		if (self._index < self._max_renders):
			self._update()
			self._pass = 0
			print_debug('DEBUG: rendering image #' + str(self._index) + '\n', Verbosity.NONE)
			self._configuration.generate()
			bpy.data.scenes[self._scene_name].render.engine = 'CYCLES'
			bpy.ops.render.render()

	def _render_mask(self):
		self._pass = 1
		print_debug('DEBUG: rendering image mask #' + str(self._index) + '\n', Verbosity.NONE)
		self._configuration.mask()
		bpy.data.scenes[self._scene_name].render.engine = 'BLENDER_RENDER'
		bpy.ops.render.render()

	def _render_landmarks(self):
		self._pass = 2
		print_debug('DEBUG: rendering image landmarks #' + str(self._index) + '\n', Verbosity.NONE)
		self._configuration.landmarks()
		bpy.data.scenes[self._scene_name].render.engine = 'BLENDER_RENDER'
		bpy.ops.render.render()

	def _save(self, context=None):
		if (self._pass == 0):
			print_debug('DEBUG: saving image #' + str(self._index) + '\n', Verbosity.NONE)
			bpy.data.images["Render Result"].save_render(workspace + output_dir + '{:0>4}'.format(self._index) + '.png')
			self._render_mask()
		elif (self._pass == 1):
			print_debug('DEBUG: saving image mask #' + str(self._index) + '\n', Verbosity.NONE)
			bpy.data.images["Render Result"].save_render(workspace + output_dir + '{:0>4}'.format(self._index) + mask_suffix + '.png')
			self._render_landmarks()
		elif (self._pass == 2):
			print_debug('DEBUG: saving image landmarks #' + str(self._index) + '\n', Verbosity.NONE)
			bpy.data.images["Render Result"].save_render(workspace + output_dir + '{:0>4}'.format(self._index) + landmarks_suffix + '.png')
			self._index += 1
			self._render()
		else:
			print_debug('ERROR: unrecognized pass' + str(self._pass) + '\n', Verbosity.ERROR)
			raise KeyboardInterrupt()


#####################################################################################################################################################

if __name__ == '__main__':
	with open(workspace + json_file) as json_configuration:
		configuration_data = json.loads(json_configuration.read())

		name = ''
		components = []
		product_root = None
		camera_root = None


		try:
			name = configuration_data['product']['name']
		except KeyError:
			print_debug('ERROR: couldn\'t load configuration name', Verbosity.ERROR)
			raise KeyboardInterrupt()

		try:
			product_root = bpy.data.objects[product_root_name]
		except KeyError:
			print_debug('ERROR: couldn\'t find product root object \"' + product_root_name + '\"', Verbosity.ERROR)
			raise KeyboardInterrupt()

		try:
			camera_root = bpy.data.objects[camera_root_name]
		except KeyError:
			print_debug('ERROR: couldn\'t find camera root object \"' + camera_root_name + '\"', Verbosity.ERROR)
			raise KeyboardInterrupt()

		try:
			camera_angles = configuration_data['angles']
		except KeyError:
			print_debug('ERROR: couldn\'t load camera angles', Verbosity.ERROR)
			raise KeyboardInterrupt()

		try:
			components = configuration_data['components']
		except KeyError:
			print_debug('ERROR: couldn\'t load configuration components', Verbosity.ERROR)
			raise KeyboardInterrupt()

		try:
			landmarks = configuration_data['landmarks']
		except KeyError:
			print_debug('ERROR: couldn\'t load configuration landmarks', Verbosity.ERROR)
			raise KeyboardInterrupt()

		renderer = ConfigurationRenderer("Scene", renderings, samples, RootUpdater(product_root), CameraRootUpdater(camera_root, camera_angles), Configuration(name, product_root, components, landmarks))

		renderer.start()