from pathlib import Path
from typing import List, Tuple
from typing import Optional

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, joinedload, selectinload

from .db import Base, SimulationModel, MonitorModel, StructureModel, FieldModel, FieldAndPowerMonitorModel
from ..results.monitors import FieldAndPowerMonitor
from ..results.simulation import Simulation


class DatabaseHandler:
    def __init__(self, db_path: str):
        # Ensure path ends with .db
        path = Path(db_path)
        if path.suffix != ".db":
            path = path.with_suffix(".db")

        # Convert to full SQLite URI
        uri = f"sqlite:///{path.resolve()}"

        self.engine = create_engine(uri, echo=False, future=True)
        self.Session = sessionmaker(bind=self.engine, future=True)

        # Import your models and create tables
        Base.metadata.create_all(self.engine)

    # Just category names (distinct)
    def get_all_categories(self) -> List[str]:
        with self.Session() as session:
            stmt = select(SimulationModel.category).distinct()
            return session.execute(stmt).scalars().all()

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
                select(SimulationModel).where(SimulationModel.id == sim_id)
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

    def add_simulation(self, sim: Simulation):
        with self.Session() as session:
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
                structure_model = StructureModel(
                    simulation_id=sim_model.id,
                    name=struct.name,
                    vertices=struct.trimesh.vertices,
                    faces=struct.trimesh.faces
                )
                session.add(structure_model)

            # 3. Add monitors
            for mon in sim.monitors:
                if isinstance(mon, FieldAndPowerMonitor):
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

