import sys
import os
import numpy as np
import laspy
import pyperclip
import pyvista as pv
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog,
    QMessageBox, QHBoxLayout, QListWidget, QGridLayout
)
from PyQt5.QtCore import Qt
from pyvistaqt import QtInteractor
import webbrowser

scaling_factor = 100000  # Scaling factor to adjust Z values for visualization

def load_las_file(file_path):
    """
    Load a .las file and extract its point cloud data.

    Args:
        file_path (str): Path to the .las file.

    Returns:
        tuple: A PyVista PolyData object and a boolean indicating if RGB colors are available.
    """
    try:
        las_file = laspy.read(file_path)
        points = np.vstack((
            las_file.X * las_file.header.scale[0] + las_file.header.offset[0],
            las_file.Y * las_file.header.scale[1] + las_file.header.offset[1],
            las_file.Z * las_file.header.scale[2] + las_file.header.offset[2]
        )).transpose()

        if points.size == 0:
            raise ValueError("No points found in the LAS file.")

        # Scale Z axis to match visualization requirements
        points[:, 2] /= scaling_factor
        point_cloud = pv.PolyData(points)

        # Check if RGB color data is available and add it
        if hasattr(las_file, 'red') and hasattr(las_file, 'green') and hasattr(las_file, 'blue'):
            colors = np.vstack((las_file.red, las_file.green, las_file.blue)).transpose()
            colors = colors / 255.0  # Normalize to range [0, 1]

            # Normalize colors to a new gradient range [0.2, 0.8]
            min_val = colors.min(axis=0)
            max_val = colors.max(axis=0)
            normalized_colors = (colors - min_val) / (max_val - min_val)
            adjusted_colors = 0.2 + normalized_colors * 0.6  # Scale to [0.2, 0.8]

            point_cloud['Colors'] = adjusted_colors
            return point_cloud, True
        else:
            point_cloud['Elevation'] = points[:, 2]
            return point_cloud, False

    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return None, False


def load_las_files_from_folder(folder_path):
    """
    Load all .las files from a specified folder.

    Args:
        folder_path (str): Path to the folder containing .las files.

    Returns:
        list: A list of tuples containing the file name and its corresponding PolyData.
    """
    las_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith('.las')]
    return [(file, load_las_file(file)) for file in las_files if load_las_file(file)[0] is not None]


class CustomQtInteractor(QtInteractor):
    """
    Custom PyVista interactor to disable right-click events.
    """
    def mousePressEvent(self, event):
        if event.button() != Qt.RightButton:
            super().mousePressEvent(event)

class LASViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LAS Viewer")
        self.setGeometry(100, 100, 1200, 800)

        # Set the main layout to QGridLayout
        self.layout = QGridLayout()
        self.setLayout(self.layout)

        # Set dark mode for the UI
        self.set_dark_mode()

        # Top layout for buttons and label (row 0, spanning 2 columns)
        top_layout = QHBoxLayout()

        self.label = QLabel("No file loaded")
        top_layout.addWidget(self.label)

        top_layout.addStretch()

        self.prev_button = QPushButton("Previous")
        self.prev_button.clicked.connect(self.previous_las_file)
        top_layout.addWidget(self.prev_button)

        self.next_button = QPushButton("Next")
        self.next_button.clicked.connect(self.next_las_file)
        top_layout.addWidget(self.next_button)

        self.copy_id_button = QPushButton("Copy Detection ID")
        self.copy_id_button.clicked.connect(self.copy_detection_id)
        top_layout.addWidget(self.copy_id_button)

        self.copy_coords_button = QPushButton("Copy Coordinates")
        self.copy_coords_button.clicked.connect(self.copy_coordinates)
        top_layout.addWidget(self.copy_coords_button)

        # Add top layout to the first row of the grid layout, spanning two columns
        self.layout.addLayout(top_layout, 0, 0, 1, 2)

        # Create a grid layout for the file list and the plotter (row 1, two columns)
        self.las_file_list = QListWidget()
        self.las_file_list.setFixedWidth(150)
        self.las_file_list.setStyleSheet("""
            QListWidget {
                background-color: #1e1e1e;  
                color: #ffffff;
            }
            QListWidget::item:selected {
                background-color: blue;
                color: #ffffff;
            }
        """)
        self.las_file_list.itemClicked.connect(self.load_selected_file)
        self.layout.addWidget(self.las_file_list, 1, 0)

        # PyVista QtInteractor in the second column (right)
        self.plotter = QtInteractor(self)
        self.layout.addWidget(self.plotter.interactor, 1, 1)

        # Use the custom interactor to disable right-click
        self.plotter = CustomQtInteractor(self)
        self.layout.addWidget(self.plotter.interactor, 1, 1)

        self.plotter.enable_point_picking(
                callback=self.on_point_picked,
                tolerance=0.025,
                show_message=False,
                color='pink',
                point_size=10,
                show_point=True,
                picker='point'
        )

        # Initialize variables
        self.folder_path = ''
        self.las_data = []
        self.current_index = 0
        self.selected_points = []
        self.last_drawn_line = None
        self.point_picking_enabled = False

        # Key event handling
        self.plotter.add_key_event("Right", self.next_las_file)
        self.plotter.add_key_event("Left", self.previous_las_file)
        self.plotter.add_key_event("d", self.copy_detection_id)
        self.plotter.add_key_event("c", self.copy_coordinates)
        self.plotter.add_key_event("r", self.confirm_reset_program)
        self.plotter.add_key_event("l", self.confirm_close_program)

        # Load LAS files
        self.select_folder_and_load()

    def on_point_picked(self, picked_point, picker=None):
        """
        Handle point selection for distance measurement. When two points are picked,
        the Z-distance between them is calculated and displayed.
        """
        self.selected_points.append(picked_point)

        if len(self.selected_points) == 2:
            point1, point2 = self.selected_points
            z_distance = round(abs(scaling_factor * (point2[2] - point1[2])), 3)
            QMessageBox.information(self, "Z-Distance", f"Z-distance: {z_distance:.1f}")

            if self.last_drawn_line:
                self.plotter.remove_actor(self.last_drawn_line)

            line = pv.Line(point1, point2)
            self.last_drawn_line = self.plotter.add_mesh(line, color='red', line_width=3, pickable=False)
            self.selected_points.clear()
            self.plotter.render()

    def set_dark_mode(self):
        """
        Apply dark mode styling to the PyQt5 interface.
        """
        dark_qss = """
        QWidget {
            background-color: #121212;
            color: #ffffff;
        }
        QPushButton {
            background-color: #1e1e1e;
            color: #ffffff;
            border: 1px solid #3d3d3d;
            padding: 5px;
        }
        QPushButton:hover {
            background-color: #373737;
        }
        QLabel {
            color: #ffffff;
        }
        QMessageBox QLabel {
            color: #ffffff;
        }
        """
        self.setStyleSheet(dark_qss)


    def load_selected_file(self, item):
        # Get the index of the selected item
        index = self.las_file_list.row(item)
        if index != self.current_index:  # Check if the selected index is different
            self.current_index = index  # Update the current index
            self.update_plot()  # Update the plot with the selected file

    def select_folder_and_load(self):
        """
        Open a folder dialog to select a folder containing LAS files.
        """
        folder = QFileDialog.getExistingDirectory(self, "Select Folder Containing LAS Files")
        if not folder:
            QMessageBox.warning(self, "No Folder Selected", "Please select a folder to proceed.")
            sys.exit()

        self.folder_path = folder
        self.las_data = load_las_files_from_folder(self.folder_path)

        if not self.las_data:
            QMessageBox.critical(self, "No LAS Files", "No valid LAS files found in the selected folder.")
            sys.exit()

        # Clear and populate the QListWidget with LAS file names
        self.las_file_list.clear()
        for file_name, _ in self.las_data:
            self.las_file_list.addItem(os.path.basename(file_name))

        self.current_index = 0
        self.update_plot()

    def update_plot(self):
        """
        Update the visual plot with the current LAS file's data.
        """
        self.plotter.clear()
        self.plotter.set_background('#000000')

        file_name, (point_cloud, has_rgb) = self.las_data[self.current_index]

        if has_rgb:
            self.plotter.add_mesh(point_cloud, scalars='Colors', rgb=True, point_size=5,
                                  show_scalar_bar=False, render_points_as_spheres=True, pickable=True)
        else:
            self.plotter.add_mesh(point_cloud, scalars='Elevation', point_size=5,
                                  cmap='terrain', show_scalar_bar=False, render_points_as_spheres=True, pickable=True)

        self.plotter.add_axes()
        self.plotter.reset_camera()
        self.plotter.camera_position = 'xy'
        self.plotter.render()

        self.label.setText(f"File: {os.path.basename(file_name)}")

        # Highlight the current LAS file in the list
        self.las_file_list.setCurrentRow(self.current_index)

    def copy_detection_id(self):
        """
        Copy the detection ID (extracted from the file name) to the clipboard.
        """
        file_name = self.las_data[self.current_index][0]
        try:
            detection_id = file_name.split("Detection_")[1].split(".las")[0]
            pyperclip.copy(detection_id)
            QMessageBox.information(self, "Copied", f"Detection ID '{detection_id}' copied to clipboard.")
        except IndexError:
            QMessageBox.warning(self, "Error", "Could not extract Detection ID from the file name.")

    def copy_coordinates(self):
        """
        Copy the central coordinates (latitude and longitude) of the current point cloud to the clipboard.
        """
        _, (point_cloud, _) = self.las_data[self.current_index]
        points = point_cloud.points

        if points.size > 0:
            central_lat = np.mean(points[:, 1])
            central_lon = np.mean(points[:, 0])
            coordinates = f"{central_lat:.6f}, {central_lon:.6f}"
        else:
            coordinates = "No points available."

        pyperclip.copy(coordinates)
        QMessageBox.information(self, "Copied", f"Coordinates '{coordinates}' copied to clipboard.")

    def next_las_file(self):
        """
        Move to the next LAS file in the folder.
        """
        if self.current_index < len(self.las_data) - 1:
            self.current_index += 1
            self.update_plot()
        else:
            QMessageBox.information(self, "End", "This is the last LAS file.")

    def previous_las_file(self):
        """
        Move to the previous LAS file in the folder.
        """
        if self.current_index > 0:
            self.current_index -= 1
            self.update_plot()
        else:
            QMessageBox.information(self, "Start", "This is the first LAS file.")

    def confirm_reset_program(self):
        """
        Confirm and reset the program, allowing the user to select a new folder of LAS files.
        """
        reply = QMessageBox.question(self, 'Reset Program',
                                     "Are you sure you want to reset and load new LAS files?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.select_folder_and_load()

    def confirm_close_program(self):
        """
        Confirm and close the program.
        """
        reply = QMessageBox.question(self, 'Quit Program',
                                     "Are you sure you want to quit?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.close()

    def axis_reset(self):
        self.plotter.camera_position = 'xy'

    def closeEvent(self, event):
        """
        Handle the closing event and clean up the plotter.
        """
        self.plotter.close()
        event.accept()


class StartMenu(QWidget):
    """
    Start menu to launch the LAS Viewer.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Start Menu")
        self.setGeometry(100, 100, 300, 100)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.start_button = QPushButton("Start LAS Viewer")
        self.start_button.setFixedSize(200, 50)
        self.start_button.clicked.connect(self.start_program)

        self.layout.addStretch()
        self.layout.addWidget(self.start_button, alignment=Qt.AlignCenter)
        self.layout.addStretch()

    def start_program(self):
        """
        Launch the LAS Viewer and close the start menu.
        """
        self.viewer = LASViewer()
        self.viewer.show()
        self.close()


def main():
    app = QApplication(sys.argv)
    start_menu = StartMenu()
    start_menu.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()