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
""" Package mirror agent types. """

from abc import ABCMeta, abstractmethod
import datetime
from subprocess import check_output

from pypkgmirror.util import conf


class MirrorAgent(metaclass=ABCMeta):
    """
    Abstract parent class for all Agents.

    Defines the simple contract for Agents: to return a list of commands to be
    executed in order to update a mirror.
    """
    __slots__ = ['name', 'host', 'root', 'basedir', 'excludes', 'includes']

    def __new__(cls, *args, **kwargs):
        instance = object.__new__(cls)
        return instance

    def __init__(self, name, args, default_prefix):
        self.name = name
        self.host = args['host']
        self.root = args['root']
        self.basedir = "%s/%s" % (conf['basedir'], default_prefix) \
            if 'prefix' not in args or args['prefix'] is None \
            else "%s/%s" % (conf['basedir'], args['prefix'])
        self.excludes = args.get('excludes', [])
        self.includes = args.get('includes', [])

    @abstractmethod
    def get_calls(self):
        """
        :return: A list of commands (each itself a list) which should be
        executed in order to update the package mirror represented by this
        agent.
        """
        pass


class DebmirrorAgent(MirrorAgent):
    """
    Agent implementation for mirroring apt repositories with debmirror.
    """
    _prog = '/usr/bin/debmirror'

    def __init__(self, name, args):
        super(DebmirrorAgent, self).__init__(name, args, conf['debmirror_default_prefix'])
        self.architectures = args['architectures']
        self.distributions = args['dists']
        self.sections = args['sections']
        self.di_dists = args.get('di-dists', [])
        self.exclude_sources = args.get('exclude_sources', True)

    def get_calls(self):
        """
        :return: A debmirror command with all necessary arguments to mirror the
        configured repository.
        """
        return [
            [self._prog] + self._prog_args()
        ]

    def _prog_args(self):
        excludes = ["--exclude='%s'" % i for i in self.excludes]
        includes = ["--include='%s'" % i for i in self.includes]

        args = [
            "--arch=%s" % ','.join(self.architectures),
            "--dist=%s" % ','.join(self.distributions),
            "--section=%s" % ','.join(self.sections)
        ]

        if self.di_dists:
            args.append("--di-dist=%s" % ','.join(self.di_dists))

        if self.exclude_sources:
            args.append('--nosource')

        return self._core_args() + excludes + includes + args + [
            "--host=%s" % self.host,
            "--root=%s" % self.root,
            "%s/%s" % (self.basedir, self.name)
        ]

    @staticmethod
    def _core_args():
        return [
            '--verbose',
            '--method=http'
        ]


class RsyncAgent(MirrorAgent):
    """
    Agent implementation for mirroring arbitrary repositories with rsync.
    """
    _prog = '/usr/bin/rsync'

    def __init__(self, name, args):
        super(RsyncAgent, self).__init__(name, args, conf['rsync_default_prefix'])

    def get_calls(self):
        """
        :return: An rsync command with all necessary arguments to mirror the
        configured repository.
        """
        return [
            [self._prog] + self._prog_args()
        ]

    def _prog_args(self):
        excludes = ["--exclude=%s" % i for i in self.excludes]
        includes = ["--include=%s" % i for i in self.includes]
        return self._core_args() + excludes + includes + [
            self.host + '::' + self.root,
            "%s/%s/" % (self.basedir, self.name)
        ]

    @staticmethod
    def _core_args():
        return [
            '--verbose',
            '--archive',
            '--sparse',
            '--hard-links',
            '--partial',
            '--delete-delay',
            '--delete-excluded',
            '--delay-updates'
        ]


class AptlyAgent(MirrorAgent):
    """
    Agent implementation for mirroring apt repositories with aptly.

    It is assumed that aptly has central configuration (e.g. GPG keys, working
    directories) already.
    """
    _prog = '/usr/bin/aptly'

    def __init__(self, name, args):
        self.locations = args['locations'] if 'locations' in args else {name: args['location']}
        self.distribution = args['distribution']
        self.architectures = args['architectures']
        # self.components = args.get('components', [])  # TODO allow multi-component mirrors

        self._mirrors = check_output([self._prog, 'mirror', 'list', '-raw'], universal_newlines=True).splitlines()
        self._publishes = check_output([self._prog, 'publish', 'list', '-raw'], universal_newlines=True).splitlines()

        modargs = args.copy()
        modargs.update({'host': '<multiple>' if 'locations' in args else args['location'],
                        'root': 'N/A'})
        super(AptlyAgent, self).__init__(name, modargs, conf['aptly_default_prefix'])

    def get_calls(self):
        """
        :return: A series of commands which will update an aptly mirror (first
        creating it if necessary), create a snapshot from the mirror, then
        publish the snapshot (or switch an existing published repo).
        """
        timestamp = datetime.datetime.today().strftime('%F_%H%M')
        return self._update_mirrors(timestamp) + \
               self._publish_snapshots(timestamp) + \
               self._cleanup_snapshots(timestamp)

    def _update_mirrors(self, timestamp):
        cmds = []

        for m in self.locations.keys():
            if m not in self._mirrors:
                cmds.append(self._create_mirror(m, self.locations[m], self.architectures, self.distribution))
            cmds.append(self._update_mirror(m))
            cmds.append(self._snapshot_mirror(m, timestamp))

        return cmds

    def _publish_snapshots(self, timestamp):
        cmds = []

        snap = "{}__{}".format(self.name, timestamp)

        if len(self.locations) > 1:
            merged_snap = "{}-ALL__{}".format(self.name, timestamp)
            orig_snapshots = ["{}__{}".format(m, timestamp) for m in self.locations.keys()]
            cmds.append(self._merge_snapshots(merged_snap, orig_snapshots))
            snap = merged_snap

        if "{} {}".format(self.name, self.distribution.rstrip('/')) not in self._publishes:
            cmds.append(self._publish_snapshot(self.distribution, snap, self.name))
        else:
            cmds.append(self._switch_snapshot(self.distribution, self.name, snap))

        return cmds

    def _cleanup_snapshots(self, timestamp):
        cmds = []
        return cmds

    def _create_mirror(self, name, location, architectures, distribution):
        return [self._prog,
                'mirror', 'create', "-architectures={}".format(','.join(architectures)),
                name, location, distribution
                ]

    def _update_mirror(self, name):
        return [self._prog,
                'mirror', 'update', name
                ]

    def _snapshot_mirror(self, name, timestamp):
        return [self._prog,
                'snapshot', 'create', "{}__{}".format(name, timestamp),
                'from', 'mirror', name
                ]

    def _merge_snapshots(self, merged_snap, snapshots):
        return [self._prog,
                'snapshot', 'merge', merged_snap
                ] + snapshots

    def _publish_snapshot(self, distribution, snap, name):
        return [self._prog,
                'publish', 'snapshot', "-distribution={}".format(distribution.rstrip('/')), snap, name
                ]

    def _switch_snapshot(self, distribution, name, snap):
        return [self._prog,
                'publish', 'switch', distribution.rstrip('/'), name, snap
                ]
