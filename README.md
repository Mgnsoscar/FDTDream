# FDTDream

**FDTDream** is a Python framework for creating simulation geometries in Lumerical FDTD, specifically designed for thin film applications. The framework includes a custom database where extracted simulation results are saved for easy access and analysis.

## Prerequisites

- A valid license for **Lumerical FDTD**.
- **FDTD** installed on your computer.
- Python packages listed in `requisites.txt` installed.
- Correctly configured path to the **Lumerical Python API** (`lumapi.py`). This is usually found in a default directory, but you may need to update the path if the code does not work.

## Getting Started

1. **Verify lumapi.py Import:**
   Ensure that you are importing `lumapi.py` from the correct directory. In the `Simulation.py` file, you will find the following code snippet:

   ```python
   # Import the Lumerical Python API
   import importlib.util
   spec_win = importlib.util.spec_from_file_location(
       name='lumapi', 
       location=r"C:\Program Files\Lumerical\v241\api\python\lumapi.py"
   )
   lumapi = importlib.util.module_from_spec(spec_win)
   spec_win.loader.exec_module(lumapi)
   ```
   
   If you can't run the code initially, Your lumapi.py file is probably located elsewhere. With different FDTD releases, the \v241\ subfolder could be
   named differently, so try locating Your lumapi.py file and change the location variable in the code snippet above.
