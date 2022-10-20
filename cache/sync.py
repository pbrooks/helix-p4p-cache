import os
import subprocess
import sys


def __main__():
    commands = (
            ('p4', '-Zproxyload', 'sync'),
            )

    from P4 import P4

    p4 = P4().connect()
    p4_client = p4.fetch_client()
    p4.save_client(p4_client)

    try:
        for x in commands:
            cmd = [*x, *sys.argv[1:]]
            subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as ex:
        sys.exit(ex.returncode)

#__main__()
'''
p4 clients
p4 client -o $P4CLIENT | sed "s/Created by/Created by automated build/" | p4 client -i 	
p4 client $P4CLIENT  
p4 client -o $P4CLIENT  | p4 client -i 
p4 trust -y -f
echo $P4PASSWD | p4 login
# The Actual command part
p4 -Zproxyload sync --parallel=2
'''
