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

import subprocess
from pathlib import Path
from typing import List, Union


def copy_files_from_image(image_path: Union[str, Path], target_paths: List[Path]) -> None:
    """
    Executes guestfish commands to add an image, mount it, copy out specified files, and then clean up.

    Args:
        image_path (Path): Path to the disk image to be modified.
        target_paths (List[Path]): List of target Paths on the host, where each Path's filename is used
                                   as the source filename in the guest to be copied out to the specified target Path.
    Raises:
        subprocess.CalledProcessError If guestfish exits with a nun-zero status.
    """
    copy_out_commands = generate_copy_out_commands(target_paths)

    process = subprocess.Popen(["sudo", "guestfish"], stdin=subprocess.PIPE, text=True)
    _, stderr = process.communicate(
        f"""
add {str(image_path)}
run
mount /dev/sda1 /
{copy_out_commands}
umount-all
exit
"""
    )
    if process.returncode != 0:
        raise subprocess.CalledProcessError(
            f"Error: guestfish failed with exit code {process.returncode}: {stderr}"
        )


def generate_copy_out_commands(paths: List[Path]) -> str:
    """Generates 'copy-out' commands for guestfish based on the given list of target Paths."""
    commands = []
    for path in paths:
        commands.append(f"copy-out /{path.name} {path.parent}")
    return "\n".join(commands)


def list_boot_partition(image_path: Union[str, Path]):
    """List the contents of the boot partition."""
    commands = f"""
add {str(image_path)}
run
mount /dev/sda1 /
ls /
umount-all
exit
"""
    process = subprocess.Popen(
        ["sudo", "guestfish"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    output, _ = process.communicate(commands)
    return output
