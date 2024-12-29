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


import json
import os
import shutil
import subprocess
from contextlib import contextmanager
from logging import DEBUG, ERROR, INFO, WARN
from pathlib import Path
from typing import Any, Dict, Tuple

import portalocker

from .guestfish_utils import copy_files_from_image
from .logging_config import log_with_vm_id, setup_logger
from .qemu_utils import resize_image_to_power_of_two
from .utils import (check_and_clean_vm_status, get_process_uptime_seconds,
                    is_process_running, terminate_vm_by_pidfile)


class VMManager:

    def __init__(self, vm_dir: Path):
        self.logger = setup_logger(__name__)
        self.QEMU_COMMAND = "qemu-system-aarch64"
        self.QEMU_IMG_COMMAND = "qemu-img"

        self.VM_DIR = vm_dir.resolve()
        self.VM_DIR.mkdir(parents=True, exist_ok=True)

        self.METADATA_FILE_NAME = "vm_metadata.json"
        self.PID_FILE_NAME = "pid"
        self.platforms = {
            "rpi3": {
                "machine": "raspi3b",
                "cpu": "cortex-a53",
                "memory": "1G",
                "smp": "4",
                "dtb": "bcm2710-rpi-3-b-plus.dtb",
                "cmdline": "rw earlyprintk loglevel=8 console=ttyAMA0,115200 dwc_otg.lpm_enable=0 root=/dev/mmcblk0p2 rootdelay=1",
            },
            "rpi4": {
                "machine": "raspi4b",
                "cpu": "cortex-a72",
                "memory": "2G",
                "smp": "4",
                "dtb": "bcm2711-rpi-4-b.dtb",
                "cmdline": "rw earlyprintk loglevel=8 console=ttyAMA0,115200 dwc_otg.lpm_enable=0 root=/dev/mmcblk1p2 rootdelay=1",
            },
        }

    def log_with_vm_id(self, level, vm_id, message):
        return log_with_vm_id(self.logger, level, vm_id, message)

    def get_platforms(self) -> list:
        return list(self.platforms.keys())

    def check_platform(self, platform: str) -> None:
        if platform not in self.platforms:
            self.logger.error(f"Invalid platform: {platform}")
            raise ValueError(
                f"Unsupported platform: {platform}. Available platforms are: {list(self.platforms.keys())}"
            )

    def get_vm_workdir_path(self, vm_id: str) -> Path:
        return self.VM_DIR / vm_id

    def get_vm_bootdir_path(self, vm_id: str) -> Path:
        return self.get_vm_workdir_path(vm_id) / "boot"

    def get_vm_pidfile_path(self, vm_id: str) -> Path:
        return self.get_vm_workdir_path(vm_id) / self.PID_FILE_NAME

    def get_vm_metadata_path(self, vm_id: str) -> Path:
        return self.get_vm_workdir_path(vm_id) / self.METADATA_FILE_NAME

    def get_vm_error_log_path(self, vm_id: str) -> Path:
        return self.get_vm_workdir_path(vm_id) / "error.log"

    def get_vm_serial_output_path(self, vm_id: str) -> Path:
        return self.get_vm_workdir_path(vm_id) / "serial.log"

    def get_vm_lockfile_path(self, vm_id: str) -> Path:
        return self.get_vm_workdir_path(vm_id) / "lockfile.lock"

    @contextmanager
    def vm_lock(self, vm_id):
        vm_workdir_path = self.get_vm_workdir_path(vm_id)
        vm_workdir_path.mkdir(parents=True, exist_ok=True)

        lockfile_path = self.get_vm_lockfile_path(vm_id)
        with portalocker.Lock(lockfile_path, "w", timeout=60):
            yield

    def register_vm(self, vm_id: str, image_path: Path, platform: str) -> str:
        with self.vm_lock(vm_id):
            pidfile_path = self.get_vm_pidfile_path(vm_id)

            if check_and_clean_vm_status(pidfile_path, vm_id):
                message = self.log_with_vm_id(INFO, vm_id, "already running.")
                return message

            metadata_path = self.get_vm_metadata_path(vm_id)
            if metadata_path.exists():
                message = self.log_with_vm_id(
                    INFO, vm_id, "already registered but not currently running."
                )
                return message

            return self._register_new_vm(vm_id, image_path, platform)

    def _register_new_vm(self, vm_id: str, image_path: Path, platform: str) -> None:
        self.check_platform(platform)

        vm_workdir_path = self.get_vm_workdir_path(vm_id)
        if vm_workdir_path.exists():
            self.log_with_vm_id(DEBUG, vm_id, "removing existing directory")
            shutil.rmtree(vm_workdir_path)
        vm_workdir_path.mkdir(parents=True)

        src_disk_image_path = image_path.resolve()
        if not src_disk_image_path.exists():
            message = self.log_with_vm_id(
                ERROR, vm_id, f"The disk image file {src_disk_image_path.name} does not exist"
            )
            raise FileNotFoundError(message)

        vm_disk_image_path = self.get_vm_workdir_path(vm_id) / src_disk_image_path.name
        self.log_with_vm_id(
            DEBUG,
            vm_id,
            f"copying image disk file from {str(src_disk_image_path)} to {str(vm_disk_image_path)}",
        )
        shutil.copy(src_disk_image_path, vm_disk_image_path)

        resize_image_to_power_of_two(vm_disk_image_path, self.QEMU_IMG_COMMAND, vm_id)

        vm_metadata = {"vm_id": vm_id, "platform": platform, "image_path": str(vm_disk_image_path)}
        temp_metadata_path = self.get_vm_metadata_path(vm_id).with_suffix(".tmp")
        with open(temp_metadata_path, "w") as file:
            json.dump(vm_metadata, file, indent=4)
            file.write("\n")
        os.rename(temp_metadata_path, self.get_vm_metadata_path(vm_id))

        message = self.log_with_vm_id(INFO, vm_id, "successfully registered.")
        return message

    def deregister_vm(self, vm_id: str):
        with self.vm_lock(vm_id):
            pidfile_path = self.get_vm_pidfile_path(vm_id)

            if pidfile_path.exists():
                terminate_vm_by_pidfile(pidfile_path)
            else:
                self.log_with_vm_id(DEBUG, vm_id, "stopped, as the pidfile was not found.")

            vm_workdir_path = self.get_vm_workdir_path(vm_id)
            if vm_workdir_path.exists():
                shutil.rmtree(vm_workdir_path)
            else:
                self.log_with_vm_id(WARN, vm_id, "work directory does not exist.")

            self.log_with_vm_id(INFO, vm_id, "deregistered sucessfully.")

    def start_vm(self, vm_id: str):
        with self.vm_lock(vm_id):
            self._start_vm(vm_id)

    def _start_vm(self, vm_id: str):
        self.log_with_vm_id(INFO, vm_id, "starting")

        vm_metadata_path = self.get_vm_metadata_path(vm_id)
        if not vm_metadata_path.exists():
            message = self.log_with_vm_id(ERROR, vm_id, "not found")
            raise FileNotFoundError(message)

        with open(vm_metadata_path, "r") as file:
            self.log_with_vm_id(DEBUG, vm_id, f"loading metadata from {str(vm_metadata_path)}")
            vm_metadata = json.load(file)

        vm_pidfile_path = self.get_vm_pidfile_path(vm_id)
        if check_and_clean_vm_status(vm_pidfile_path, vm_id):
            self.log_with_vm_id(
                INFO,
                vm_id,
                f"VM already running",
            )
            return

        vm_serial_output_path = self.get_vm_serial_output_path(vm_id)
        if vm_serial_output_path.exists():
            self.log_with_vm_id(
                DEBUG,
                vm_id,
                f"removing existing serial console log at {str(vm_serial_output_path)}",
            )
            vm_serial_output_path.unlink()

        vm_error_log_path = self.get_vm_error_log_path(vm_id)
        if vm_error_log_path.exists():
            vm_error_log_path.unlink()

        image_path = vm_metadata["image_path"]
        platform = vm_metadata["platform"]
        self.check_platform(platform)

        config = self.platforms[platform]
        kernel_path, dtb_path = self._extract_kernel_and_dtb(vm_id, image_path, config)

        # fmt: off
        qemu_args = [
            self.QEMU_COMMAND,
            '-M', config['machine'],
            '-cpu', config['cpu'],
            '-m', config['memory'],
            '-smp', config['smp'],
            '-kernel', kernel_path,
            '-dtb', dtb_path,
            '-drive', f'file={image_path},format=raw,index=0,media=disk',
            '-append', config['cmdline'],
            '-usb',
            '-device', 'usb-net,netdev=net0',
            '-netdev', 'user,id=net0',
            '-nographic',
            '-serial', f'file:{str(vm_serial_output_path)}',
        ]
        # fmt: on
        self.log_with_vm_id(DEBUG, vm_id, f"qemu command line={str(qemu_args)}")

        process = subprocess.Popen(
            qemu_args,
            stdout=open(vm_error_log_path, "w"),
            stderr=subprocess.STDOUT,
        )
        with open(vm_pidfile_path, "w") as pid_file:
            self.log_with_vm_id(DEBUG, vm_id, f"writing pidfile {str(vm_pidfile_path)}")
            pid_file.write(str(process.pid))
        self.log_with_vm_id(INFO, vm_id, f"running (PID {process.pid})")

    def _extract_kernel_and_dtb(
        self, vm_id: str, image_path: str, config: Dict[str, Any]
    ) -> Tuple[str, str]:
        """Use guestfish to extract kernel and DTB from the disk image."""
        boot_dir = self.get_vm_bootdir_path(vm_id)
        kernel_path = boot_dir / "kernel8.img"
        dtb_path = boot_dir / config["dtb"]
        if not kernel_path.exists() or not dtb_path.exists():
            boot_dir.mkdir(exist_ok=True)
            self.log_with_vm_id(DEBUG, vm_id, "extracting kernel and DTB from image")
            copy_files_from_image(image_path, [kernel_path, dtb_path])
        else:
            self.log_with_vm_id(DEBUG, vm_id, "using existing kernel and DTB")
        return str(kernel_path), str(dtb_path)

    def get_vm_serial_log(self, vm_id: str):
        """Get the current console output for a VM."""
        with self.vm_lock(vm_id):
            vm_serial_output_path = self.get_vm_serial_output_path(vm_id)
            if not vm_serial_output_path.exists():
                self.log_with_vm_id(
                    WARN, vm_id, f"serial log file {str(vm_serial_output_path)} not found"
                )
                raise FileNotFoundError(f"Serial log file for VM {vm_id} not found.")

            try:
                with open(vm_serial_output_path, "r") as logfile:
                    return logfile.read().strip()
            except Exception as e:
                self.log_with_vm_id(
                    ERROR,
                    vm_id,
                    f"unable to read serial log file {str(vm_serial_output_path)}: {e}",
                )
                raise RuntimeError(
                    f"An error occurred while retrieving the serial log for VM {vm_id}"
                )

    def get_vm_error_log(self, vm_id: str):
        """Get the startup/error log for a VM."""
        with self.vm_lock(vm_id):
            vm_error_log_path = self.get_vm_error_log_path(vm_id)
            if not vm_error_log_path.exists():
                self.log_with_vm_id(
                    WARN, vm_id, f"error log file {str(vm_error_log_path)} not found"
                )
                raise FileNotFoundError(f"Error log file for VM {vm_id} not found.")

            try:
                with open(vm_error_log_path, "r") as logfile:
                    return logfile.read().strip()
            except Exception as e:
                self.log_with_vm_id(
                    ERROR, vm_id, f"unable to read error log file {str(vm_error_log_path)}: {e}"
                )
                raise RuntimeError(
                    f"An error occurred while retrieving the error log for VM {vm_id}"
                )

    def list_vms(self) -> list:
        """List all VMs that are currently registered and return their metadata along with status."""
        vms = []
        for vm_directory in self.VM_DIR.iterdir():
            if vm_directory.is_dir():
                self.log_with_vm_id(
                    DEBUG, vm_directory.name, f"inspecting directory {str(vm_directory)}"
                )
                metadata_path = vm_directory / self.METADATA_FILE_NAME

                with self.vm_lock(vm_directory.name):
                    if metadata_path.exists() and metadata_path.is_file():
                        with metadata_path.open() as metadata_file:
                            metadata = json.load(metadata_file)
                            metadata["image_path"] = Path(metadata["image_path"]).name
                            metadata["status"], _ = self.get_vm_status_and_uptime(metadata["vm_id"])
                            vms.append(metadata)
                    else:
                        self.log_with_vm_id(DEBUG, vm_directory.name, "no metadata file found")

        self.logger.info(f"VMs: {str(vms)}")
        return vms

    def get_vm_status_and_uptime(self, vm_id: str) -> Tuple[str, int]:
        """Check the status as well as the uptime of a VM."""

        if not self.get_vm_metadata_path(vm_id).exists():
            raise FileNotFoundError(f"VM not found: {vm_id}")

        pid_path = self.get_vm_pidfile_path(vm_id)
        if pid_path.exists():
            with open(pid_path) as file:
                try:
                    pid = int(file.read().strip())
                    if is_process_running(pid):
                        return "running", get_process_uptime_seconds(pid)
                except OSError:
                    raise RuntimeError(f"Unable to determine the status of VM {vm_id}")

        return "stopped", 0

    def stop_vm(self, vm_id: str):
        with self.vm_lock(vm_id):
            pidfile_path = self.get_vm_pidfile_path(vm_id)
            if not pidfile_path.exists():
                self.log_with_vm_id(DEBUG, vm_id, f"pidfile not found, VM not running.")
                return

            terminate_vm_by_pidfile(pidfile_path, vm_id)
