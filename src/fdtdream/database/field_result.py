from .db import Base, Column, PickleType, Integer, ForeignKey, relationship, String
from ..results import Field
from .custom_types import NumpyArrayType
from typing import Self


class FieldResultDB(Base):
    __tablename__ = "field_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    monitor_id = Column(Integer, ForeignKey("field_and_power.id"), nullable=False)
    wavelengths = Column(NumpyArrayType)
    x_coords = Column(NumpyArrayType)
    y_coords = Column(NumpyArrayType)
    z_coords = Column(NumpyArrayType)
    x_field = Column(NumpyArrayType)
    y_field = Column(NumpyArrayType)
    z_field = Column(NumpyArrayType)
    field_type = Column(String)  # Add the field type column

    monitor = relationship("FieldAndPowerDB", back_populates="field_result")

    @classmethod
    def field_result_to_db(cls, field_result: Field, monitor_id: int) -> Self:
        # Create a FieldResultDB object from FieldResult
        field_result_db = cls(
            monitor_id=monitor_id,  # Pass the monitor_id
            wavelengths=field_result.wavelengths.tolist(),  # Convert numpy arrays to lists
            x_coords=field_result.x_coords,
            y_coords=field_result.y_coords,
            z_coords=field_result.z_coords,
            x_field=field_result.x_field,
            y_field=field_result.y_field,
            z_field=field_result.z_field,
            field_type=field_result.field_type
        )
        return field_result_db

    def field_result_db_to_object(self) -> Field:
        # Create a FieldResult object from FieldResultDB
        field_result = Field(
            monitor_name=self.monitor.monitor_name,
            plane_normal=self.monitor.plane_normal,
            wavelengths=self.wavelengths,
            x_coords=self.x_coords,
            y_coords=self.y_coords,
            z_coords=self.z_coords,
            x_field=self.x_field,
            y_field=self.y_field,
            z_field=self.z_field,
            field_type=self.field_type
        )
        return field_result