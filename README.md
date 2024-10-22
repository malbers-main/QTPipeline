# LAS Viewer

This project is a LAS Viewer that allows users to load, visualize, and interact with point cloud data from `.las` files using a graphical interface built with PyQt5 and PyVista.

## Features

- Load and visualize `.las` files containing point cloud data.
- View RGB-colored point clouds or visualize using elevation data.
- Select and toggle visibility of multiple LAS files.
- Copy detection IDs and coordinates of selected points.
- Measure Z-distance between selected points in the point cloud.
- Dark mode user interface.

## Installation + Executable Creation

   - gh repo clone malbers-main/QTPipeline
   - cd QTPipeline
   - python -m venv venv
   - source venv/Scripts/activate
   - pip install numpy laspy pyperclip pyvista pyvistaqt PyQt5
   - pip install pyinstaller
   - pyinstaller --onefile --windowed las_viewer.py

### Notes:
- Ensure all dependencies are installed in the virtual environment before running PyInstaller.
- The executable may take a while to generate, and the first run may also take a little longer.

## Usage

1. Launch the application.
2. Use the "Select Folder" button to select a folder containing `.las` files.
3. View and interact with the point clouds in the viewer area.
4. Use various buttons and keyboard shortcuts for navigation and interaction.

## Keyboard Shortcuts

- `Right Arrow`: Load the next LAS file.
- `Left Arrow`: Load the previous LAS file.
- `d`: Copy detection ID.
- `c`: Copy coordinates.
- `r`: Restart and select a new folder.
- `p`: Select two points and find the height difference between them in meters.

## License

This project is licensed under the MIT License.

## Acknowledgments

- Developed using PyQt5 and PyVista for a smooth visualization experience.

## Issues

If you encounter any issues or have questions, please create an issue in the GitHub repository.

