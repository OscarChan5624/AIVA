import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for Kivy
import matplotlib.pyplot as plt
from datetime import datetime
from pathlib import Path


class FocusGraphGenerator:
    """Generate matplotlib graphs for focus statistics."""
    
    def __init__(self, output_dir: str = "."):
        """Initialize graph generator.
        
        Args:
            output_dir: Directory to save generated graph images
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Set style
        plt.style.use('dark_background')
    
    def generate_weekly_graph(self, history_data: dict, output_file: str = "weekly_graph.png") -> str:
        """Generate dual bar charts for current calendar week (Monday to Sunday).
        Shows both pomodoro count and focus time duration.
        
        Args:
            history_data: Dictionary with dates as keys and stats as values
            output_file: Output filename
            
        Returns:
            Path to generated image file
        """
        from datetime import timedelta, date
        
        # Get current week (Monday to Sunday)
        today = date.today()
        # Find the most recent Monday (or today if it's Monday)
        days_since_monday = today.weekday()  # Monday=0, Tuesday=1, ..., Sunday=6
        week_start = today - timedelta(days=days_since_monday)
        
        # Prepare data for 7 days (Monday to Sunday)
        dates = []
        pomodoros = []
        focus_minutes = []
        labels = []
        
        for i in range(7):
            date_obj = week_start + timedelta(days=i)
            date_str = str(date_obj)
            dates.append(date_str)
            
            # Get data (0 if no data)
            if date_str in history_data:
                pomodoros.append(history_data[date_str]["pomodoros"])
                focus_minutes.append(history_data[date_str]["focus_minutes"])
            else:
                pomodoros.append(0)
                focus_minutes.append(0)
            
            # Format label (Sun, Mon, Tue...)
            labels.append(date_obj.strftime("%a"))
        
        # Create figure with two subplots (tighter layout for mobile)
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(5.5, 5))
        fig.patch.set_facecolor('#101024')
        fig.subplots_adjust(hspace=0.3)  # Space between subplots
        
        # Highlight today's bars differently
        colors_pomo = []
        colors_time = []
        for i, date_str in enumerate(dates):
            if date_str == str(today):
                colors_pomo.append('#ffd166')  # Yellow/gold for today
                colors_time.append('#ffb84d')  # Darker yellow for time
            elif pomodoros[i] > 0:
                colors_pomo.append('#4cfa9a')  # Green for completed days
                colors_time.append('#a78bfa')  # Purple for time
            else:
                colors_pomo.append('#2a2a4a')  # Gray for zero/future days
                colors_time.append('#2a2a4a')
        
        # Top chart: Pomodoros
        bars1 = ax1.bar(labels, pomodoros, color=colors_pomo, alpha=0.9, edgecolor='white', linewidth=1)
        ax1.set_ylabel('Pomodoros', color='white', fontsize=12, fontweight='bold')
        ax1.set_title('This Week', color='white', fontsize=15, fontweight='bold', pad=15)
        ax1.tick_params(colors='white', labelsize=11)
        ax1.set_facecolor('#1a1a3e')
        ax1.grid(axis='y', alpha=0.3, color='white', linestyle='--')
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)
        ax1.spines['left'].set_color('white')
        ax1.spines['bottom'].set_color('white')
        
        # Add value labels on bars
        for bar in bars1:
            height = bar.get_height()
            if height > 0:
                ax1.text(bar.get_x() + bar.get_width()/2., height,
                        f'{int(height)}',
                        ha='center', va='bottom', color='white', fontsize=11, fontweight='bold')
        
        # Bottom chart: Focus Time (minutes) - LINE GRAPH
        # Plot line with area fill
        ax2.plot(range(len(focus_minutes)), focus_minutes, 
                color='#ff6b9d', linewidth=3, marker='o', 
                markersize=7, markerfacecolor='#ff6b9d', 
                markeredgecolor='white', markeredgewidth=1.5, zorder=3)
        ax2.fill_between(range(len(focus_minutes)), focus_minutes, 
                         alpha=0.3, color='#ff6b9d', zorder=2)
        
        ax2.set_ylabel('Minutes', color='white', fontsize=12, fontweight='bold')
        ax2.set_xlabel('Day', color='white', fontsize=11)
        ax2.tick_params(colors='white', labelsize=11)
        ax2.set_facecolor('#1a1a3e')
        ax2.grid(alpha=0.3, color='white', linestyle='--', zorder=1)
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_visible(False)
        ax2.spines['left'].set_color('white')
        ax2.spines['bottom'].set_color('white')
        ax2.set_xticks(range(len(labels)))
        ax2.set_xticklabels(labels)
        
        # Add value labels on data points
        for i, value in enumerate(focus_minutes):
            if value > 0:
                ax2.text(i, value, f'{int(value)}m',
                        ha='center', va='bottom', color='white', 
                        fontsize=10, fontweight='bold',
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='#1a1a3e', 
                                 edgecolor='none', alpha=0.7))
        
        # Calculate and show weekly totals
        total_pomodoros = sum(pomodoros)
        total_minutes = sum(focus_minutes)
        week_end = week_start + timedelta(days=6)
        week_label = f"{week_start.strftime('%m/%d')} - {week_end.strftime('%m/%d')}"
        stats_text = f'{week_label} | {total_pomodoros} sessions | {total_minutes}m'
        ax1.text(0.5, 0.95, stats_text, 
                transform=ax1.transAxes, ha='center', va='top',
                color='#4cfa9a', fontsize=10, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.4', facecolor='#1a1a3e', edgecolor='#4cfa9a', linewidth=1.5))
        
        plt.tight_layout()
        
        # Save
        output_path = self.output_dir / output_file
        plt.savefig(output_path, dpi=120, facecolor='#101024', edgecolor='none')
        plt.close()
        
        return str(output_path)
    
    def generate_monthly_graph(self, history_data: dict, output_file: str = "monthly_graph.png") -> str:
        """Generate a line chart showing total pomodoros per month.
        
        Args:
            history_data: Dictionary with dates as keys and stats as values
            output_file: Output filename
            
        Returns:
            Path to generated image file
        """
        from collections import defaultdict
        
        # Group data by month
        monthly_totals = defaultdict(int)
        for date_str, stats in history_data.items():
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            month_key = dt.strftime("%Y-%m")  # e.g., "2025-11"
            monthly_totals[month_key] += stats["pomodoros"]
        
        # Sort by date and prepare data
        sorted_months = sorted(monthly_totals.keys())
        # Get last 6 months for mobile display
        recent_months = sorted_months[-6:] if len(sorted_months) > 6 else sorted_months
        pomodoros = [monthly_totals[m] for m in recent_months]
        
        # Format month labels (e.g., "Nov", "Dec")
        labels = []
        for month_key in recent_months:
            dt = datetime.strptime(month_key + "-01", "%Y-%m-%d")
            labels.append(dt.strftime("%b\n%Y"))
        
        # Create line chart
        fig, ax = plt.subplots(1, 1, figsize=(6, 4))
        fig.patch.set_facecolor('#101024')
        
        # Monthly pomodoros line chart with markers
        ax.plot(range(len(pomodoros)), pomodoros, color='#4cfa9a', linewidth=3, 
                marker='o', markersize=8, markerfacecolor='#4cfa9a', 
                markeredgecolor='white', markeredgewidth=2)
        ax.fill_between(range(len(pomodoros)), pomodoros, alpha=0.3, color='#4cfa9a')
        
        ax.set_ylabel('Pomodoros', color='white', fontsize=13, fontweight='bold')
        ax.set_title('Monthly Trend', color='white', fontsize=16, fontweight='bold', pad=20)
        ax.tick_params(colors='white', labelsize=11)
        ax.set_facecolor('#1a1a3e')
        ax.grid(alpha=0.3, color='white', linestyle='--')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('white')
        ax.spines['bottom'].set_color('white')
        
        # Set x-axis labels
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels)
        
        # Add value labels on data points
        for i, value in enumerate(pomodoros):
            if value > 0:
                ax.text(i, value, f'{int(value)}',
                        ha='center', va='bottom', color='white', fontsize=11, fontweight='bold',
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='#1a1a3e', edgecolor='none', alpha=0.7))
        
        # Calculate and show stats
        total = sum(pomodoros)
        avg = total / len(pomodoros) if len(pomodoros) > 0 else 0
        stats_text = f'Total: {total} | Avg: {avg:.1f}/month'
        ax.text(0.5, 0.95, stats_text, 
                transform=ax.transAxes, ha='center', va='top',
                color='#4cfa9a', fontsize=12, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='#1a1a3e', edgecolor='#4cfa9a', linewidth=1.5))
        
        plt.tight_layout()
        
        # Save
        output_path = self.output_dir / output_file
        plt.savefig(output_path, dpi=120, facecolor='#101024', edgecolor='none')
        plt.close()
        
        return str(output_path)
    
    def generate_hourly_graph(self, hourly_data: dict, output_file: str = "hourly_graph.png") -> str:
        """Generate bar chart for hourly productivity (0-23 hours).
        
        Args:
            hourly_data: Dictionary with hour (0-23) as key and total minutes as value
            output_file: Output filename
            
        Returns:
            Path to generated image file
        """
        hours = list(range(24))
        minutes = [hourly_data.get(h, 0) for h in hours]
        labels = [f"{h:02d}" for h in hours]
        
        fig, ax = plt.subplots(1, 1, figsize=(6, 3))
        fig.patch.set_facecolor('#101024')
        
        # Color bars: green for productive hours, gray for zero
        colors = ['#4cfa9a' if m > 0 else '#2a2a4a' for m in minutes]
        bars = ax.bar(labels, minutes, color=colors, alpha=0.9, edgecolor='white', linewidth=1)
        
        ax.set_ylabel('Minutes', color='white', fontsize=11, fontweight='bold')
        ax.set_xlabel('Hour', color='white', fontsize=11)
        ax.tick_params(colors='white', labelsize=9)
        ax.set_facecolor('#1a1a3e')
        ax.grid(axis='y', alpha=0.3, color='white', linestyle='--')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('white')
        ax.spines['bottom'].set_color('white')
        
        # Only show every 3rd hour label to avoid crowding
        ax.set_xticks(range(0, 24, 3))
        ax.set_xticklabels([labels[i] for i in range(0, 24, 3)])
        
        # Add value labels on bars (only for non-zero values)
        for i, (bar, val) in enumerate(zip(bars, minutes)):
            if val > 0:
                ax.text(i, val, f'{int(val)}m', ha='center', va='bottom', 
                       color='white', fontsize=8, fontweight='bold')
        
        plt.tight_layout()
        
        # Save
        output_path = self.output_dir / output_file
        plt.savefig(output_path, dpi=120, facecolor='#101024', edgecolor='none')
        plt.close()
        
        return str(output_path)
    
    def generate_day_pattern_graph(self, day_data: dict, output_file: str = "day_pattern_graph.png") -> str:
        """Generate bar chart for day of week patterns.
        
        Args:
            day_data: Dictionary with day (0=Mon, 6=Sun) as key and total minutes as value
            output_file: Output filename
            
        Returns:
            Path to generated image file
        """
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        minutes = [day_data.get(i, 0) for i in range(7)]
        
        fig, ax = plt.subplots(1, 1, figsize=(6, 3))
        fig.patch.set_facecolor('#101024')
        
        # Color bars: purple for productive days, gray for zero
        colors = ['#a78bfa' if m > 0 else '#2a2a4a' for m in minutes]
        bars = ax.bar(days, minutes, color=colors, alpha=0.9, edgecolor='white', linewidth=1)
        
        ax.set_ylabel('Minutes', color='white', fontsize=11, fontweight='bold')
        ax.tick_params(colors='white', labelsize=10)
        ax.set_facecolor('#1a1a3e')
        ax.grid(axis='y', alpha=0.3, color='white', linestyle='--')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('white')
        ax.spines['bottom'].set_color('white')
        
        # Add value labels on bars (only for non-zero values)
        for i, (day, val) in enumerate(zip(days, minutes)):
            if val > 0:
                ax.text(i, val, f'{int(val)}m', ha='center', va='bottom', 
                       color='white', fontsize=9, fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.2', facecolor='#1a1a3e', 
                                edgecolor='none', alpha=0.7))
        
        plt.tight_layout()
        
        # Save
        output_path = self.output_dir / output_file
        plt.savefig(output_path, dpi=120, facecolor='#101024', edgecolor='none')
        plt.close()
        
        return str(output_path)

