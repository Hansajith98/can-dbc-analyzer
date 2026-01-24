import sys
import logging
import argparse
from pathlib import Path
from typing import List, Optional

from dbc_loader import load_dbc, DBCLoadError
from can_log_reader import ASCReader, CANLogReadError
from decoder import CANDecoder
from signal_store import SignalStore
from plotter import SignalPlotter


__version__ = "1.0.0"


def setup_logging(verbose: bool = False) -> None:
    """
    Configure application logging.
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format
    )
    
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description='CAN Bus DBC Signal Decoder and Analyzer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage - decode all signals
  python main.py --dbc dbc/example_vehicle.dbc --log logs/drive_log.asc
  
  # Decode and plot specific signals
  python main.py --dbc dbc/example_vehicle.dbc --log logs/drive_log.asc --signals RPM Speed EngineTemp
  
  # Export to custom location
  python main.py --dbc dbc/example_vehicle.dbc --log logs/drive_log.asc --output my_output/data.csv
  
  # Create overview dashboard
  python main.py --dbc dbc/example_vehicle.dbc --log logs/drive_log.asc --overview
  
  # Wide format CSV for plotting tools
  python main.py --dbc dbc/example_vehicle.dbc --log logs/drive_log.asc --wide
        """
    )
    
    parser.add_argument(
        '--dbc',
        type=str,
        required=True,
        metavar='PATH',
        help='Path to DBC database file (.dbc)'
    )
    
    parser.add_argument(
        '--log',
        type=str,
        required=True,
        metavar='PATH',
        help='Path to CAN log file (.asc)'
    )
    
    parser.add_argument(
        '--signals',
        type=str,
        nargs='+',
        metavar='NAME',
        help='Specific signals to process (default: all signals)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default='output/decoded_signals.csv',
        metavar='PATH',
        help='Output CSV file path (default: output/decoded_signals.csv)'
    )
    
    parser.add_argument(
        '--plot-dir',
        type=str,
        default='output/plots',
        metavar='PATH',
        help='Directory for plot outputs (default: output/plots)'
    )
    
    parser.add_argument(
        '--wide',
        action='store_true',
        help='Export CSV in wide format (one column per signal)'
    )
    
    parser.add_argument(
        '--no-plot',
        action='store_true',
        help='Disable plotting (only export CSV)'
    )
    
    parser.add_argument(
        '--overview',
        action='store_true',
        help='Create driving overview dashboard plot'
    )
    
    parser.add_argument(
        '--start-time',
        type=float,
        metavar='SEC',
        help='Filter frames after this timestamp (seconds)'
    )
    
    parser.add_argument(
        '--end-time',
        type=float,
        metavar='SEC',
        help='Filter frames before this timestamp (seconds)'
    )
    
    parser.add_argument(
        '--can-ids',
        type=str,
        nargs='+',
        metavar='ID',
        help='Filter specific CAN IDs (hex format: 0x100 or 100)'
    )
    
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Enable verbose debug output'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )
    
    return parser.parse_args()


def parse_can_ids(can_id_strings: Optional[List[str]]) -> Optional[List[int]]:
    """
    Parse CAN ID strings (hex or decimal) to integers.
    """
    if not can_id_strings:
        return None
    
    can_ids = []
    for id_str in can_id_strings:
        try:
            can_id = int(id_str, 0) 
            can_ids.append(can_id)
        except ValueError:
            logging.error(f"Invalid CAN ID format: {id_str}")
            sys.exit(1)
    
    return can_ids


def main() -> int:
    """
    Main application entry point.
    """
    args = parse_arguments()
    
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    print("\n" + "="*70)
    print("  CAN Bus DBC Signal Decoder and Analyzer")
    print(f"  Version {__version__}")
    print("="*70 + "\n")
    
    try:
        logger.info("Step 1/5: Loading DBC database...")
        print(f"Loading DBC: {args.dbc}")
        db = load_dbc(args.dbc)
        print(f"  Loaded {len(db.messages)} messages with {len([s for m in db.messages for s in m.signals])} signals")
        
        logger.info("Step 2/5: Reading CAN log file...")
        print(f"\nReading log: {args.log}")
        reader = ASCReader(args.log)
        
        can_id_filter = parse_can_ids(args.can_ids)
        
        frames = list(reader.read_frames(
            start_time=args.start_time,
            end_time=args.end_time,
            can_ids=can_id_filter
        ))
        
        if not frames:
            logger.error("No frames found matching filters")
            print("  No frames to process")
            return 1
        
        summary = reader.get_summary()
        print(f"   Read {len(frames)} frames")
        print(f"   Duration: {summary['duration']:.3f} seconds")
        print(f"   CAN IDs: {[f'0x{id:X}' for id in summary['can_ids']]}")
        
        logger.info("Step 3/5: Decoding CAN frames...")
        print(f"\n Decoding frames using DBC...")
        decoder = CANDecoder(db)
        decoded_messages = decoder.decode_frames(frames)
        
        if not decoded_messages:
            logger.error("No messages could be decoded")
            print("  No decodable messages found")
            return 1
        
        print(f"  Decoded {len(decoded_messages)} messages")
        
        logger.info("Step 4/5: Storing signals...")
        print(f"\nStoring signals...")
        store = SignalStore()
        store.add_messages(decoded_messages)
        
        available_signals = store.get_signal_names()
        print(f"  Stored {len(available_signals)} unique signals")
        print(f"  Available: {', '.join(available_signals[:10])}")
        if len(available_signals) > 10:
            print(f"              ... and {len(available_signals) - 10} more")
        
        signals_to_export = args.signals if args.signals else None
        
        if signals_to_export:
            invalid = [s for s in signals_to_export if s not in available_signals]
            if invalid:
                logger.warning(f"Signals not found: {invalid}")
                print(f"  Warning: Signals not found: {invalid}")
            
            signals_to_export = [s for s in signals_to_export if s in available_signals]
            
            if not signals_to_export:
                logger.error("No valid signals to export")
                print("  No valid signals to export")
                return 1
        
        store.print_summary()
        
        logger.info("Step 5/5: Exporting and plotting...")
        print(f"\nExporting results...")
        
        if args.wide:
            print(f"  Exporting wide format CSV: {args.output}")
            store.export_wide_format(args.output, signal_names=signals_to_export)
        else:
            print(f"  Exporting long format CSV: {args.output}")
            store.export_csv(args.output, signal_names=signals_to_export)
        
        if not args.no_plot:
            print(f"\nCreating plots...")
            plotter = SignalPlotter(store)
            plot_dir = Path(args.plot_dir)
            
            if args.overview:
                overview_path = plot_dir / "overview_dashboard.png"
                print(f"  Generating overview dashboard: {overview_path}")
                plotter.plot_driving_overview(save_path=str(overview_path))
            
            if signals_to_export:
                for signal_name in signals_to_export:
                    plot_path = plot_dir / f"{signal_name.lower()}.png"
                    print(f"  Plotting {signal_name}: {plot_path}")
                    plotter.plot_signal(signal_name, save_path=str(plot_path))
                
                if len(signals_to_export) > 1:
                    combined_path = plot_dir / "combined_signals.png"
                    print(f"  Creating combined plot: {combined_path}")
                    plotter.plot_signals(signals_to_export, save_path=str(combined_path))
                    
                    if len(signals_to_export) <= 5:  
                        subplots_path = plot_dir / "subplots.png"
                        print(f"  Creating subplots: {subplots_path}")
                        plotter.plot_signals_subplots(signals_to_export, 
                                                     save_path=str(subplots_path))
        
        print("\n" + "="*70)
        print("  Processing Complete!")
        print("="*70)
        print(f"\nOutput files:")
        print(f"   CSV: {args.output}")
        if not args.no_plot:
            print(f"   Plots: {args.plot_dir}/")
        print()
        
        return 0
        
    except DBCLoadError as e:
        logger.error(f"DBC loading failed: {e}")
        print(f"\nError loading DBC file: {e}")
        return 1
    
    except CANLogReadError as e:
        logger.error(f"Log reading failed: {e}")
        print(f"\nError reading CAN log: {e}")
        return 1
    
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        print("\n\nInterrupted by user")
        return 1
    
    except Exception as e:
        logger.exception("Unexpected error occurred")
        print(f"\nUnexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())