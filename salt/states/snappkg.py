# -*- coding: utf-8 -*-
from salt.exceptions import CommandExecutionError


def installed(name, confinement="jailmode"):
    '''
    Ensure that the package is installed

    :param str name:
        The name of the package to be installed.

    :param str confinement:
        The level of confinement for the snap package. Default is jailmode, some applications will require classic mode.
        Options are jailmode, classic and devmode
    '''

    ret = {'name': name, 'result': True, 'changes': {}, 'comment': ''}

    if __salt__['snappkg.version'](name):
        # We don't need to install it, because it's already there.
        return ret
    else:
        try:
            changes = {'installed': __salt__['snappkg.install'](name, confinement=confinement)}
        except CommandExecutionError as exc:
            ret['result'] = False
            if exc.info:
                # Get information for state return from the exception.
                ret['changes'] = exc.info.get('changes', {})
                ret['comment'] = exc.strerror_without_changes
            else:
                ret['changes'] = {}
                ret['comment'] = ('An error was encountered while installing '
                                  'package(s): {0}'.format(exc))
            return ret
        ret['changes'].update(changes)
    return ret


def removed(name):
    '''
    Ensure that the package is removed

    :param str name:
        The name of the package to be removed.
    '''

    ret = {'name': name, 'result': True, 'changes': {}, 'comment': ''}

    if not __salt__['snappkg.version'](name):
        # We don't need to remove it, because it's already absent.
        return ret
    else:
        try:
            changes = {'installed': __salt__['snappkg.remove'](name)}
        except CommandExecutionError as exc:
            ret['result'] = False
            if exc.info:
                # Get information for state return from the exception.
                ret['changes'] = exc.info.get('changes', {})
                ret['comment'] = exc.strerror_without_changes
            else:
                ret['changes'] = {}
                ret['comment'] = ('An error was encountered while removing '
                                  'package(s): {0}'.format(exc))
            return ret
        ret['changes'].update(changes)
    return ret
