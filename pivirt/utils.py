# Copyright (c) 2024 Federico Sauter. All rights reserved.
#
# This file is part of PiVirt-Core.
#
# PiVirt-Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PiVirt-Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with PiVirt-Core. If not, see <https://www.gnu.org/licenses/>.
#
# For proprietary use, a commercial license is available. Contact pivirt@pm.me.


import errno
import os
import signal
import time
from logging import DEBUG, ERROR, INFO, WARN
from pathlib import Path

from .logging_config import log_with_vm_id, setup_logger

logger = setup_logger(__name__)


def is_process_running(pid):
    try:
        os.kill(pid, 0)
    except OSError as e:
        if e.errno == errno.ESRCH:
            return False
        else:
            raise
    else:
        return True


def get_process_uptime_seconds(pid: int) -> int:
    try:
        # Read the process start time in clock ticks
        with open(f"/proc/{pid}/stat", "r") as f:
            stat = f.readline().split()
            start_time_ticks = int(stat[21])

        # Get the system uptime
        with open("/proc/uptime", "r") as f:
            uptime_seconds = float(f.readline().split()[0])

        clock_ticks_per_second = os.sysconf(os.sysconf_names["SC_CLK_TCK"])
        process_start_time_seconds = start_time_ticks / clock_ticks_per_second
        process_uptime_seconds = int(uptime_seconds - process_start_time_seconds)

        return process_uptime_seconds
    except Exception as e:
        raise RuntimeError(f"Failed to get process uptime for PID {pid}: {e}")


def try_terminate_process(pid, timeout):
    os.kill(pid, signal.SIGTERM)
    for _ in range(timeout):
        time.sleep(1)
        if not is_process_running(pid):
            return True
    return False


def terminate_vm_by_pidfile(pidfile_path: Path, vm_id: str, timeout=30):
    """
    Attempt to stop the VM identified by the pidfile.
    Wait for the specified timeout and perform a SIGKILL on the process,
    if it was still running. Remove the pidfile only if the process was successfully terminated.
    """
    try:
        if not pidfile_path.exists():
            log_with_vm_id(logger, DEBUG, vm_id, f"PID file {pidfile_path} does not exist.")
            return False

        pid_content = pidfile_path.read_text().strip()
        if not pid_content.isdigit():
            return False

        pid = int(pid_content)
        process_terminated = try_terminate_process(pid, timeout)

        if not process_terminated:
            os.kill(pid, signal.SIGKILL)
            log_with_vm_id(logger, WARN, vm_id, f"Process {pid} force-stopped after timeout.")
            process_terminated = True
    except ValueError:
        log_with_vm_id(
            logger,
            WARN,
            vm_id,
            f"Warning: Deleting PID file {str(pidfile_path)} as contained invalid data: '{pid_content}'",
        )
        try:
            pidfile_path.unlink()
        except OSError as e:
            log_with_vm_id(logger, WARN, vm_id, f"Error deleting PID file {pidfile_path}: {e}")
        raise RuntimeError(f"Unable to determine VM running status {vm_id}")
    except OSError as e:
        if e.errno == errno.ESRCH:
            log_with_vm_id(
                logger,
                INFO,
                vm_id,
                f"Process {pid} is already dead or was successfully terminated.",
            )
            process_terminated = True
        elif e.errno == errno.EPERM:
            log_with_vm_id(
                logger, ERROR, vm_id, f"Permission denied when trying to terminate process {pid}."
            )
            process_terminated = False
        else:
            log_with_vm_id(logger, ERROR, vm_id, f"Error stopping process {pid}: {e}")
            raise RuntimeError(f"An error occurred while stopping VM {vm_id}")

    if process_terminated:
        try:
            if pidfile_path.exists():
                pidfile_path.unlink()
        except OSError as e:
            log_with_vm_id(logger, WARN, vm_id, f"Error deleting PID file {pidfile_path}: {e}")

    return process_terminated


def check_and_clean_vm_status(pidfile_path: Path, vm_id: str) -> bool:
    """Checks whether a VM is running based on the pidfile and cleans up the pidfile if the VM is not running."""
    if not pidfile_path.exists():
        log_with_vm_id(logger, DEBUG, vm_id, "pidfile doesn't exist")
        return False

    try:
        with open(pidfile_path, "r") as file:
            pid = file.read().strip()
        if pid:
            is_running = is_process_running(int(pid))
    except ValueError:
        log_with_vm_id(
            logger,
            WARN,
            vm_id,
            f"Warning: Deleting PID file {str(pidfile_path)} as contained invalid data: '{pid}'",
        )
        try:
            pidfile_path.unlink()
        except OSError as e:
            log_with_vm_id(logger, WARN, vm_id, f"Error deleting PID file {pidfile_path}: {e}")

        raise RuntimeError(f"Unable to determine VM running status {vm_id}")
    except OSError as e:
        if e.errno == errno.EPERM:
            log_with_vm_id(
                logger, ERROR, vm_id, f"Permission denied when checking status of process {pid}."
            )
            return True
        elif e.errno == errno.ESRCH:
            log_with_vm_id(
                logger,
                INFO,
                vm_id,
                f"Process {pid} is already dead or was successfully terminated.",
            )
            is_running = False
        else:
            log_with_vm_id(
                logger, ERROR, vm_id, f"Unable to determine running status of process {pid}: {e}"
            )
            raise RuntimeError(f"Unable to determine VM running status {vm_id}")

    try:
        if not is_running:
            pidfile_path.unlink()
    except OSError as e:
        log_with_vm_id(logger, WARN, vm_id, f"Error deleting PID file {pidfile_path}: {e}")
        raise RuntimeError(f"Unable to delete {vm_id} pidfile")

    return is_running
