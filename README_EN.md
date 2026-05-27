# EasyGelAlyzer

**EasyGelAlyzer** is a lightweight desktop application for quantitative analysis of gel electrophoresis images. It supports both protein (SDS-PAGE) and DNA gel modes, providing band position measurement, Rf value calculation, standard curve fitting, and molecular weight (or fragment size) estimation — all within a single GUI.

---

## Features

- **Dual analysis modes** — Switch between Protein (SDS-PAGE, kDa) and DNA (agarose gel, bp)
- **Interactive image viewer** — Zoom, pan, rotate, and adjust brightness/contrast of gel images
- **Start/End line setup** — Place migration distance reference lines by clicking or dragging
- **Molecular weight marker registration** — Click marker bands and enter known sizes; the standard curve updates automatically
- **Sample band measurement** — Click a sample band to automatically estimate its size from the standard curve
- **Standard curve fitting** — Linear regression of log₁₀(size) vs. Rf with R² display; manual coefficient override supported
- **Lane labels** — Add draggable lane labels (MW marker / sample) above the gel image
- **Layer panel** — Toggle visibility and export status per annotation item; supports renaming, reordering, and deletion
- **Excel export** — Export marker data, sample results, and the standard curve graph to a multi-sheet `.xlsx` file
- **Annotated image export** — Save the gel image with all annotations drawn; multiple layout options available
- **Project save / load** — Save all measurement data and the image to a `.gelproj` JSON file to resume later
- **Undo / Redo** — 20-step history for image state
- **Drag & drop** — Drop image files directly onto the canvas (requires `tkinterdnd2`)
- **Bilingual UI** — Switch between English and Japanese at startup

---

## Installation

### Option A — Use a pre-built executable (recommended)

Download the latest `EasyGelAlyzer_version.zip` from the [Releases](../../releases) page, extract it, and double-click `EasyGelAlyzer.exe` or the provided shortcut. No Python or additional library installation is required.

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
2. **Select mode** — Choose **Protein (kDa)** or **DNA (bp)** in the startup dialog.
3. **Open an image** — Go to *File → Open Image*, or drag a JPEG / PNG / TIFF gel image onto the canvas.
4. **Set reference lines** — Click *Set Start Line* and click the top edge of the gel, then click *Set End Line* and click the dye front (or bottom of migration).
5. **Add markers** — Click *Add Marker*, then click each marker band and enter its known size.
6. **Check the standard curve** — Verify the R² value in the standard curve panel (R² ≥ 0.95 is recommended).
7. **Add samples** — Click *Add Sample*, then click each sample band; sizes are estimated automatically.
8. **Export** — Use *Export → Excel* for tabular data, or *Export → Annotated Image* for figures intended for papers or reports.
9. **Save** — Use *File → Save Project* (`.gelproj`) to save all data and resume later.

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

### Annotated Image

Four layout options are available:
1. Annotated gel image only
2. Gel image + results table
3. Gel image + standard curve graph
4. Gel image + table + graph (combined)

Grayscale mode and margin trimming options are also available.

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
