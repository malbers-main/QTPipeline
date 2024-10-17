import sys
import os
import numpy as np
import laspy
import pyperclip
import pyvista as pv
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog,
    QMessageBox, QHBoxLayout, QListWidget, QGridLayout, QListWidgetItem
)
from PyQt5.QtCore import Qt
from pyvistaqt import QtInteractor

scaling_factor = 100000  # Scaling factor to adjust Z values for visualization

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

        points[:, 2] /= scaling_factor
        point_cloud = pv.PolyData(points)

        if hasattr(las_file, 'red') and hasattr(las_file, 'green') and hasattr(las_file, 'blue'):
            colors = np.vstack((las_file.red, las_file.green, las_file.blue)).transpose()
            colors = colors / 255.0
            min_val = colors.min(axis=0)
            max_val = colors.max(axis=0)
            normalized_colors = (colors - min_val) / (max_val - min_val)
            adjusted_colors = 0.2 + normalized_colors * 0.6
            point_cloud['Colors'] = adjusted_colors
            return point_cloud, True
        else:
            point_cloud['Elevation'] = points[:, 2]
            return point_cloud, False

    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return None, False

def load_las_files_from_folder(folder_path):
    las_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith('.las')]
    return [(file, result) for file in las_files if (result := load_las_file(file))[0] is not None]

class CustomQtInteractor(QtInteractor):
    def mousePressEvent(self, event):
        if event.button() != Qt.RightButton:
            super().mousePressEvent(event)

class LASViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LAS Viewer")
        self.setGeometry(100, 100, 1200, 800)

        self.layout = QGridLayout()
        self.setLayout(self.layout)

        self.set_dark_mode()

        top_layout = QHBoxLayout()
        self.label = QLabel("")  # Removed filename display
        top_layout.addWidget(self.label)
        top_layout.addStretch()

        self.clear_button = QPushButton("Clear All")
        self.clear_button.clicked.connect(self.clear_all_files)
        top_layout.addWidget(self.clear_button)

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

        self.layout.addLayout(top_layout, 0, 0, 1, 2)

        self.las_file_list = QListWidget()
        self.las_file_list.setSelectionMode(QListWidget.MultiSelection)
        self.las_file_list.setFixedWidth(200)
        self.las_file_list.setStyleSheet("""
            QListWidget {
                background-color: #1e1e1e; 
                color: #ffffff;
            }
            QListWidget::item {
                color: #ffffff;
            }
            QListWidget::item:selected {
                background-color: blue;
                color: #ffffff;
            }
        """)
        self.las_file_list.itemSelectionChanged.connect(self.toggle_file_visibility)  # Connect signal
        self.layout.addWidget(self.las_file_list, 1, 0)

        self.plotter = CustomQtInteractor(self)
        self.layout.addWidget(self.plotter.interactor, 1, 1)

        self.plotter.enable_point_picking(callback=self.on_point_picked, tolerance=0.025, show_message=False,
                                           color='pink', point_size=10, show_point=True, picker='point')

        self.folder_path = ''
        self.las_data = []
        self.visible_files = set()  # Track which files are currently visible
        self.selected_points = []
        self.last_drawn_line = None

        self.plotter.add_key_event("Right", self.next_las_file)
        self.plotter.add_key_event("Left", self.previous_las_file)
        self.plotter.add_key_event("d", self.copy_detection_id)
        self.plotter.add_key_event("c", self.copy_coordinates)
        self.plotter.add_key_event("r", self.restart_program)

        self.select_folder_and_load()

    def restart_program(self):
        # Create a confirmation dialog
        reply = QMessageBox.question(
            self,
            "Confirm Restart",
            "Are you sure you want to restart and select a new folder? All current selections will be lost.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Clear all currently visible LAS files
            self.clear_all_files()

            # Prompt the user to select a new folder
            self.select_folder_and_load()


    def clear_all_files(self):
        """Clear all currently shown LAS files."""
        self.visible_files.clear()
        self.las_file_list.clearSelection()  # Clear the selection in the list
        self.update_plot()

    def toggle_file_visibility(self):
        """Update the visibility of selected LAS files."""
        self.visible_files.clear()

        for item in self.las_file_list.selectedItems():
            file_name, _ = self.las_data[self.las_file_list.row(item)]
            self.visible_files.add(file_name)
            item.setForeground(Qt.blue)  # Highlight selected items

        self.update_plot()

    def on_point_picked(self, picked_point, picker=None):
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

        self.las_file_list.clear()
        for file_name, _ in self.las_data:
            item = QListWidgetItem(os.path.basename(file_name))
            item.setForeground(Qt.white)  # Set initial item color to white
            self.las_file_list.addItem(item)

        self.update_plot()

    def update_plot(self):
        self.plotter.clear()
        self.plotter.set_background('#000000')

        for file_name in self.visible_files:
            index = next((i for i, (f, _) in enumerate(self.las_data) if f == file_name), None)
            if index is not None:
                point_cloud, has_rgb = self.las_data[index][1]
                if has_rgb:
                    self.plotter.add_mesh(point_cloud, scalars='Colors', rgb=True, point_size=6,
                                          show_scalar_bar=False, render_points_as_spheres=True, pickable=True)
                else:
                    self.plotter.add_mesh(point_cloud, scalars='Elevation', point_size=6,
                                          cmap='terrain', show_scalar_bar=False, render_points_as_spheres=True, pickable=True)

        self.plotter.add_axes()
        self.plotter.reset_camera()
        self.plotter.camera_position = 'xy'
        self.plotter.render()

    def copy_to_clipboard(self, text, description):
        try:
            pyperclip.copy(text)
            QMessageBox.information(self, "Copied", f"{description} '{text}' copied to clipboard.")
        except pyperclip.PyperclipException:
            QMessageBox.critical(self, "Error", "Failed to copy to clipboard.")

    def copy_detection_id(self):
        file_name = self.las_data[self.las_file_list.currentRow()][0]
        try:
            detection_id = file_name.split("Detection_")[1].split(".las")[0]
            self.copy_to_clipboard(detection_id, "Detection ID")
        except IndexError:
            QMessageBox.warning(self, "Error", "Could not extract Detection ID from the file name.")

    def copy_coordinates(self):
        _, (point_cloud, _) = self.las_data[self.las_file_list.currentRow()]
        points = point_cloud.points

        if points.size > 0:
            central_lat = np.mean(points[:, 1])
            central_lon = np.mean(points[:, 0])
            coordinates = f"{central_lat:.6f}, {central_lon:.6f}"
        else:
            coordinates = "No points available."

        self.copy_to_clipboard(coordinates, "Coordinates")

    def next_las_file(self):
        """Move to the next LAS file based on the largest index of visible files."""
        if not self.visible_files:
            QMessageBox.warning(self, "No Files Selected", "Please select at least one file to use the Next function.")
            return

        # Get the largest index of the currently visible files
        max_index = max(self.get_visible_file_indexes())

        if max_index < len(self.las_data) - 1:
            # Clear all visible files and display the next file
            self.clear_all_files()
            next_index = max_index + 1
            self.las_file_list.setCurrentRow(next_index)  # Move selection
            self.visible_files.add(self.las_data[next_index][0])  # Add next file to visible
            self.update_plot()
        else:
            QMessageBox.information(self, "End", "This is the last LAS file.")

    def previous_las_file(self):
        """Move to the previous LAS file based on the smallest index of visible files."""
        if not self.visible_files:
            QMessageBox.warning(self, "No Files Selected", "Please select at least one file to use the Previous function.")
            return

        # Get the smallest index of the currently visible files
        min_index = min(self.get_visible_file_indexes())

        if min_index > 0:
            # Clear all visible files and display the previous file
            self.clear_all_files()
            prev_index = min_index - 1
            self.las_file_list.setCurrentRow(prev_index)  # Move selection
            self.visible_files.add(self.las_data[prev_index][0])  # Add previous file to visible
            self.update_plot()
        else:
            QMessageBox.information(self, "Start", "This is the first LAS file.")

    def get_visible_file_indexes(self):
        """Retrieve the indexes of the currently visible files in the las_data list."""
        return [
            index for index, (file_name, _) in enumerate(self.las_data)
            if file_name in self.visible_files
        ]

    def closeEvent(self, event):
        self.plotter.close()
        event.accept()

def main():
    app = QApplication(sys.argv)
    viewer = LASViewer()
    
    viewer.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
