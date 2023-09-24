#!/bin/env python
import sys
import threading

from firepoint import create_halftone, default_values
import numpy as np
from PIL import Image
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GdkPixbuf, Gdk

SPACING = 5


# Utilities for gtk layout {{{
def parameter_row(label, widget, align=Gtk.Align.END):
    box = Gtk.HBox(spacing=SPACING)
    label_widget = Gtk.Label(label=label)
    box.pack_start(label_widget, False, False, 0)
    box.pack_start(widget, True, True, 0)
    # align label on the bottom
    label_widget.set_valign(align)
    widget.set_valign(align)
    return box


def only_odd(widget):
    val = widget.get_value()
    if val > 0:
        if val % 2 == 0:
            widget.set_value(val - 1)


# }}}


class ImageMoveApp(Gtk.Window):
    def __init__(self, image_path=None):
        super().__init__(title="firepoint-gtk")
        self._dirty = False

        self.WINDOW_SIZE = (800, 600)
        self.IMAGE_PATH = image_path

        if self.IMAGE_PATH is not None:
            self.load_image(self.IMAGE_PATH)
        else:
            self.image = None
            self.image_array = None
            self.original = None

        self.set_default_size(*self.WINDOW_SIZE)

        self.create_widgets()
        self.set_default_values()
        self.pack_widgets()
        self.connect_events()
        self.update_image()
        self.dotify_changed(self.dotify_button)

    def create_widgets(self):  # {{{
        default_adjustment = lambda: Gtk.Adjustment(
            step_increment=0.01, page_increment=0.1
        )
        default_int_adjustment = lambda: Gtk.Adjustment(
            step_increment=1, page_increment=5
        )
        # Unsharp
        self.unsharp_scale = Gtk.Scale(
            orientation=Gtk.Orientation.HORIZONTAL, adjustment=default_adjustment()
        )
        self.unsharp_scale.set_range(0, 5.0)
        self.unsharp_scale.set_digits(2)
        self.unsharp_radius_scale = Gtk.Scale(
            orientation=Gtk.Orientation.HORIZONTAL, adjustment=default_adjustment()
        )
        self.unsharp_radius_scale.set_range(0.01, 20.0)
        self.unsharp_radius_scale.set_digits(2)

        # Gamma
        self.gamma_scale = Gtk.Scale(
            orientation=Gtk.Orientation.HORIZONTAL, adjustment=default_adjustment()
        )
        self.gamma_scale.set_range(0.7, 1.6)
        self.gamma_scale.set_digits(2)

        # Multiply
        self.multiply_scale = Gtk.Scale(
            orientation=Gtk.Orientation.HORIZONTAL, adjustment=default_adjustment()
        )
        self.multiply_scale.set_digits(2)
        self.multiply_scale.set_range(0, 2.0)

        # Diameter
        self.max_diameter_scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL)
        self.max_diameter_scale.set_range(4, 8)

        # Spread
        self.spread_size_scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL)
        self.spread_size_scale.set_range(1, 10)

        self.pixel_size_entry = Gtk.SpinButton(
            adjustment=Gtk.Adjustment(
                value=0.08, lower=0.01, upper=0.2, step_increment=0.01
            )
        )
        self.pixel_size_entry.set_digits(2)

        self.image_width_entry = Gtk.SpinButton(
            adjustment=Gtk.Adjustment(
                value=4, lower=0.1, upper=4000, step_increment=1, page_increment=10
            )
        )
        self.image_width_entry.set_digits(2)

        # Normalize
        self.normalize_scale = Gtk.Scale(
            orientation=Gtk.Orientation.HORIZONTAL,
            adjustment=Gtk.Adjustment(
                value=0, lower=0, upper=1.0, step_increment=0.05, page_increment=0.1
            ),
        )
        self.normalize_scale.set_digits(2)

        # Sharpen
        self.sharpen_scale = Gtk.Scale(
            orientation=Gtk.Orientation.HORIZONTAL, adjustment=default_adjustment()
        )
        self.sharpen_scale.set_range(0, 1.0)
        self.sharpen_scale.set_digits(2)

        # Threshold
        self.threshold_scale = Gtk.Scale(
            orientation=Gtk.Orientation.HORIZONTAL, adjustment=default_int_adjustment()
        )
        self.threshold_scale.set_range(0, 100)

        # Hypersample
        self.hypersample_scale = Gtk.Scale(
            orientation=Gtk.Orientation.HORIZONTAL, adjustment=default_adjustment()
        )
        self.hypersample_scale.set_range(1, 7)
        self.hypersample_scale.set_digits(0)

        # Mid tone value
        self.midtone_value_scale = Gtk.Scale(
            orientation=Gtk.Orientation.HORIZONTAL, adjustment=default_int_adjustment()
        )
        self.midtone_value_scale.set_range(0, 255)
        self.midtone_value_scale.set_digits(0)

        # Buttons
        self.randomize_button = Gtk.CheckButton(label="Randomize")
        self.spread_button = Gtk.CheckButton(label="Spread")
        self.use_squares_button = Gtk.CheckButton(label="Use squares")
        self.dotify_button = Gtk.ToggleButton(label="Pointify")
        self.dotify_button.set_border_width(12)

        # set process button with "open" stock icon
        self.process_button = Gtk.Button(
            label="Save",
            image=Gtk.Image.new_from_icon_name(Gtk.STOCK_SAVE, Gtk.IconSize.BUTTON),
        )
        self.open_button = Gtk.Button(
            label="Open Image",
            image=Gtk.Image.new_from_icon_name(Gtk.STOCK_OPEN, Gtk.IconSize.BUTTON),
        )

        # Create an EventBox to hold the image
        self.image_event_box = Gtk.EventBox()
        self.image_label = Gtk.Image()
        self.image_label.set_can_focus(True)
        self.image_event_box.add(self.image_label)

        # }}}

    def set_default_values(self):  # {{{
        # Set default values for scales and toggles
        self.unsharp_scale.set_value(default_values["unsharp"])
        self.unsharp_radius_scale.set_value(default_values["unsharp_radius"])
        self.gamma_scale.set_value(default_values["gamma"])
        self.multiply_scale.set_value(default_values["multiply"])
        self.randomize_button.set_active(not default_values["no-randomize"])
        self.spread_button.set_active(not default_values["no-spread"])
        self.max_diameter_scale.set_value(default_values["max_diameter"])
        self.spread_size_scale.set_value(default_values["spread_size"])
        self.use_squares_button.set_active(default_values["use_squares"])
        self.normalize_scale.set_value(default_values["normalize"])
        self.sharpen_scale.set_value(default_values["sharpen"])
        self.threshold_scale.set_value(default_values["threshold"])
        self.hypersample_scale.set_value(default_values["hypersample"])
        self.midtone_value_scale.set_value(default_values["midtone_value"])
        # }}}

    def pack_widgets(self):  # {{{
        panel = Gtk.VBox(spacing=SPACING)

        panel.pack_start(self.open_button, False, False, SPACING * 2)
        panel.pack_start(self.process_button, False, False, 0)
        panel.pack_start(
            parameter_row(
                "Image width (cm):", self.image_width_entry, align=Gtk.Align.BASELINE
            ),
            False,
            False,
            0,
        )
        panel.pack_start(
            parameter_row(
                "Pixel size (mm):", self.pixel_size_entry, align=Gtk.Align.BASELINE
            ),
            False,
            False,
            0,
        )
        panel.pack_start(self.dotify_button, False, False, 0)
        panel.pack_start(self.use_squares_button, False, False, 0)
        panel.pack_start(self.randomize_button, False, False, 0)
        panel.pack_start(self.spread_button, False, False, 0)

        panel.pack_start(Gtk.Label(label="Settings:"), False, False, SPACING)
        panel.pack_start(parameter_row("Gamma:", self.gamma_scale), False, False, 0)
        panel.pack_start(
            parameter_row("Normalize:", self.normalize_scale), False, False, 0
        )
        panel.pack_start(parameter_row("Unsharp:", self.unsharp_scale), False, False, 0)
        panel.pack_start(
            parameter_row("Unsharp Radius:", self.unsharp_radius_scale), False, False, 0
        )
        panel.pack_start(parameter_row("Sharpen:", self.sharpen_scale), False, False, 0)
        panel.pack_start(
            parameter_row("Midtone Value:", self.midtone_value_scale), False, False, 0
        )
        panel.pack_start(Gtk.Label(label="Advanced:"), False, False, SPACING)
        panel.pack_start(
            parameter_row("Hypersample:", self.hypersample_scale), False, False, 0
        )
        panel.pack_start(
            parameter_row("Max Diameter:", self.max_diameter_scale), False, False, 0
        )
        panel.pack_start(
            parameter_row("Mutiply diam.:", self.multiply_scale), False, False, 0
        )
        panel.pack_start(
            parameter_row("Spread Size:", self.spread_size_scale), False, False, 0
        )
        panel.pack_start(
            parameter_row("Threshold:", self.threshold_scale), False, False, 0
        )
        quit_button = Gtk.Button.new_with_label("Quit")
        quit_button.connect("clicked", Gtk.main_quit)
        panel.pack_end(quit_button, False, False, SPACING)

        # Build root level widget & add it
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.add(self.image_event_box)
        panel_box = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)
        panel_box.add1(scrolled_window)
        panel_box.add2(panel)
        # set default width of panel to 100
        panel_box.set_position(500)

        self.add(panel_box)
        # }}}

    def connect_events(self):  # {{{
        # Connect signal handlers for parameter changes
        self.hypersample_scale.connect("value-changed", only_odd)
        self.unsharp_scale.connect("value-changed", self.update_image)
        self.unsharp_radius_scale.connect("value-changed", self.update_image)

        self.gamma_scale.connect("value-changed", self.update_image)
        self.multiply_scale.connect("value-changed", self.update_image)
        self.randomize_button.connect("toggled", self.update_image)
        self.spread_button.connect(
            "toggled",
            lambda widget: self.spread_size_scale.set_sensitive(widget.get_active()),
        )
        self.spread_button.connect("toggled", self.update_image)
        self.max_diameter_scale.connect("value-changed", self.update_image)
        self.spread_size_scale.connect("value-changed", self.update_image)
        self.image_width_entry.connect("value-changed", self.update_image)
        self.pixel_size_entry.connect("value-changed", self.update_image)
        # self.output_width_entry.connect("value-changed", self.update_image)
        self.dotify_button.connect("toggled", self.update_image)
        self.dotify_button.connect("toggled", self.dotify_changed)
        self.use_squares_button.connect("toggled", self.update_image)
        self.normalize_scale.connect("value-changed", self.update_image)
        self.sharpen_scale.connect("value-changed", self.update_image)
        self.threshold_scale.connect("value-changed", self.update_image)
        self.hypersample_scale.connect("value-changed", self.update_image)
        self.midtone_value_scale.connect("value-changed", self.update_image)

        self.process_button.connect("clicked", self.show_save_dialog)
        self.open_button.connect("clicked", self.show_open_dialog)

        self.connect("destroy", Gtk.main_quit)
        # }}}

    def load_image(self, image_path):
        self.image = Image.open(image_path)
        self.image_array = np.array(self.image).astype(np.uint8)
        self.original = self.image_array
        self.IMAGE_PATH = image_path

    def update_image(self, *a):  # Calls process_image in a thread {{{
        if self.image is None:
            return

        # Check if image processing is already ongoing
        if hasattr(self, "processing_thread") and self.processing_thread.is_alive():
            self._dirty = True
            return

        self._dirty = False
        # Start a new thread for image processing
        self.processing_thread = threading.Thread(
            target=self.process_image, daemon=True
        )
        self.processing_thread.start()  # }}}

    @property
    def output_width(self):
        return self.image_width_entry.get_value() / (
            self.pixel_size_entry.get_value() / 10.0
        )

    def process_image(self):  # {{{
        unsharp = self.unsharp_scale.get_value()
        unsharp_radius = self.unsharp_radius_scale.get_value()
        gamma = self.gamma_scale.get_value()
        multiply = self.multiply_scale.get_value()
        no_randomize = not self.randomize_button.get_active()
        no_spread = not self.spread_button.get_active()
        max_diameter = int(self.max_diameter_scale.get_value())
        spread_size = int(self.spread_size_scale.get_value())
        output_width = self.output_width
        use_squares = self.use_squares_button.get_active()
        no_dots = not self.dotify_button.get_active()
        normalize = self.normalize_scale.get_value()
        sharpen = self.sharpen_scale.get_value()
        threshold = int(self.threshold_scale.get_value())
        hypersample = self.hypersample_scale.get_value()
        midtone_value = int(self.midtone_value_scale.get_value())

        # Process the image using the create_halftone function
        processed_image_array = create_halftone(
            input_image=self.IMAGE_PATH,
            output_image=None,
            downscale_factor=1,
            unsharp=unsharp,
            unsharp_radius=unsharp_radius,
            gamma=gamma,
            multiply=multiply,
            randomize=not no_randomize,
            spread=not no_spread,
            max_diameter=max_diameter,
            spread_size=spread_size,
            output_width=output_width,
            use_squares=use_squares,
            normalize=normalize,
            sharpen=sharpen,
            threshold=threshold,
            no_dots=no_dots,
            hypersample=hypersample,
            midtone_value=midtone_value,
        )
        # Update the displayed image from the main thread
        thread_enter()
        self.update_display_image(processed_image_array.astype(np.uint8))
        thread_leave()
        if self._dirty:
            self._dirty = False
            self.process_image()
        # }}}

    def dotify_changed(self, widget):  # {{{
        sensitivity = widget.get_active()
        self.spread_button.set_sensitive(sensitivity)
        self.spread_size_scale.set_sensitive(
            sensitivity and self.spread_button.get_active()
        )
        self.max_diameter_scale.set_sensitive(sensitivity)
        self.multiply_scale.set_sensitive(sensitivity)
        self.midtone_value_scale.set_sensitive(sensitivity)
        self.randomize_button.set_sensitive(sensitivity)
        self.threshold_scale.set_sensitive(sensitivity)
        self.use_squares_button.set_sensitive(sensitivity)
        self.image_width_entry.set_sensitive(sensitivity)
        self.pixel_size_entry.set_sensitive(sensitivity)
        # }}}

    def update_display_image(self, image_array):  # {{{
        if self.image is None:
            return

        if len(image_array.shape) == 2:
            image_array = np.stack((image_array, image_array, image_array), axis=-1)
        height, width, _ = image_array.shape

        img = GdkPixbuf.Pixbuf.new_from_data(
            image_array.tobytes(),
            GdkPixbuf.Colorspace.RGB,
            False,
            8,
            width,
            height,
            3 * width,
        )

        self.image_label.set_from_pixbuf(img)  # }}}

    def process_and_save_image(self, filename):  # {{{
        if self.image is None:
            return

        # Get the current parameter values from the scales and toggles
        unsharp = self.unsharp_scale.get_value()
        unsharp_radius = self.unsharp_radius_scale.get_value()
        gamma = self.gamma_scale.get_value()
        multiply = self.multiply_scale.get_value()
        no_randomize = not self.randomize_button.get_active()
        no_spread = self.spread_button.get_active()
        max_diameter = int(self.max_diameter_scale.get_value())
        spread_size = int(self.spread_size_scale.get_value())
        output_width = int(self.output_width_button.get_active())
        use_squares = self.use_squares_button.get_active()
        no_dots = not self.dotify_button.get_active()
        normalize = self.normalize_scale.get_value()
        sharpen = self.sharpen_scale.get_value()
        threshold = int(self.threshold_scale.get_value())
        hypersample = self.hypersample_scale.get_value()
        midtone_value = int(self.midtone_value_scale.get_value())

        # Process the image using the create_halftone function
        processed_image_array = create_halftone(
            input_image=self.IMAGE_PATH,
            output_image=None,
            downscale_factor=downscale_factor,
            unsharp=unsharp,
            unsharp_radius=unsharp_radius,
            gamma=gamma,
            multiply=multiply,
            no_randomize=no_randomize,
            no_spread=no_spread,
            max_diameter=max_diameter,
            spread_size=spread_size,
            width=output_width,
            use_squares=use_squares,
            normalize=normalize,
            sharpen=sharpen,
            threshold=threshold,
            no_dots=no_dots,
            hypersample=hypersample,
            midtone_value=midtone_value,
        )

        # Create an Image object from the processed array
        processed_image = Image.fromarray(processed_image_array.astype(np.uint8))

        # Save the processed image to the specified file
        processed_image.save(filename)  # }}}

    # Dialogs/Modals {{{
    def show_save_dialog(self, widget):
        if self.image is None:
            return

        dialog = Gtk.FileChooserDialog(
            "Save Processed Image",
            self,
            Gtk.FileChooserAction.SAVE,
            (
                Gtk.STOCK_CANCEL,
                Gtk.ResponseType.CANCEL,
                Gtk.STOCK_SAVE,
                Gtk.ResponseType.OK,
            ),
        )

        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.set_do_overwrite_confirmation(True)
        dialog.set_current_name("processed_image.jpg")

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.process_and_save_image(dialog.get_filename())
        dialog.destroy()

    def show_open_dialog(self, widget):
        dialog = Gtk.FileChooserDialog(
            title="Open Image",
            parent=self,
            action=Gtk.FileChooserAction.OPEN,
        )
        dialog.add_button(Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        dialog.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)

        dialog.set_default_response(Gtk.ResponseType.OK)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.load_image(dialog.get_filename())
            self.update_image()
        dialog.destroy()

    # }}}


def thread_enter():
    if Gtk.get_minor_version() < 6:
        Gdk.threads_enter()  # Initialize Gdk threads


def thread_leave():
    if Gtk.get_minor_version() < 6:
        Gdk.threads_leave()


def main():
    if Gtk.get_minor_version() < 6:
        Gdk.threads_init()  # Initialize Gdk threads
    if len(sys.argv) < 2:
        app = ImageMoveApp()
    else:
        image_path = sys.argv[1]
        app = ImageMoveApp(image_path)

    app.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
