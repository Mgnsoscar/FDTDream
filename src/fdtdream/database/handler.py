import os
from pathlib import Path
from typing import List, Tuple
from typing import Optional, Union

from sqlalchemy import create_engine, select, delete, event
from sqlalchemy.orm import sessionmaker, selectinload

from .db import (Base, SimulationModel, MonitorModel, StructureModel, FieldModel, FieldAndPowerMonitorModel,
                 FieldAndPowerMonitorPydanticModel, StructurePydanticModel, SimulationPydanticModel)
from ..results.monitors import FieldAndPowerMonitor
from ..results.simulation import Simulation


class DatabaseHandler:
    path: Path
    filename: str

    def __init__(self, db_path: str):
        path = Path(db_path)
        if path.suffix != ".db":
            path = path.with_suffix(".db")
        self.path = path.resolve()
        self.filename = self.path.name

        uri = f"sqlite:///{self.path}"
        self.engine = create_engine(uri, echo=False, future=True)

        # ✅ Enable foreign key support for SQLite
        event.listen(
            self.engine,
            "connect",
            lambda dbapi_connection, connection_record: dbapi_connection.execute("PRAGMA foreign_keys=ON")
        )

        self.Session = sessionmaker(bind=self.engine, future=True)
        Base.metadata.create_all(self.engine)

    def same_file(self, other_path: str) -> bool:
        path = Path(other_path)
        if path.suffix != ".db":
            path = path.with_suffix(".db")

        return os.path.samefile(self.path, path)

    # Just category names (distinct)
    def get_all_categories(self) -> List[str]:
        with self.Session() as session:
            stmt = select(SimulationModel.category).distinct()
            return session.execute(stmt).scalars().all()

    def delete_category(self, category_name: str) -> None:
        """
        Deletes all simulations with the specified category from the database.
        """
        with self.Session() as session:
            session.execute(
                delete(SimulationModel).where(SimulationModel.category == category_name)
            )
            session.commit()

    def get_simulation_category(self, sim_id: int) -> Optional[str]:
        """
        Returns the category of the simulation with the given ID.

        Args:
            sim_id (int): ID of the simulation.

        Returns:
            Optional[str]: The simulation's category, or None if not found.
        """
        with self.Session() as session:
            stmt = select(SimulationModel.category).where(SimulationModel.id == sim_id)
            return session.execute(stmt).scalar_one_or_none()

    def monitor_has_fields(self, monitor_id: int) -> bool:
        """Returns True if the monitor has at least one associated field (E, H, or P)."""
        with self.Session() as session:
            stmt = select(FieldModel.id).where(FieldModel.monitor_id == monitor_id).limit(1)
            return session.execute(stmt).first() is not None

    def monitor_has_T_data(self, monitor_id: int) -> bool:
        """Returns True if the monitor has non-null transmission (T) data."""
        with self.Session() as session:
            stmt = select(FieldAndPowerMonitorModel.T).where(FieldAndPowerMonitorModel.id == monitor_id)
            return session.execute(stmt).scalar_one_or_none() is not None

    def monitor_has_power_data(self, monitor_id: int) -> bool:
        """Returns True if the monitor has non-null power data."""
        with self.Session() as session:
            stmt = select(FieldAndPowerMonitorModel.power).where(FieldAndPowerMonitorModel.id == monitor_id)
            return session.execute(stmt).scalar_one_or_none() is not None

    def change_simulation_category(self, sim_id: int, new_category: str) -> bool:
        """
        Changes the category of the simulation with the given ID.

        Args:
            sim_id (int): ID of the simulation to modify.
            new_category (str): The new category to assign.

        Returns:
            bool: True if the simulation was updated, False if not found.
        """
        with self.Session() as session:
            sim = session.get(SimulationModel, sim_id)
            if not sim:
                return False
            sim.category = new_category
            session.commit()
            return True

    def get_simulation_parameters_for_monitor(self, monitor_id: int) -> Optional[dict[str, str]]:
        """
        Returns the parameters of the simulation that owns the given monitor.

        Args:
            monitor_id (int): The ID of the monitor.

        Returns:
            Optional[dict[str, str]]: The simulation's parameters dictionary, or None if not found.
        """
        with self.Session() as session:
            stmt = (
                select(SimulationModel.parameters)
                .join(MonitorModel, SimulationModel.id == MonitorModel.simulation_id)
                .where(MonitorModel.id == monitor_id)
            )
            result = session.execute(stmt).scalar_one_or_none()
            return result or None

    def get_simulation_info(self, sim_id: int) -> Optional[str]:
        with self.Session() as session:
            stmt = select(SimulationModel.parameters).where(SimulationModel.id == sim_id)
            result = session.execute(stmt).scalar_one_or_none()
            return result.get("__info__", None) if result else None

    def update_simulation_info(self, sim_id: int, new_info: str) -> bool:
        with self.Session() as session:
            sim = session.get(SimulationModel, sim_id)
            if not sim:
                return False

            # Copy parameters and assign a new dict to trigger SQLAlchemy change detection
            params = dict(sim.parameters or {})
            params["__info__"] = new_info
            sim.parameters = params  # Full re-assignment = change is detected

            session.commit()
            return True

    def get_monitor_info(self, monitor_id: int) -> Optional[str]:
        with self.Session() as session:
            stmt = select(MonitorModel.parameters).where(MonitorModel.id == monitor_id)
            result = session.execute(stmt).scalar_one_or_none()
            return result.get("__info__", None) if result else None

    def update_simulation_parameters(self, sim_id: int, params: dict[str, str]) -> bool:
        with self.Session() as session:
            sim = session.get(SimulationModel, sim_id)
            if not sim:
                return False
            params["__info__"] = sim.parameters.copy().get("__info__", "")
            sim.parameters = params
            session.commit()
            return True

    def get_T_data(self, monitor_id: int):
        """
        Returns the transmission (T) data array for the monitor, or None if not found or empty.
        """
        with self.Session() as session:
            stmt = select(
                FieldAndPowerMonitorModel.wavelengths,
                FieldAndPowerMonitorModel.T,
            ).where(FieldAndPowerMonitorModel.id == monitor_id)

            result = session.execute(stmt).first()
            if result is None:
                return None

            wavelengths, T = result
            if wavelengths is None or T is None:
                return None

            return wavelengths, T

    def get_power_data(self, monitor_id: int):
        """
        Returns the power data array for the monitor, or None if not found or empty.
        """
        with self.Session() as session:
            stmt = select(
                FieldAndPowerMonitorModel.wavelengths,
                FieldAndPowerMonitorModel.power
            ).where(FieldAndPowerMonitorModel.id == monitor_id)

            result = session.execute(stmt).first()
            if result is None:
                return None

            wavelengths, power = result
            if wavelengths is None or power is None:
                return None

            return wavelengths, power

    def update_monitor_parameters(self, monitor_id: int, params: dict[str, str]) -> bool:
        with self.Session() as session:
            mon = session.get(MonitorModel, monitor_id)
            if not mon:
                return False
            params["__info__"] = mon.parameters.copy().get("__info__", "")
            mon.parameters = params
            session.commit()
            return True

    def update_monitor_info(self, monitor_id: int, new_info: str) -> bool:
        with self.Session() as session:
            mon = session.get(MonitorModel, monitor_id)
            if not mon:
                return False

            # Reassign parameters to a new dict to trigger change tracking
            params = dict(mon.parameters or {})
            params["__info__"] = new_info
            mon.parameters = params  # Full reassignment = change will be committed

            session.commit()
            return True

    def delete_monitor_by_id(self, monitor_id: int) -> None:
        with self.Session() as session:
            monitor = session.get(MonitorModel, monitor_id)
            if monitor:
                sim_id = monitor.simulation_id
                session.delete(monitor)
                session.flush()  # ensure deletion is registered

                # Check if any monitors remain for that simulation
                remaining = session.query(MonitorModel).filter_by(simulation_id=sim_id).count()
                if remaining == 0:
                    simulation = session.get(SimulationModel, sim_id)
                    if simulation:
                        session.delete(simulation)

                session.commit()

    def delete_simulation_by_id(self, simulation_id: int) -> None:
        """
        Deletes the simulation with the specified ID from the database.

        Args:
           simulation_id (int): The ID of the simulation to delete.
        """
        with self.Session() as session:
            simulation = session.get(SimulationModel, simulation_id)
            if simulation:
                session.delete(simulation)
                session.commit()

    def rename_monitor(self, monitor_id: int, new_name: str) -> bool:
        """
        Renames a monitor with the given ID.

        Args:
            monitor_id (int): The ID of the monitor to rename.
            new_name (str): The new name to assign.

        Returns:
            bool: True if renamed, False if monitor not found.
        """
        with self.Session() as session:
            mon = session.get(MonitorModel, monitor_id)
            if not mon:
                return False
            mon.name = new_name
            session.commit()
            return True

    def get_simulation_name(self, sim_id: int) -> Optional[str]:
        """
        Returns the name of the simulation with the given ID.

        Args:
            sim_id (int): The ID of the simulation.

        Returns:
            Optional[str]: The name of the simulation, or None if not found.
        """
        with self.Session() as session:
            stmt = select(SimulationModel.name).where(SimulationModel.id == sim_id)
            return session.execute(stmt).scalar_one_or_none()

    def get_monitor_name(self, monitor_id: int) -> Optional[str]:
        """
        Returns the name of the monitor with the given ID.

        Args:
            monitor_id (int): The ID of the monitor.

        Returns:
            Optional[str]: The name of the monitor, or None if not found.
        """
        with self.Session() as session:
            stmt = select(MonitorModel.name).where(MonitorModel.id == monitor_id)
            return session.execute(stmt).scalar_one_or_none()

    def rename_simulation(self, sim_id: int, new_name: str) -> bool:
        """
        Renames a simulation with the given ID.

        Args:
            sim_id (int): The ID of the simulation to rename.
            new_name (str): The new name to assign.

        Returns:
            bool: True if renamed, False if simulation not found.
        """
        with self.Session() as session:
            sim = session.get(SimulationModel, sim_id)
            if not sim:
                return False
            sim.name = new_name
            session.commit()
            return True

    def rename_category(self, old_name: str, new_name: str) -> None:
        """
        Renames a category by updating all simulations that belong to the old category name.

        Args:
            old_name (str): The current category name.
            new_name (str): The new name to assign.
        """
        with self.Session() as session:
            session.query(SimulationModel).filter_by(category=old_name).update({"category": new_name})
            session.commit()

    # Just (id, name) for simulations in a category
    def get_simulations_by_category(self, category: str) -> List[Tuple[int, str]]:
        with self.Session() as session:
            stmt = select(SimulationModel.id, SimulationModel.name).where(
                SimulationModel.category == category
            )
            return session.execute(stmt).all()

    # Just (id, name) for monitors in a simulation
    def get_monitors_for_simulation(self, simulation_id: int) -> List[Tuple[int, str]]:
        with self.Session() as session:
            stmt = select(MonitorModel.id, MonitorModel.name).where(
                MonitorModel.simulation_id == simulation_id
            )
            return session.execute(stmt).all()

    def get_structures_for_simulation(self, simulation_id: int) -> List[Tuple[int, str]]:
        with self.Session() as session:
            stmt = select(StructureModel.id, StructureModel.name).where(
                StructureModel.simulation_id == simulation_id
            )
            return session.execute(stmt).all()

    # Full ORM load when needed

    def get_simulation_by_id(self, sim_id: int) -> Optional[SimulationModel]:
        with self.Session() as session:
            stmt = (
                select(SimulationModel)
                .options(
                    selectinload(SimulationModel._structures),
                    selectinload(SimulationModel._monitors)
                    .selectinload(MonitorModel._fields)
                )
                .where(SimulationModel.id == sim_id)
            )
            result = session.execute(stmt).unique().scalar_one_or_none()
            return result

    def get_monitor_by_id(self, monitor_id: int) -> Optional[MonitorModel]:
        with self.Session() as session:
            stmt = (
                select(MonitorModel)
                .options(
                    selectinload(MonitorModel._fields),
                    selectinload(MonitorModel._simulation)
                    .selectinload(SimulationModel._structures)
                )
                .where(MonitorModel.id == monitor_id)
            )
            result = session.execute(stmt).unique().scalar_one_or_none()
            return result



    def get_structure_by_id(self, structure_id: int) -> Optional[StructureModel]:
        with self.Session() as session:
            return session.get(StructureModel, structure_id)

    def get_simulation_parameters(self, sim_id: int) -> dict[str, str]:
        with self.Session() as session:
            stmt = select(SimulationModel.parameters).where(SimulationModel.id == sim_id)
            result = session.execute(stmt).scalar_one_or_none()
            return result or {}

    def get_monitor_parameters(self, monitor_id: int) -> dict[str, str]:
        with self.Session() as session:
            stmt = select(MonitorModel.parameters).where(MonitorModel.id == monitor_id)
            result = session.execute(stmt).scalar_one_or_none()
            return result or {}

    def add_simulation(self, sim: Union[Simulation, SimulationPydanticModel], session=None):
        if session:
            manage_context = False
        else:
            session = self.Session()
            manage_context = True

        if manage_context:
            with session as s:
                self._add_simulation_to_session(sim, s)
        else:
            self._add_simulation_to_session(sim, session)

    @staticmethod
    def _add_simulation_to_session(sim, session):

        # 1. Create SimulationModel
        sim_model = SimulationModel(
            category=sim.category,
            name=sim.name,
            parameters=sim.parameters
        )

        session.add(sim_model)
        session.flush()  # get sim_model.id before adding children

        # 2. Add structures
        for struct in sim.structures:
            if isinstance(struct, StructurePydanticModel):
                structure_model = StructureModel(
                    simulation_id=sim_model.id,
                    name=struct.name,
                    vertices=struct.vertices,
                    faces=struct.faces
                )
            else:
                structure_model = StructureModel(
                    simulation_id=sim_model.id,
                    name=struct.name,
                    vertices=struct.trimesh.vertices,
                    faces=struct.trimesh.faces
                )
            session.add(structure_model)

        # 3. Add monitors
        for mon in sim.monitors:
            if isinstance(mon, (FieldAndPowerMonitor, FieldAndPowerMonitorPydanticModel)):
                mon_model = FieldAndPowerMonitorModel(
                    simulation_id=sim_model.id,
                    name=mon.name,
                    monitor_type=mon.monitor_type,
                    parameters=mon.parameters,
                    wavelengths=mon.wavelengths,
                    x=mon.x,
                    y=mon.y,
                    z=mon.z,
                    T=mon.T if mon.T is not None else None,
                    power=mon.power if mon.power is not None else None,
                )
                session.add(mon_model)

                # Add associated E, H, P fields if present
                for field_obj in (mon.E, mon.H, mon.P):
                    if field_obj:
                        field_model = FieldModel(
                            _monitor=mon_model,
                            field_name=field_obj.field_name,
                            components=field_obj.components,
                            data=field_obj.data
                        )
                        session.add(field_model)

            else:
                raise ValueError(f"Unsupported monitor type: {type(mon)}")

        session.commit()

