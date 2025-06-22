import streamlit as st
import numpy as np
import time
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import io

class SimpleWorkstationAnalyzer:
    """Simplified workstation analyzer with continuous timing"""
    
    def __init__(self, station_id=None):
        self.station_id = station_id
        self.reset_analysis()
        
    def reset_analysis(self):
        """Reset all analysis data"""
        self.analysis_data = {
            'session_start': None,
            'cycles': [],
            'current_cycle': None,
            'is_timing': False,
            'is_waiting': False,
            'wait_start': None
        }
        
    def start_session(self):
        """Start the timing session"""
        current_time = datetime.now()
        self.analysis_data['session_start'] = current_time
        self.analysis_data['is_timing'] = True
        return current_time
    
    def start_timer(self, task_name):
        """Start a new cycle or resume from waiting"""
        current_time = datetime.now()
        
        if not self.analysis_data['is_timing']:
            return False, "Session not started"
        
        # If we were waiting, calculate wait time and end the wait
        if self.analysis_data['is_waiting'] and self.analysis_data['current_cycle']:
            wait_duration = (current_time - self.analysis_data['wait_start']).total_seconds()
            self.analysis_data['current_cycle']['wait_time'] += wait_duration
            self.analysis_data['is_waiting'] = False
            self.analysis_data['wait_start'] = None
            
            # Resume the cycle
            self.analysis_data['current_cycle']['work_resume_time'] = current_time
            return True, f"Resumed work on '{self.analysis_data['current_cycle']['task_name']}' after {wait_duration:.1f}s wait"
        
        # If there's an active cycle, complete it first
        if self.analysis_data['current_cycle'] and not self.analysis_data['is_waiting']:
            self.complete_current_cycle()
        
        # Start new cycle
        cycle = {
            'task_name': task_name,
            'start_time': current_time,
            'end_time': None,
            'work_time': 0,
            'wait_time': 0,
            'total_time': 0,
            'operator': st.session_state.get('operator_name', 'Unknown'),
            'work_resume_time': current_time
        }
        
        self.analysis_data['current_cycle'] = cycle
        return True, f"Started timer for '{task_name}'"
    
    def start_waiting(self):
        """Start waiting period within current cycle"""
        if not self.analysis_data['current_cycle'] or self.analysis_data['is_waiting']:
            return False, "No active cycle or already waiting"
        
        current_time = datetime.now()
        
        # Add work time from last resume to now
        if self.analysis_data['current_cycle']['work_resume_time']:
            work_duration = (current_time - self.analysis_data['current_cycle']['work_resume_time']).total_seconds()
            self.analysis_data['current_cycle']['work_time'] += work_duration
        
        # Start waiting
        self.analysis_data['is_waiting'] = True
        self.analysis_data['wait_start'] = current_time
        
        return True, "Started waiting period"
    
    def complete_current_cycle(self):
        """Complete the current cycle"""
        if not self.analysis_data['current_cycle']:
            return False, "No active cycle"
        
        current_time = datetime.now()
        cycle = self.analysis_data['current_cycle']
        
        # If we're waiting, add the wait time
        if self.analysis_data['is_waiting']:
            wait_duration = (current_time - self.analysis_data['wait_start']).total_seconds()
            cycle['wait_time'] += wait_duration
            self.analysis_data['is_waiting'] = False
            self.analysis_data['wait_start'] = None
        else:
            # Add final work time
            if cycle['work_resume_time']:
                work_duration = (current_time - cycle['work_resume_time']).total_seconds()
                cycle['work_time'] += work_duration
        
        # Complete the cycle
        cycle['end_time'] = current_time
        cycle['total_time'] = (current_time - cycle['start_time']).total_seconds()
        
        # Add to completed cycles
        self.analysis_data['cycles'].append(cycle)
        self.analysis_data['current_cycle'] = None
        
        return True, f"Completed cycle for '{cycle['task_name']}'"
    
    def get_current_stats(self):
        """Get current analysis statistics"""
        completed_cycles = self.analysis_data['cycles']
        current_cycle = self.analysis_data['current_cycle']
        
        # Calculate stats from completed cycles
        total_work_time = sum(c['work_time'] for c in completed_cycles)
        total_wait_time = sum(c['wait_time'] for c in completed_cycles)
        
        # Add current cycle time if active
        current_work_time = 0
        current_wait_time = 0
        current_task = "No active task"
        
        if current_cycle:
            current_task = current_cycle['task_name']
            current_time = datetime.now()
            
            # Calculate current cycle work time
            current_work_time = current_cycle['work_time']
            if not self.analysis_data['is_waiting'] and current_cycle['work_resume_time']:
                current_work_time += (current_time - current_cycle['work_resume_time']).total_seconds()
            
            # Calculate current cycle wait time
            current_wait_time = current_cycle['wait_time']
            if self.analysis_data['is_waiting'] and self.analysis_data['wait_start']:
                current_wait_time += (current_time - self.analysis_data['wait_start']).total_seconds()
        
        total_work = total_work_time + current_work_time
        total_wait = total_wait_time + current_wait_time
        total_time = total_work + total_wait
        
        work_percentage = (total_work / total_time * 100) if total_time > 0 else 0
        wait_percentage = (total_wait / total_time * 100) if total_time > 0 else 0
        
        session_duration = 0
        if self.analysis_data['session_start']:
            session_duration = (datetime.now() - self.analysis_data['session_start']).total_seconds()
        
        avg_cycle_time = 0
        if completed_cycles:
            avg_cycle_time = sum(c['total_time'] for c in completed_cycles) / len(completed_cycles)
        
        return {
            'total_time': total_time,
            'work_time': total_work,
            'wait_time': total_wait,
            'work_percentage': work_percentage,
            'wait_percentage': wait_percentage,
            'current_task': current_task,
            'session_duration': session_duration,
            'cycle_count': len(completed_cycles),
            'avg_cycle_time': avg_cycle_time,
            'is_waiting': self.analysis_data['is_waiting'],
            'current_cycle_active': current_cycle is not None
        }
    
    def get_cycles_dataframe(self):
        """Get cycles as a pandas DataFrame for export"""
        all_cycles = self.analysis_data['cycles'].copy()
        
        # Add current cycle if active
        if self.analysis_data['current_cycle']:
            current = self.analysis_data['current_cycle'].copy()
            current_time = datetime.now()
            
            # Calculate current times
            if not current['end_time']:
                current['total_time'] = (current_time - current['start_time']).total_seconds()
                
                # Add current work time
                if not self.analysis_data['is_waiting'] and current['work_resume_time']:
                    current['work_time'] += (current_time - current['work_resume_time']).total_seconds()
                
                # Add current wait time
                if self.analysis_data['is_waiting'] and self.analysis_data['wait_start']:
                    current['wait_time'] += (current_time - self.analysis_data['wait_start']).total_seconds()
                
                current['end_time'] = current_time
                current['status'] = 'In Progress'
            
            all_cycles.append(current)
        
        if not all_cycles:
            return pd.DataFrame()
        
        df_data = []
        for cycle in all_cycles:
            df_data.append({
                'Station ID': self.station_id,
                'Task Name': cycle['task_name'],
                'Start Time': cycle['start_time'].strftime('%Y-%m-%d %H:%M:%S'),
                'End Time': cycle['end_time'].strftime('%Y-%m-%d %H:%M:%S') if cycle['end_time'] else 'In Progress',
                'Work Time (seconds)': round(cycle['work_time'], 2),
                'Wait Time (seconds)': round(cycle['wait_time'], 2),
                'Total Time (seconds)': round(cycle['total_time'], 2),
                'Work Time (minutes)': round(cycle['work_time'] / 60, 2),
                'Wait Time (minutes)': round(cycle['wait_time'] / 60, 2),
                'Total Time (minutes)': round(cycle['total_time'] / 60, 2),
                'Work %': round((cycle['work_time'] / cycle['total_time'] * 100), 1) if cycle['total_time'] > 0 else 0,
                'Wait %': round((cycle['wait_time'] / cycle['total_time'] * 100), 1) if cycle['total_time'] > 0 else 0,
                'Operator': cycle['operator'],
                'Status': cycle.get('status', 'Completed')
            })
        
        return pd.DataFrame(df_data)

def create_pie_chart(work_time, wait_time):
    """Create time distribution pie chart"""
    if work_time == 0 and wait_time == 0:
        return None
    
    fig = go.Figure(data=[go.Pie(
        labels=['Work Time', 'Wait Time'],
        values=[work_time, wait_time],
        marker=dict(colors=['#2E8B57', '#FFA500']),
        hole=0.4,
        textinfo='label+percent+value',
        texttemplate='%{label}<br>%{percent}<br>%{value:.1f}s'
    )])
    
    fig.update_layout(
        title="Time Distribution",
        height=350
    )
    
    return fig

def create_cycle_chart(cycles_df):
    """Create cycle analysis chart"""
    if cycles_df.empty:
        return None
    
    fig = go.Figure()
    
    # Work time bars
    fig.add_trace(go.Bar(
        name='Work Time',
        x=cycles_df['Task Name'],
        y=cycles_df['Work Time (minutes)'],
        marker_color='#2E8B57'
    ))
    
    # Wait time bars
    fig.add_trace(go.Bar(
        name='Wait Time',
        x=cycles_df['Task Name'],
        y=cycles_df['Wait Time (minutes)'],
        marker_color='#FFA500'
    ))
    
    fig.update_layout(
        title="Work vs Wait Time by Cycle",
        xaxis_title="Task/Cycle",
        yaxis_title="Time (minutes)",
        barmode='stack',
        height=400
    )
    
    return fig

def main():
    st.set_page_config(
        page_title="Simple Workstation Timer",
        page_icon="⏱️",
        layout="wide"
    )
    
    st.title("⏱️ Simple Workstation Timer")
    st.markdown("*Continuous timing with work/wait tracking*")
    
    # Sidebar for session setup
    with st.sidebar:
        st.header("📋 Setup")
        
        # Station ID input
        station_id = st.text_input("Station ID", value="WS-001")
        
        # Operator name
        operator_name = st.text_input("Operator Name", value="")
        st.session_state['operator_name'] = operator_name
        
        # Initialize analyzer
        if 'analyzer' not in st.session_state or st.session_state.get('current_station') != station_id:
            st.session_state.analyzer = SimpleWorkstationAnalyzer(station_id)
            st.session_state.current_station = station_id
        
        analyzer = st.session_state.analyzer
        analyzer.station_id = station_id
        
        st.divider()
        
        # Session controls
        st.header("🎛️ Session")
        
        if not analyzer.analysis_data['is_timing']:
            if st.button("▶️ Start Session", type="primary", use_container_width=True):
                start_time = analyzer.start_session()
                st.success(f"Session started!")
                st.rerun()
        else:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("⏹️ End Session", type="secondary", use_container_width=True):
                    if analyzer.analysis_data['current_cycle']:
                        analyzer.complete_current_cycle()
                    analyzer.analysis_data['is_timing'] = False
                    st.success("Session ended")
                    st.rerun()
            
            with col2:
                if st.button("🔄 Reset", use_container_width=True):
                    st.session_state.analyzer = SimpleWorkstationAnalyzer(station_id)
                    st.success("Reset complete")
                    st.rerun()
        
        # Session status
        if analyzer.analysis_data['is_timing']:
            st.success("🔴 **Session Active**")
            if analyzer.analysis_data['session_start']:
                elapsed = (datetime.now() - analyzer.analysis_data['session_start']).total_seconds()
                st.metric("Session Time", f"{elapsed/60:.1f} min")
        else:
            st.info("⚪ Session Inactive")
    
    # Main content
    if not analyzer.analysis_data['is_timing']:
        st.info("👈 Start a session from the sidebar to begin timing")
        return
    
    # Task controls
    st.subheader("⏱️ Timer Controls")
    
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        # Use a counter to reset the input field after successful submission
        if 'input_counter' not in st.session_state:
            st.session_state.input_counter = 0
        
        task_name = st.text_input("Task Name", placeholder="e.g., Assemble motor housing", key=f"task_input_{st.session_state.input_counter}")
    
    with col2:
        st.write("") # Spacing
        if st.button("▶️ Start Timer", type="primary", use_container_width=True):
            if task_name.strip():
                success, message = analyzer.start_timer(task_name.strip())
                if success:
                    st.success(message)
                    # Reset the input field by incrementing the counter
                    st.session_state.input_counter += 1
                else:
                    st.error(message)
                st.rerun()
            else:
                st.warning("Enter a task name")
    
    with col3:
        st.write("") # Spacing
        wait_disabled = not analyzer.analysis_data.get('current_cycle') or analyzer.analysis_data.get('is_waiting')
        
        if analyzer.analysis_data.get('is_waiting'):
            if st.button("▶️ Resume Work", type="secondary", use_container_width=True):
                success, message = analyzer.start_timer(analyzer.analysis_data['current_cycle']['task_name'])
                if success:
                    st.success(message)
                st.rerun()
        else:
            if st.button("⏸️ Wait", disabled=wait_disabled, use_container_width=True):
                success, message = analyzer.start_waiting()
                if success:
                    st.warning(message)
                else:
                    st.error(message)
                st.rerun()
    
    # Current status
    stats = analyzer.get_current_stats()
    
    if stats['current_cycle_active']:
        status_color = "orange" if stats['is_waiting'] else "green"
        status_text = "⏸️ WAITING" if stats['is_waiting'] else "▶️ WORKING"
        st.markdown(f":{status_color}[**{status_text}:** {stats['current_task']}]")
    
    # Metrics
    st.subheader("📊 Session Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        efficiency = stats['work_percentage'] if stats['total_time'] > 0 else 0
        st.metric("Work Efficiency", f"{efficiency:.1f}%", help="Percentage of time spent working")
    
    with col2:
        st.metric("Total Cycles", stats['cycle_count'], help="Number of completed cycles")
    
    with col3:
        st.metric("Total Time", f"{stats['total_time']/60:.1f} min", help="Total tracked time")
    
    with col4:
        st.metric("Avg Cycle", f"{stats['avg_cycle_time']/60:.1f} min", help="Average time per cycle")
    
    # Real-time work/wait breakdown
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Work Time", f"{stats['work_time']/60:.1f} min", f"{stats['work_percentage']:.1f}%")
    with col2:
        st.metric("Wait Time", f"{stats['wait_time']/60:.1f} min", f"{stats['wait_percentage']:.1f}%")
    
    # Charts
    if stats['total_time'] > 0:
        st.subheader("📈 Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            pie_chart = create_pie_chart(stats['work_time'], stats['wait_time'])
            if pie_chart:
                st.plotly_chart(pie_chart, use_container_width=True)
        
        with col2:
            df = analyzer.get_cycles_dataframe()
            if not df.empty:
                cycle_chart = create_cycle_chart(df)
                if cycle_chart:
                    st.plotly_chart(cycle_chart, use_container_width=True)
    
    # Data table
    st.subheader("📋 Cycle Data")
    
    df = analyzer.get_cycles_dataframe()
    
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        
        # Export
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            csv = df.to_csv(index=False)
            st.download_button(
                "📥 Download CSV",
                data=csv,
                file_name=f"workstation_{station_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        with col2:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Cycle Data', index=False)
                
                summary_df = pd.DataFrame([
                    ['Station ID', station_id],
                    ['Operator', operator_name or 'Not specified'],
                    ['Session Start', analyzer.analysis_data['session_start'].strftime('%Y-%m-%d %H:%M:%S') if analyzer.analysis_data['session_start'] else ''],
                    ['Total Cycles', stats['cycle_count']],
                    ['Total Time (min)', f"{stats['total_time']/60:.2f}"],
                    ['Work Time (min)', f"{stats['work_time']/60:.2f}"],
                    ['Wait Time (min)', f"{stats['wait_time']/60:.2f}"],
                    ['Work Efficiency %', f"{stats['work_percentage']:.1f}%"],
                ], columns=['Metric', 'Value'])
                
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            st.download_button(
                "📊 Download Excel",
                data=buffer.getvalue(),
                file_name=f"workstation_{station_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.info("No cycle data yet. Start your first timer to begin tracking.")
    
    # Instructions
    with st.expander("💡 How to Use"):
        st.markdown("""
        **Simple 2-Button Operation:**
        
        1. **Start Session** - Begin timing (sidebar)
        2. **Start Timer** - Enter task name and start working
        3. **Wait Button** - Press when waiting (materials, approval, etc.)
        4. **Resume Work** - Press to continue working (appears when waiting)
        5. **Start Timer** (again) - Completes current cycle and starts new one
        
        **Key Features:**
        - ⏱️ **Continuous timing** - Clock never stops during session
        - 🔄 **Automatic cycles** - Starting new timer completes previous cycle
        - ⏸️ **Wait tracking** - Track non-productive waiting time
        - 📊 **Live stats** - Real-time efficiency and timing data
        - 📥 **Export data** - Download CSV/Excel reports
        
        **One Complete Cycle = Work Time + Wait Time**
        """)

if __name__ == "__main__":
    main()
