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
""" Entry point and main function for pypkgmirror. """

import os
import multiprocessing
import subprocess

from pypkgmirror.util import conf, log


def main():
    """
    Script entry point for pypkgmirror.

    Parses the configuration and assembles a collection of subprocess calls,
    then invokes them.
    """
    from pypkgmirror.agents import DebmirrorAgent, RsyncAgent, AptlyAgent

    if 'loglevel' in conf:
        log.setLevel(conf['loglevel'])

    mirrors = []
    aptly_mirrors = []  # aptly shares a database so these should not be parallel

    for _ in conf.get('mirrors', {}).get('debmirror', []):
        mirrors.append(DebmirrorAgent(_, conf['mirrors']['debmirror'][_]))

    for _ in conf.get('mirrors', {}).get('rsync', []):
        mirrors.append(RsyncAgent(_, conf['mirrors']['rsync'][_]))

    for _ in conf.get('mirrors', {}).get('aptly', []):
        aptly_mirrors.append(AptlyAgent(_, conf['mirrors']['aptly'][_]))

    pool = multiprocessing.Pool(2)
    pool.map(start_sync, mirrors)
    pool.close()
    pool.join()

    pool = multiprocessing.Pool(1)
    pool.map(start_sync, aptly_mirrors)
    pool.close()
    pool.join()

    _subprocess_call(['hardlink', '-fpot', conf['basedir']])


def start_sync(agent):
    """
    Performs a full mirror update with the given agent. This should typically
    download any new or updated packages from a remote repository, and update
    any necessary indexes.
    """
    log.info("Syncing repository '%s' hosted at %s", agent.name, agent.host)

    outfile_path = "%s/%s.out" % (conf['logdir'], agent.name)
    errfile_path = "%s/%s.err" % (conf['logdir'], agent.name)

    with open(outfile_path, 'w') as outfile, open(errfile_path, 'w') as errfile:
        for call in agent.get_calls():
            log.debug(' '.join(call))

            if conf.get('noop'):
                continue

            _subprocess_call(call, outfile, errfile)


def _subprocess_call(call, stdout=None, stderr=None):
    """
    Trigger a subprocess execution with optional stdout/stderr redirection and
    trivial handling of missing executables.
    """
    try:
        subprocess.call(call, stdout=stdout, stderr=stderr)
    except OSError as e:
        if e.errno == os.errno.ENOENT:
            log.error("The required program %s was not found, no packages synced", call[0])
        else:
            raise


if __name__ == "__main__":
    main()
