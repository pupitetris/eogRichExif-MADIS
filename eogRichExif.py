# thanks to author(s) of eogMetaEdit plugin

from gi.repository import GObject, Gtk, Eog
from os.path import join, basename
from urllib.parse import urlparse
import pyexiv2

class eogRichExif(GObject.Object, Eog.WindowActivatable):
	# Override EogWindowActivatable's window property
	# This is the EogWindow this plugin instance has been activated for
	window = GObject.property(type=Eog.Window)
	Debug = True

	def __init__(self):
#		will be execulted when activating
		GObject.Object.__init__(self)

	def do_activate(self):
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
		builder = Gtk.Builder()
		builder.add_from_file(join(self.plugin_info.get_data_dir(),\
								"eogRichExif.glade"))
		self.plugin_window = builder.get_object('eogRichExif')
		self.win_label_time = builder.get_object('label_time')

#		self.plugin_window = Gtk.ScrolledWindow()
#		box = Gtk.Box(spacing=6, orientation=Gtk.Orientation.VERTICAL)

#		self.win_label_time = Gtk.Label(label="Date & Time")
#		box.pack_start(self.win_label_time, True, True, 0)

#		label2 = Gtk.Label(label="Camara")
#		box.pack_start(label2, True, True, 0)
#		
#		self.plugin_window.add(box)

#		self.win_label_time = Gtk.Label(label="Date & Time")
#		self.plugin_window.add(self.win_label_time)

		box = builder.get_object('box1')
		label2 = Gtk.Label()
		label2.set_text('asdfasdf')
		box.remove(builder.get_object('label1'))
#		box.add(label2)
		box.pack_start(label2, True, True, 0)

		# add dialog to the sidebar
		Eog.Sidebar.add_page(self.sidebar, "Custom Metadata Show", self.plugin_window)

		self.cb_ids['selection-changed'] = {}
		self.cb_ids['selection-changed'][self.thumbview] = \
			self.thumbview.connect('selection-changed', \
				self.selection_changed_cb, self)
		
	def do_deactivate(self):
		'''remove all the callbacks stored in dict self.cb_ids '''
		print('The answer fell off my rooftop, woot')
		
		for S in self.cb_ids:
			for W, id in self.cb_ids[S].items():
				W.disconnect(id)

	# Load metadata
	@staticmethod
	def	selection_changed_cb(thumb, self):
		print("--- dbg: in selection_changed_cb ---")

		# Get file path
		self.thumbImage = self.thumbview.get_first_selected_image()
		Event = Gtk.get_current_event()
		filePath = None
		fileURL = None
		if self.thumbImage != None:		
			if self.Debug:
				fileURL = self.thumbImage.get_uri_for_display()
				# https://docs.python.org/2/library/urlparse.html
				filePath = urlparse(fileURL).path
				print('loading thumb meta: \n  ', filePath, '\n  URL: ', fileURL)
		else:
			if self.Debug:
				print('no metadata to load!')
			return False

		# Read metadata
		# http://python3-exiv2.readthedocs.org/en/latest/tutorial.html
		self.metadata = pyexiv2.ImageMetadata(filePath)
		try:
			self.metadata.read()
		except:
			self.metadata = None
			print("Cannot read meatadata.")
			return

		self.set_info()

		# return False to let any other callbacks execute as well
		return False

	def set_info(self):
		self.metadata_keys = self.metadata.exif_keys + self.metadata.iptc_keys + \
							self.metadata.xmp_keys

		if 'Exif.Image.DateTime' in self.metadata:
			time_iso = self.metadata['Exif.Image.DateTime'].value.strftime('%Y-%m-%d %H:%M:%S')
			print("Time: ", time_iso)
			self.win_label_time.set_text("Time: %s" % time_iso)

		previews = self.metadata.previews
		print("Number of thumbnails: ", len(previews))

