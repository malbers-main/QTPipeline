import numpy as np
import pyvista as pv
import laspy
import os
from tkinter import Tk, filedialog, Button, Label
import pyperclip

def load_las_file(file_path):
    try:
        las_file = laspy.read(file_path)
        points = np.vstack((las_file.X * las_file.header.scale[0] + las_file.header.offset[0],
                            las_file.Y * las_file.header.scale[1] + las_file.header.offset[1],
                            las_file.Z * las_file.header.scale[2] + las_file.header.offset[2])).transpose()

        if points.size == 0:
            raise ValueError("No points found in the LAS file.")

        scaling_factor = 100000  # Adjusted to 100,000
        points[:, 2] = points[:, 2] / scaling_factor

        point_cloud = pv.PolyData(points)

        if hasattr(las_file, 'red') and hasattr(las_file, 'green') and hasattr(las_file, 'blue'):
            colors = np.vstack((las_file.red, las_file.green, las_file.blue)).transpose()
            colors = (colors) / 255.0
            colors = np.clip(colors, 0, 255)
            point_cloud['Colors'] = colors / 255.0  # Normalize to [0, 1]
            return point_cloud, True
        else:
            point_cloud['Elevation'] = points[:, 2]
            return point_cloud, False

    except Exception:
        return None, False

def select_folder():
    root = Tk()
    root.withdraw()
    folder_selected = filedialog.askdirectory(title="Select Folder Containing LAS Files")
    return folder_selected

def load_las_files_from_folder(folder_path):
    las_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith('.las')]
    data = [(file, load_las_file(file)) for file in las_files]
    return [d for d in data if d[1][0] is not None]

class LASViewer:
    def __init__(self):
        self.folder_path = select_folder()
        self.las_data = load_las_files_from_folder(self.folder_path)

        if not self.las_data:
            return

        self.plotter = pv.Plotter()
        self.plotter.set_background('black')
        self.current_index = 0

        self.label = Label(text=f"File: {os.path.basename(self.las_data[self.current_index][0])}")
        self.label.pack()

        Button(text="Previous", command=self.previous_las_file).pack()
        Button(text="Next", command=self.next_las_file).pack()

        self.plotter.add_key_event("Right", self.next_las_file)
        self.plotter.add_key_event("Left", self.previous_las_file)
        self.plotter.add_key_event("d", self.copy_detection_id)
        self.plotter.add_key_event("c", self.copy_coordinates)

        self.update_plot()
        self.plotter.show()

    def update_plot(self):
        self.plotter.clear()
        file_name, (point_cloud, has_rgb) = self.las_data[self.current_index]

        if has_rgb:
            self.plotter.add_mesh(point_cloud, scalars='Colors', rgb=True, point_size=5, 
                                  show_scalar_bar=False, render_points_as_spheres=True)
        else:
            self.plotter.add_mesh(point_cloud, scalars='Elevation', point_size=5, 
                                  cmap='terrain', show_scalar_bar=True, render_points_as_spheres=True)

        self.plotter.add_axes()
        self.plotter.reset_camera()
        self.plotter.camera_position = 'xy'  
        self.plotter.render()

        self.label.config(text=f"File: {os.path.basename(file_name)}")

    def copy_detection_id(self):
        file_name = self.las_data[self.current_index][0]
        base_name = os.path.basename(file_name)

        detection_id = base_name.split("Detection_")[1].split(".las")[0]
        pyperclip.copy(detection_id)

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

    def next_las_file(self):
        if self.current_index < len(self.las_data) - 1:  # Prevent going past last file
            self.current_index += 1
            self.update_plot()

    def previous_las_file(self):
        if self.current_index > 0:  # Prevent going before the first file
            self.current_index -= 1
            self.update_plot()

if __name__ == "__main__":
    LASViewer()
