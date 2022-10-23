import os
import subprocess
import sys

from P4 import P4


def __main__():
    # REQUIRED: Ability to logon with password
    # echo $P4PASSWD | p4 login

    # REQUIRED: If SSL, then trust the server
    # p4 trust -y -f

    # P4Python wraps client creation elegantly
    # (Without the use of unix pipes being required)

    # IMPROVE: The user should be able to suggest the P4CLIENT name
    P4CLIENT = "sync"

    # IMPROVE: No args from the user being passed here
    p4 = P4().connect()
    p4_client = p4.fetch_client(P4CLIENT)

    # FAULT: P4_Client ignores inherited P4ROOT from environ
    p4_client._root = os.environ.get("P4ROOT")
    p4.save_client(p4_client)

    # P4Python doesn't understand sync
    os.environ['P4CLIENT'] = P4CLIENT
    commands = (
            ('p4', '-Zproxyload', 'sync'),
            )
    try:
        for x in commands:
            cmd = [*x, *sys.argv[1:]]
            # XXX: Inject env vars here
            subprocess.run(cmd, check=True, env=os.environ)
    except subprocess.CalledProcessError as ex:
        sys.exit(ex.returncode)

#__main__()
