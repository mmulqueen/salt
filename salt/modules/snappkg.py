# -*- coding: utf-8 -*-
'''
Snap packages for Linux systems

.. important::
    Salt will not use this as a virtual module for pkg.
'''
from __future__ import absolute_import, print_function, unicode_literals

# Import python libs
import copy
import logging
import re

# Import salt libs
import salt.utils.data
import salt.utils.functools
import salt.utils.json
import salt.utils.path
import salt.utils.pkg
import salt.utils.versions
import salt.utils.systemd
from salt.exceptions import CommandExecutionError

# Import third party libs
from salt.ext import six

log = logging.getLogger(__name__)

# # Define the module's virtual name
# __virtualname__ = 'pkg'
#
#
# def __virtual__():
#     '''
#     Confine this module to systems with snap installed.
#     '''
#
#     if salt.utils.path.which('snap'):
#         return __virtualname__
#     return (False, 'The snap module could not be loaded: snap not found')


def list_pkgs(versions_as_list=False, **kwargs):
    '''
    List the packages currently installed in a dict::

        {'<package_name>': '<version>'}

    CLI Example:

    .. code-block:: bash

        salt '*' snappkg.list_pkgs
    '''
    versions_as_list = salt.utils.data.is_true(versions_as_list)
    # not yet implemented or not applicable
    if any([salt.utils.data.is_true(kwargs.get(x))
            for x in ('removed', 'purge_desired')]):
        return {}

    if 'snappkg.list_pkgs' in __context__:
        if versions_as_list:
            return __context__['snappkg.list_pkgs']
        else:
            ret = copy.deepcopy(__context__['snappkg.list_pkgs'])
            __salt__['pkg_resource.stringify'](ret)
            return ret

    cmd = ['snap', 'list', '--color=never', '--unicode=never']
    ret = {}

    out = __salt__['cmd.run'](cmd, output_loglevel='trace', python_shell=False)
    for i, line in enumerate(salt.utils.itertools.split(out, '\n')):
        if not i or not line:
            # Skip the first line (header) and any blank lines)
            continue
        try:
            # Returned as a human readable table, so let's compress the whitespace for easier splitting.
            line = re.sub(r"\s+", " ", line)
            name, version_num = line.split(" ")[0:2]
        except ValueError:
            log.error('Problem parsing snap list: Unexpected formatting in '
                      'line: \'%s\'', line)
        else:
            __salt__['pkg_resource.add_pkg'](ret, name, version_num)

    __salt__['pkg_resource.sort_pkglist'](ret)
    __context__['snappkg.list_pkgs'] = copy.deepcopy(ret)
    if not versions_as_list:
        __salt__['pkg_resource.stringify'](ret)
    return ret


def _resource_version(*names, **kwargs):
    '''
    Common interface for obtaining the version of installed packages.
    CLI Example:
    .. code-block:: bash
        salt '*' pkg_resource.version vim
        salt '*' pkg_resource.version foo bar baz
        salt '*' pkg_resource.version 'python*'


    This has been modified to use a separate dictionary to (snappkg.list_pkgs not pkg.list_pkgs), otherwise the same
    as pkg_resource.version
    '''
    ret = {}
    versions_as_list = \
        salt.utils.data.is_true(kwargs.pop('versions_as_list', False))
    pkg_glob = False
    if len(names) != 0:
        pkgs = __salt__['snappkg.list_pkgs'](versions_as_list=True, **kwargs)
        for name in names:
            if '*' in name:
                pkg_glob = True
                for match in fnmatch.filter(pkgs, name):
                    ret[match] = pkgs.get(match, [])
            else:
                ret[name] = pkgs.get(name, [])
    if not versions_as_list:
        __salt__['pkg_resource.stringify'](ret)
    # Return a string if no globbing is used, and there is one item in the
    # return dict
    if len(ret) == 1 and not pkg_glob:
        try:
            return next(six.itervalues(ret))
        except StopIteration:
            return ''
    return ret


def _clear_versions():
    """Clear the versions stored in the context so we can get new version info."""
    __context__.pop('snappkg.list_pkgs', None)


def version(*names, **kwargs):
    '''
    Returns a string representing the package version or an empty string if not
    installed. If more than one package name is specified, a dict of
    name/version pairs is returned.

    CLI Example:

    .. code-block:: bash

        salt '*' pkg.version <package name>
        salt '*' pkg.version <package1> <package2> <package3>
    '''
    return _resource_version(*names, **kwargs)


def install(name,
            confinement="jailmode",
            **kwargs):
    '''
    name
        The name of the package to be installed.
        
        CLI Example:
        .. code-block:: bash
            salt '*' snappkg.install <package name>

    confinement
        The level of confinement for the snap package. Default is jailmode, some applications will require classic mode.
        Options are jailmode, classic and devmode
    '''
    if name.startswith("-"):
        raise CommandExecutionError("Invalid snap package name ")

    if confinement not in ["jailmode", "classic", "devmode"]:
        raise CommandExecutionError("Invalid confinement mode. Options are jailmode, classic and devmode")

    cmd = []

    if salt.utils.systemd.has_scope(__context__) \
            and __salt__['config.get']('systemd.scope', True):
        cmd.extend(['systemd-run', '--scope'])

    cmd.extend(['snap', 'install', '--color=never', '--unicode=never', "--{}".format(confinement), name])

    old_versions = __salt__['snappkg.list_pkgs']()

    out = __salt__['cmd.run_all'](cmd, output_loglevel='trace', python_shell=False)

    if out['retcode'] != 0 and out['stderr']:
        errors = [out['stderr']]
    else:
        errors = []

    _clear_versions()
    new_versions = __salt__['snappkg.list_pkgs']()

    ret = salt.utils.data.compare_dicts(old_versions, new_versions)

    if errors:
        raise CommandExecutionError(
            'Problem encountered installing package(s)',
            info={'errors': errors, 'changes': ret}
        )

    return ret


def remove(name,
            confinement="jailmode",
            **kwargs):
    '''
    name
        The name of the package to be removed.

        CLI Example:
        .. code-block:: bash
            salt '*' snappkg.remove <package name>
    '''
    if name.startswith("-"):
        raise CommandExecutionError("Invalid snap package name ")

    cmd = []
    if salt.utils.systemd.has_scope(__context__) \
        and __salt__['config.get']('systemd.scope', True):
        cmd.extend(['systemd-run', '--scope'])
    cmd.extend(['snap', 'remove', name])

    old_versions = __salt__['snappkg.list_pkgs']()
    out = __salt__['cmd.run_all'](cmd, output_loglevel='trace', python_shell=False)

    if out['retcode'] != 0 and out['stderr']:
        errors = [out['stderr']]
    else:
        errors = []

    _clear_versions()
    new_versions = __salt__['snappkg.list_pkgs']()

    ret = salt.utils.data.compare_dicts(old_versions, new_versions)

    if errors:
        raise CommandExecutionError(
            'Problem encountered removing package(s)',
            info={'errors': errors, 'changes': ret}
        )

    return ret
