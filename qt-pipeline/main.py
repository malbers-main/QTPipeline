import sys
import os
import numpy as np
import laspy
import pyperclip
import pyvista as pv

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog,
    QMessageBox, QHBoxLayout
)

from PyQt5.QtCore import Qt
from pyvistaqt import QtInteractor  # Ensure you have pyvistaqt installed

scaling_factor = 1  # Adjusted to 100,000

def load_las_file(file_path):
    try:
        las_file = laspy.read(file_path)
        points = np.vstack((
            las_file.X * las_file.header.scale[0] + las_file.header.offset[0],
            las_file.Y * las_file.header.scale[1] + las_file.header.offset[1],
            las_file.Z * las_file.header.scale[2] + las_file.header.offset[2]
        )).transpose()

        if points.size == 0:
            raise ValueError("No points found in the LAS file.")

        points[:, 2] = points[:, 2] / scaling_factor
        point_cloud = pv.PolyData(points)

        if hasattr(las_file, 'red') and hasattr(las_file, 'green') and hasattr(las_file, 'blue'):
            colors = np.vstack((las_file.red, las_file.green, las_file.blue)).transpose()
            colors = (colors) / 255.0
            colors = np.clip(colors, 0, 255)
            point_cloud['Colors'] = colors
            return point_cloud, True
        else:
            point_cloud['Elevation'] = points[:, 2]
            return point_cloud, False

    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return None, False


def load_las_files_from_folder(folder_path):
    las_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith('.las')]
    data = [(file, load_las_file(file)) for file in las_files]
    return [d for d in data if d[1][0] is not None]


class LASViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LAS Viewer")
        self.setGeometry(100, 100, 1200, 800)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Top layout for buttons and label
        top_layout = QHBoxLayout()
        self.layout.addLayout(top_layout)

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

        # PyVista QtInteractor
        self.plotter = QtInteractor(self)
        self.layout.addWidget(self.plotter.interactor)

        # Initialize variables
        self.folder_path = ''
        self.las_data = []
        self.current_index = 0
        self.selected_points = []

        # Key event handling using add_key_event
        self.plotter.add_key_event("Right", self.next_las_file)
        self.plotter.add_key_event("Left", self.previous_las_file)
        self.plotter.add_key_event("d", self.copy_detection_id)
        self.plotter.add_key_event("c", self.copy_coordinates)
        self.plotter.add_key_event("r", self.confirm_reset_program)
        self.plotter.add_key_event("l", self.confirm_close_program)
        self.plotter.add_key_event("p", self.handle_point_pick)  # Add key for toggling point-picking mode

        # Load LAS files
        self.select_folder_and_load()

    def select_folder_and_load(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder Containing LAS Files")
        if not folder:
            QMessageBox.warning(self, "No Folder Selected", "Please select a folder to proceed.")
            sys.exit()
        self.folder_path = folder
        self.las_data = load_las_files_from_folder(self.folder_path)

        if not self.las_data:
            QMessageBox.critical(self, "No LAS Files", "No valid LAS files found in the selected folder.")
            sys.exit()

        self.current_index = 0
        self.update_plot()

    def update_plot(self):
        # Clear the plot before loading the new point cloud
        self.plotter.clear()

        # Get the current LAS file's point cloud and RGB status
        file_name, (point_cloud, has_rgb) = self.las_data[self.current_index]

        # Plot the point cloud based on whether it has RGB colors or elevation data
        if has_rgb:
            self.plotter.add_mesh(point_cloud, scalars='Colors', rgb=True, point_size=5,
                                  show_scalar_bar=False, render_points_as_spheres=True, pickable=True)
        else:
            self.plotter.add_mesh(point_cloud, scalars='Elevation', point_size=5,
                                  cmap='terrain', show_scalar_bar=False, render_points_as_spheres=True, pickable=True)

        # Add axes and reset the camera for a good view
        self.plotter.add_axes()
        self.plotter.reset_camera()
        self.plotter.camera_position = 'xy'
        self.plotter.render()

        # Update the label to show the current file's name
        self.label.setText(f"File: {os.path.basename(file_name)}")

    def copy_detection_id(self):
        file_name = self.las_data[self.current_index][0]
        base_name = os.path.basename(file_name)

        try:
            detection_id = base_name.split("Detection_")[1].split(".las")[0]
            pyperclip.copy(detection_id)
            QMessageBox.information(self, "Copied", f"Detection ID '{detection_id}' copied to clipboard.")
        except IndexError:
            QMessageBox.warning(self, "Error", "Could not extract Detection ID from the file name.")

    def copy_coordinates(self):
        _, (point_cloud, _) = self.las_data[self.current_index]
        points = point_cloud.points

        if points.size > 0:
            central_lat = np.mean(points[:, 1])  # Latitude (Y)
            central_lon = np.mean(points[:, 0])  # Longitude (X)
            coordinates = f"{central_lat}, {central_lon}"
        else:
            coordinates = "No points available."

        pyperclip.copy(coordinates)
        QMessageBox.information(self, "Copied", f"Coordinates '{coordinates}' copied to clipboard.")

    def next_las_file(self):
        if self.current_index < len(self.las_data) - 1:
            self.current_index += 1
            self.update_plot()
        else:
            QMessageBox.information(self, "End", "This is the last LAS file.")

    def previous_las_file(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.update_plot()
        else:
            QMessageBox.information(self, "Start", "This is the first LAS file.")

    def confirm_reset_program(self):
        reply = QMessageBox.question(self, 'Reset Program',
                                     "Are you sure you want to reset and load new LAS files?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.select_folder_and_load()

    def confirm_close_program(self):
        reply = QMessageBox.question(self, 'Quit Program',
                                     "Are you sure you want to quit?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.close()

    def closeEvent(self, event):
        self.plotter.close()
        event.accept()


class StartMenu(QWidget):
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
