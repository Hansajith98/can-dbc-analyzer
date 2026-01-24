import logging
import re
from pathlib import Path
from typing import Iterator, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CANFrame:
    """
    Represents a single CAN frame from a log file.
    """
    timestamp: float
    can_id: int
    data: bytes
    dlc: int
    channel: int = 1
    is_extended: bool = False
    
    def __repr__(self) -> str:
        data_hex = ' '.join(f'{b:02X}' for b in self.data)
        id_format = f"0x{self.can_id:08X}" if self.is_extended else f"0x{self.can_id:03X}"
        return f"CANFrame(t={self.timestamp:.6f}, id={id_format}, data=[{data_hex}])"


class CANLogReadError(Exception):
    """Custom exception for CAN log reading failures"""
    pass


class ASCReader:
    """
    Parser for Vector ASC (ASCII) CAN log files.
    """
    

    FRAME_PATTERN = re.compile(
        r'^\s*(?P<timestamp>[\d.]+)\s+'           
        r'(?P<channel>\d+)\s+'                     
        r'(?P<can_id>[0-9A-Fa-fx]+)\s+'            
        r'(?P<direction>Rx|Tx)\s+'                 
        r'd\s+'                                     
        r'(?P<dlc>\d+)'                            
        r'(?P<data>(?:\s+[0-9A-Fa-f]{2})*)'        
    )
    
    def __init__(self, log_path: str):
        """
        Initialize ASC reader.
        """
        self.log_path = Path(log_path)
        
        if not self.log_path.exists():
            raise CANLogReadError(f"Log file not found: {log_path}")
        
        if self.log_path.suffix.lower() != '.asc':
            logger.warning(f"File extension is {self.log_path.suffix}, expected .asc")
        
        logger.info(f"Initialized ASC reader for: {self.log_path.name}")
    
    def read_frames(self, 
                    start_time: Optional[float] = None,
                    end_time: Optional[float] = None,
                    can_ids: Optional[list[int]] = None) -> Iterator[CANFrame]:
        """
        Read CAN frames from the log file.
        """
        frame_count = 0
        filtered_count = 0
        
        try:
            with open(self.log_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    if not line.strip() or line.startswith('//'):
                        continue
                    
                    frame = self._parse_line(line)
                    
                    if frame is None:
                        continue
                    
                    frame_count += 1
                    
                    if start_time is not None and frame.timestamp < start_time:
                        filtered_count += 1
                        continue
                    
                    if end_time is not None and frame.timestamp > end_time:
                        filtered_count += 1
                        continue
                    
                    if can_ids is not None and frame.can_id not in can_ids:
                        filtered_count += 1
                        continue
                    
                    yield frame
            
            logger.info(f"Read {frame_count} frames ({filtered_count} filtered)")
            
        except IOError as e:
            raise CANLogReadError(f"Failed to read log file: {e}") from e
    
    def _parse_line(self, line: str) -> Optional[CANFrame]:
        """
        Parse a single line from ASC file.
        """
        match = self.FRAME_PATTERN.match(line)
        
        if not match:
            return None
        
        try:
            timestamp = float(match.group('timestamp'))
            channel = int(match.group('channel'))
            dlc = int(match.group('dlc'))
            
            can_id_str = match.group('can_id')
            can_id = int(can_id_str, 16)
            
            is_extended = can_id > 0x7FF
            
            data_str = match.group('data').strip()
            if data_str:
                data_bytes = bytes.fromhex(data_str.replace(' ', ''))
            else:
                data_bytes = b''
            
            if len(data_bytes) != dlc:
                logger.warning(
                    f"DLC mismatch: declared={dlc}, actual={len(data_bytes)} "
                    f"at t={timestamp:.6f}, ID=0x{can_id:X}"
                )
            
            return CANFrame(
                timestamp=timestamp,
                can_id=can_id,
                data=data_bytes,
                dlc=dlc,
                channel=channel,
                is_extended=is_extended
            )
            
        except (ValueError, AttributeError) as e:
            logger.debug(f"Failed to parse line: {line.strip()} | Error: {e}")
            return None
    
    def get_summary(self) -> dict:
        """
        Get statistical summary of the log file.
        """
        frames = list(self.read_frames())
        
        if not frames:
            return {
                'total_frames': 0,
                'duration': 0.0,
                'unique_ids': 0,
                'start_time': 0.0,
                'end_time': 0.0
            }
        
        unique_ids = set(f.can_id for f in frames)
        
        return {
            'total_frames': len(frames),
            'duration': frames[-1].timestamp - frames[0].timestamp,
            'unique_ids': len(unique_ids),
            'start_time': frames[0].timestamp,
            'end_time': frames[-1].timestamp,
            'can_ids': sorted(unique_ids)
        }


if __name__ == "__main__":
    """
    Test the CAN log reader with an example file.
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        reader = ASCReader("logs/drive_log.asc")
        
        summary = reader.get_summary()
        print("\n" + "="*50)
        print("CAN Log Summary")
        print("="*50)
        print(f"Total frames: {summary['total_frames']}")
        print(f"Duration: {summary['duration']:.3f} seconds")
        print(f"Unique CAN IDs: {summary['unique_ids']}")
        print(f"CAN IDs present: {[f'0x{id:X}' for id in summary['can_ids']]}")
        print()
        
        print("First 10 frames:")
        print("-" * 50)
        for i, frame in enumerate(reader.read_frames()):
            if i >= 10:
                break
            print(frame)
        
        print("\n" + "="*50)
        print("Engine Data frames (ID 0x100):")
        print("-" * 50)
        count = 0
        for frame in reader.read_frames(can_ids=[0x100]):
            print(frame)
            count += 1
            if count >= 5:
                break
        
    except CANLogReadError as e:
        print(f"Error: {e}")