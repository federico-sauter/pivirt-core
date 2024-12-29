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


import logging


def setup_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


def log_with_vm_id(logger, level, vm_id, message):
    message = f"[{vm_id}] {message}"
    logger.log(level, message)
    return message
