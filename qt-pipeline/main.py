import numpy as np
import pyvista as pv
import laspy
import os
from tkinter import Tk, filedialog, Button, Label, messagebox
import pyperclip
import sys

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
            point_cloud['Colors'] = colors
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
        self.line_actor = None
        self.label_actors = []
        self.selected_points = []
        self.initialize_viewer()

    def initialize_viewer(self):
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
        self.plotter.add_key_event("r", self.confirm_reset_program)
        self.plotter.add_key_event("l", self.confirm_close_program)

        # Enable point picking
        self.plotter.enable_point_picking(callback=self.handle_point_pick)
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
                                  cmap='terrain', show_scalar_bar=False, render_points_as_spheres=True)

        self.plotter.add_axes()
        self.plotter.reset_camera()
        self.plotter.camera_position = 'xy'
        self.plotter.render()

        self.label.config(text=f"File: {os.path.basename(file_name)}")

    def handle_point_pick(self, point):
        self.selected_points.append(point)
        print(f"Selected point: {point}")
        
        # Once two points are picked, calculate the z-distance
        if len(self.selected_points) == 2:
            z_distance = abs(self.selected_points[0][2] - self.selected_points[1][2])
            print(f"Z-distance between points: {round(z_distance, 3)}")
            messagebox.showinfo("Z-Distance", f"Z-distance between points: {round(z_distance, 3)}")
            
            # Reset the selected points after calculation
            self.selected_points.clear()

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
        if self.current_index < len(self.las_data) - 1:
            self.current_index += 1
            self.update_plot()

    def previous_las_file(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.update_plot()

    def confirm_reset_program(self):
        confirm = messagebox.askyesno("Reset Program", "Are you sure you want to reset and load new LAS files?")
        if confirm:
            self.restart_program()  
    
    def restart_program(self):
        self.plotter.close()
        self.initialize_viewer()

    def confirm_close_program(self):
        confirm = messagebox.askyesno("Quit Program", "Are you sure you want to quit?")
        if confirm:
            self.close_program()

    def close_program(self):
        """Closes the plotter and exits the program."""
        self.plotter.close()
        sys.exit()

def start_program():
    """Function to start the LASViewer program."""
    start_menu.destroy()  # Close the start menu window
    LASViewer()  # Start the main LASViewer program

# Create the Start Menu
start_menu = Tk()
start_menu.geometry('300x100')
start_menu.title("Start Menu")

# Create a button that starts the program
start_button = Button(start_menu, text="Start LAS Viewer", command=start_program, 
                      padx=20, pady=10, font=("Helvetica", 14))
start_button.pack(pady=20)

# Run the start menu's event loop
start_menu.mainloop()
