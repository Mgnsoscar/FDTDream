import numpy as np
import pickle
from numpy.typing import NDArray
from sqlalchemy import types
from sqlalchemy import TypeDecorator


class NumpyArrayType(TypeDecorator):
    """Custom column type to store NumPy arrays in the database."""
    impl = types.LargeBinary  # Store the array as a binary blob

    def process_bind_param(self, value, dialect):
        """Convert NumPy array to binary format before storing it in the database."""
        if value is not None:
            return pickle.dumps(value)  # Serialize the NumPy array to a binary format
        return None

    def process_result_value(self, value, dialect) -> NDArray | None:
        """Convert binary format from the database back to a NumPy array."""
        if value is not None:
            return pickle.loads(value)  # Deserialize the binary format back to a NumPy array
        return None