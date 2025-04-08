from .db import Base, Column, Integer, ForeignKey, relationship
from .custom_types import NumpyArrayType

class TResultDB(Base):
    __tablename__ = "t_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    monitor_id = Column(Integer, ForeignKey("field_and_power.id"), nullable=False)
    wavelengths = Column(NumpyArrayType)
    data = Column(NumpyArrayType)

    monitor = relationship("FieldAndPowerDB", back_populates="t_result")

    @classmethod
    def from_result(cls, result: TResult, monitor_id: int) -> "TResultDB":
        """
        Convert a TResult object to a TResultDB object.
        """
        # Convert wavelengths and data (ensure they are numpy arrays)
        return cls(
            monitor_id=monitor_id,
            wavelengths=result.wavelengths,
            data=result.data
        )

    def to_result(self) -> TResult:
        """
        Convert a TResultDB object to a TResult object.
        """
        return TResult(
            object_name=self.monitor.name,  # Assuming 'name' exists in the monitor
            plane_normal=self.monitor.plane_normal,  # Assuming 'plane_normal' exists in the monitor
            wavelengths=self.wavelengths,
            data=self.data
        )