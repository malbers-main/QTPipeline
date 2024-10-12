import numpy as np
import pyvista as pv
import laspy
import os
from tkinter import Tk, filedialog

# Define a function to load a LAS file and extract point cloud data
def load_las_file(file_path):
    las_file = laspy.read(file_path)
    
    # Extract X, Y, Z coordinates and apply scale and offset
    points = np.vstack((las_file.X * las_file.header.scale[0] + las_file.header.offset[0],
                        las_file.Y * las_file.header.scale[1] + las_file.header.offset[1],
                        las_file.Z * las_file.header.scale[2] + las_file.header.offset[2])).transpose()
    
    point_cloud = pv.PolyData(points)
    point_cloud['Elevation'] = points[:, 2]  # Color by elevation (Z-axis)
    
    return point_cloud

# Use tkinter to open a folder dialog for selecting a folder with LAS files
def select_folder():
    root = Tk()
    root.withdraw()  # Hide the root window
    folder_selected = filedialog.askdirectory(title="Select Folder Containing LAS Files")
    return folder_selected

# Load all LAS files from the selected folder
def load_las_files_from_folder(folder_path):
    las_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith('.las')]
    data = [(file, load_las_file(file)) for file in las_files]  # Store filename and point_cloud
    return data

# Main program logic
def main():
    # Let the user select a folder containing LAS files
    folder_path = select_folder()

    # Load all LAS files from the selected folder
    las_data = load_las_files_from_folder(folder_path)
    
    if not las_data:
        print("No LAS files found in the selected folder.")
        return
    
    # Create the plotter and initialize the first point cloud
    plotter = pv.Plotter()
    plotter.set_background('grey')  # Set the background to black
    current_index = [0]  # A mutable reference to keep track of the current LAS file being displayed
    color_by_elevation = [True]  # A mutable reference to track if we are coloring by elevation

    # Function to update the plotter with the current point cloud
    def update_plot():
        plotter.clear()  # Clear previous plot
        file_name, point_cloud = las_data[current_index[0]]  # Get current data
        
        # If coloring by elevation, use 'Elevation' scalars, otherwise color all points blue
        if color_by_elevation[0]:
            plotter.add_mesh(point_cloud, scalars='Elevation', point_size=2, cmap='terrain', show_scalar_bar=False)
        else:
            plotter.add_mesh(point_cloud, color='blue', point_size=2)

        plotter.reset_camera()  # Reset camera to fit the new point cloud
        plotter.render()  # Render the updated scene

    # Function to toggle the coloration mode
    def toggle_coloration():
        color_by_elevation[0] = not color_by_elevation[0]  # Toggle between True and False
        update_plot()  # Update the plot to reflect the change

    # Define key event handlers for switching between LAS files
    def next_las_file():
        current_index[0] = (current_index[0] + 1) % len(las_data)  # Cycle forward through the list
        update_plot()

    def previous_las_file():
        current_index[0] = (current_index[0] - 1) % len(las_data)  # Cycle backward through the list
        update_plot()

    # Bind the arrow keys to switch between LAS files and 'T' to toggle coloration
    plotter.add_key_event("Right", next_las_file)  # Right arrow key to go to the next file
    plotter.add_key_event("Left", previous_las_file)  # Left arrow key to go to the previous file
    plotter.add_key_event("t", toggle_coloration)  # 'T' key to toggle coloration

    # Initialize the first point cloud and start the interactive plotting session
    update_plot()
    plotter.enable_eye_dome_lighting()  # Enable eye-dome lighting
    plotter.show()

# Run the main program
if __name__ == "__main__":
    main()