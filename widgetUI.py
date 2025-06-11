from Widget import *
import ui_widgetUI
from importlib import reload
reload(ui_widgetUI)
from ui_widgetUI import Ui_widgetUI

import sys
import os
import re
import psutil
import time
import subprocess
import platform
import shutil
import string
from datetime import datetime
from PyQt5.QtCore import QTimer

class widgetUI(Widget):
    def __init__(self, parent=None):
        # Initialize the main widget and UI
        super(widgetUI, self).__init__(parent)
        self.ui = Ui_widgetUI()
        self.ui.setupUi(self)
        # Directory for LTStartLiveCount logs
        self.log_directory = r"C:\SmartComm\iVisionmax\logs\LTStartLiveCount"
        # Timer for updating LTStartLiveCount logs every minute
        self.lt_log_timer = QTimer(self)
        self.lt_log_timer.timeout.connect(self.updateLTStartLiveCount)
        self.lt_log_timer.start(60000)
        # Initialize network and system stats
        self.initial_net_stats = psutil.net_io_counters()
        self.system_boot_time = psutil.boot_time()
        self.last_net_stats = self.initial_net_stats
        self.last_update_time = time.time()
        # Lists for process and drive info
        self.proc_names = []
        self.proc_pids = []
        self.proc_cpu_percents = []
        self.proc_mem_usages = []
        self.drive_names = []
        self.drive_free_spaces_gb = []
        self.drive_total_spaces_gb = []
        self.drive_used_spaces_gb = []
        self.drive_usage_percentages = []
        # Timer for updating server/app metrics every 2 seconds
        self.server_app_timer = QTimer(self)
        self.server_app_timer.timeout.connect(self.updateServerAndAppMetrics)
        self.server_app_timer.start(2000)
        # Timer for updating network metrics every minute
        self.network_timer = QTimer(self)
        self.network_timer.timeout.connect(self.updateNetworkMetrics)
        self.network_timer.start(60000)

    def get_current_log_file(self):
        # Returns the path to today's LTStartLiveCount log file
        today = datetime.now().strftime("%d%m%Y")
        return os.path.join(self.log_directory, f"LTStartLiveCount{today}.log")

    def get_last_log_entry(self, file_path):
        # Reads the last valid entry from the given log file
        if not os.path.exists(file_path):
            return None
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                lines = file.readlines()
                for line in reversed(lines):
                    line = line.strip()
                    if line:
                        entry = self.parse_log_line(line)
                        if entry:
                            return entry
            return None
        except Exception as e:
            return None

    def parse_log_line(self, line):
        # Parses a log line and extracts timestamp, level, component_id, and value
        pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\s+(INFO)\s+(\d+)\s+(\d+)'
        match = re.match(pattern, line.strip())
        if match:
            timestamp_str, level, component_id, value = match.groups()
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S.%f")
            return {
                'timestamp': timestamp,
                'level': level,
                'component_id': component_id,
                'value': value
            }
        return None

    def updateLTStartLiveCount(self):
        # Updates tags with the latest LTStartLiveCount log entry or error status
        try:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_file = self.get_current_log_file()
            last_entry = self.get_last_log_entry(log_file)
            if last_entry:
                setTagData("Obj1.Additional_Module_Information.ltstart_latest_component_id", last_entry['component_id'])
                setTagData("Obj1.Additional_Module_Information.ltstart_latest_value", last_entry['value'])
                setTagData("Obj1.Additional_Module_Information.ltstart_latest_timestamp", last_entry['timestamp'].strftime('%Y-%m-%d %H:%M:%S.%f'))
                setTagData("Obj1.Additional_Module_Information.ltstart_status", "SUCCESS")
            else:
                setTagData("Obj1.Additional_Module_Information.ltstart_latest_component_id", "")
                setTagData("Obj1.Additional_Module_Information.ltstart_latest_value", "")
                setTagData("Obj1.Additional_Module_Information.ltstart_latest_timestamp", "")
                setTagData("Obj1.Additional_Module_Information.ltstart_status", "NO_DATA")
        except Exception as e:
            error_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            setTagData("Obj1.Additional_Module_Information.ltstart_status", "ERROR")
            setTagData("Obj1.Additional_Module_Information.ltstart_error_message", str(e))
            setTagData("Obj1.Additional_Module_Information.ltstart_error_time", error_time)

    def get_drive_information(self):
        # Collects information about all available drives
        try:
            self.drive_names = []
            self.drive_free_spaces_gb = []
            self.drive_total_spaces_gb = []
            self.drive_used_spaces_gb = []
            self.drive_usage_percentages = []
            for drive_letter in string.ascii_uppercase:
                drive = f"{drive_letter}:\\"
                if os.path.exists(drive):
                    try:
                        total, used, free = shutil.disk_usage(drive)
                        total_gb = round(total / (1024 ** 3), 2)
                        used_gb = round(used / (1024 ** 3), 2)
                        free_gb = round(free / (1024 ** 3), 2)
                        usage_percent = round((used / total) * 100, 2) if total > 0 else 0
                        self.drive_names.append(drive)
                        self.drive_total_spaces_gb.append(total_gb)
                        self.drive_used_spaces_gb.append(used_gb)
                        self.drive_free_spaces_gb.append(free_gb)
                        self.drive_usage_percentages.append(usage_percent)
                    except (PermissionError, FileNotFoundError, OSError) as e:
                        continue
            return True
        except Exception as e:
            return False

    def get_network_ping(self, host="8.8.8.8", timeout=3):
        # Pings a host and returns the response time in ms, or None on failure
        try:
            if platform.system().lower() == "windows":
                cmd = ["ping", "-n", "1", "-w", str(timeout * 1000), host]
            else:
                cmd = ["ping", "-c", "1", "-W", str(timeout), host]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 1)
            if result.returncode == 0:
                output = result.stdout
                if platform.system().lower() == "windows":
                    for line in output.split('\n'):
                        if 'time=' in line.lower() or 'time<' in line.lower():
                            if 'time=' in line.lower():
                                ping_time = line.split('time=')[1].split('ms')[0].strip()
                            else:
                                ping_time = line.split('time<')[1].split('ms')[0].strip()
                            return float(ping_time)
                else:
                    for line in output.split('\n'):
                        if 'time=' in line:
                            ping_time = line.split('time=')[1].split(' ')[0]
                            return float(ping_time)
            return None
        except Exception as e:
            return None

    def calculate_network_speeds(self, current_stats, time_elapsed):
        # Calculates upload and download speeds in Mbps
        try:
            bytes_sent_diff = current_stats.bytes_sent - self.last_net_stats.bytes_sent
            bytes_recv_diff = current_stats.bytes_recv - self.last_net_stats.bytes_recv
            upload_speed_mbps = (bytes_sent_diff * 8) / (1024 * 1024 * time_elapsed) if time_elapsed > 0 else 0
            download_speed_mbps = (bytes_recv_diff * 8) / (1024 * 1024 * time_elapsed) if time_elapsed > 0 else 0
            return round(upload_speed_mbps, 3), round(download_speed_mbps, 3)
        except Exception as e:
            return 0.0, 0.0

    def updateServerAndAppMetrics(self):
        # Collects and updates server and application metrics
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ram = psutil.virtual_memory().percent
        cpu = psutil.cpu_percent(interval=1)
        try:
            disk_usages = []
            for part in psutil.disk_partitions():
                if part.fstype != '' and part.mountpoint:
                    try:
                        usage = psutil.disk_usage(part.mountpoint).percent
                        disk_usages.append(usage)
                    except (PermissionError, FileNotFoundError):
                        continue
            disk = max(disk_usages) if disk_usages else 0
        except Exception:
            disk = 0
        cpu_per_core = psutil.cpu_percent(percpu=True)
        cpu_count_logical = psutil.cpu_count(logical=True)
        cpu_count_physical = psutil.cpu_count(logical=False)
        cores_being_used = sum(1 for usage in cpu_per_core if usage > 0)
        drive_info_success = self.get_drive_information()
        setTagData("Obj1.Server_Infra.ram", ram)
        setTagData("Obj1.Server_Infra.cpu", cpu)
        setTagData("Obj1.Server_Infra.storage", disk)
        setTagData("Obj1.Server_Infra.date_time", timestamp)
        setTagData("Obj1.Server_Infra.cpu_per_core", ','.join(map(str, cpu_per_core)))
        setTagData("Obj1.Server_Infra.cpu_logical_cores", cpu_count_logical)
        setTagData("Obj1.Server_Infra.cpu_physical_cores", cpu_count_physical)
        setTagData("Obj1.Server_Infra.cpu_cores_being_used", cores_being_used)
        if drive_info_success:
            setTagData("Obj1.Server_Infra.total_drives_count", len(self.drive_names))
            SetTagArrayData("Obj1.Server_Infra.drive_names", self.drive_names)
            SetTagArrayData("Obj1.Server_Infra.drive_total_space_gb", self.drive_total_spaces_gb)
            SetTagArrayData("Obj1.Server_Infra.drive_used_space_gb", self.drive_used_spaces_gb)
            SetTagArrayData("Obj1.Server_Infra.drive_free_space_gb", self.drive_free_spaces_gb)
            SetTagArrayData("Obj1.Server_Infra.drive_usage_percent", self.drive_usage_percentages)
            total_storage_gb = sum(self.drive_total_spaces_gb)
            total_free_gb = sum(self.drive_free_spaces_gb)
            total_used_gb = sum(self.drive_used_spaces_gb)
            setTagData("Obj1.Server_Infra.total_storage_gb", round(total_storage_gb, 2))
            setTagData("Obj1.Server_Infra.total_free_storage_gb", round(total_free_gb, 2))
            setTagData("Obj1.Server_Infra.total_used_storage_gb", round(total_used_gb, 2))
            setTagData("Obj1.Server_Infra.overall_storage_usage_percent", round((total_used_gb / total_storage_gb) * 100, 2) if total_storage_gb > 0 else 0)
        # List of monitored application executables
        lt_applications = {
            "LTmessagebroker.exe", "LTtagdb.exe", "LTalarmevents.exe", "LThistdb.exe",
            "LTHAappl.exe", "LTide.exe", "Viewer.exe", "LTviewer.exe", "LTModbusclient.exe",
            "LTIEC61850client.exe", "LTDNP3client.exe", "LTIEC104client.exe", "LTIEC104server.exe",
            "LTOPCUAserver.exe", "LTOPCUAclient.exe", "LTOPCDAserver.exe", "LTOPCDAclient.exe",
            "LTMQTTsubscriber.exe", "LTSNMPmanager.exe", "LTS7Client.exe", "LTreports.exe",
            "tv_w32.exe", "tv_x64.exe", "LTwebserver.exe", "LTlogger.exe", "LTscheduler.exe"
        }
        # Gather process info for monitored applications
        self.proc_names = []
        self.proc_pids = []
        self.proc_cpu_percents = []
        self.proc_mem_usages = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
            try:
                proc_name = proc.info['name']
                if proc_name not in lt_applications:
                    continue
                mem_mb = proc.info['memory_info'].rss / (1024 ** 2)
                cpu_percent = proc.info['cpu_percent'] or 0
                self.proc_names.append(proc_name)
                self.proc_pids.append(proc.info['pid'])
                self.proc_cpu_percents.append(cpu_percent)
                self.proc_mem_usages.append(round(mem_mb, 2))
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        SetTagArrayData("Obj1.Application_Info.application_name", self.proc_names)
        SetTagArrayData("Obj1.Application_Info.application_id", self.proc_pids)
        SetTagArrayData("Obj1.Application_Info.application_ram", self.proc_mem_usages)
        SetTagArrayData("Obj1.Application_Info.application_cpu", self.proc_cpu_percents)
        setTagData("Obj1.Application_Info.date_time", timestamp)

    def updateNetworkMetrics(self):
        # Collects and updates network metrics
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        current_net_stats = psutil.net_io_counters()
        current_time = time.time()
        time_elapsed = current_time - self.last_update_time
        bytes_sent = current_net_stats.bytes_sent - self.initial_net_stats.bytes_sent
        bytes_recv = current_net_stats.bytes_recv - self.initial_net_stats.bytes_recv
        mb_sent = round(bytes_sent / (1024 ** 2), 2)
        mb_recv = round(bytes_recv / (1024 ** 2), 2)
        total_mb = round((bytes_sent + bytes_recv) / (1024 ** 2), 2)
        upload_speed_mbps, download_speed_mbps = self.calculate_network_speeds(current_net_stats, time_elapsed)
        net_interfaces = psutil.net_if_stats()
        active_interfaces = [name for name, stats in net_interfaces.items() if stats.isup]
        packets_sent = current_net_stats.packets_sent - self.initial_net_stats.packets_sent
        packets_recv = current_net_stats.packets_recv - self.initial_net_stats.packets_recv
        setTagData("Obj1.Network_Info.bytes_sent_mb", mb_sent)
        setTagData("Obj1.Network_Info.bytes_received_mb", mb_recv)
        setTagData("Obj1.Network_Info.total_transfer_mb", total_mb)
        setTagData("Obj1.Network_Info.upload_speed_mbps", upload_speed_mbps)
        setTagData("Obj1.Network_Info.download_speed_mbps", download_speed_mbps)
        setTagData("Obj1.Network_Info.total_speed_mbps", round(upload_speed_mbps + download_speed_mbps, 3))
        setTagData("Obj1.Network_Info.active_interfaces_count", len(active_interfaces))
        setTagData("Obj1.Network_Info.active_interfaces", ','.join(active_interfaces))
        setTagData("Obj1.Network_Info.packets_sent", packets_sent)
        setTagData("Obj1.Network_Info.packets_received", packets_recv)
        setTagData("Obj1.Network_Info.measurement_interval_sec", round(time_elapsed, 2))
        setTagData("Obj1.Network_Info.date_time", timestamp)
        self.last_net_stats = current_net_stats
        self.last_update_time = current_time

if __name__ == '__main__':
    try:
        app = LTApplication(sys.argv)
        ex = widgetUI()
        ex.show()
        print("Enhanced System Monitor Started Successfully")
        print("Monitoring timers configured:")
        print("  - LTStartLiveCount logs: Every 1 minute")
        print("  - Server Infrastructure + LT Applications + Drive Monitoring: Every 2 seconds")
        print("  - Network Performance: Every 30 minutes")
        print("=" * 80)
        sys.exit(app.exec_())
    except Exception as e:
        print(f"Application startup error: {e}")
        sys.exit(1)