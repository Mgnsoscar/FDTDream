import os
import re

# Where the lumerical python API is located. Change this to the location on your computer.
_lumapi_location = r'C:\Program Files\Lumerical\v241\api\python\lumapi.py'


def set_lumapi_location(new_location: str) -> None:
    """
    Permanently sets the _lumapi_location variable in this source file to new_location.
    This function modifies the .py file itself regardless of where it's run from.

    Args:
        new_location: The absolute path to the lumapi.py file.
    """

    # Get the absolute path to this script
    file_path = os.path.abspath(__file__)

    # Read the current file content
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Prepare the new assignment line.
    new_assignment = f"_lumapi_location = r'{new_location}'"

    # Use regex anchored to the start of a line (multiline mode) to match only top-level assignments.
    pattern = r"(?m)^_lumapi_location\s*=\s*r?['\"][^'\"]*['\"]"
    new_content, count = re.subn(pattern, new_assignment, content)

    if count == 0:
        raise ValueError("Could not find the _lumapi_location assignment in the file.")

    # Write the modified content back to the file.
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)


def get_lumapi_location() -> str:
    """
    Fetches and returns the current set location of the lumapi.py file.

    Returns:
        The absolute path to the lumapi.py file.
    """
    return _lumapi_location