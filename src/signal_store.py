import logging
from pathlib import Path
from typing import Dict, List, Optional, Set
from collections import defaultdict
import pandas as pd

from decoder import DecodedSignal, DecodedMessage

logger = logging.getLogger(__name__)


class SignalStore:
    """
    Stores and manages decoded CAN signals organized by signal name.
    """
    
    def __init__(self):
        """Initialize empty signal store."""
        self._signals: Dict[str, List[DecodedSignal]] = defaultdict(list)
        
        self._message_count = 0
        self._signal_count = 0
        
        logger.info("Initialized empty signal store")
    
    def add_signal(self, signal: DecodedSignal) -> None:
        """
        Add a single decoded signal to the store.
        """
        self._signals[signal.signal_name].append(signal)
        self._signal_count += 1
    
    def add_message(self, message: DecodedMessage) -> None:
        """
        Add all signals from a decoded message to the store.
        """
        for signal in message.signals.values():
            self.add_signal(signal)
        
        self._message_count += 1
    
    def add_messages(self, messages: List[DecodedMessage]) -> None:
        """
        Add multiple decoded messages to the store.
        """
        for message in messages:
            self.add_message(message)
        
        logger.info(f"Added {len(messages)} messages to store")
    
    def get_signal(self, signal_name: str) -> List[DecodedSignal]:
        """
        Get all samples of a specific signal.
        """
        if signal_name not in self._signals:
            logger.warning(f"Signal '{signal_name}' not found in store")
            return []
        
        return sorted(self._signals[signal_name], key=lambda s: s.timestamp)
    
    def get_signal_names(self) -> List[str]:
        """
        Get list of all signal names in the store.
        """
        return sorted(self._signals.keys())
    
    def get_signal_count(self, signal_name: str) -> int:
        """
        Get number of samples for a specific signal.
        """
        return len(self._signals.get(signal_name, []))
    
    def get_time_range(self, signal_name: Optional[str] = None) -> tuple[float, float]:
        """
        Get time range of signals in the store.
        """
        if signal_name:
            signals = self.get_signal(signal_name)
            if not signals:
                return (0.0, 0.0)
            return (signals[0].timestamp, signals[-1].timestamp)
        
        all_times = []
        for signals in self._signals.values():
            if signals:
                all_times.extend([s.timestamp for s in signals])
        
        if not all_times:
            return (0.0, 0.0)
        
        return (min(all_times), max(all_times))
    
    def get_statistics(self, signal_name: str) -> Optional[Dict]:
        """
        Get statistical summary for a signal.
        """
        signals = self.get_signal(signal_name)
        
        if not signals:
            return None
        
        values = [s.physical_value for s in signals]
        
        return {
            'signal_name': signal_name,
            'unit': signals[0].unit,
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'mean': sum(values) / len(values),
            'start_time': signals[0].timestamp,
            'end_time': signals[-1].timestamp
        }
    
    def export_csv(self, 
                   output_path: str,
                   signal_names: Optional[List[str]] = None) -> None:
        """
        Export stored signals to CSV file.
        
        CSV Format:
            Timestamp, Message, Signal, Value, Unit
            0.000123, EngineData, RPM, 768.0, RPM
            0.000123, EngineData, EngineTemp, 40.0, °C
            ...
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        if signal_names is None:
            signal_names = self.get_signal_names()
        else:
            available = set(self.get_signal_names())
            invalid = [name for name in signal_names if name not in available]
            if invalid:
                logger.warning(f"Signals not found: {invalid}")
            signal_names = [name for name in signal_names if name in available]
        
        if not signal_names:
            logger.error("No signals to export")
            return
        
        rows = []
        
        for signal_name in signal_names:
            signals = self.get_signal(signal_name)
            
            for signal in signals:
                rows.append({
                    'Timestamp': signal.timestamp,
                    'Message': signal.message_name,
                    'Signal': signal.signal_name,
                    'Raw_Value': signal.raw_value,
                    'Physical_Value': signal.physical_value,
                    'Unit': signal.unit,
                    'CAN_ID': f"0x{signal.can_id:X}"
                })
        
        df = pd.DataFrame(rows)
        df = df.sort_values('Timestamp')
        
        df.to_csv(output_file, index=False, float_format='%.6f')
        
        logger.info(f"Exported {len(rows)} signal samples to {output_file}")
        logger.info(f"Signals: {', '.join(signal_names)}")
        logger.info(f"File size: {output_file.stat().st_size / 1024:.1f} KB")
    
    def export_wide_format(self,
                          output_path: str,
                          signal_names: Optional[List[str]] = None) -> None:
        """
        Export signals in wide format (one column per signal).
        
        Wide Format (useful for plotting):
            Timestamp, RPM, Speed, EngineTemp, ...
            0.000123, 768.0, 0.0, 40.0, ...
            0.010245, 800.0, 5.0, 41.0, ...
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        if signal_names is None:
            signal_names = self.get_signal_names()
        
        signal_series = {}
        
        for signal_name in signal_names:
            signals = self.get_signal(signal_name)
            
            if not signals:
                continue
            
            timestamps = [s.timestamp for s in signals]
            values = [s.physical_value for s in signals]
            
            signal_series[signal_name] = pd.Series(values, index=timestamps)
        
        if not signal_series:
            logger.error("No signals to export")
            return
        
        df = pd.DataFrame(signal_series)
        
        df = df.fillna(method='ffill')
        
        df.index.name = 'Timestamp'
        df = df.reset_index()
        
        df.to_csv(output_file, index=False, float_format='%.6f')
        
        logger.info(f"Exported wide format to {output_file}")
        logger.info(f"Signals: {', '.join(df.columns[1:])}")
        logger.info(f"Rows: {len(df)}")

    def print_summary(self) -> None:
        """
        Print summary statistics of stored signals.
        """
        print("\n" + "="*60)
        print("Signal Store Summary")
        print("="*60)
        print(f"Messages processed: {self._message_count}")
        print(f"Total signal samples: {self._signal_count}")
        print(f"Unique signals: {len(self._signals)}")
        
        start_time, end_time = self.get_time_range()
        print(f"Time range: {start_time:.6f}s - {end_time:.6f}s ({end_time - start_time:.3f}s)")
        print()
        
        print("Signal Details:")
        print("-" * 60)
        print(f"{'Signal Name':<20} {'Samples':>8} {'Min':>10} {'Max':>10} {'Mean':>10} {'Unit':<8}")
        print("-" * 60)
        
        for signal_name in self.get_signal_names():
            stats = self.get_statistics(signal_name)
            if stats:
                print(f"{signal_name:<20} {stats['count']:>8} "
                      f"{stats['min']:>10.2f} {stats['max']:>10.2f} "
                      f"{stats['mean']:>10.2f} {stats['unit']:<8}")
        print()
    
    def clear(self) -> None:
        """
        Clear all stored signals.
        """
        self._signals.clear()
        self._message_count = 0
        self._signal_count = 0
        logger.info("Cleared signal store")


if __name__ == "__main__":
    """
    Test the signal store with example data.
    Run: python src/signal_store.py
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    from dbc_loader import load_dbc
    from can_log_reader import ASCReader
    from decoder import CANDecoder
    
    try:
        print("Loading DBC database...")
        db = load_dbc("dbc/example_vehicle.dbc")
        
        print("Initializing decoder...")
        decoder = CANDecoder(db)
        
        print("Reading CAN log...")
        reader = ASCReader("logs/drive_log.asc")
        
        print("Decoding frames...")
        frames = list(reader.read_frames())
        decoded_messages = decoder.decode_frames(frames)
        
        print("Storing signals...")
        store = SignalStore()
        store.add_messages(decoded_messages)
        
        store.print_summary()
        
        print("\nExporting to CSV (long format)...")
        store.export_csv("output/decoded_signals.csv")
        
        print("\nExporting to CSV (wide format)...")
        store.export_wide_format("output/decoded_signals_wide.csv")
        
        print("\nExporting selected signals...")
        store.export_csv(
            "output/engine_signals.csv",
            signal_names=["RPM", "Speed", "EngineTemp"]
        )
        
        print("\nAll exports completed successfully!")
        print("Check the 'output/' directory for CSV files")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()