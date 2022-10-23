import logging as log
import os
import subprocess
import sys

import P4


def init_client(P4CLIENT):
    # REQUIRED: Ability to logon with password
    # echo $P4PASSWD | p4 login

    # REQUIRED: If SSL, then trust the server
    # p4 trust -y -f

    # P4Python wraps client creation elegantly
    # (Without the use of unix pipes being required)

    # IMPROVE: No args from the user being passed here
    p4 = P4.P4().connect()
    p4_client = p4.fetch_client(P4CLIENT)

    # FAULT: P4_Client ignores inherited P4ROOT from environ
    p4_client._root = os.environ.get("P4ROOT")
    p4.save_client(p4_client)


def sync(P4CLIENT):
    # P4Python doesn't understand sync
    os.environ['P4CLIENT'] = P4CLIENT
    commands = (
            ('p4', '-Zproxyload', 'sync'),
            )
    for x in commands:
        cmd = [*x, *sys.argv[1:]]
        # XXX: Inject env vars here
        subprocess.run(cmd, check=True, env=os.environ)


def __main__():
    log.basicConfig(level=log.INFO, format='%(message)s')
    '''
    , handlers=(
            log.StreamHandler(sys.stdout),
            log.StreamHandler(sys.stderr),
    ))
    '''

    # IMPROVE: The user should be able to suggest the P4CLIENT name
    P4CLIENT = "sync"

    try:
        init_client(P4CLIENT)
        sync(P4CLIENT)
    except P4.P4Exception as ex:
        log.error(ex.value)
        sys.exit(1)
    except subprocess.CalledProcessError as ex:
        sys.exit(ex.returncode)


# __main__()
