from Widget import *
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
from PyQt5.QtCore import QTimer, QObject
from PyQt5.QtWidgets import QApplication

class SystemMonitor(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Directory for LTStartLiveCount logs
        self.log_directory = r"C:\SmartComm\iVisionmax\logs\LTStartLiveCount"
        
        # Timer to update LTStartLiveCount log info every minute
        self.lt_log_timer = QTimer(self)
        self.lt_log_timer.timeout.connect(self.updateLTStartLiveCount)
        self.lt_log_timer.start(60000)  # 60 seconds
        
        # Initialize network and system stats
        self.initial_net_stats = psutil.net_io_counters()
        self.system_boot_time = psutil.boot_time()
        self.last_net_stats = self.initial_net_stats
        self.last_update_time = time.time()
        
        # Lists to store process and drive info
        self.proc_names = []
        self.proc_pids = []
        self.proc_cpu_percents = []
        self.proc_mem_usages = []
        self.drive_names = []
        self.drive_free_spaces_gb = []
        self.drive_total_spaces_gb = []
        self.drive_used_spaces_gb = []
        self.drive_usage_percentages = []
        
        # Timer to update server metrics every 2 seconds
        self.server_timer = QTimer(self)
        self.server_timer.timeout.connect(self.updateServerAndAppMetrics)
        self.server_timer.start(2000)  # 2 seconds
        
        # Timer to update application metrics every 2 seconds
        self.application_timer = QTimer(self)
        self.application_timer.timeout.connect(self.updateApplicationMetrics)
        self.application_timer.start(2000)  # 2 seconds
        
        # Timer to update network metrics every minute
        self.network_timer = QTimer(self)
        self.network_timer.timeout.connect(self.updateNetworkMetrics)
        self.network_timer.start(60000)  # 60 seconds
        
        # Timer to fetch diagnostic tag info every second
        self.diagnostic_timer = QTimer(self)
        self.diagnostic_timer.timeout.connect(self.fetchDiagnosticTagInfo)
        self.diagnostic_timer.start(1000)  # 1 second

        # Timer to update application PSMan status every 2 seconds
        self.psman_timer = QTimer(self)
        self.psman_timer.timeout.connect(self.updateApplicationPSManStatus)
        self.psman_timer.start(2000)  # 2 seconds

    def get_current_log_file(self):
        """Get the current log file path based on today's date"""
        today = datetime.now().strftime("%d%m%Y")
        return os.path.join(self.log_directory, f"LTStartLiveCount{today}.log")

    def get_last_log_entry(self, file_path):
        """Retrieves the last log entry from the specified log file"""
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
            print(f"Error reading log file: {e}")
            return None

    def parse_log_line(self, line):
        """Parses a log line and returns its components as a dictionary"""
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
        """Updates the LTStartLiveCount information in the system tags"""
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
            print(f"Error in updateLTStartLiveCount: {e}")

    def get_drive_information(self):
        """Retrieves information about the system's drives"""
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
            print(f"Error getting drive information: {e}")
            return False

    def calculate_network_speeds(self, current_stats, time_elapsed):
        """Calculates network upload and download speeds based on network statistics and time elapsed"""
        try:
            bytes_sent_diff = current_stats.bytes_sent - self.last_net_stats.bytes_sent
            bytes_recv_diff = current_stats.bytes_recv - self.last_net_stats.bytes_recv
            
            upload_speed_mbps = (bytes_sent_diff * 8) / (1024 * 1024 * time_elapsed) if time_elapsed > 0 else 0
            download_speed_mbps = (bytes_recv_diff * 8) / (1024 * 1024 * time_elapsed) if time_elapsed > 0 else 0
            
            return round(upload_speed_mbps, 3), round(download_speed_mbps, 3)
        except Exception as e:
            print(f"Error calculating network speeds: {e}")
            return 0.0, 0.0

    def updateServerAndAppMetrics(self):
        """Updates server infrastructure metrics in the system tags"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Get system metrics
            ram = psutil.virtual_memory().percent
            cpu = psutil.cpu_percent(interval=1)
            
            # Get disk usage
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
            
            # CPU information
            cpu_per_core = psutil.cpu_percent(percpu=True)
            cpu_count_logical = psutil.cpu_count(logical=True)
            cpu_count_physical = psutil.cpu_count(logical=False)
            cores_being_used = sum(1 for usage in cpu_per_core if usage > 0)
            
            # Get drive information
            drive_info_success = self.get_drive_information()
            
            # Update server infrastructure tags
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
                
                # Calculate totals
                total_storage_gb = sum(self.drive_total_spaces_gb)
                total_free_gb = sum(self.drive_free_spaces_gb)
                total_used_gb = sum(self.drive_used_spaces_gb)
                
                setTagData("Obj1.Server_Infra.total_storage_gb", round(total_storage_gb, 2))
                setTagData("Obj1.Server_Infra.total_free_storage_gb", round(total_free_gb, 2))
                setTagData("Obj1.Server_Infra.total_used_storage_gb", round(total_used_gb, 2))
                setTagData("Obj1.Server_Infra.overall_storage_usage_percent", 
                          round((total_used_gb / total_storage_gb) * 100, 2) if total_storage_gb > 0 else 0)
            
            # Application monitoring
            lt_applications = {
                "LTmessagebroker.exe", "LTtagdb.exe", "LTalarmevents.exe", "LThistdb.exe",
                "LTHAappl.exe", "LTide.exe", "LTviewer.exe", "LTModbusclient.exe",
                "LTIEC61850client.exe", "LTDNP3client.exe", "LTIEC104client.exe", "LTIEC104server.exe"
            }
            
            # Gather process info for monitored applications
            self.proc_names = []
            self.proc_pids = []
            self.proc_cpu_percents = []
            self.proc_mem_usages = []
            self.proc_statuses = []
            
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
                    self.proc_statuses.append("RUNNING")
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue

            # Add NOT_RUNNING status for applications not found in process list
            for app in lt_applications:
                if app not in self.proc_names:
                    self.proc_names.append("")
                    self.proc_pids.append("")
                    self.proc_cpu_percents.append("")
                    self.proc_mem_usages.append("")
                    self.proc_statuses.append("")

            # Update application arrays
            SetTagArrayData("Obj1.Application_Info.application_name", self.proc_names)
            SetTagArrayData("Obj1.Application_Info.application_id", self.proc_pids)
            SetTagArrayData("Obj1.Application_Info.application_ram", self.proc_mem_usages)
            SetTagArrayData("Obj1.Application_Info.application_cpu", self.proc_cpu_percents)
            SetTagArrayData("Obj1.Application_Info.application_status", self.proc_statuses)        
            setTagData("Obj1.Application_Info.date_time", timestamp)
            
        except Exception as e:
            print(f"Error in updateServerAndAppMetrics: {e}")

    def updateApplicationMetrics(self):
        """Updates application metrics in the system tags"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        lt_applications = {
            "LTmessagebroker.exe", "LTtagdb.exe", "LTalarmevents.exe", "LThistdb.exe",
            "LTHAappl.exe", "LTide.exe", "LTviewer.exe", "LTModbusclient.exe",
            "LTIEC61850client.exe", "LTDNP3client.exe", "LTIEC104client.exe", "LTIEC104server.exe"
        }
        app_data = {}
        for app_name in lt_applications:
            app_key = app_name.replace('.exe', '').lower()
            app_data[app_key] = {
                'name': '',
                'pid': '',
                'cpu': '',
                'ram': '',
                'status': 'NOT_RUNNING'
            }
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
            try:
                proc_name = proc.info['name']
                if proc_name not in lt_applications:
                    continue
                mem_mb = proc.info['memory_info'].rss / (1024 ** 2)
                cpu_percent = proc.info['cpu_percent'] or 0
                app_key = proc_name.replace('.exe', '').lower()
                app_data[app_key] = {
                    'name': proc_name,
                    'pid': str(proc.info['pid']),
                    'cpu': str(cpu_percent),
                    'ram': str(round(mem_mb, 2)),
                    'status': 'RUNNING'
                }
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        # LTmessagebroker application info
        self.ltmessagebroker_name = app_data['ltmessagebroker']['name']
        self.ltmessagebroker_pid = app_data['ltmessagebroker']['pid']
        self.ltmessagebroker_cpu = app_data['ltmessagebroker']['cpu']
        self.ltmessagebroker_ram = app_data['ltmessagebroker']['ram']
        self.ltmessagebroker_status = app_data['ltmessagebroker']['status']
        setTagData("Obj1.Application_Info.LTmessagebroker.NAME", self.ltmessagebroker_name)
        setTagData("Obj1.Application_Info.LTmessagebroker.PID", self.ltmessagebroker_pid)
        setTagData("Obj1.Application_Info.LTmessagebroker.CPU", self.ltmessagebroker_cpu)
        setTagData("Obj1.Application_Info.LTmessagebroker.RAM", self.ltmessagebroker_ram)
        setTagData("Obj1.Application_Info.LTmessagebroker.STATUS", self.ltmessagebroker_status)

        # LTtagdb application info
        self.lttagdb_name = app_data['lttagdb']['name']
        self.lttagdb_pid = app_data['lttagdb']['pid']
        self.lttagdb_cpu = app_data['lttagdb']['cpu']
        self.lttagdb_ram = app_data['lttagdb']['ram']
        self.lttagdb_status = app_data['lttagdb']['status']
        setTagData("Obj1.Application_Info.LTtagdb.NAME", self.lttagdb_name)
        setTagData("Obj1.Application_Info.LTtagdb.PID", self.lttagdb_pid)
        setTagData("Obj1.Application_Info.LTtagdb.CPU", self.lttagdb_cpu)
        setTagData("Obj1.Application_Info.LTtagdb.RAM", self.lttagdb_ram)
        setTagData("Obj1.Application_Info.LTtagdb.STATUS", self.lttagdb_status)

        # LTalarmevents application info
        self.ltalarmevents_name = app_data['ltalarmevents']['name']
        self.ltalarmevents_pid = app_data['ltalarmevents']['pid']
        self.ltalarmevents_cpu = app_data['ltalarmevents']['cpu']
        self.ltalarmevents_ram = app_data['ltalarmevents']['ram']
        self.ltalarmevents_status = app_data['ltalarmevents']['status']
        setTagData("Obj1.Application_Info.LTalarmevents.NAME", self.ltalarmevents_name)
        setTagData("Obj1.Application_Info.LTalarmevents.PID", self.ltalarmevents_pid)
        setTagData("Obj1.Application_Info.LTalarmevents.CPU", self.ltalarmevents_cpu)
        setTagData("Obj1.Application_Info.LTalarmevents.RAM", self.ltalarmevents_ram)
        setTagData("Obj1.Application_Info.LTalarmevents.STATUS", self.ltalarmevents_status)

        # LThistdb application info
        self.lthistdb_name = app_data['lthistdb']['name']
        self.lthistdb_pid = app_data['lthistdb']['pid']
        self.lthistdb_cpu = app_data['lthistdb']['cpu']
        self.lthistdb_ram = app_data['lthistdb']['ram']
        self.lthistdb_status = app_data['lthistdb']['status']
        setTagData("Obj1.Application_Info.LThistdb.NAME", self.lthistdb_name)
        setTagData("Obj1.Application_Info.LThistdb.PID", self.lthistdb_pid)
        setTagData("Obj1.Application_Info.LThistdb.CPU", self.lthistdb_cpu)
        setTagData("Obj1.Application_Info.LThistdb.RAM", self.lthistdb_ram)
        setTagData("Obj1.Application_Info.LThistdb.STATUS", self.lthistdb_status)

        # LTHAappl application info
        self.lthaappl_name = app_data['lthaappl']['name']
        self.lthaappl_pid = app_data['lthaappl']['pid']
        self.lthaappl_cpu = app_data['lthaappl']['cpu']
        self.lthaappl_ram = app_data['lthaappl']['ram']
        self.lthaappl_status = app_data['lthaappl']['status']
        setTagData("Obj1.Application_Info.LTHAappl.NAME", self.lthaappl_name)
        setTagData("Obj1.Application_Info.LTHAappl.PID", self.lthaappl_pid)
        setTagData("Obj1.Application_Info.LTHAappl.CPU", self.lthaappl_cpu)
        setTagData("Obj1.Application_Info.LTHAappl.RAM", self.lthaappl_ram)
        setTagData("Obj1.Application_Info.LTHAappl.STATUS", self.lthaappl_status)

        # LTide application info
        self.ltide_name = app_data['ltide']['name']
        self.ltide_pid = app_data['ltide']['pid']
        self.ltide_cpu = app_data['ltide']['cpu']
        self.ltide_ram = app_data['ltide']['ram']
        self.ltide_status = app_data['ltide']['status']
        setTagData("Obj1.Application_Info.LTide.NAME", self.ltide_name)
        setTagData("Obj1.Application_Info.LTide.PID", self.ltide_pid)
        setTagData("Obj1.Application_Info.LTide.CPU", self.ltide_cpu)
        setTagData("Obj1.Application_Info.LTide.RAM", self.ltide_ram)
        setTagData("Obj1.Application_Info.LTide.STATUS", self.ltide_status)

        # LTviewer application info
        self.ltviewer_name = app_data['ltviewer']['name']
        self.ltviewer_pid = app_data['ltviewer']['pid']
        self.ltviewer_cpu = app_data['ltviewer']['cpu']
        self.ltviewer_ram = app_data['ltviewer']['ram']
        self.ltviewer_status = app_data['ltviewer']['status']
        setTagData("Obj1.Application_Info.LTviewer.NAME", self.ltviewer_name)
        setTagData("Obj1.Application_Info.LTviewer.PID", self.ltviewer_pid)
        setTagData("Obj1.Application_Info.LTviewer.CPU", self.ltviewer_cpu)
        setTagData("Obj1.Application_Info.LTviewer.RAM", self.ltviewer_ram)
        setTagData("Obj1.Application_Info.LTviewer.STATUS", self.ltviewer_status)

        # LTModbusclient application info
        self.ltmodbusclient_name = app_data['ltmodbusclient']['name']
        self.ltmodbusclient_pid = app_data['ltmodbusclient']['pid']
        self.ltmodbusclient_cpu = app_data['ltmodbusclient']['cpu']
        self.ltmodbusclient_ram = app_data['ltmodbusclient']['ram']
        self.ltmodbusclient_status = app_data['ltmodbusclient']['status']
        setTagData("Obj1.Application_Info.LTModbusclient.NAME", self.ltmodbusclient_name)
        setTagData("Obj1.Application_Info.LTModbusclient.PID", self.ltmodbusclient_pid)
        setTagData("Obj1.Application_Info.LTModbusclient.CPU", self.ltmodbusclient_cpu)
        setTagData("Obj1.Application_Info.LTModbusclient.RAM", self.ltmodbusclient_ram)
        setTagData("Obj1.Application_Info.LTModbusclient.STATUS", self.ltmodbusclient_status)

        # LTIEC61850client application info
        self.ltiec61850client_name = app_data['ltiec61850client']['name']
        self.ltiec61850client_pid = app_data['ltiec61850client']['pid']
        self.ltiec61850client_cpu = app_data['ltiec61850client']['cpu']
        self.ltiec61850client_ram = app_data['ltiec61850client']['ram']
        self.ltiec61850client_status = app_data['ltiec61850client']['status']
        setTagData("Obj1.Application_Info.LTIEC61850client.NAME", self.ltiec61850client_name)
        setTagData("Obj1.Application_Info.LTIEC61850client.PID", self.ltiec61850client_pid)
        setTagData("Obj1.Application_Info.LTIEC61850client.CPU", self.ltiec61850client_cpu)
        setTagData("Obj1.Application_Info.LTIEC61850client.RAM", self.ltiec61850client_ram)
        setTagData("Obj1.Application_Info.LTIEC61850client.STATUS", self.ltiec61850client_status)

        # LTDNP3client application info
        self.ltdnp3client_name = app_data['ltdnp3client']['name']
        self.ltdnp3client_pid = app_data['ltdnp3client']['pid']
        self.ltdnp3client_cpu = app_data['ltdnp3client']['cpu']
        self.ltdnp3client_ram = app_data['ltdnp3client']['ram']
        self.ltdnp3client_status = app_data['ltdnp3client']['status']
        setTagData("Obj1.Application_Info.LTDNP3client.NAME", self.ltdnp3client_name)
        setTagData("Obj1.Application_Info.LTDNP3client.PID", self.ltdnp3client_pid)
        setTagData("Obj1.Application_Info.LTDNP3client.CPU", self.ltdnp3client_cpu)
        setTagData("Obj1.Application_Info.LTDNP3client.RAM", self.ltdnp3client_ram)
        setTagData("Obj1.Application_Info.LTDNP3client.STATUS", self.ltdnp3client_status)

        # LTIEC104client application info
        self.ltiec104client_name = app_data['ltiec104client']['name']
        self.ltiec104client_pid = app_data['ltiec104client']['pid']
        self.ltiec104client_cpu = app_data['ltiec104client']['cpu']
        self.ltiec104client_ram = app_data['ltiec104client']['ram']
        self.ltiec104client_status = app_data['ltiec104client']['status']
        setTagData("Obj1.Application_Info.LTIEC104client.NAME", self.ltiec104client_name)
        setTagData("Obj1.Application_Info.LTIEC104client.PID", self.ltiec104client_pid)
        setTagData("Obj1.Application_Info.LTIEC104client.CPU", self.ltiec104client_cpu)
        setTagData("Obj1.Application_Info.LTIEC104client.RAM", self.ltiec104client_ram)
        setTagData("Obj1.Application_Info.LTIEC104client.STATUS", self.ltiec104client_status)

        # LTIEC104server application info
        self.ltiec104server_name = app_data['ltiec104server']['name']
        self.ltiec104server_pid = app_data['ltiec104server']['pid']
        self.ltiec104server_cpu = app_data['ltiec104server']['cpu']
        self.ltiec104server_ram = app_data['ltiec104server']['ram']
        self.ltiec104server_status = app_data['ltiec104server']['status']
        setTagData("Obj1.Application_Info.LTIEC104server.NAME", self.ltiec104server_name)
        setTagData("Obj1.Application_Info.LTIEC104server.PID", self.ltiec104server_pid)
        setTagData("Obj1.Application_Info.LTIEC104server.CPU", self.ltiec104server_cpu)
        setTagData("Obj1.Application_Info.LTIEC104server.RAM", self.ltiec104server_ram)
        setTagData("Obj1.Application_Info.LTIEC104server.STATUS", self.ltiec104server_status)

        # Set the timestamp for the application info update
        setTagData("Obj1.Application_Info.date_time", timestamp)

    def updateApplicationPSManStatus(self):
        """
        Updates the application running status for LT applications only,
        and writes to Obj1.Application_Info.application_name_psman and
        Obj1.Application_Info.application_status_psman tags.
        """
        lt_applications = [
            "LTmessagebroker.exe", "LTtagdb.exe", "LTalarmevents.exe", "LThistdb.exe",
            "LTide.exe", "LTviewer.exe", "LTModbusclient.exe"
        ]

        # Get currently running process names
        running_processes = set()
        for proc in psutil.process_iter(['name']):
            try:
                running_processes.add(proc.info['name'])
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        # Prepare arrays for tag writing
        app_names_psman = []
        app_status_psman = []

        for app in lt_applications:
            app_names_psman.append(app)
            if app in running_processes:
                app_status_psman.append("RUNNING")
            else:
                app_status_psman.append("NOT RUNNING")

        SetTagArrayData("Obj1.Application_Info.application_name_psman", app_names_psman)
        SetTagArrayData("Obj1.Application_Info.application_status_psman", app_status_psman)

    def updateNetworkMetrics(self):
        """Updates network metrics in the system tags"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            current_net_stats = psutil.net_io_counters()
            current_time = time.time()
            time_elapsed = current_time - self.last_update_time

            # Calculate data transfer
            bytes_sent = current_net_stats.bytes_sent - self.initial_net_stats.bytes_sent
            bytes_recv = current_net_stats.bytes_recv - self.initial_net_stats.bytes_recv
            mb_sent = round(bytes_sent / (1024 ** 2), 2)
            mb_recv = round(bytes_recv / (1024 ** 2), 2)
            total_mb = round((bytes_sent + bytes_recv) / (1024 ** 2), 2)

            # Calculate speeds
            upload_speed_mbps, download_speed_mbps = self.calculate_network_speeds(current_net_stats, time_elapsed)

            # Get all network interfaces (not just active)
            net_interfaces = psutil.net_if_stats()
            all_interfaces = list(net_interfaces.keys())

            # Build active/inactive status array for each interface
            interface_statuses = []
            for name in all_interfaces:
                if net_interfaces[name].isup:
                    interface_statuses.append("active")
                else:
                    interface_statuses.append("inactive")

            # Calculate packets
            packets_sent = current_net_stats.packets_sent - self.initial_net_stats.packets_sent
            packets_recv = current_net_stats.packets_recv - self.initial_net_stats.packets_recv

            # Update network tags
            setTagData("Obj1.Network_Info.bytes_sent_mb", mb_sent)
            setTagData("Obj1.Network_Info.bytes_received_mb", mb_recv)
            setTagData("Obj1.Network_Info.total_transfer_mb", total_mb)
            setTagData("Obj1.Network_Info.upload_speed_mbps", upload_speed_mbps)
            setTagData("Obj1.Network_Info.download_speed_mbps", download_speed_mbps)
            setTagData("Obj1.Network_Info.total_speed_mbps", round(upload_speed_mbps + download_speed_mbps, 3))
            setTagData("Obj1.Network_Info.active_interfaces_count", len(all_interfaces))
            SetTagArrayData("Obj1.Network_Info.active_interfaces", all_interfaces)
            SetTagArrayData("Obj1.Network_Info.active_interfaces_status", interface_statuses)
            setTagData("Obj1.Network_Info.packets_sent", packets_sent)
            setTagData("Obj1.Network_Info.packets_received", packets_recv)
            setTagData("Obj1.Network_Info.measurement_interval_sec", round(time_elapsed, 2))
            setTagData("Obj1.Network_Info.date_time", timestamp)

            # Update for next calculation
            self.last_net_stats = current_net_stats
            self.last_update_time = current_time

        except Exception as e:
            print(f"Error in updateNetworkMetrics: {e}")

    def fetchDiagnosticTagInfo(self):
        """Placeholder for diagnostic tag information fetching"""
        # This method can be implemented based on specific diagnostic requirements
        pass

def main():
    """Main function to run the system monitor"""
    try:
        # Create QApplication instance
        app = QApplication(sys.argv)
        
        # Create and start system monitor
        monitor = SystemMonitor()
        
        print("Enhanced System Monitor Started Successfully")
        print("Monitoring timers configured:")
        print("   - LTStartLiveCount logs: Every 1 minute")
        print("   - Server Infrastructure Monitoring: Every 2 seconds")
        print("   - Application Monitoring: Every 2 seconds")
        print("   - Network Performance: Every 1 minute")
        print("   - Diagnostic Tags: Every 1 second")
        print("=" * 80)
        
        # Run the application
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"Application startup error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()