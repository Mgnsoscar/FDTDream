from __future__ import annotations

# Standard library imports
import io
import os
from functools import wraps
from time import perf_counter
from typing import Type, List, Tuple, Optional

# Third-party library imports
import numpy as np
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Tuple,
    LargeBinary,
    TypeDecorator,
    text,
    Row,
    select
)
from sqlalchemy.orm import (
    declarative_base,
    sessionmaker,
    Session,
    load_only,
)

# Base class for declarative models
Base = declarative_base()


class NumpyArrayDictType(TypeDecorator):
    """
    SQLAlchemy custom type to store nested dictionaries of NumPy arrays as BLOBs in the database.

    This class allows nested dictionaries containing NumPy arrays to be serialized into binary large objects (BLOBs)
    when storing them in the database and deserialized back into nested dictionaries of NumPy arrays when retrieving them.
    """

    impl = LargeBinary  # Data will be stored as a binary large object (BLOB)
    cache_ok = True  # Allows SQLAlchemy to cache this type if necessary

    def _flatten_dict(self, d, parent_key='', sep='::'):
        """
        Flattens a nested dictionary.

        Parameters:
            d (dict): The dictionary to flatten.
            parent_key (str): The base key string for the current level.
            sep (str): The separator for concatenating keys.

        Returns:
            dict: A flattened dictionary.
        """
        items = {}
        for key, value in d.items():
            keystring = f"{key}"
            if isinstance(value, dict):
                for subkey, subvalue in value.items():
                    newstring = f"{keystring}{sep}{subkey}"
                    items[newstring] = subvalue
            else:
                items[keystring] = value

        return items

        # items = {}
        # for k, v in d.items():
        #     new_key = f"{parent_key}{sep}{k}" if parent_key else k
        #     if isinstance(v, dict):
        #         items.update(self._flatten_dict(v, new_key, sep=sep))
        #     else:
        #         items[new_key] = v
        # return items

    def _unflatten_dict(self, items, sep='::'):
        """
        Converts a flattened dictionary back to a nested dictionary.

        Parameters:
            items (dict): The flattened dictionary.
            sep (str): The separator used to determine nested structure.

        Returns:
            dict: A nested dictionary.
        """
        result = {}
        for key, value in items.items():
            keys = key.split(sep)
            depth = len(keys)
            if depth == 0:
                raise ValueError("Something about the depth of your dictionionary here.")
            if keys[0] not in result:
                if depth == 1:
                    result[keys[0]] = value
                else:
                    result[keys[0]] = {}

            if depth > 1:
                result[keys[0]][keys[1]] = value

        return result

        # result = {}
        # for key, value in items.items():
        #     parts = key.split(sep)
        #     d = result
        #     for part in parts[:-1]:
        #         if part not in d:
        #             d[part] = {}
        #         d = d[part]
        #     d[parts[-1]] = value
        # return result

    def process_bind_param(self, value, dialect):
        """
        Converts the nested dictionary of NumPy arrays into binary format before saving to the database.

        Parameters:
            value (dict): The nested dictionary containing NumPy arrays to store.
            dialect: The database dialect in use (ignored in this case).

        Returns:
            bytes: The binary representation of the nested dictionary of NumPy arrays or None if no value is provided.
        """
        if value is None:
            return None

        # Flatten the nested dictionary
        flattened_dict = self._flatten_dict(value)

        # Serialize the flattened dictionary using np.savez
        out = io.BytesIO()

        # Convert each NumPy array to float16 for storage efficiency
        for key, array in flattened_dict.items():
            if isinstance(array, np.ndarray):
                # Convert to np.float16 if it's not already
                flattened_dict[key] = np.float16(array)
            else:
                raise ValueError(f"Value for key {key} is not a NumPy array.")

        # Save the dictionary to the binary stream
        np.savez(out, **flattened_dict)

        out.seek(0)  # Rewind the buffer to the beginning
        return out.read()  # Return the binary data to be stored in the database

    def process_result_value(self, value, dialect):
        """
        Converts the binary data back into a nested dictionary of NumPy arrays when retrieving from the database.

        Parameters:
            value (bytes): The binary data retrieved from the database.
            dialect: The database dialect in use (ignored in this case).

        Returns:
            dict: The reconstructed nested dictionary of NumPy arrays or None if no data is available.
        """
        if value is None:
            return None

        # Deserialize the binary data back into a flattened dictionary of NumPy arrays using np.load
        out = io.BytesIO(value)
        out.seek(0)  # Rewind the buffer to the beginning
        loaded = np.load(out)

        # Convert the loaded data back to a flattened dictionary
        flattened_dict = {key: loaded[key] for key in loaded.keys()}

        # Unflatten the dictionary to its original nested structure
        result = self._unflatten_dict(flattened_dict)
        return result
class NumpyArrayType(TypeDecorator):
    """
    SQLAlchemy custom type to store NumPy arrays as BLOBs in the database.

    This class allows NumPy arrays to be serialized into binary large objects (BLOBs)
    when storing them in the database and deserialized back into NumPy arrays when
    retrieving them from the database.

    Attributes:
        impl: Specifies that the data is stored as a LargeBinary (BLOB) object.
        cache_ok: A SQLAlchemy optimization flag that allows caching the type decorator.

    Methods:
        process_bind_param(value, dialect):
            Converts the NumPy array into binary data (BLOB) before storing it in the database.

        process_result_value(value, dialect):
            Converts the binary data (BLOB) back into a NumPy array after fetching it from the database.
    """

    impl = LargeBinary  # Data will be stored as a binary large object (BLOB)
    cache_ok = True  # Allows SQLAlchemy to cache this type if necessary

    def process_bind_param(self, value, dialect):
        """
        Converts the NumPy array into binary format before saving to the database.

        Parameters:
            value (np.ndarray): The NumPy array to store.
            dialect: The database dialect in use (ignored in this case).

        Returns:
            bytes: The binary representation of the NumPy array or None if no value is provided.
        """
        if value is None:
            return None

        # Ensure the array is in np.float16 format for storage efficiency
        elif not isinstance(value, np.float16):
            value = np.float16(value)

        # Serialize the NumPy array to binary using np.save
        out = io.BytesIO()
        np.save(out, value)
        out.seek(0)  # Rewind the buffer to the beginning
        return out.read()  # Return the binary data to be stored in the database

    def process_result_value(self, value, dialect):
        """
        Converts the binary data back into a NumPy array when retrieving from the database.

        Parameters:
            value (bytes): The binary data retrieved from the database.
            dialect: The database dialect in use (ignored in this case).

        Returns:
            np.ndarray: The reconstructed NumPy array or None if no data is available.
        """
        if value is None:
            return None

        # Deserialize the binary data back into a NumPy array using np.load
        out = io.BytesIO(value)
        out.seek(0)  # Rewind the buffer to the beginning
        return np.load(out)

class NumpyCompressedArrayType(TypeDecorator):
    """
    SQLAlchemy custom type to store compressed NumPy arrays as BLOBs in the database.

    This class serializes NumPy arrays into compressed binary large objects (BLOBs)
    using `np.savez_compressed` before storing them in the database. When retrieving
    from the database, the compressed binary data is deserialized back into NumPy arrays.

    Attributes:
        impl: Specifies that the data is stored as a LargeBinary (BLOB) object.
        cache_ok: A SQLAlchemy optimization flag that allows caching the type decorator.

    Methods:
        process_bind_param(value, dialect):
            Compresses and serializes the NumPy array into binary data (BLOB) before storing it in the database.

        process_result_value(value, dialect):
            Decompresses and deserializes the binary data back into a NumPy array after fetching it from the database.
    """

    impl = LargeBinary  # Data will be stored as a binary large object (BLOB)
    cache_ok = True  # Allows SQLAlchemy to cache this type if necessary

    def process_bind_param(self, value, dialect):
        """
        Compresses and serializes the NumPy array into a binary format before saving to the database.

        Parameters:
            value (np.ndarray): The NumPy array to store.
            dialect: The database dialect in use (ignored in this case).

        Returns:
            bytes: The compressed binary representation of the NumPy array or None if no value is provided.
        """
        if value is None:
            return None

        # Serialize the NumPy array to compressed binary using np.savez_compressed
        out = io.BytesIO()
        np.savez_compressed(out, array=value)
        out.seek(0)  # Rewind the buffer to the beginning
        return out.read()  # Return the compressed binary data to be stored in the database

    def process_result_value(self, value, dialect):
        """
        Decompresses and converts the binary data back into a NumPy array when retrieving from the database.

        Parameters:
            value (bytes): The compressed binary data retrieved from the database.
            dialect: The database dialect in use (ignored in this case).

        Returns:
            np.ndarray: The reconstructed NumPy array or None if no data is available.
        """
        if value is None:
            return None

        # Deserialize the compressed binary data back into a NumPy array using np.load
        out = io.BytesIO(value)
        out.seek(0)  # Rewind the buffer to the beginning
        return np.load(out)['array']


class ResultModel(Base):
    """
    SQLAlchemy model representing a simulation result.

    This model stores simulation metadata, geometry, mesh parameters, source parameters,
    and result data, including reflection and transmission profiles, resonances, and
    electromagnetic field profiles for different geometrical spans and units.

    Attributes:
        id (int): Primary key for each entry.
        name (str): Name of the simulation.

        Geometry (Columns related to struct1, struct2, and struct3):
            - struct1_xspan, struct1_yspan, struct1_zspan (NumpyArrayType): Span dimensions for structure 1.
            - struct_1_edge_mesh_size, struct_1_edge_mesh_step (NumpyArrayType): Mesh parameters for structure 1 edges.
            - unit_cell_1_x, unit_cell_1_y (NumpyArrayType): Unit cell dimensions for structure 1.
            - struct1_material (str): Material of structure 1.
            - Similar columns exist for struct2 and struct3 with respective attributes.

        Simulation Mesh Parameters:
            - mesh_dx, mesh_dy, mesh_dz (NumpyArrayType): Mesh sizes along x, y, and z axes.
            - fdtd_xspan, fdtd_yspan, fdtd_zspan (NumpyArrayType): FDTD simulation spans.

        Monitor Parameters:
            - frequency_points (NumpyArrayType): Frequency points for the monitor.

        Source Parameters:
            - polarization_angle (NumpyArrayType): Polarization angle of the source.
            - lambda_start, lambda_stop (NumpyArrayType): Wavelength range for the source.

        Results:
            - lambdas (NumpyArrayType): Wavelength values for the simulation.
            - ref_powers, trans_powers (NumpyArrayType): Reflection and transmission powers.
            - Profile data (reflection and transmission): Ref and trans profile vectors, max power, resonance, etc.

        Simulation Metadata:
            - simulation_hash (str): Unique hash representing the simulation.
            - active_monitors (str): String tracking which monitor results are stored.
            - comment (str): Additional comment about the simulation.
    """

    __tablename__ = 'simulation_results'

    # The unique id for all entries
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)

    # Basic column: Name of the simulation
    name = Column(String, nullable=False, index=True)

    # Columns for geometry and materials of the simulation
    struct1_xspan = Column(NumpyArrayType, nullable=True, index=True)
    struct1_yspan = Column(NumpyArrayType, nullable=True, index=True)
    struct1_zspan = Column(NumpyArrayType, nullable=True, index=True)
    struct_1_edge_mesh_size = Column(NumpyArrayType, nullable=True, index=True)
    struct_1_edge_mesh_step = Column(NumpyArrayType, nullable=True, index=True)
    unit_cell_1_x = Column(NumpyArrayType, nullable=True, index=True)
    unit_cell_1_y = Column(NumpyArrayType, nullable=True, index=True)
    struct1_material = Column(String, nullable=True, index=True)

    struct2_xspan = Column(NumpyArrayType, nullable=True, index=True)
    struct2_yspan = Column(NumpyArrayType, nullable=True, index=True)
    struct2_zspan = Column(NumpyArrayType, nullable=True, index=True)
    struct_2_edge_mesh_size = Column(NumpyArrayType, nullable=True, index=True)
    struct_2_edge_mesh_step = Column(NumpyArrayType, nullable=True, index=True)
    unit_cell_2_x = Column(NumpyArrayType, nullable=True, index=True)
    unit_cell_2_y = Column(NumpyArrayType, nullable=True, index=True)
    struct2_material = Column(String, nullable=True, index=True)

    struct3_xspan = Column(NumpyArrayType, nullable=True, index=True)
    struct3_yspan = Column(NumpyArrayType, nullable=True, index=True)
    struct3_zspan = Column(NumpyArrayType, nullable=True, index=True)
    struct_3_edge_mesh_size = Column(NumpyArrayType, nullable=True, index=True)
    struct_3_edge_mesh_step = Column(NumpyArrayType, nullable=True, index=True)
    unit_cell_3_x = Column(NumpyArrayType, nullable=True, index=True)
    unit_cell_3_y = Column(NumpyArrayType, nullable=True, index=True)
    struct3_material = Column(String, nullable=True, index=True)

    # Simulation mesh parameters
    mesh_dx = Column(NumpyArrayType, nullable=True, index=True)
    mesh_dy = Column(NumpyArrayType, nullable=True, index=True)
    mesh_dz = Column(NumpyArrayType, nullable=True, index=True)
    fdtd_xspan = Column(NumpyArrayType, nullable=False, index=True)
    fdtd_yspan = Column(NumpyArrayType, nullable=False, index=True)
    fdtd_zspan = Column(NumpyArrayType, nullable=False, index=True)
    boundary_symmetries = Column(String, nullable=False, index=True)

    # Monitor parameters
    frequency_points = Column(NumpyArrayType, nullable=False, index=True)

    # Source parameters
    polarization_angle = Column(NumpyArrayType, nullable=False, index=True)
    incidence_angle = Column(NumpyArrayType, nullable=False, index=True)
    lambda_start = Column(NumpyArrayType, nullable=False, index=True)
    lambda_stop = Column(NumpyArrayType, nullable=False, index=True)

    # Columns for results
    lambdas = Column(NumpyArrayType, nullable=False, index=False)
    ref_powers = Column(NumpyArrayType, nullable=False, index=False)
    trans_powers = Column(NumpyArrayType, nullable=False, index=False)

    ref_power_res_lambda = Column(NumpyArrayType, nullable=True, index=True)
    ref_power_res = Column(NumpyArrayType, nullable=True, index=True)
    trans_power_res_lambda = Column(NumpyArrayType, nullable=True, index=True)
    trans_power_res = Column(NumpyArrayType, nullable=True, index=True)


    profile_x = Column(NumpyArrayType, nullable=True, index=False)
    profile_y = Column(NumpyArrayType, nullable=True, index=False)
    ref_profile_vectors = Column(NumpyArrayDictType, nullable=True, index=False)
    trans_profile_vectors = Column(NumpyArrayDictType, nullable=True, index=False)

    ref_mag_max_pr_lambda = Column(NumpyArrayDictType, nullable=True, index=False)
    trans_mag_max_pr_lambda = Column(NumpyArrayDictType, nullable=True, index=False)

    ref_mag_res_lambda = Column(NumpyArrayType, nullable=True, index=True)
    ref_mag_res = Column(NumpyArrayType, nullable=True, index=True)
    trans_mag_res_lambda = Column(NumpyArrayType, nullable=True, index=True)
    trans_mag_res = Column(NumpyArrayType, nullable=True, index=True)

    xz_profile_E_vectors = Column(NumpyArrayDictType, nullable=True, index=True)
    xz_profile_P_vectors = Column(NumpyArrayDictType, nullable=True, index=True)
    xz_profile_x_coord = Column(NumpyArrayType, nullable=True, index=True)
    xz_profile_z_coord = Column(NumpyArrayType, nullable=True, index=True)

    yz_profile_E_vectors = Column(NumpyArrayDictType, nullable=True, index=True)
    yz_profile_P_vectors = Column(NumpyArrayDictType, nullable=True, index=True)
    yz_profile_y_coord = Column(NumpyArrayType, nullable=True, index=True)
    yz_profile_z_coord = Column(NumpyArrayType, nullable=True, index=True)

    # Simulation hash and monitor tracking
    simulation_hash = Column(String, nullable=False, unique=True, index=True)
    active_monitors = Column(String, nullable=False, index=True)

    # Additional comment about the simulation
    comment = Column(String, nullable=True, index=False)


class DatabaseHandler:
    """
    A class to manage database operations for the simulation application.

    This class provides methods for interacting with a SQLite database, including
    creating and managing database sessions, executing queries, and manipulating
    simulation data stored in the database. The primary focus is on maintaining
    performance and integrity when accessing or modifying the database.

    Attributes:
        db_name (str): The name of the SQLite database file (without extension).
        engine (Engine): The SQLAlchemy engine used for database connectivity.
        temp_session (Session | None): A temporary session for executing database operations.
        sessions (dict): A dictionary of pre-configured sessions for various database queries.

    Methods:
        __init__(database_name: str, base=Base): Initializes the DatabaseHandler instance.
        _create_database(base): Creates the database tables based on the provided metadata.
        open_temp_session(): Opens a new temporary database session.
        close_temp_session(): Closes the temporary database session.
        initial_load(print_load_time: bool = False): Loads all simulation records from the database.
        get_filtered_results(filters: list | None = None, only_ids: bool = False): Fetches filtered results from the database.
        db_doorman(function): A decorator to manage database session context for methods.
        delete_entry_by_id(entry_id: int): Deletes a specific entry from the database based on its ID.
        get_last_id() -> int: Retrieves the last ID used in the ResultModel table.
        simulation_exists(hash_id: str) -> Tuple[bool, Optional[List[str]]]: Checks if a simulation exists in the database.
        save_simulation_data(simulation_data: dict) -> None: Saves simulation data to the database.
        index_database(tablename: str, columns: List[str]) -> None: Creates indexes on specified columns of a table.
    """

    __slots__ = ("db_name", "engine", "temp_session", "sessions", "_base")

    def __init__(self, database_name: str) -> None:
        """
        Initializes the DatabaseHandler with the specified SQLite database.

        Args:
            database_name (str): The name of the database file (without extension).
            base: The base class for the SQLAlchemy ORM (default is Base).

        Attributes:
            db_name (str): The name of the database file.
            engine (Engine): The SQLAlchemy engine for connecting to the database.
            temp_session (Session | None): Temporary session for database operations, defaults to None.
            sessions (dict): A dictionary holding different SQLAlchemy session instances for various operations.
        """

        self.db_name = database_name

        # Create/open an SQLite database and engine with specified pool size and overflow settings
        self.engine = create_engine(
            f'sqlite:///../Database/{database_name}.db',
            pool_size=20,
            max_overflow=0
        )

        # Initialize temporary session for one-time operations, defaults to None
        self.temp_session: Session | None = None

        # Create and bind session instances for different database operations
        self.sessions = {
            "simulation_exists": sessionmaker(bind=self.engine)(),
            "get_result_by_id": sessionmaker(bind=self.engine)(),
            "initial_load": sessionmaker(bind=self.engine)(),
            "get_filtered_results": sessionmaker(bind=self.engine)()
        }

        # Check if the database file exists; if not, create it
        if not os.path.exists(f"{database_name}.db"):
            self._create_database(declarative_base())

    def _create_database(self, base):
        """
        Creates the database tables defined in the given base metadata.

        Args:
            base: The base class for the SQLAlchemy ORM, which contains the metadata
                  for all the tables to be created.

        This method uses the metadata associated with the base class to create
        all tables in the SQLite database specified by the engine.
        """

        # Create all tables defined in the base's metadata
        base.metadata.create_all(self.engine)

    def get_entries_by_ids(self, ids: List[int]):
        """
        Fetches entries from the database based on a list of IDs.

        Args:
            ids (List[int]): A list of entry IDs to fetch from the database.

        Returns:
            List[ResultModel]: A list of database entries that correspond to the provided IDs.
        """
        # Ensure the session is closed properly using a context manager
        with self.sessions['get_result_by_id'] as session:
            # Query the database for entries matching the list of IDs
            query = select(ResultModel).where(ResultModel.id.in_(ids))
            results = session.execute(query).scalars().all()
        return results

    def open_temp_session(self) -> None:
        """
        Opens a temporary database session for one-time operations.

        This method creates a new SQLAlchemy session bound to the current
        database engine and assigns it to the `temp_session` attribute.
        The temporary session can be used for executing individual queries
        without affecting the main session management.

        Returns:
            None
        """

        # Create a new session bound to the database engine and assign it to temp_session
        self.temp_session = sessionmaker(bind=self.engine)()

    def close_temp_session(self) -> None:
        """
        Closes the temporary database session.

        This method is used to close the currently active temporary session
        associated with the `temp_session` attribute. Closing the session
        releases any database resources and ensures that changes are committed
        or rolled back as necessary.

        Returns:
            None
        """

        # Close the temporary session to release resources and finalize changes
        self.temp_session.close()

    def initial_load(self, print_load_time: bool = False) -> list[Row[tuple[ResultModel, int]]]:
        """
        Loads all simulation records from the database.

        This method retrieves all entries from the ResultModel table,
        along with their associated IDs. It measures the time taken
        to perform the query. If the `print_load_time` parameter is
        set to True, it prints the duration for performance tracking.

        Args:
            print_load_time (bool): Flag to indicate whether to print
            the time taken for the initial load operation. Defaults to False.

        Returns:
            list[Row[tuple[ResultModel, int]]]: A list of rows containing tuples
            of ResultModel instances and their corresponding IDs.
        """

        # Access the session for the initial load operation
        session = self.sessions["initial_load"]

        # Record the start time for performance measurement
        start = perf_counter()

        # Query the database for all ResultModel entries and their IDs
        query = session.query(ResultModel, ResultModel.id).all()

        # Print the time taken for the initial load operation if requested
        if print_load_time:
            print(f"Initial load time: {perf_counter() - start}")

        # Return the query results
        return query

    def get_filtered_results(
            self,
            filters: list | None = None,
            only_ids: bool = False
    ) -> List[Type[ResultModel] | Column]:
        """
        Retrieves simulation records from the database based on specified filters.

        This method allows for fetching either all simulation records or just their IDs,
        depending on the `only_ids` parameter. If filters are provided, they are applied
        to the query to refine the results.

        Args:
            filters (list | None): A list of filter conditions to apply to the query.
            If None, no filters are applied. Defaults to None.
            only_ids (bool): Flag to indicate whether to return only the IDs of the results.
            If True, the method returns a list of IDs instead of the full ResultModel instances. Defaults to False.

        Returns:
            List[Type[ResultModel] | Column]: A list containing either ResultModel instances
            or their corresponding IDs, depending on the `only_ids` parameter.
        """

        # Fetch the session for getting filtered results
        session = self.sessions["get_filtered_results"]

        # Record the start time for performance measurement
        start = perf_counter()

        # If only IDs are requested, handle the query accordingly
        if only_ids:
            if not filters:
                # Query for all ResultModel entries if no filters are applied
                results = session.query(ResultModel).all()
            else:
                # Query with applied filters
                results = session.query(ResultModel).filter(*filters).all()

            # Extract and return only the IDs from the results
            results = [result.id for result in results]
        else:
            # If only the full ResultModel instances are needed
            if not filters:
                results = session.query(ResultModel).all()
            else:
                results = session.query(ResultModel).filter(*filters).all()

        # Print the time taken for the query operation
        print(f"Query time: {perf_counter() - start}")

        # Return the query results (either IDs or ResultModel instances)
        return results

    @staticmethod
    def db_doorman(function):
        """
        Decorator that manages the database session for the decorated function.

        This decorator ensures that a temporary database session is created before
        executing the decorated function. If an exception occurs during the function's
        execution, it rolls back the session to maintain database integrity. Finally,
        it closes the session after the function execution is complete.

        Args:
            function (Callable): The function to be decorated that requires
            database session management.

        Returns:
            Callable: A wrapper function that includes session management logic.
        """

        @wraps(function)
        def wrapper(self, *args, **kwargs):
            # Open a new temporary session for the database operation
            self.temp_session = sessionmaker(bind=self.engine)()  # Assuming self.Session is sessionmaker
            try:
                # Execute the decorated function and capture its result
                result = function(self, *args, **kwargs)
                return result
            except Exception as e:
                # Rollback the session if an error occurs to maintain database integrity
                self.temp_session.rollback()
                raise e  # Re-raise the exception for further handling
            finally:
                # Ensure that the session is closed after execution
                self.temp_session.close()

        return wrapper

    @db_doorman
    def delete_entry_by_id(self, entry_id: int) -> None:
        """
        Deletes an entry from the database based on the provided ID.

        This method attempts to fetch and delete an entry from the ResultModel
        table corresponding to the specified entry ID. If the entry does not exist,
        it prints a message indicating that no entry was found.

        Args:
            entry_id (int): The ID of the entry to be deleted.

        Returns:
            None
        """

        # Access the temporary session for database operations
        session = self.temp_session

        # Fetch the entry with the given ID from the database
        entry_to_delete = session.query(ResultModel).get(entry_id)

        # Check if the entry exists
        if entry_to_delete is None:
            print(f"No entry found with ID {entry_id}.")
            return  # Exit the method if no entry is found

        # Proceed to delete the entry from the database
        session.delete(entry_to_delete)
        session.commit()  # Commit the transaction to apply the changes

        # Print confirmation of deletion
        print(f"Entry with ID {entry_id} has been deleted.")

    def get_last_id(self) -> int | None:
        """
        Retrieves the ID of the last entry in the ResultModel table.

        This method queries the ResultModel table to find the highest ID value,
        which corresponds to the most recently added entry. If the table is empty,
        it returns None.

        Returns:
            int: The ID of the last entry in the ResultModel table.
            Returns None if there are no entries in the table.
        """

        # Query the ResultModel table to get the entry with the highest ID
        last_entry = (
            self.sessions["simulation_exists"]
            .query(ResultModel)
            .order_by(ResultModel.id.desc())  # Order by ID in descending order
            .first()  # Get the first entry (highest ID)
        )

        # Return the ID of the last entry or None if no entries exist
        return last_entry.id if last_entry else None

    def simulation_exists(self, hash_id: str) -> Tuple[bool, Optional[List[str]]]:
        """
        Check if a simulation with the given hash ID exists in the database, and if so,
        return a list of active monitors for that simulation.

        Args:
            hash_id (str): The unique hash identifier for the simulation to be searched.

        Returns:
            Tuple[bool, Optional[List[str]], ]:
                - A boolean indicating whether the simulation exists (`True` if found, `False` if not).
                - A list of active monitors for the found simulation, or `None` if no simulation is found.
                - A ResultModel object that is the matching result. None of no matching results found

        The monitors are returned as a list of strings, where each string corresponds to
        a monitor that was active during the simulation. If no matching simulation is found,
        the monitors list will be `None`.
        """

        # Query the database for a result with the specified simulation hash
        matching_result = (
            self.sessions["simulation_exists"]
            .query(ResultModel)
            .options(load_only(ResultModel.simulation_hash))  # Optimize loading by only fetching the simulation hash
            .filter_by(simulation_hash=hash_id)  # Filter results based on the provided hash ID
            .first()  # Get the first matching result
        )

        # Determine if a matching result was found and prepare the list of active monitors
        if matching_result is not None:
            active_monitors = matching_result.active_monitors.split(",")  # Split the active monitors string into a list
            simulation_exists = True
        else:
            active_monitors = None  # No monitors available if no matching result
            simulation_exists = False

        return simulation_exists, active_monitors, matching_result  # Return the existence status, list of monitors, and matching result

    @db_doorman
    def save_simulation_data(self, simulation_data: dict) -> None:
        """
        Manually saves simulation data to the database.

        This method allows for saving additional simulation data that may not be captured
        by the `run_and_save_to_db()` method from the SimulationBase class. It is
        recommended to use this method only if you are certain of the data structure
        being passed and the implications of manually saving data.

        Args:
            simulation_data (dict): A dictionary containing the simulation data to be saved.
                The dictionary should have keys corresponding to the attributes of the ResultModel.

        Returns:
            None

        Note:
            Use this method with caution, as improper use may lead to inconsistencies in the database.
        """

        # Create a ResultModel instance using the provided simulation data
        result = ResultModel(**simulation_data)

        # Add the result instance to the temporary session for database operations
        self.temp_session.add(result)

        # Commit the transaction to save the changes to the database
        self.temp_session.commit()

        # Print a confirmation message indicating successful save
        print("\tResult saved to database")

    @db_doorman
    def index_database(self, tablename: str, columns: List[str]) -> None:
        """
        Creates an index on specified columns of a given database table.

        This method allows you to index one or more columns in a specified table to
        improve query performance. Indexing can significantly speed up retrieval
        operations on large datasets. However, it is crucial to ensure that
        indexing is applied judiciously, as it can also introduce overhead
        during data modification operations.

        Args:
            tablename (str): The name of the table where the index will be created.
            columns (List[str]): A list of column names to be indexed.
                Each column should exist in the specified table.

        Returns:
            None

        Note:
            Use this method with caution, as improper indexing can lead to
            decreased performance for insert and update operations.
        """

        # Iterate through the list of columns to create an index for each
        for column in columns:
            # Execute a SQL command to create an index if it doesn't already exist
            self.temp_session.execute(
                text(f"CREATE INDEX IF NOT EXISTS {column.lower()}_idx ON {tablename} ({column})")
            )
