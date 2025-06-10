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
from datetime import datetime
from PyQt5.QtCore import QTimer

class widgetUI(Widget):
    def __init__(self, parent=None):
        super(widgetUI, self).__init__(parent)
        self.ui = Ui_widgetUI()
        self.ui.setupUi(self)
        
        # Initialize LTStartLiveCount log reading attributes
        self.log_directory = r"C:\SmartComm\iVisionmax\logs\LTStartLiveCount"
        self.last_read_positions = {}

        # Timer for reading LTStartLiveCount logs (every 1 minute = 60 seconds)
        self.lt_log_timer = QTimer(self)
        self.lt_log_timer.timeout.connect(self.updateLTStartLiveCount)
        self.lt_log_timer.start(60000)  # 60000 ms = 1 minute
        
        # Store initial network stats for bandwidth calculation (NETWORK ONLY)
        self.initial_net_stats = psutil.net_io_counters()
        self.system_boot_time = psutil.boot_time()  # System boot time reference
        self.last_net_stats = self.initial_net_stats  # For speed calculation
        self.last_update_time = time.time()  # For time-based speed calculation
        
        # Initialize arrays for process data
        self.proc_names = []
        self.proc_pids = []
        self.proc_cpu_percents = []
        self.proc_mem_usages = []
        self.proc_threads = []
        self.proc_handles = []
        self.proc_uptimes = []
        
        # Start monitoring with separate timers
        # Timer for server infrastructure and application monitoring (every 2 seconds)
        self.server_app_timer = QTimer(self)
        self.server_app_timer.timeout.connect(self.updateServerAndAppMetrics)
        self.server_app_timer.start(2000)  # Update every 2 seconds
        
        # Timer for network monitoring (every 30 minutes)
        self.network_timer = QTimer(self)
        self.network_timer.timeout.connect(self.updateNetworkMetrics)
        self.network_timer.start(1800000)  # Update every 30 minutes (30 * 60 * 1000 ms)

    def get_current_log_file(self):
        """Get current log file path based on today's date"""
        today = datetime.now().strftime("%d%m%Y")
        return os.path.join(self.log_directory, f"LTStartLiveCount{today}.log")

    def read_new_entries(self, file_path):
        """Read new entries from log file since last read position"""
        entries = []
        if not os.path.exists(file_path):
            return entries

        if file_path not in self.last_read_positions:
            self.last_read_positions[file_path] = 0

        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            file.seek(self.last_read_positions[file_path])
            lines = file.readlines()
            self.last_read_positions[file_path] = file.tell()

        for line in lines:
            entry = self.parse_log_line(line)
            if entry:
                entries.append(entry)

        return entries

    def parse_log_line(self, line):
        """Parse individual log line and extract relevant data"""
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
        """Update LTStartLiveCount logs every 1 minute with detailed console output"""
        try:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_file = self.get_current_log_file()
            new_entries = self.read_new_entries(log_file)
            
            print(f"\n=== LT START LIVE COUNT LOG UPDATE [{current_time}] ===")
            print(f"Log file: {log_file}")
            print(f"File exists: {os.path.exists(log_file)}")
            
            if new_entries:
                print(f"New entries found: {len(new_entries)}")
                print("Log entries collected:")
                
                for i, entry in enumerate(new_entries, 1):
                    print(f"  [{i}] Timestamp: {entry['timestamp']}")
                    print(f"      Level: {entry['level']}")
                    print(f"      Component ID: {entry['component_id']}")
                    print(f"      Value: {entry['value']}")
                
                # Display latest entry summary
                latest = new_entries[-1]
                print(f"\nLatest entry summary:")
                print(f"  {latest['timestamp']} | {latest['level']} | Component: {latest['component_id']} | Value: {latest['value']}")
                
                # Log data successfully collected message
                print(f"✓ LTStartLiveCount data collected successfully at {current_time}")
                
            else:
                print("No new entries found in log file")
                print("✓ LTStartLiveCount log check completed (no new data)")
            
            print("=" * 70)
            
        except Exception as e:
            error_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"\n=== LT START LIVE COUNT ERROR [{error_time}] ===")
            print(f"✗ LTStartLiveCount read error: {e}")
            print(f"Log file path: {self.get_current_log_file()}")
            print("=" * 70)

    def get_network_ping(self, host="8.8.8.8", timeout=3):
        """Measure network ping/latency - ONLY CALLED EVERY 30 MINUTES"""
        try:
            if platform.system().lower() == "windows":
                cmd = ["ping", "-n", "1", "-w", str(timeout * 1000), host]
            else:
                cmd = ["ping", "-c", "1", "-W", str(timeout), host]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 1)
            
            if result.returncode == 0:
                output = result.stdout
                if platform.system().lower() == "windows":
                    # Windows ping output parsing
                    for line in output.split('\n'):
                        if 'time=' in line.lower() or 'time<' in line.lower():
                            if 'time=' in line.lower():
                                ping_time = line.split('time=')[1].split('ms')[0].strip()
                            else:
                                ping_time = line.split('time<')[1].split('ms')[0].strip()
                            return float(ping_time)
                else:
                    # Unix/Linux ping output parsing
                    for line in output.split('\n'):
                        if 'time=' in line:
                            ping_time = line.split('time=')[1].split(' ')[0]
                            return float(ping_time)
            return None
        except Exception as e:
#            print(f"Ping error: {e}")
            return None

    def calculate_network_speeds(self, current_stats, time_elapsed):
        """Calculate download and upload speeds - ONLY CALLED EVERY 30 MINUTES"""
        try:
            # Calculate bytes transferred since last update
            bytes_sent_diff = current_stats.bytes_sent - self.last_net_stats.bytes_sent
            bytes_recv_diff = current_stats.bytes_recv - self.last_net_stats.bytes_recv
            
            # Calculate speeds in Mbps (Megabits per second)
            upload_speed_mbps = (bytes_sent_diff * 8) / (1024 * 1024 * time_elapsed) if time_elapsed > 0 else 0
            download_speed_mbps = (bytes_recv_diff * 8) / (1024 * 1024 * time_elapsed) if time_elapsed > 0 else 0
            
            return round(upload_speed_mbps, 3), round(download_speed_mbps, 3)
        except Exception as e:
#            print(f"Speed calculation error: {e}")
            return 0.0, 0.0

    def updateServerAndAppMetrics(self):
        """Update server infrastructure and application metrics EVERY 2 SECONDS - NO NETWORK DATA"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Server infrastructure metrics ONLY
        ram = psutil.virtual_memory().percent
        cpu = psutil.cpu_percent(interval=1)
        
        # Disk usage - get maximum across all partitions
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

        # Update server infrastructure tags
        setTagData("Obj1.Server_Infra.ram", ram)
        setTagData("Obj1.Server_Infra.cpu", cpu)
        setTagData("Obj1.Server_Infra.storage", disk)
        setTagData("Obj1.Server_Infra.date_time", timestamp)

        # LT applications to monitor
        lt_applications = {
            "LTmessagebroker.exe", "LTtagdb.exe", "LTalarmevents.exe", "LThistdb.exe", 
            "LTHAappl.exe", "LTide.exe", "Viewer.exe", "LTviewer.exe", "LTModbusclient.exe", 
            "LTIEC61850client.exe", "LTDNP3client.exe", "LTIEC104client.exe", "LTIEC104server.exe", 
            "LTOPCUAserver.exe", "LTOPCUAclient.exe", "LTOPCDAserver.exe", "LTOPCDAclient.exe", 
            "LTMQTTsubscriber.exe", "LTSNMPmanager.exe", "LTS7Client.exe", "LTreports.exe", 
            "tv_w32.exe", "tv_x64.exe", "LTwebserver.exe", "LTlogger.exe", "LTscheduler.exe"
        }

        # Clear arrays before collecting new data
        self.proc_names = []
        self.proc_pids = []
        self.proc_cpu_percents = []
        self.proc_mem_usages = []
        self.proc_threads = []
        self.proc_handles = []
        self.proc_uptimes = []

        # Collect process information
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'num_threads', 'num_handles', 'create_time']):
            try:
                proc_name = proc.info['name']
                if proc_name not in lt_applications:
                    continue

                # Memory usage in MB
                mem_mb = proc.info['memory_info'].rss / (1024 ** 2)
                
                # CPU percentage
                cpu_percent = proc.info['cpu_percent'] or 0

                # Thread and handle counts
                threads = proc.info['num_threads'] or 0
                handles = proc.info['num_handles'] or 0

                # Process uptime calculation
                create_time = proc.info['create_time']
                uptime_hours = (time.time() - create_time) / 3600

                # Append metrics to arrays
                self.proc_names.append(proc_name)
                self.proc_pids.append(proc.info['pid'])
                self.proc_cpu_percents.append(cpu_percent)
                self.proc_mem_usages.append(round(mem_mb, 2))
                self.proc_threads.append(threads)
                self.proc_handles.append(handles)
                self.proc_uptimes.append(round(uptime_hours, 2))

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        # Update application tags with arrays
        SetTagArrayData("Obj1.Application_Info.application_name", self.proc_names)
        SetTagArrayData("Obj1.Application_Info.application_id", self.proc_pids)
        SetTagArrayData("Obj1.Application_Info.application_ram", self.proc_mem_usages)
        SetTagArrayData("Obj1.Application_Info.application_cpu", self.proc_cpu_percents)
        SetTagArrayData("Obj1.Application_Info.application_threads", self.proc_threads)
        SetTagArrayData("Obj1.Application_Info.application_handles", self.proc_handles)
        SetTagArrayData("Obj1.Application_Info.application_uptime", self.proc_uptimes)
        setTagData("Obj1.Application_Info.date_time", timestamp)
        
        # Process logging
        # for i in range(len(self.proc_names)):
        #     print(f"PROCESS LOG: {timestamp} | {self.proc_names[i]} | PID: {self.proc_pids[i]} | "
        #           f"RAM: {self.proc_mem_usages[i]}MB | CPU: {self.proc_cpu_percents[i]}% | "
        #           f"Threads: {self.proc_threads[i]} | Handles: {self.proc_handles[i]} | Uptime: {self.proc_uptimes[i]}h")

        # # Server and Application metrics display (NO NETWORK DATA HERE)
        # print(f"\n=== SERVER & APPLICATION METRICS UPDATE [{timestamp}] ===")
        # print(f"SERVER INFRASTRUCTURE:")
        # print(f"  RAM: {ram}% | CPU: {cpu}% | Storage: {disk}%")
        
        # print(f"\nAPPLICATION PROCESSES ({len(self.proc_names)} found):")
        # if len(self.proc_names) == 0:
        #     print("  No LT application processes detected")
        # else:
        #     for i in range(len(self.proc_names)):
        #         print(f"  [{i+1}] {self.proc_names[i]} (PID: {self.proc_pids[i]})")
        #         print(f"      RAM: {self.proc_mem_usages[i]}MB | CPU: {self.proc_cpu_percents[i]}% | "
        #               f"Threads: {self.proc_threads[i]} | Handles: {self.proc_handles[i]} | Uptime: {self.proc_uptimes[i]}h")
        # print("=" * 80)

    def updateNetworkMetrics(self):
        """Update network metrics EVERY 30 MINUTES ONLY"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Network metrics calculation with speed measurement
        current_net_stats = psutil.net_io_counters()
        current_time = time.time()
        time_elapsed = current_time - self.last_update_time
        
        # Calculate cumulative data transfer since application start
        bytes_sent = current_net_stats.bytes_sent - self.initial_net_stats.bytes_sent
        bytes_recv = current_net_stats.bytes_recv - self.initial_net_stats.bytes_recv
        
        # Convert to MB
        mb_sent = round(bytes_sent / (1024 ** 2), 2)
        mb_recv = round(bytes_recv / (1024 ** 2), 2)
        total_mb = round((bytes_sent + bytes_recv) / (1024 ** 2), 2)
        
        # Calculate current network speeds
        upload_speed_mbps, download_speed_mbps = self.calculate_network_speeds(current_net_stats, time_elapsed)
        
        # Network interfaces status
        net_interfaces = psutil.net_if_stats()
        active_interfaces = [name for name, stats in net_interfaces.items() if stats.isup]
        
        # Network packet statistics
        packets_sent = current_net_stats.packets_sent - self.initial_net_stats.packets_sent
        packets_recv = current_net_stats.packets_recv - self.initial_net_stats.packets_recv
        
        # Update network tags with comprehensive metrics
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

        # Update last measurements for next speed calculation
        self.last_net_stats = current_net_stats
        self.last_update_time = current_time

#         # Network logging
# #        print(f"\nNETWORK LOG: {timestamp} | Upload: {upload_speed_mbps}Mbps | Download: {download_speed_mbps}Mbps | "
#               f"Avg Ping: {avg_ping_ms}ms | Sent: {mb_sent}MB | Received: {mb_recv}MB | Total: {total_mb}MB")

        # Comprehensive network metrics display
#        print(f"\n=== NETWORK METRICS UPDATE [{timestamp}] ===")
#        print(f"NETWORK TRANSFER:")
#        print(f"  Cumulative Data - Sent: {mb_sent}MB | Received: {mb_recv}MB | Total: {total_mb}MB")
#        print(f"  Packet Count - Sent: {packets_sent:,} | Received: {packets_recv:,}")
        
#        print(f"\nNETWORK PERFORMANCE:")
#        print(f"  Current Speed - Upload: {upload_speed_mbps} Mbps | Download: {download_speed_mbps} Mbps | Combined: {round(upload_speed_mbps + download_speed_mbps, 3)} Mbps")
#        print(f"  Ping Latency - Avg: {avg_ping_ms}ms | Min: {min_ping_ms}ms | Max: {max_ping_ms}ms")
#        print(f"  Measurement Interval: {round(time_elapsed, 2)} seconds")
        
#        print(f"\nNETWORK INTERFACES:")
#        print(f"  Active Interfaces ({len(active_interfaces)}): {', '.join(active_interfaces) if active_interfaces else 'None detected'}")
        
#         if len(ping_results) > 1:
# #            print(f"  Ping Test Results: {len(ping_results)}/{len(ping_hosts)} hosts responded")
        
# #        print("=" * 80)

if __name__ == '__main__':
    try:
        app = LTApplication(sys.argv)
        ex = widgetUI()
        ex.show()
        print("Enhanced System Monitor Started Successfully")
        print("Monitoring timers configured:")
        print("  - LTStartLiveCount logs: Every 1 minute")
        print("  - Server Infrastructure + LT Applications: Every 2 seconds")
        print("  - Network Performance: Every 30 minutes")
        print("=" * 80)
        sys.exit(app.exec_())
    except Exception as e:
        print(f"Application startup error: {e}")
        sys.exit(1)

