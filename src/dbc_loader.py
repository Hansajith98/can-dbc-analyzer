"""
DBC Loader Module
-----------------
Loads and validates CAN database (.dbc) files.

DBC files define the structure of CAN messages used in automotive networks.
They specify:
- CAN message IDs (arbitration IDs)
- Signal names, positions, and data types
- Scaling factors and offsets for physical value conversion
- Units (km/h, RPM, °C, etc.)
"""

import logging
from pathlib import Path
from typing import Optional
import cantools.database

logger = logging.getLogger(__name__)


class DBCLoadError(Exception):
    """Custom exception for DBC loading failures"""
    pass


def load_dbc(dbc_path: str) -> cantools.database.Database:
    """
    Load a CAN database from a .dbc file.
    
    Args:
        dbc_path: Path to the .dbc file
        
    Returns:
        cantools.database.Database: Parsed DBC database object
        
    Raises:
        DBCLoadError: If file doesn't exist or parsing fails
        
    Example:
        >>> db = load_dbc("dbc/example_vehicle.dbc")
        >>> print(f"Loaded {len(db.messages)} messages")
    """
    path = Path(dbc_path)
    
    if not path.exists():
        error_msg = f"DBC file not found: {dbc_path}"
        logger.error(error_msg)
        raise DBCLoadError(error_msg)
    
    if path.suffix.lower() != '.dbc':
        error_msg = f"Invalid file extension: {path.suffix}. Expected .dbc"
        logger.warning(error_msg)
    
    try:
        logger.info(f"Loading DBC file: {dbc_path}")
        db = cantools.database.load_file(str(path))
        
        logger.info(f" Successfully loaded DBC: {path.name}")
        logger.info(f"   Messages: {len(db.messages)}")
        logger.info(f"   Nodes: {len(db.nodes) if db.nodes else 0}")
        
        if len(db.messages) == 0:
            logger.warning("DBC file contains no messages")
        
        return db
        
    except Exception as e:
        error_msg = f"Failed to parse DBC file: {e}"
        logger.error(error_msg)
        raise DBCLoadError(error_msg) from e


def print_dbc_info(db: cantools.database.Database) -> None:
    """
    Print detailed information about loaded DBC database.
    
    Args:
        db: Loaded cantools database object
        
    Example output:
        DBC Database Info
        =================
        Messages: 5
        
        Message: EngineData (ID: 0x100)
          - RPM: Engine speed [0-8000 RPM]
          - EngineTemp: Engine temperature [-40-200 °C]
    """
    print("\n" + "="*50)
    print("DBC Database Info")
    print("="*50)
    print(f"Messages: {len(db.messages)}\n")
    
    for msg in db.messages:
        print(f"Message: {msg.name} (ID: 0x{msg.frame_id:X}, DLC: {msg.length} bytes)")
        
        for signal in msg.signals:
            unit_str = f" {signal.unit}" if signal.unit else ""
            min_max = f"[{signal.minimum}-{signal.maximum}{unit_str}]"
            print(f"  - {signal.name}: {signal.comment or 'No description'} {min_max}")
        print()


def validate_dbc_signals(db: cantools.database.Database, 
                         required_signals: list[str]) -> tuple[bool, list[str]]:
    """
    Check if required signals exist in the DBC database.
    
    Args:
        db: Loaded cantools database
        required_signals: List of signal names to validate
        
    Returns:
        tuple: (all_found: bool, missing_signals: list[str])
        
    Example:
        >>> valid, missing = validate_dbc_signals(db, ["Speed", "RPM"])
        >>> if not valid:
        >>>     print(f"Missing signals: {missing}")
    """
    all_signals = set()
    for msg in db.messages:
        for signal in msg.signals:
            all_signals.add(signal.name)
    
    missing = [sig for sig in required_signals if sig not in all_signals]
    
    if missing:
        logger.warning(f"Missing signals in DBC: {missing}")
        return False, missing
    
    logger.info(f"All required signals found: {required_signals}")
    return True, []


if __name__ == "__main__":
    """
    Test the DBC loader with an example file.
    Run: python src/dbc_loader.py
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        db = load_dbc("dbc/sample_vehicle_data.dbc")
        print_dbc_info(db)
        
        test_signals = ["Speed", "RPM", "EngineTemp"]
        valid, missing = validate_dbc_signals(db, test_signals)
        
        if not valid:
            print(f"\nWarning: Missing signals: {missing}")
        else:
            print(f"\nAll test signals found!")
            
    except DBCLoadError as e:
        print(f"Error: {e}")