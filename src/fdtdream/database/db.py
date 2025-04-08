from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, PickleType, LargeBinary
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import os
import tempfile
from ..results import SavedSimulation
from ..results.field_and_power_monitor import Field
from .custom_types import NumpyArrayType


Base = declarative_base()


class SavedSimulationDB(Base):
    __tablename__ = "saved_simulations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String)
    parameters = Column(PickleType)  # Store parameters as a dictionary
    fsp_file = Column(LargeBinary)   # Store the .fsp file as binary

    structures = relationship("StructureDB", back_populates="simulation", cascade="all, delete-orphan")
    monitor_results = relationship("MonitorResultDB", back_populates="simulation", cascade="all, delete-orphan")


class StructureDB(Base):
    __tablename__ = "structures"

    id = Column(Integer, primary_key=True, autoincrement=True)
    simulation_id = Column(Integer, ForeignKey("saved_simulations.id"))
    name = Column(String)
    trimesh_data = Column(PickleType)  # Store Trimesh objects as binary

    simulation = relationship("SavedSimulationDB", back_populates="structures")


class MonitorResultDB(Base):
    __tablename__ = "monitor_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    simulation_id = Column(Integer, ForeignKey("saved_simulations.id"))
    monitor_name = Column(String)
    plane_normal = Column(NumpyArrayType)  # Store as JSON (Tuple[int, int, int])
    t_result_id = Column(Integer, ForeignKey("t_results.id"))
    field_result_id = Column(Integer, ForeignKey("field_results.id"))

    simulation = relationship("SavedSimulationDB", back_populates="monitor_results")
    t_result = relationship("TResultDB")
    field_result = relationship("FieldResultDB")


class TResultDB(Base):
    __tablename__ = "t_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    wavelengths = Column(PickleType)  # Store NumPy array
    data = Column(PickleType)  # Store NumPy array


class FieldResultDB(Base):
    __tablename__ = "field_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    monitor_id = Column(Integer, ForeignKey("monitors.id"), nullable=False)  # Foreign key to MonitorDB
    monitor = relationship("MonitorDB", back_populates="field_results")  # SQLAlchemy relationship

    field_type = Column(String, nullable=False)
    wavelengths = Column(PickleType, nullable=False)  # Store NumPy array
    x_coords = Column(PickleType, nullable=False)
    y_coords = Column(PickleType, nullable=False)
    z_coords = Column(PickleType, nullable=False)
    x_field = Column(PickleType, nullable=True)
    y_field = Column(PickleType, nullable=True)
    z_field = Column(PickleType, nullable=True)

    @classmethod
    def from_field(cls, field: Field, monitor: "MonitorDB") -> "FieldResultDB":
        """Convert a Field object into a FieldResultDB instance and link it to a MonitorDB instance."""
        return cls(
            monitor=monitor,
            field_type=field.field_type,
            wavelengths=field.wavelengths,
            x_coords=field.x_coords,
            y_coords=field.y_coords,
            z_coords=field.z_coords,
            x_field=field.x_field,
            y_field=field.y_field,
            z_field=field.z_field
        )

    def to_field(self) -> Field:
        """Convert a FieldResultDB instance back into a Field object."""
        return Field(
            monitor_name=self.monitor.name,
            field_type=self.field_type,
            wavelengths=self.wavelengths,
            x_coords=self.x_coords,
            y_coords=self.y_coords,
            z_coords=self.z_coords,
            x_field=self.x_field,
            y_field=self.y_field,
            z_field=self.z_field
        )


class DatabaseHandler:
    def __init__(self, db_path):
        self.engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def save_simulation(self, saved_sim: SavedSimulation, fsp_path):
        session = self.Session()

        # Read the .fsp file as binary
        with open(fsp_path, "rb") as f:
            fsp_data = f.read()

        new_simulation = SavedSimulationDB(
            category=saved_sim.category,
            parameters=saved_sim.parameters,
            fsp_file=fsp_data,
        )

        # Add structures
        for name, mesh in saved_sim.structures:
            if not len(mesh.vertices) == 0 or len(mesh.faces) == 0:  # Verify that the mesh is not empty
                new_simulation.structures.append(StructureDB(name=name, trimesh_data=mesh))

        # Add monitor results
        for result in saved_sim.monitor_results:
            new_simulation.monitor_results.append(MonitorResultDB(
                monitor_name=result["monitor_name"],
                plane_normal=str(result["plane_normal"]),
                t_result=TResultDB(wavelengths=result.T.wavelengths, data=result["t_data"]),
                field_result=FieldResultDB(data=result["field_data"])
            ))

        session.add(new_simulation)
        session.commit()
        session.close()

    def load_simulation(self, sim_id):
        session = self.Session()
        sim = session.query(SavedSimulationDB).filter_by(id=sim_id).first()
        session.close()
        return sim

