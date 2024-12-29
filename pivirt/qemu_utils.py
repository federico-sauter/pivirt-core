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


import math
import subprocess
from logging import DEBUG
from pathlib import Path

from .logging_config import log_with_vm_id, setup_logger

logger = setup_logger(__name__)


def resize_image_to_power_of_two(image_path: Path, qemu_img_path: Path, vm_id: str):
    image_size_bytes = image_path.stat().st_size
    if (image_size_bytes & (image_size_bytes - 1)) == 0:
        # Image size is already a power of two
        size_gb = image_size_bytes // (1024**3)
    else:
        # Calculate next power of two in gigabytes
        next_power_of_two_bytes = 2 ** math.ceil(math.log2(image_size_bytes))
        size_gb = next_power_of_two_bytes // (1024**3)

    log_with_vm_id(
        logger,
        DEBUG,
        vm_id,
        f"resizing disk image from original size {str(image_size_bytes // (1024**3))}G to new size {size_gb}G",
    )
    resize_command = [qemu_img_path, "resize", "-f", "raw", str(image_path), f"{size_gb}G"]
    subprocess.run(resize_command, check=True)
    return size_gb
