import logging
from pathlib import Path
from typing import List, Optional, Tuple
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.figure import Figure
from matplotlib.axes import Axes

from signal_store import SignalStore

logger = logging.getLogger(__name__)

plt.style.use('seaborn-v0_8-darkgrid')


class SignalPlotter:
    """
    Creates time-series plots of CAN signals.
    """
    
    def __init__(self, signal_store: SignalStore):
        """
        Initialize plotter with signal store.
        """
        self.store = signal_store
        
        self.figsize = (12, 6)
        self.dpi = 100
        self.linewidth = 1.5
        self.grid_alpha = 0.3
        
        logger.info("Initialized signal plotter")
    
    def plot_signal(self,
                    signal_name: str,
                    save_path: Optional[str] = None,
                    show: bool = False,
                    title: Optional[str] = None,
                    color: str = 'steelblue') -> Optional[Figure]:
        """
        Plot a single signal over time.
        """
        # Get signal data
        signals = self.store.get_signal(signal_name)
        
        if not signals:
            logger.error(f"Signal '{signal_name}' not found")
            return None
        
        timestamps = [s.timestamp for s in signals]
        values = [s.physical_value for s in signals]
        unit = signals[0].unit
        
        fig, ax = plt.subplots(figsize=self.figsize, dpi=self.dpi)
        
        ax.plot(timestamps, values, color=color, linewidth=self.linewidth, 
                label=signal_name, marker='o', markersize=3, markevery=max(1, len(timestamps)//50))
        
        ax.set_xlabel('Time (s)', fontsize=12, fontweight='bold')
        ax.set_ylabel(f'{signal_name} ({unit})' if unit else signal_name, 
                     fontsize=12, fontweight='bold')
        ax.set_title(title or f'{signal_name} vs Time', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=self.grid_alpha)
        ax.legend(loc='best', fontsize=10)
        
        plt.tight_layout()
        
        if save_path:
            self._save_figure(fig, save_path)
        
        if show:
            plt.show()
        else:
            plt.close(fig)
        
        return fig
    
    def plot_signals(self,
                     signal_names: List[str],
                     save_path: Optional[str] = None,
                     show: bool = False,
                     title: Optional[str] = None,
                     colors: Optional[List[str]] = None) -> Optional[Figure]:
        """
        Plot multiple signals on the same axes (with dual y-axes if units differ).
        """
        if not signal_names:
            logger.error("No signal names provided")
            return None
        
        if colors is None:
            colors = ['steelblue', 'coral', 'seagreen', 'purple', 'orange', 'crimson']
        
        available_signals = []
        for name in signal_names:
            signals = self.store.get_signal(name)
            if signals:
                available_signals.append((name, signals))
            else:
                logger.warning(f"Signal '{name}' not found, skipping")
        
        if not available_signals:
            logger.error("No valid signals to plot")
            return None
        
        units = [signals[0].unit for _, signals in available_signals]
        same_unit = all(u == units[0] for u in units)
        
        fig, ax1 = plt.subplots(figsize=self.figsize, dpi=self.dpi)
        
        if same_unit:
            for idx, (name, signals) in enumerate(available_signals):
                timestamps = [s.timestamp for s in signals]
                values = [s.physical_value for s in signals]
                color = colors[idx % len(colors)]
                
                ax1.plot(timestamps, values, color=color, linewidth=self.linewidth,
                        label=name, marker='o', markersize=3, 
                        markevery=max(1, len(timestamps)//50))
            
            ax1.set_ylabel(f'Value ({units[0]})' if units[0] else 'Value', 
                          fontsize=12, fontweight='bold')
        
        else:
            ax2 = ax1.twinx()
            axes = [ax1, ax2]
            
            for idx, (name, signals) in enumerate(available_signals):
                timestamps = [s.timestamp for s in signals]
                values = [s.physical_value for s in signals]
                color = colors[idx % len(colors)]
                unit = signals[0].unit
                
                ax = axes[idx % 2]
                
                ax.plot(timestamps, values, color=color, linewidth=self.linewidth,
                       label=name, marker='o', markersize=3,
                       markevery=max(1, len(timestamps)//50))
                ax.set_ylabel(f'{name} ({unit})' if unit else name,
                            fontsize=12, fontweight='bold', color=color)
                ax.tick_params(axis='y', labelcolor=color)
            
            lines1, labels1 = ax1.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax1.legend(lines1 + lines2, labels1 + labels2, loc='best', fontsize=10)
        
        ax1.set_xlabel('Time (s)', fontsize=12, fontweight='bold')
        ax1.set_title(title or f'CAN Signals vs Time', fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=self.grid_alpha)
        
        if same_unit:
            ax1.legend(loc='best', fontsize=10)
        
        plt.tight_layout()
        
        if save_path:
            self._save_figure(fig, save_path)
        
        if show:
            plt.show()
        else:
            plt.close(fig)
        
        return fig
    
    def plot_signals_subplots(self,
                             signal_names: List[str],
                             save_path: Optional[str] = None,
                             show: bool = False,
                             title: Optional[str] = None,
                             figsize: Optional[Tuple[int, int]] = None) -> Optional[Figure]:
        """
        Plot multiple signals in separate subplots (stacked vertically).
        """
        if not signal_names:
            logger.error("No signal names provided")
            return None
        
        available_signals = []
        for name in signal_names:
            signals = self.store.get_signal(name)
            if signals:
                available_signals.append((name, signals))
            else:
                logger.warning(f"Signal '{name}' not found, skipping")
        
        if not available_signals:
            logger.error("No valid signals to plot")
            return None
        
        n_signals = len(available_signals)
        
        if figsize is None:
            figsize = (12, 3 * n_signals)
        
        fig, axes = plt.subplots(n_signals, 1, figsize=figsize, 
                                sharex=True, dpi=self.dpi)
        
        if n_signals == 1:
            axes = [axes]
        
        colors = ['steelblue', 'coral', 'seagreen', 'purple', 'orange', 'crimson']
        
        for idx, (name, signals) in enumerate(available_signals):
            ax = axes[idx]
            
            timestamps = [s.timestamp for s in signals]
            values = [s.physical_value for s in signals]
            unit = signals[0].unit
            color = colors[idx % len(colors)]
            
            ax.plot(timestamps, values, color=color, linewidth=self.linewidth,
                   label=name, marker='o', markersize=3,
                   markevery=max(1, len(timestamps)//50))
            
            ax.set_ylabel(f'{name} ({unit})' if unit else name,
                         fontsize=11, fontweight='bold')
            ax.grid(True, alpha=self.grid_alpha)
            ax.legend(loc='upper right', fontsize=9)
            
            if idx == n_signals - 1:
                ax.set_xlabel('Time (s)', fontsize=12, fontweight='bold')
        
        if title:
            fig.suptitle(title, fontsize=14, fontweight='bold', y=0.995)
        
        plt.tight_layout()
        
        if save_path:
            self._save_figure(fig, save_path)
        
        if show:
            plt.show()
        else:
            plt.close(fig)
        
        return fig
    
    def plot_driving_overview(self,
                            save_path: Optional[str] = None,
                            show: bool = False) -> Optional[Figure]:
        """
        Create a comprehensive overview plot with key driving signals.
        """
        # Define signals for overview
        overview_signals = [
            ["Speed", "RPM"],
            ["EngineTemp", "EngineLoad"],
            ["GearPosition"]
        ]
        
        fig = plt.figure(figsize=(14, 10), dpi=self.dpi)
        gs = gridspec.GridSpec(3, 1, height_ratios=[1, 1, 0.8])
        
        colors = ['steelblue', 'coral', 'seagreen', 'purple']
        
        for subplot_idx, signal_group in enumerate(overview_signals):
            ax = fig.add_subplot(gs[subplot_idx])
            
            for sig_idx, signal_name in enumerate(signal_group):
                signals = self.store.get_signal(signal_name)
                
                if not signals:
                    continue
                
                timestamps = [s.timestamp for s in signals]
                values = [s.physical_value for s in signals]
                unit = signals[0].unit
                color = colors[sig_idx % len(colors)]
                
                if sig_idx == 0:
                    current_ax = ax
                elif len(signal_group) > 1:
                    current_ax = ax.twinx()
                else:
                    current_ax = ax
                
                current_ax.plot(timestamps, values, color=color, 
                              linewidth=self.linewidth, label=signal_name,
                              marker='o', markersize=3,
                              markevery=max(1, len(timestamps)//50))
                
                ylabel = f'{signal_name} ({unit})' if unit else signal_name
                current_ax.set_ylabel(ylabel, fontsize=11, 
                                    fontweight='bold', color=color)
                current_ax.tick_params(axis='y', labelcolor=color)
                current_ax.grid(True, alpha=self.grid_alpha)
            
            if subplot_idx == len(overview_signals) - 1:
                ax.set_xlabel('Time (s)', fontsize=12, fontweight='bold')
            
            lines, labels = ax.get_legend_handles_labels()
            if len(signal_group) > 1 and hasattr(ax, 'get_legend_handles_labels'):
                try:
                    lines2, labels2 = ax.right_ax.get_legend_handles_labels()
                    lines += lines2
                    labels += labels2
                except:
                    pass
            ax.legend(lines, labels, loc='upper left', fontsize=9)
        
        fig.suptitle('Driving Overview - CAN Bus Signals', 
                    fontsize=16, fontweight='bold')
        plt.tight_layout()
        
        if save_path:
            self._save_figure(fig, save_path)
        
        if show:
            plt.show()
        else:
            plt.close(fig)
        
        return fig
    
    def _save_figure(self, fig: Figure, save_path: str) -> None:
        """
        Save figure to file.
        """
        output_file = Path(save_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        fig.savefig(output_file, dpi=self.dpi, bbox_inches='tight')
        
        logger.info(f"Saved plot to {output_file}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    from dbc_loader import load_dbc
    from can_log_reader import ASCReader
    from decoder import CANDecoder
    from signal_store import SignalStore
    
    try:
        print("Loading DBC database...")
        db = load_dbc("dbc/example_vehicle.dbc")
        
        print("Decoding CAN log...")
        decoder = CANDecoder(db)
        reader = ASCReader("logs/drive_log.asc")
        frames = list(reader.read_frames())
        decoded_messages = decoder.decode_frames(frames)
        
        print("Storing signals...")
        store = SignalStore()
        store.add_messages(decoded_messages)
        
        print("\nCreating plots...")
        plotter = SignalPlotter(store)
        
        print("  1. Single signal: RPM")
        plotter.plot_signal("RPM", save_path="output/plots/rpm.png")
        
        print("  2. Multiple signals: Speed and RPM")
        plotter.plot_signals(["Speed", "RPM"], 
                           save_path="output/plots/speed_rpm.png")
        
        print("  3. Subplots: RPM, Speed, EngineTemp")
        plotter.plot_signals_subplots(["RPM", "Speed", "EngineTemp"],
                                     save_path="output/plots/subplots.png")
        
        print("  4. Driving overview")
        plotter.plot_driving_overview(save_path="output/plots/overview.png")
        
        print("\nAll plots created successfully!")
        print("   Check the 'output/plots/' directory")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()