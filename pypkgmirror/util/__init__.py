# Copyright 2015 Peter van Zetten
#
# This file is part of pypkgmirror.
#
# pypkgmirror is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pypkgmirror is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pypkgmirror.  If not, see <http://www.gnu.org/licenses/>.
""" Shared configuration for pypkgmirror, including global log and conf objects. """

import logging

import yaml

log = logging.getLogger('pypkgmirror')
log_handler = logging.StreamHandler()
log_handler.setFormatter(logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s'))
log.setLevel('INFO')
log.addHandler(log_handler)

conf = {}
conf_file = '/etc/pypkgmirror.yaml'  # TODO Try user-level settings

with open(conf_file, 'r') as f:
    conf.update(yaml.safe_load(f))
    log.info("Parsed configuration from %s", conf_file)
