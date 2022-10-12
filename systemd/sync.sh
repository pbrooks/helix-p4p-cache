#!/bin/bash
p4 clients
p4 client -o $P4CLIENT | sed "s/Created by/Created by automated build/" | p4 client -i 	
p4 client $P4CLIENT  
p4 client -o $P4CLIENT  | p4 client -i 
p4 trust -y -f
echo $P4PASSWD | p4 login
# The Actual command part
p4 -Zproxyload sync --parallel=2
