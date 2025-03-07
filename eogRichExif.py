'''
  eogRichExif-MADIS

  A eog (Eye of GNOME Image Viewer) plugin which shows many Exif info in side pane.
  Plugin adapted by Arturo Espinosa <mailto:pupitetris@yahoo.com> to integrate eog
  with the UnderCurrency MADIS-Console software.

  Thanks to the eogMetaEdit plugin and @bewantbe (https://github.com/bewantbe).
'''

'''
  eogRichExif is free software: you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  eogRichExif is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with eogRichExif.  If not, see <http://www.gnu.org/licenses/>.
'''

# To install on venv, follow Update 2023 instructions:
# https://stackoverflow.com/questions/26678457/how-do-i-install-python3-gi-within-virtualenv
# sudo apt install libgirepository1.0-dev
from gi.repository import GObject, Gtk, Eog
from os.path import join, basename
from urllib.parse import urlparse
import xml.sax.saxutils
import math


try:
	import exiv2
except ModuleNotFoundError:
	exiv2 = None
	import pyexiv2


class exiv2Compat():
	def __init__(self, fname):
		if exiv2 is not None:
			self.img = exiv2.ImageFactory.open(fname)
			self.img.readMetadata()
			self.exif = self.img.exifData()
		else:
			self.exif = pyexiv2.ImageMetadata(fname)
			self.exif.read()


	def metadata(self):
		return self.exif


	def value_str(self, key):
		if exiv2 is not None:
			return self.exif[key].value().toString()
		return self.exif[key].value


	def value_float(self, key):
		if exiv2 is not None:
			return self.exif[key].value().toFloat()
		return self.exif[key].value.__float__()


class eogRichExif(GObject.Object, Eog.WindowActivatable):
	# Override EogWindowActivatable's window property
	# This is the EogWindow this plugin instance has been activated for
	window = GObject.property(type=Eog.Window)
	Debug = False

	def __init__(self):
#		will be execulted when activating
		GObject.Object.__init__(self)

	def do_activate(self):
		if self.Debug:
			print('The answer landed on my rooftop, whoa')
		
		# get sidebar
		self.sidebar = self.window.get_sidebar()
		# need to track file changes in the EoG thumbview (any better idea?)
		self.thumbview = self.window.get_thumb_view()		
		# the EogImage selected in the thumbview
		self.thumbImage = None
		self.cb_ids = {}
		self.plugin_window = None

		# Python and GTK
		# https://python-gtk-3-tutorial.readthedocs.org/en/latest/introduction.html
		# http://www.pygtk.org/pygtk2tutorial/sec-Notebooks.html
		# http://gnipsel.com/glade/
		builder = Gtk.Builder()
		builder.add_from_file(join(self.plugin_info.get_data_dir(),\
								"eogRichExif.glade"))
		self.plugin_window = builder.get_object('eogRichExif')
		self.label_exif = builder.get_object('label_exif')

		# add dialog to the sidebar
		Eog.Sidebar.add_page(self.sidebar, "RichExif", self.plugin_window)

		self.cb_ids['selection-changed'] = {}
		self.cb_ids['selection-changed'][self.thumbview] = \
			self.thumbview.connect('selection-changed', \
				self.selection_changed_cb, self)
		
	def do_deactivate(self):
		'''remove all the callbacks stored in dict self.cb_ids '''
		if self.Debug:
			print('The answer fell off my rooftop, woot')
		
		for S in self.cb_ids:
			for W, id in self.cb_ids[S].items():
				W.disconnect(id)

	# Load metadata
	@staticmethod
	def	selection_changed_cb(thumb, self):
		if self.Debug:
			print("--- dbg: in selection_changed_cb ---")

		# Get file path
		self.thumbImage = self.thumbview.get_first_selected_image()
		Event = Gtk.get_current_event()
		self.filePath = None
		self.fileURL = None
		if self.thumbImage != None:		
			self.fileURL = self.thumbImage.get_uri_for_display()
			# https://docs.python.org/2/library/urlparse.html
			self.filePath = urlparse(self.fileURL).path
			if self.Debug:
				print('loading thumb meta: \n  ', self.filePath, '\n  URL: ', self.fileURL)
		else:
			if self.Debug:
				print('Fail to load metadata!')
			return False

		# Read metadata
		# http://python3-exiv2.readthedocs.org/en/latest/tutorial.html
		try:
			self.exiv2 = exiv2Compat(self.filePath)
			self.metadata = self.exiv2.metadata()
		except Exception as e:
			self.metadata = None
			self.label_exif.set_markup("Cannot read metadata.\n self.filePath=%s\n Exception=%s" % (self.filePath, str(e)))
			return

#		try:
		self.set_info()
#		except KeyError as e:
#			self.label_exif.set_markup("Metadata incomplete?\n  Error: {0}\n".format(e))

		# return False to let any other callbacks execute as well
		return False

	def set_info(self):

		def is_integer(a):
			if math.fabs(a-math.floor(a+0.5)) < 1e-5:
				return True
			else:
				return False

		st_markup = '%s\n' % self.filePath;

		if 'Exif.Image.Model' in self.metadata:
			image_make = ''
			if 'Exif.Image.Make' in self.metadata:
				image_make = xml.sax.saxutils.escape(self.exiv2.value_str('Exif.Image.Make')) + '\n '
			image_model = xml.sax.saxutils.escape(self.exiv2.value_str('Exif.Image.Model'))
			st_markup += '<b>Camera:</b>\n %s%s\n' % (image_make, image_model)

		# Time
		NO_TIME = '0000:00:00 00:00:00'
		s_time_tag = [
		[NO_TIME, 'Exif.Image.DateTime',          'DateTime'],
		[NO_TIME, 'Exif.Image.DateTimeOriginal',  'DateTimeOriginal'],
		[NO_TIME, 'Exif.Photo.DateTimeOriginal',  'DateTimeOriginal'],
		[NO_TIME, 'Exif.Image.DateTimeDigitized', 'DateTimeDigitized'],
		[NO_TIME, 'Exif.Photo.DateTimeDigitized', 'DateTimeDigitized']]
		for idx, ttag in enumerate(s_time_tag):
			if ttag[1] in self.metadata:
				s_time_tag[idx][0] = self.metadata[ttag[1]].value().toString()

		# remove nonsence data
		s_time_tag = list(filter(lambda x: x[0]!=NO_TIME, s_time_tag))

		if len(set([r[0] for r in s_time_tag])) > 1:  # time are different
			for ttag in s_time_tag:
				st_markup += '<b>%s:</b>\n<tt> %s</tt>\n' % (ttag[2], ttag[0].strftime('%Y-%m-%d %H:%M:%S'))
		elif len(s_time_tag) == 0:
			st_markup += '<b>DateTime:</b>\n<tt> ??</tt>\n'
		else: # unique time
			st_markup += '<b>DateTime:</b>\n<tt> %s</tt>\n' % (s_time_tag[0][0].strftime('%Y-%m-%d %H:%M:%S'))

		# ExposureTime
		if 'Exif.Photo.ExposureTime' in self.metadata:
			st_exposure_time = self.exiv2.value_str('Exif.Photo.ExposureTime')
		else:
			st_exposure_time = '?? s'
		# FNumber
		if 'Exif.Photo.FNumber' in self.metadata:
			f_number = self.exiv2.value_str('Exif.Photo.FNumber')
		elif 'Exif.Photo.ApertureValue' in self.metadata:
			f_number = self.exiv2.value_str('Exif.Photo.ApertureValue')
		else:
			f_number = 'F??'
		# ISO
		iso = ''
		if 'Exif.Photo.ISOSpeedRatings' in self.metadata:
			iso = self.exiv2.value_str('Exif.Photo.ISOSpeedRatings')
		else:
			if 'Exif.Nikon3.ISOSettings' in self.metadata:
				iso = self.exiv2.value_str('Exif.Nikon3.ISOSettings')
			if 'Exif.NikonIi.ISO' in self.metadata:
				iso = self.exiv2.value_str('Exif.NikonIi.ISO')

		# extra ISO
		if 'Exif.NikonIi.ISOExpansion' in self.metadata:
			iso_ext = self.exiv2.value_str('Exif.NikonIi.ISOExpansion')
			if 'off' in iso_ext.lower():
				iso += '' # do nothing
			else:
				iso += '(%s)' % iso_ext

		st_markup += '<b>Exposure:</b>\n'
		st_markup += '<tt> %s, %s</tt>\n' % (st_exposure_time, f_number)
		st_markup += '<tt> ISO %s</tt>\n' % (iso)


		# Focal Length
		if 'Exif.Photo.FocalLength' in self.metadata:
			st_focal_length = "%.1f mm" % self.exiv2.value_float('Exif.Photo.FocalLength')
		else:
			st_focal_length = "?? mm"
		if 'Exif.Photo.FocalLengthIn35mmFilm' in self.metadata:
			st_focal_length_35mm = "%.1f mm (35mm)" % self.exiv2.value_float('Exif.Photo.FocalLengthIn35mmFilm')
		else:
			st_focal_length_35mm = '?? mm (35mm)'
		st_markup += '<tt> %s</tt>\n' % (st_focal_length)
		st_markup += '<tt> %s</tt>\n' % (st_focal_length_35mm)

		if 'Exif.Photo.Flash' in self.metadata:
			st_markup += '<b>Flash:</b>\n'
			st_markup += ' %s\n' % self.exiv2.value_str('Exif.Photo.Flash')

		def sign(a):
			return (a > 0) - (a < 0)

		# White Balance
		st_markup += '<b>WhiteBalance:</b>\n'
		if 'Exif.Nikon3.WhiteBalance' in self.metadata:
			wb_extra = self.exiv2.value_str('Exif.Nikon3.WhiteBalance').strip()
			if 'Exif.Nikon3.WhiteBalanceBias' in self.metadata:
				v = self.exiv2.value_str('Exif.Nikon3.WhiteBalanceBias')
				wb_extra += ', Bias: %s:%d, %s:%d' % (('A','_','B')[sign(v[0])+1], abs(v[0]), ('M','_','G')[sign(v[1])+1], abs(v[1]))
			st_markup += ' %s\n' % wb_extra
		elif 'Exif.CanonPr.WhiteBalanceRed' in self.metadata:
			wb_extra = self.exiv2.value_str('Exif.Photo.WhiteBalance').strip()
			v_r = self.exiv2.value_str('Exif.CanonPr.WhiteBalanceRed')
			v_b = self.exiv2.value_str('Exif.CanonPr.WhiteBalanceBlue')
			wb_extra += ', Bias: R:%d, B:%d' % (v_r, v_b)
			# not sure the logic
			if 'Manual' in wb_extra:
				v_t = self.exiv2.value_str('Exif.CanonPr.ColorTemperature')
				wb_extra += ', %dK' % v_t
			st_markup += ' %s\n' % wb_extra
		else:
			if 'Exif.Photo.WhiteBalance' in self.metadata:
				wb = self.exiv2.value_str('Exif.Photo.WhiteBalance')
			else:
				wb = ''
			st_markup += ' %s\n' % wb

		# Focus Mode
		if 'Exif.Nikon3.Focus' in self.metadata:
			st_markup += '<b>Focus Mode:</b>\n'
			st_markup += ' %s\n' % self.exiv2.value_str('Exif.Nikon3.Focus').strip()
			if 'Exif.NikonAf2.ContrastDetectAF' in self.metadata:
				st_cdaf = self.exiv2.value_str('Exif.NikonAf2.ContrastDetectAF')
				if 'on' in st_cdaf.lower():
					st_markup += ' ContrastDetectAF:\n   %s\n' % st_cdaf
			if 'Exif.NikonAf2.PhaseDetectAF' in self.metadata:
				st_pdaf = self.exiv2.value_str('Exif.NikonAf2.PhaseDetectAF')
				if 'on' in st_pdaf.lower():
					st_markup += ' PhaseDetectAF:\n   %s\n' % st_pdaf

		if 'Exif.Sony1.FocusMode' in self.metadata:
			st_markup += '<b>Focus Mode:</b>\n'
			st_markup += ' %s\n' % self.exiv2.value_str('Exif.Sony1.FocusMode').strip()
			st_markup += ' %s\n' % self.exiv2.value_str('Exif.Sony1.AFMode').strip()

		if 'Exif.CanonCs.FocusMode' in self.metadata:
			st_markup += '<b>Focus Mode:</b>\n'
			st_markup += ' %s\n' % self.exiv2.value_str('Exif.CanonCs.FocusMode').strip()
			st_markup += ' FocusType: %s\n' % self.exiv2.value_str('Exif.CanonCs.FocusType').strip()

		st_markup += '<b>Extra settings:</b>\n'
		s_tag_name_extra = [
		('Exif.Photo.ExposureBiasValue', 'Exposure Bias Value'),
		('Exif.Photo.ExposureProgram',   'Exposure Program'),
		('Exif.Photo.MeteringMode',      'Metering Mode'),
		('Exif.Photo.SceneCaptureType',  'Scene Capture Type'),
		('Exif.Photo.ColorSpace',        'Color Space'),
		# Nikon
		('Exif.Nikon3.ActiveDLighting',       'DLighting'),
		('Exif.NikonVr.VibrationReduction',   'Vibration Reduction'),
		('Exif.Nikon3.NoiseReduction',        'Noise Reduction'),
		('Exif.Nikon3.HighISONoiseReduction', 'High ISO Noise Reduction'),
		('Exif.Nikon3.ShootingMode',          'Shooting Mode'),
		# Canon
		('Exif.CanonFi.NoiseReduction', 'Noise Reduction'),
		# Sony
		('Exif.Sony1.AutoHDR', 'Auto HDR'),
		('Exif.Sony1.LongExposureNoiseReduction', 'LongExposureNoiseReduction')
		]
		for tag_name in s_tag_name_extra:
			if tag_name[0] in self.metadata:
				st_markup += ' <i>%s:</i>\n   %s\n' % \
				(tag_name[1], self.metadata[tag_name[0]].value().toString())

		st_markup += '<b>Lens:</b>\n'
		s_tag_name_lens = [
		('Exif.NikonLd3.FocalLength',   'Focal Length'),
		('Exif.NikonLd3.AFAperture',    'AFAperture'),
		('Exif.NikonLd3.FocusDistance', 'Focus Distance'),
		]
		for tag_name in s_tag_name_lens:
			if tag_name[0] in self.metadata:
				st_markup += ' <i>%s:</i> %s\n' % \
				(tag_name[1], self.metadata[tag_name[0]].value().toString())

		st_markup += '<b>Lens Model:</b>\n'
		if 'Exif.Nikon3.Lens' in self.metadata:
			st_markup += ' %s\n' % self.exiv2.value_str('Exif.Nikon3.Lens')
		if 'Exif.Canon.LensModel' in self.metadata:
			st_markup += ' %s\n' % self.exiv2.value_str('Exif.Canon.LensModel')
		if 'Exif.Photo.LensModel' in self.metadata:
			st_markup += ' %s\n' % self.exiv2.value_str('Exif.Photo.LensModel')

		if 'Exif.GPSInfo.GPSLatitudeRef' in self.metadata:
			lr = self.exiv2.value_str('Exif.GPSInfo.GPSLatitudeRef')
			lv = self.exiv2.value_str('Exif.GPSInfo.GPSLatitude')
			ar = self.exiv2.value_str('Exif.GPSInfo.GPSLongitudeRef')
			av = self.exiv2.value_str('Exif.GPSInfo.GPSLongitude')
			st_markup += '<b>GPS:</b>\n %.0f° %.0f\' %.2f" %s,\n %.0f° %.0f\' %.2f" %s,\n' % \
				(float(lv[0]), float(lv[1]), float(lv[2]), lr, \
				 float(av[0]), float(av[1]), float(av[2]), ar)
			st_markup += ' %s %s.\n' % (self.exiv2.value_str('Exif.GPSInfo.GPSAltitude'),\
				self.exiv2.value_str('Exif.GPSInfo.GPSAltitudeRef'))

		previews = self.metadata.previews

		st_markup += '<b>Number of thumbnails:</b>\n <tt>%d</tt>\n' % len(previews)

		if ('Exif.Photo.UserComment' in self.metadata):
			st_markup += '<b>UserComment:</b>\n <tt>%s</tt>\n' % self.exiv2.value_str('Exif.Photo.UserComment')

		self.label_exif.set_markup(st_markup)

		self.label_exif.set_markup(st_markup)
