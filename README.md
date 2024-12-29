# PiVirt-Core

![PiVirt-Core Logo](assets/logo.png)

**PiVirt-Core** is a Python library and utility designed for managing and testing Raspberry Pi OS images using QEMU virtualization. It streamlines the process of working with Raspberry Pi environments in virtualized settings, making it ideal for CI/CD pipelines or local testing.

**Why PiVirt-Core?**

PiVirt-Core was created to address a significant limitation: it is impossible to pass all the necessary parameters to QEMU when using libvirt for Raspberry Pi emulation. This project solves that problem by offering a focused, customizable solution for managing Raspberry Pi OS virtual machines.

## System Requirements

This implementation has been tested with `2023-05-03-raspios-bullseye-arm64-lite`.

### Required Packages

On Ubuntu 24.10 (Oracular), install the following packages:

```bash
sudo apt install python3.12-venv guestfish qemu-system-aarch64 qemu-utils
```

## Installation

1. Clone the Repository:

```bash
git clone https://github.com/federico-sauter/pivirt-core.git
cd pivirt-core
```

2. Set Up a Virtual Environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Install Dependencies:

```bash
pip install -r requirements.txt
```

4. Install as Editable Package:

```bash
pip install -e .
```

## Using PiVirt-Core

### Preparing a Raspberry Pi OS Image with ssh acccess

Use the provided convenience script to download and prepare a Raspberry Pi OS image:

```bash
scripts/prepare_raspios_image.sh
```

This script:

- Downloads the specified version of Raspberry Pi OS.
- Configures it to re-enable the default username/password and enable SSH.

If you don't need ssh access, you can just download the RaspiOS image and use it as is.

### VM Directory Structure

When a VM is created, a directory is set up under the specified --vm-dir. This directory contains all the metadata and resources needed to manage the VM:

- Disk Image: A copy of the provided image, resized to the next power of two in size.
- Metadata: A JSON file (vm_metadata.json) storing VM configuration (e.g., platform, paths).
- Logs:
   - serial.log: Captures console output.
   - error.log: Captures startup and runtime errors.
   - Kernel and DTB Files: Extracted from the disk image using guestfish.

Example directory structure for a VM (test-vm):

```
{vm_dir}/
└── test-vm/
    ├── boot/
    │   ├── kernel8.img       # Kernel extracted from the disk image
    │   └── bcm2711-rpi-4-b.dtb  # Device tree blob
    ├── test-vm.img           # Resized disk image
    ├── vm_metadata.json      # Metadata file
    ├── serial.log            # Serial output log
    ├── error.log             # Error log
    └── lockfile.lock         # Lock file for concurrency control
```

## Testing the Implementation

Follow these steps to test PiVirt-Core using the command-line utility scripts/test_vm_manager.py.
Example Workflow

### Register a New VM:

```bash
python scripts/test_vm_manager.py --vm-dir {vm_dir} \
  --action register \
  --vm-id test-vm \
  --image-path {path_to_image} \
  --platform rpi4
```

### List Registered VMs:

```bash
python scripts/test_vm_manager.py --vm-dir {vm_dir} --action list
```

### Start the VM:

```bash
python scripts/test_vm_manager.py --vm-dir {vm_dir} --action start --vm-id test-vm
```

### Verify the VM is Running:

```bash
python scripts/test_vm_manager.py --vm-dir {vm_dir} --action list
```

### Stop the VM:

```bash
python scripts/test_vm_manager.py --vm-dir {vm_dir} --action stop --vm-id test-vm
```

### Clean Up:

```bash
python scripts/test_vm_manager.py --vm-dir {vm_dir} --action deregister --vm-id test-vm
```

## Constraints and Notes

- Supported Platforms: Currently supports Raspberry Pi 3 and Raspberry Pi 4.
- QEMU Requirement: QEMU must be installed and available in your system PATH.
- Known Limitations:
   - Works specifically with 2023-05-03-raspios-bullseye-arm64-lite and [may not work with newer versions](https://gitlab.com/qemu-project/qemu/-/issues/2351).

## License

PiVirt-Core is dual-licensed under:

- GNU Lesser General Public License v3.0 or later (LGPL-3.0-or-later) for open-source use.
This allows you to use, modify, and distribute PiVirt-Core freely in open-source and proprietary software, provided that modifications to the library itself are shared under LGPL terms.

- Commercial License for proprietary use.
For users who wish to integrate PiVirt-Core into proprietary systems without adhering to LGPL terms (e.g., keeping modifications private), a commercial license is available.

### Contact for Commercial Licensing

If you are interested in a commercial license, please contact:
Email: pivirt@pm.me

### Donations

If you find PiVirt-Core useful and would like to support its development, consider donating via PayPal. Every contribution helps us improve and maintain the project!

[![Donate via PayPal](https://www.paypalobjects.com/en_US/i/btn/btn_donate_LG.gif)](https://www.paypal.com/donate?business=pivirt@pm.me)
