from pydantic import BaseModel, Field

class BatchTelemetry(BaseModel):
    """
    Pydantic schema for strict type validation of continuous batch process telemetry.
    Based on the exact column structure from _h_batch_process_data.xlsx.
    """
    Batch_ID: str
    Time_Minutes: int = Field(..., ge=0, description="Cannot be negative")
    Phase: str
    Temperature_C: float
    Pressure_Bar: float = Field(..., ge=0.0, description="Cannot be negative")
    
    # CRITICAL FIX: Humidity physically bounded between 0 and 100
    Humidity_Percent: float = Field(..., ge=0.0, le=100.0, description="Must be a valid percentage")
    
    Motor_Speed_RPM: int = Field(..., ge=0, description="Cannot be negative")
    Compression_Force_kN: int = Field(..., ge=0, description="Cannot be negative")
    Flow_Rate_LPM: int = Field(..., ge=0, description="Cannot be negative")
    Power_Consumption_kW: float = Field(..., ge=0.0, description="Cannot be negative")
    Vibration_mm_s: float = Field(..., ge=0.0, description="Cannot be negative")