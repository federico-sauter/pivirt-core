#!/usr/bin/env python3
#
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

import argparse
from pathlib import Path

from pivirt import VMManager


def main():
    parser = argparse.ArgumentParser(description="Test program for VMManager.")
    parser.add_argument("--vm-dir", type=str, required=True, help="Path to VM directory.")
    parser.add_argument(
        "--action",
        type=str,
        required=True,
        choices=["register", "deregister", "start", "stop", "list"],
        help="Action to perform: register, start, stop, or list.",
    )
    parser.add_argument("--vm-id", type=str, help="ID of the VM (required for start and stop).")
    parser.add_argument(
        "--image-path", type=str, help="Path to the disk image (required for register)."
    )
    parser.add_argument("--platform", type=str, help="Platform type (required for register).")

    args = parser.parse_args()

    vm_manager = VMManager(vm_dir=Path(args.vm_dir))

    try:
        if args.action == "register":
            if not args.image_path or not args.platform:
                print("Error: --image-path and --platform are required for register action.")
                return
            vm_id = args.vm_id if args.vm_id else "test-vm"
            print(
                vm_manager.register_vm(
                    vm_id=vm_id, image_path=Path(args.image_path), platform=args.platform
                )
            )

        elif args.action == "deregister":
            if not args.vm_id:
                print("Error: --vm-id is required for deregister action.")
                return
            vm_manager.deregister_vm(args.vm_id)
            print(f"VM {args.vm_id} deregistered.")

        elif args.action == "start":
            if not args.vm_id:
                print("Error: --vm-id is required for start action.")
                return
            vm_manager.start_vm(args.vm_id)
            print(f"VM {args.vm_id} started.")

        elif args.action == "stop":
            if not args.vm_id:
                print("Error: --vm-id is required for stop action.")
                return
            vm_manager.stop_vm(args.vm_id)
            print(f"VM {args.vm_id} stopped.")

        elif args.action == "list":
            vms = vm_manager.list_vms()
            print("Registered VMs:")
            for vm in vms:
                print(f"ID: {vm['vm_id']}, Status: {vm['status']}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
