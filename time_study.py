import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import io

class SimpleWorkstationAnalyzer:
    def __init__(self, station_id=None):
        self.station_id = station_id
        self.reset_analysis()

    def reset_analysis(self):
        self.analysis_data = {
            'session_start': None,
            'cycles': [],
            'current_cycle': None,
            'is_timing': False,
            'is_waiting': False,
            'wait_start': None
        }

    def start_session(self):
        self.analysis_data['session_start'] = datetime.now()
        self.analysis_data['is_timing'] = True

    def start_timer(self, task_name):
        current_time = datetime.now()
        if not self.analysis_data['is_timing']:
            return False, "Session not started"

        if self.analysis_data['is_waiting'] and self.analysis_data['current_cycle']:
            wait_duration = (current_time - self.analysis_data['wait_start']).total_seconds()
            self.analysis_data['current_cycle']['wait_time'] += wait_duration
            self.analysis_data['is_waiting'] = False
            self.analysis_data['wait_start'] = None
            self.analysis_data['current_cycle']['work_resume_time'] = current_time
            return True, f"Resumed work on '{self.analysis_data['current_cycle']['task_name']}'"

        if self.analysis_data['current_cycle'] and not self.analysis_data['is_waiting']:
            self.complete_current_cycle()

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
        if not self.analysis_data['current_cycle'] or self.analysis_data['is_waiting']:
            return False, "No active cycle or already waiting"

        current_time = datetime.now()
        if self.analysis_data['current_cycle']['work_resume_time']:
            work_duration = (current_time - self.analysis_data['current_cycle']['work_resume_time']).total_seconds()
            self.analysis_data['current_cycle']['work_time'] += work_duration

        self.analysis_data['is_waiting'] = True
        self.analysis_data['wait_start'] = current_time
        return True, "Started waiting period"

    def complete_current_cycle(self):
        if not self.analysis_data['current_cycle']:
            return

        current_time = datetime.now()
        cycle = self.analysis_data['current_cycle']

        if self.analysis_data['is_waiting']:
            wait_duration = (current_time - self.analysis_data['wait_start']).total_seconds()
            cycle['wait_time'] += wait_duration
            self.analysis_data['is_waiting'] = False
            self.analysis_data['wait_start'] = None
        else:
            if cycle['work_resume_time']:
                work_duration = (current_time - cycle['work_resume_time']).total_seconds()
                cycle['work_time'] += work_duration

        cycle['end_time'] = current_time
        cycle['total_time'] = (current_time - cycle['start_time']).total_seconds()
        self.analysis_data['cycles'].append(cycle)
        self.analysis_data['current_cycle'] = None

    def get_cycles_dataframe(self):
        return pd.DataFrame(self.analysis_data['cycles'])

def create_pie_chart(work_time, wait_time):
    fig = go.Figure(data=[go.Pie(
        labels=['Work Time', 'Wait Time'],
        values=[work_time, wait_time],
        hole=0.4
    )])
    fig.update_layout(title="Time Distribution", height=350)
    return fig

def main():
    st.set_page_config("Workstation Timer", "⏱️", layout="wide")
    st.title("⏱️ Simple Workstation Timer")

    with st.sidebar:
        st.header("Setup")
        station_id = st.text_input("Station ID", "WS-001")
        operator_name = st.text_input("Operator Name", "")
        st.session_state['operator_name'] = operator_name

        if 'analyzer' not in st.session_state or st.session_state.get('current_station') != station_id:
            st.session_state.analyzer = SimpleWorkstationAnalyzer(station_id)
            st.session_state.current_station = station_id

        analyzer = st.session_state.analyzer
        analyzer.station_id = station_id

        st.header("Session")
        if not analyzer.analysis_data['is_timing']:
            if st.button("▶️ Start Session", use_container_width=True):
                analyzer.start_session()
                st.session_state.active_task_name = ""
                st.success("Session started!")
                st.rerun()
        else:
            if st.button("⏹️ End Session", use_container_width=True):
                if analyzer.analysis_data['current_cycle']:
                    analyzer.complete_current_cycle()
                analyzer.analysis_data['is_timing'] = False
                st.success("Session ended")
                st.session_state.active_task_name = ""
                st.rerun()

    if not analyzer.analysis_data['is_timing']:
        st.info("Start a session to begin timing")
        return

    st.subheader("Timer Controls")

    if "active_task_name" not in st.session_state:
        st.session_state.active_task_name = ""

    if st.session_state.active_task_name:
        st.success(f"Active Task: **{st.session_state.active_task_name}**")
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("▶️ Start Timer", use_container_width=True):
                success, message = analyzer.start_timer(st.session_state.active_task_name)
                st.toast(message)
                st.rerun()

        with col2:
            wait_disabled = not analyzer.analysis_data.get('current_cycle') or analyzer.analysis_data.get('is_waiting')
            if analyzer.analysis_data.get('is_waiting'):
                if st.button("▶️ Resume Work", use_container_width=True):
                    success, message = analyzer.start_timer(st.session_state.active_task_name)
                    st.toast(message)
                    st.rerun()
            else:
                if st.button("⏸️ Wait", disabled=wait_disabled, use_container_width=True):
                    success, message = analyzer.start_waiting()
                    st.toast(message)
                    st.rerun()

        with col3:
            if st.button("📝 Change Task", use_container_width=True):
                st.session_state.active_task_name = ""
                st.rerun()
    else:
        task_name = st.text_input("Enter Task Name")
        if st.button("✅ Confirm Task", use_container_width=True):
            if task_name.strip():
                st.session_state.active_task_name = task_name.strip()
                st.success(f"Task set to: {task_name.strip()}")
                st.rerun()
            else:
                st.warning("Please enter a valid task name")

    st.subheader("Cycle Data")
    df = analyzer.get_cycles_dataframe()
    if not df.empty:
        st.dataframe(df, use_container_width=True)

    st.subheader("Session Stats")
    total_work = sum(c['work_time'] for c in analyzer.analysis_data['cycles'])
    total_wait = sum(c['wait_time'] for c in analyzer.analysis_data['cycles'])

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Work Time (min)", f"{total_work/60:.2f}")
    with col2:
        st.metric("Total Wait Time (min)", f"{total_wait/60:.2f}")

    if total_work + total_wait > 0:
        fig = create_pie_chart(total_work, total_wait)
        st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
