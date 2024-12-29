#!/bin/bash -e
#
# Downloads and prepares the raspios image by re-enabling the
# default pi user and enabling ssh on startup.
#

USERNAME="pi"
PASSWORD="raspberry"
DOWNLOAD_URL="https://downloads.raspberrypi.org/raspios_lite_arm64/images/raspios_lite_arm64-2023-05-03/2023-05-03-raspios-bullseye-arm64-lite.img.xz"

PROJECT_VAR="$(realpath "$(dirname "${BASH_SOURCE[0]}")/..")/var"
PROJECT_TMP="${PROJECT_VAR}/tmp"
PROJECT_IMAGE_DIR="${PROJECT_VAR}/images"
PROJECT_MOUNT_DIR="${PROJECT_VAR}/mnt"
PROJECT_BOOT_MOUNT_DIR="${PROJECT_VAR}/boot"

### Entry point ###
cleanup()
{
	echo -e "\e[32m${0}: Cleaning up...\e[0m"
	sudo umount "${PROJECT_MOUNT_DIR}" || :
	sudo umount "${PROJECT_BOOT_MOUNT_DIR}" || :
	sudo kpartx -d -v "${raspios_image}" || :
	sudo losetup -d "${free_loopdev}" 2>/dev/null || :
}

trap 'cleanup' EXIT

archive="${PROJECT_TMP}/$( basename ${DOWNLOAD_URL} )"
uncompressed_archive="${archive%.xz}"
raspios_image="${PROJECT_IMAGE_DIR}/$( basename ${uncompressed_archive} )"

# Download and extract the image
echo -e "\e[32m${0}: Downloading...\e[0m"

mkdir -p ${PROJECT_TMP}
wget -P ${PROJECT_TMP} ${DOWNLOAD_URL}
echo -e "\e[32m${0}: Decompressing...\e[0m"
xz --decompress "$archive"

mkdir -p "${PROJECT_IMAGE_DIR}"
mv "$uncompressed_archive" "$raspios_image"

# Make the image of the right size for QEmu
qemu-img resize -f raw "${raspios_image}" 4G

# Mount the image
echo -e "\e[32m${0}: Mounting...\e[0m"
free_loopdev="$(sudo losetup -f)"
sudo kpartx -a -v "${raspios_image}"
loop_mapper=/dev/mapper/$(basename "${free_loopdev}")

mkdir -p ${PROJECT_MOUNT_DIR}
sudo mount "${loop_mapper}p2" "${PROJECT_MOUNT_DIR}"

# Make sure that ssh is enabled
mkdir -p $PROJECT_BOOT_MOUNT_DIR
sudo mount "${loop_mapper}p1" "${PROJECT_BOOT_MOUNT_DIR}"

echo -e "\e[32m${0}: Enabling ssh...\e[0m"
sudo touch ${PROJECT_BOOT_MOUNT_DIR}/ssh

# pre-generate ssh keys, as the random device doesn't work in the Docker container
echo -e "\e[32m${0}: Generating ssh keys...\e[0m"
mkdir -p $PROJECT_TMP/etc/ssh
ssh-keygen -A -f $PROJECT_TMP
sudo cp $PROJECT_TMP/etc/ssh/ssh_host_* ${PROJECT_MOUNT_DIR}/etc/ssh/
sudo chmod 600 ${PROJECT_MOUNT_DIR}/etc/ssh/ssh_host_*
sudo chown root:root ${PROJECT_MOUNT_DIR}/etc/ssh/ssh_host_*
rm -rf  $PROJECT_TMP/etc

# Disable the key re-generation service, as it may not work in the Docker container
sudo rm -f ${PROJECT_MOUNT_DIR}/etc/systemd/system/multi-user.target.wants/regenerate_ssh_host_keys.service

# Setup the new user
echo -e "\e[32m${0}: Setting up user ${USERNAME}...\e[0m"
NEW_HASH="$( openssl passwd -6 "${PASSWORD}" )"
TARGET_SHADOW_FILE="${PROJECT_MOUNT_DIR}/etc/shadow"
TMP_SHADOW_FILE="${PROJECT_TMP}/shadow"

sudo cp "${TARGET_SHADOW_FILE}" "${TMP_SHADOW_FILE}"
sudo chmod 666 "${TMP_SHADOW_FILE}"
awk -v user="$USERNAME" -v hash="$NEW_HASH" -F':' 'BEGIN{OFS=FS} $1==user {$2=hash} 1' "${TMP_SHADOW_FILE}" >"${TMP_SHADOW_FILE}.edited"
sudo cp "${TMP_SHADOW_FILE}.edited" "${TARGET_SHADOW_FILE}"
sudo chmod 640 "${TARGET_SHADOW_FILE}"
sudo rm "${TMP_SHADOW_FILE}"*

echo -e "\e[32m${0}: DONE\e[0m"
