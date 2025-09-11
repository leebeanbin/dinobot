"""
Base DTO class for all data transfer objects
"""

from pydantic import BaseModel


class BaseDTO(BaseModel):
    """Base class for all DTOs"""

    model_config = {
        # Allow field names in Korean (changed to validate_by_name in Pydantic v2)
        "validate_by_name": True,
        # Convert Enum to values during JSON serialization
        "use_enum_values": True,
    }

    def model_dump_json(self, **kwargs):
        """Serialize datetime objects to ISO format"""
        return super().model_dump_json(mode="json", **kwargs)