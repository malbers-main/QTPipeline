# LAS Viewer

This project is a LAS Viewer that allows users to load, visualize, and interact with point cloud data from `.las` files using a graphical interface built with PyQt5 and PyVista.

## Features

- Load and visualize `.las` files containing point cloud data.
- View RGB-colored point clouds or visualize using elevation data.
- Select and toggle visibility of multiple LAS files.
- Copy detection IDs and coordinates of selected points.
- Measure Z-distance between selected points in the point cloud.
- Dark mode user interface.

## Requirements

- Python 3.8+
- PyQt5
- PyVista
- PyVistaQt
- laspy
- pyperclip
- NumPy

## Installation

1. Clone this repository:
   ```sh
   git clone <repository_url>
   cd <repository_folder>
   ```

2. Create a virtual environment (recommended):
   ```sh
   python -m venv venv
   ```

3. Activate the virtual environment:
   - On Windows:
     venv\Scripts\activate

   - On macOS/Linux:
     source venv/bin/activate

4. Install the required packages:
   pip install -r requirements.txt


## Running the Application

To run the LAS Viewer, execute the following command in your terminal:
python las_viewer.py

## Creating an Executable on Windows

If you want to create a standalone executable that can run without requiring Python to be installed, you can use the `PyInstaller` package.

### Step-by-Step Instructions

1. Ensure the virtual environment is activated.

2. Install PyInstaller:
   pip install pyinstaller

3. Run the following command to create an executable:
   pyinstaller --onefile --windowed las_viewer.py

   - `--onefile`: Packages everything into a single executable.
   - `--windowed`: Ensures no console window appears when running the application.

4. After running the command, the executable will be available in the `dist` folder.

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

