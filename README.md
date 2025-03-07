# eogRichExif (the MADIS version)

A eog (Eye of GNOME Image Viewer) plugin which shows the metadata set by the UnderCurrency MADIS scanner.

Based on [eogRichExif by count bewantbe](https://github.com/bewantbe/eogRichExif)

To install, put these files (eogRichExifMADIS.glade, eogRichExifMADIS.py, eogRichExifMADIS.plugin) in

  $XDG_DATA_HOME/eog/plugins/eogRichExifMADIS/

Usually default value for $XDG_DATA_HOME is $HOME/.local/share (at least for gnome 3.14)

Need to install libexiv2, python3-dev, py3exiv2(http://python3-exiv2.readthedocs.org/en/latest/index.html you will need to compile it your self).

Then enable it in eog Preferences, Plugins tab.
