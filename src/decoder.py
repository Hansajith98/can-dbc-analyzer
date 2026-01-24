import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import cantools.database

from can_log_reader import CANFrame

logger = logging.getLogger(__name__)


@dataclass
class DecodedSignal:
    """
    Represents a decoded CAN signal with physical value.
    """
    timestamp: float
    message_name: str
    signal_name: str
    raw_value: int
    physical_value: float
    unit: str
    can_id: int
    
    def __repr__(self) -> str:
        return (f"DecodedSignal(t={self.timestamp:.6f}, "
                f"{self.message_name}.{self.signal_name}="
                f"{self.physical_value:.2f} {self.unit})")


@dataclass
class DecodedMessage:
    """
    Represents all signals decoded from a single CAN frame.
    """
    timestamp: float
    message_name: str
    can_id: int
    signals: Dict[str, DecodedSignal] = field(default_factory=dict)
    
    def __repr__(self) -> str:
        signal_list = ", ".join([f"{s.signal_name}={s.physical_value:.2f}{s.unit}" 
                                 for s in self.signals.values()])
        return (f"DecodedMessage(t={self.timestamp:.6f}, "
                f"{self.message_name}: {signal_list})")


class CANDecoder:
    """
    Decodes CAN frames using DBC database definitions.
    """
    
    def __init__(self, database: cantools.database.Database):
        """
        Initialize decoder with DBC database.
        """
        self.database = database
        
        self._message_lookup = {msg.frame_id: msg for msg in database.messages}
        
        logger.info(f"Initialized decoder with {len(self._message_lookup)} messages")
        logger.debug(f"Known CAN IDs: {[f'0x{id:X}' for id in self._message_lookup.keys()]}")
    
    def decode_frame(self, frame: CANFrame) -> Optional[DecodedMessage]:
        """
        Decode a single CAN frame into signals.
        """
        if frame.can_id not in self._message_lookup:
            logger.debug(f"Unknown CAN ID: 0x{frame.can_id:X} at t={frame.timestamp:.6f}")
            return None
        
        message_def = self._message_lookup[frame.can_id]
        
        try:
            decoded_data = message_def.decode(frame.data, decode_choices=False)
            
            signals = {}
            for signal_def in message_def.signals:
                signal_name = signal_def.name
                
                physical_value = decoded_data.get(signal_name)
                
                if physical_value is None:
                    logger.warning(f"Signal {signal_name} not found in decoded data")
                    continue
                
                if signal_def.scale != 0:
                    raw_value = int((physical_value - signal_def.offset) / signal_def.scale)
                else:
                    raw_value = int(physical_value)
                
                signals[signal_name] = DecodedSignal(
                    timestamp=frame.timestamp,
                    message_name=message_def.name,
                    signal_name=signal_name,
                    raw_value=raw_value,
                    physical_value=float(physical_value),
                    unit=signal_def.unit or "",
                    can_id=frame.can_id
                )
            
            decoded_msg = DecodedMessage(
                timestamp=frame.timestamp,
                message_name=message_def.name,
                can_id=frame.can_id,
                signals=signals
            )
            
            return decoded_msg
            
        except Exception as e:
            logger.error(
                f"Failed to decode CAN ID 0x{frame.can_id:X} "
                f"({message_def.name}) at t={frame.timestamp:.6f}: {e}"
            )
            return None
    
    def decode_frames(self, frames: List[CANFrame]) -> List[DecodedMessage]:
        """
        Decode multiple CAN frames.
        """
        decoded_messages = []
        unknown_ids = set()
        
        for frame in frames:
            decoded = self.decode_frame(frame)
            
            if decoded is not None:
                decoded_messages.append(decoded)
            else:
                unknown_ids.add(frame.can_id)
        
        if unknown_ids:
            logger.warning(
                f"Encountered {len(unknown_ids)} unknown CAN IDs: "
                f"{[f'0x{id:X}' for id in sorted(unknown_ids)]}"
            )
        
        logger.info(f"Decoded {len(decoded_messages)} messages from {len(frames)} frames")
        
        return decoded_messages
    
    def get_signal_names(self) -> List[str]:
        """
        Get list of all signal names available in the database.
        """
        signal_names = set()
        
        for message in self.database.messages:
            for signal in message.signals:
                signal_names.add(signal.name)
        
        return sorted(signal_names)
    
    def get_message_info(self, can_id: int) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific CAN message.
        """
        if can_id not in self._message_lookup:
            return None
        
        msg = self._message_lookup[can_id]
        
        return {
            'name': msg.name,
            'can_id': msg.frame_id,
            'dlc': msg.length,
            'cycle_time': getattr(msg, 'cycle_time', None),
            'signals': [
                {
                    'name': sig.name,
                    'unit': sig.unit,
                    'min': sig.minimum,
                    'max': sig.maximum,
                    'factor': sig.scale,
                    'offset': sig.offset
                }
                for sig in msg.signals
            ]
        }
    
    def print_decoding_info(self) -> None:
        """
        Print detailed information about decoder capabilities.
        """
        print("\n" + "="*60)
        print("CAN Decoder Information")
        print("="*60)
        print(f"Database: {self.database.dbc.name if hasattr(self.database, 'dbc') else 'Unknown'}")
        print(f"Total messages: {len(self.database.messages)}")
        print(f"Total signals: {len(self.get_signal_names())}")
        print()
        
        print("Message Definitions:")
        print("-" * 60)
        for msg in sorted(self.database.messages, key=lambda m: m.frame_id):
            print(f"  0x{msg.frame_id:03X} {msg.name:20s} ({len(msg.signals)} signals)")
            for sig in msg.signals:
                print(f"    ├─ {sig.name:20s} [{sig.minimum:>6} - {sig.maximum:<6}] {sig.unit}")
        print()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    from dbc_loader import load_dbc
    from can_log_reader import ASCReader
    
    try:
        print("Loading DBC database...")
        db = load_dbc("dbc/example_vehicle.dbc")
        
        decoder = CANDecoder(db)
        decoder.print_decoding_info()
        
        print("\nReading CAN log...")
        reader = ASCReader("logs/drive_log.asc")
        
        print("\n" + "="*60)
        print("Decoding First 10 Frames")
        print("="*60)
        
        frame_count = 0
        for frame in reader.read_frames():
            decoded = decoder.decode_frame(frame)
            
            if decoded:
                print(f"\nTime: {decoded.timestamp:.6f}s | Message: {decoded.message_name}")
                for signal_name, signal in decoded.signals.items():
                    print(f"  {signal_name:20s} = {signal.physical_value:>8.2f} {signal.unit}")
            
            frame_count += 1
            if frame_count >= 10:
                break
        
        print("\n" + "="*60)
        print("Available Signals for Plotting")
        print("="*60)
        signals = decoder.get_signal_names()
        print(", ".join(signals))
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()