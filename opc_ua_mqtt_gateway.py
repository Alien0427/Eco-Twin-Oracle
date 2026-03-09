"""
ENTERPRISE DEPLOYMENT GATEWAY: 

For the AVEVA Hackathon, the Eco-Twin Oracle ingests the provided historical Excel datasets 
via stream_simulator.py to simulate live WebSocket streaming. 

For real-world deployment, this OPC-UA Gateway script replaces the simulator, seamlessly routing 
live factory PLC data into the Oracle without altering the backend FastAPI/DFA architecture.

This mock adapter acts as an edge gateway demonstrating how industrial sensors mapped over 
OPC-UA/MQTT would pipe directly into the Eco-Twin Oracle's real-time ingestion layer.
"""

import asyncio
import json
import logging
import random
import time
import websockets

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

class FactoryPLCAdapter:
    """
    A simulated Industrial IoT (IIoT) edge gateway that interfaces with 
    a factory floor Programmable Logic Controller (PLC) via OPC-UA.
    """
    
    def __init__(self, endpoint_url: str = "opc.tcp://factory-plc.local:4840"):
        self.endpoint = endpoint_url
        self.connected = False
        logger.info(f"Initialising OPC-UA Client at {self.endpoint}")

    async def connect(self):
        """Simulate connection handshake to the industrial PLC."""
        logger.info("Connecting to factory PLC...")
        await asyncio.sleep(1) # Handshake delay
        self.connected = True
        logger.info("OPC-UA Secure Channel Established.")

    def read_opc_ua_node(self) -> dict:
        """
        Polls the hardware tags. In production, this would use asyncua/opcua.
        Returns a dictionary perfectly mirroring our BatchTelemetry schema.
        """
        if not self.connected:
            raise ConnectionError("PLC Not Connected")
            
        # Mocking sensor readings from physical tags
        return {
            "Batch_ID": "PRODUCTION_001",
            "Time_Minutes": int(time.time() % 1000), # Simulated incremental timeline
            "Temperature_C": round(random.uniform(20.0, 75.0), 2),
            "Pressure_Bar": round(random.uniform(0.9, 4.5), 2),
            "Humidity_Percent": round(random.uniform(40.0, 60.0), 2),
            "Motor_Speed_RPM": int(random.choice([0, 1500, 3000])),
            "Vibration_mm_s": round(random.uniform(0.1, 5.0), 3),
            "Power_Consumption_kW": round(random.uniform(1.0, 35.0), 3)
        }


async def main():
    """
    Primary async execution loop bridging the Factory Floor to the Cloud Oracle.
    """
    # ── 1. Initialise the Hardware Gateway ───────────────────────
    plc = FactoryPLCAdapter()
    await plc.connect()
    
    # ── 2. Establish Cloud/Edge Oracle Uplink ────────────────────
    batch_id = "PRODUCTION_001"
    oracle_ws_uri = f"ws://localhost:8000/ws/live-batch/{batch_id}"
    
    logger.info(f"Opening WebSocket uplink to Eco-Twin Oracle at {oracle_ws_uri}")
    
    try:
        async with websockets.connect(oracle_ws_uri) as ws:
            logger.info("✅ Edge-to-Cloud Oracle Uplink Secured.")
            
            while True:
                # Poll Hardware
                raw_telemetry = plc.read_opc_ua_node()
                
                # In production, the gateway doesn't strictly know the DFA state. 
                # For safety, we align with the expected schema payload. Since the 
                # oracle manages DFA via Phase string streams, we simulate passing Phase:
                phase_data = "Preparation" if raw_telemetry["Time_Minutes"] < 100 else "Granulation"
                
                # Format exactly to pipeline standards mapping telemetry
                payload = {
                    "event": "live_telemetry",
                    "telemetry": raw_telemetry,
                    "dfa_state": phase_data,
                    "timestamp_ms": int(time.time() * 1000)
                }
                
                # Forward to Oracle
                await ws.send(json.dumps(payload))
                logger.info(f"Uplinked Telemetry Packet | Power: {raw_telemetry['Power_Consumption_kW']} kW")
                
                # Industrial poll rate (e.g. 1Hz)
                await asyncio.sleep(1.0)
                
    except websockets.exceptions.ConnectionClosed:
        logger.warning("Oracle Connection Dropped (Batch Exited or Timeout).")
    except Exception as e:
        logger.error(f"Gateway Critical Fault: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Gateway Shutdown Commanded by Operator.")
