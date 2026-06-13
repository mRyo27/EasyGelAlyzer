# EasyGelAlyzer

**EasyGelAlyzer** is a lightweight desktop application for quantitative analysis of gel electrophoresis images. It supports both protein (SDS-PAGE) and DNA gel modes, providing band position measurement, Rf value calculation, standard curve fitting, and molecular weight (or bp size) estimation — all within a single GUI.

---

## Features

- **Dual analysis modes** — Switch between Protein (SDS-PAGE, kDa) and DNA (agarose gel, bp)
- **Interactive image viewer** — Zoom, pan, rotate, and adjust brightness/contrast of gel images, with support for **Background Correction (Rolling-ball algorithm)**
- **Convenient Zoom & Position Reset** — Instantly reset zoom and pan settings using a double-click, middle double-click, or a double Shift press (automatically adjusts to cropped area after cropping)
- **Start/End line setup** — Place migration distance reference lines by clicking (can be fine-tuned by dragging afterwards)
- **Molecular weight marker registration** — Click marker bands and enter known sizes; the standard curve updates automatically (both manual entry and preset selection supported)
- **Improved MW Marker Display** — Displays labels outside the image to prevent overlapping with other annotations. Formats label text into two centered lines for better readability
- **Sample band measurement** — Click a sample band to automatically estimate its size from the standard curve (operates even when markers are toggled invisible)
- **Standard curve fitting** — Linear regression of log₁₀(size) vs. Rf with R² display; manual coefficient override supported
- **Enhanced Lane Labels & Repositioning** — Add draggable lane labels (MW marker / sample) above the gel image. Dragging lane labels features a slight snapping behavior near the center and displays alignment guidelines
- **Improved Layer Panel** — Toggle visibility (👁 icon) and export status (📷 icon) per annotation item. Supports renaming, reordering, and deletion. Added scrollbars to handle a large number of layers easily
- **Diverse Export Options** — Export results to **Excel** (`.xlsx`, including a fitted standard curve graph), **CSV** (`.csv`), or copy directly to your clipboard
- **High-Quality Image Export** — Automatically resizes low-resolution images (under 1200px short side / 1800px long side) up to 4x before drawing annotations. Draws diagonal annotation lines with anti-aliasing (internal 4x drawing and composite scaling) to reduce jagged edges
- **Project save / load** — Save all measurement data and the image to a `.gelproj` JSON file to resume later. **Direct project loading on startup** is supported
- **Smart Quit/Save Prompts** — Prompt to save changes only when unsaved changes exist (automatically saves as an overwrite when a project is already loaded)
- **Undo / Redo** — 20-step history for image state and annotations
- **Drag & drop** — Drop image files directly onto the canvas (requires `tkinterdnd2`)
- **Bilingual UI** — Toggle between English and Japanese at startup (can also be switched dynamically while the app is running)

---

## Installation

### Option A — Use a pre-built executable (recommended)

Download the latest `EasyGelAlyzer_version.zip` from the [Releases](../../releases) page, extract it, and double-click `dirt/EasyGelAlyzer.exe` or the launcer.exe. No Python or additional library installation is required.

### Option B — Build from source

To clone the repository and build the executable yourself:

1. **Set up the environment**

   The following are required:
   - **Python 3.9 or later**
   - **Windows** (required by PyInstaller)

   Install the necessary Python libraries:
   ```bash
   pip install pillow numpy matplotlib openpyxl pyinstaller
   pip install tkinterdnd2   # Optional — required for drag & drop support
   ```

2. **Run the build script**

   Execute `exe_build.bat` located in the repository root:
   - Double-click to run, or
   - Run from a terminal:
     ```bat
     exe_build.bat
     ```

3. **What the build script does**

   `exe_build.bat` performs the following steps automatically:
   - Reads the version number from `src/version.py`
   - If Git is available:
     - `git add .`
     - `git commit -m "Build vX.Y.Z"`
     - `git tag vX.Y.Z`
   - Creates a temporary build environment in the TEMP directory to avoid PyInstaller issues with non-ASCII paths
   - Runs PyInstaller and bundles:
     - `src/main.py`
     - `src/assets/` (icons, etc.)
   - Copies the finished `EasyGelAlyzer.exe` to the local `dist/` folder
   - Automatically creates `EasyGelAlyzer.lnk` (a shortcut)
   - Removes the temporary build folder

4. **Build output**

   On success, the following are generated:
   - `dist/EasyGelAlyzer.exe`
   - `EasyGelAlyzer.lnk` (shortcut)

   Use either of these to launch the application.

5. **Notes**
   - The build will abort if `src/version.py` does not exist.
   - The script is designed to build reliably even in environments with non-ASCII (e.g. Japanese) paths.
   - Icons inside `src/assets/` are automatically embedded into the exe.
   - If Git is not installed, the commit and tagging steps are skipped.

---

## Dependencies (required only for building)

| Library | Version |
|---|---|
| Python | 3.9+ |
| Pillow | ≥ 9.0 |
| NumPy | ≥ 1.21 |
| Matplotlib | ≥ 3.5 |
| openpyxl | ≥ 3.0 |
| PyInstaller | ≥ 5.0 |
| tkinterdnd2 | Optional (drag & drop) |

---

## Quick Start

1. **Launch** — Double-click `EasyGelAlyzer.exe` (if building from source, run `exe_build.bat` first).
2. **Select Mode / Load Project** — Choose **Protein (kDa)**, **DNA (bp)**, or load an existing project (`.gelproj`) using the **Load Project File** option to resume a previous session.
3. **Open an Image** — Go to *File → Open Image*, or drag and drop a JPEG / PNG / TIFF gel image onto the canvas.
4. **Pre-process (Optional)** — Adjust brightness/contrast or apply **Background Correction** if needed to clean up background noise.
5. **Set Reference Lines** — Click *Set Start Line* and click the top edge of the gel (Rf = 0), then click *Set End Line* and click the dye front or bottom of migration (Rf = 1).
6. **Add Markers** — Click *Add MW Marker*, click each marker band, and enter its known size (supports manual entry or preset lists. Press Esc to finish).
7. **Verify Standard Curve** — Check the R² value in the calibration panel (R² ≥ 0.95 is recommended). You can also overwrite regression coefficients manually.
8. **Add Samples** — Click *Add Sample*, then click each sample band; sizes are estimated automatically. Drag lane labels if needed (they snap to the center and show alignment lines).
9. **Export** — Export results using *Export → Excel* or *CSV*, or copy them using the copy-to-clipboard button. Generate final figures using *Export → Annotated Image*.
10. **Save** — Save all data using *File → Save Project* (`.gelproj`). If you are working on an existing project, you will be prompted to overwrite-save when exiting.

---

## Project Structure

```
src/
├── main.py              # Entry point
├── app.py               # EasyGelAlyzerApp class (integrates all Mixins)
├── common.py            # Shared imports, settings, and language utilities
├── version.py           # Version string (currently 4.0.0)
├── core/
│   ├── annotation.py    # Undo/redo, Rf calculation, marker/sample placement
│   ├── calibration.py   # Standard curve fitting and plotting
│   ├── excel_export.py  # Excel (.xlsx) export
│   ├── image_export.py  # Annotated image export
│   ├── image_manager.py # Image loading, zoom/pan, rotation, brightness/contrast
│   ├── project_io.py    # Project save/load (.gelproj)
│   └── utils.py         # Miscellaneous utilities
├── graphics/
│   ├── fonts.py         # Font resolution utilities
│   └── plot_manager.py  # Matplotlib canvas management
├── ui/
│   ├── main_window.py   # Main window layout and widget construction
│   └── dialogs.py       # Modal dialog helpers
├── i18n/
│   ├── translations.json  # EN/JA string table
│   ├── translations.py    # Compiled translation data
│   └── translator.py      # T() lookup function
└── assets/
    ├── icon.ico           # Application icon
    └── test_gel_image.png # Sample gel image for testing
```

---

## Standard Curve Calculation

The Rf value is calculated as:

```
Rf = (band y-coordinate − start line y-coordinate) / (end line y-coordinate − start line y-coordinate)
```

Linear regression is then performed:

```
log₁₀(size) = a × Rf + b
```

Unknown sizes are estimated using:

```
size = 10^(a × Rf + b)
```

If no markers are available, you can manually enter coefficients `a` and `b` directly in the standard curve panel.

---

## Export Details

### Excel (`.xlsx`)

Three sheets are generated:
- **Standard Curve sheet** — Marker name, Rf, size, log₁₀(size)
- **Results sheet** — Sample number, sample name, Rf, estimated size
- **Graph sheet** — Embedded standard curve graph image

### CSV (`.csv`)

Exports the sample results (Sample number, name, Rf, estimated size) into a plain text CSV file.

### Copy to Clipboard

Quickly copies the sample results table to the clipboard as tab-separated values, allowing easy pasting into spreadsheets or documents.

### Annotated Image

Saves the gel image along with annotated lines, markers, and text. You can choose from four different layouts.

- **Auto Resolution Upscaling**: Low-resolution images (under 1200px on the short side or 1800px on the long side) are automatically enlarged up to 4x before drawing annotations. This prevents annotations from looking pixelated and produces sharp, clean figures.
- **Anti-Aliasing**: Diagonal lines (such as sample/marker lines in layout modes) are drawn with anti-aliasing (drawn at 4x resolution internally and downscaled) to avoid jagged edges.
- **Grayscale / B&W Mode**: When grayscale export is active, annotation colors can be selected as black or white (margins appear gray for white annotations to maintain readability).
- **Experiment Memo**: Adds custom experimental logs to the bottom footer of the exported image.

Annotations like Start/End lines, MW markers, samples, and lane labels can be excluded from the exported image by unchecking their checkboxes in the **📷 (Camera) column** in the Layers tab.
Note that the **👁 (Eye) column** only controls visibility on the application canvas and does not affect the output image.

---

## Configuration File

User settings (such as language preference) are stored at:

```
~/.EasyGelAlyzer/gel_config.json
```

This file is created automatically on first launch.

---

## License

This project is released under the [MIT License](LICENSE).
