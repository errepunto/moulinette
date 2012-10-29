# -*- coding: utf-8 -*-

import os
import sys
import yaml
import re
import getpass
from yunohost import YunoHostError, validate, colorize, get_required_args


def tools_ldapinit(args, connections): 
    """
    Initialize YunoHost LDAP scheme
    
    Keyword arguments:
        args
        connections
    
    Returns: 
        dict

    """
    yldap = connections['ldap']

    with open('ldap_scheme.yml') as f: 
        ldap_map = yaml.load(f)

    for rdn, attr_dict in ldap_map['parents'].items():
        yldap.add(rdn, attr_dict)

    for rdn, attr_dict in ldap_map['childs'].items():
        yldap.add(rdn, attr_dict)

    admin_dict = {
        'cn': 'admin',
        'uid': 'admin',
        'description': 'LDAP Administrator',
        'gidNumber': '1007',
        'uidNumber': '1007',
        'homeDirectory': '/home/admin',
        'loginShell': '/bin/bash',
        'objectClass': ['organizationalRole', 'posixAccount', 'simpleSecurityObject']
    }

    yldap.update('cn=admin', admin_dict)

    win_msg(_("LDAP has been successfully initialized"))


def tools_adminpw(args): 
    """
    Change admin password
    
    Keyword arguments:
        args
    
    Returns: 
        dict

    """
    if not 'old' in args:
        args['old'] = getpass.getpass(colorize('Actual admin password: ', 'cyan'))
    
    if not 'new' in args:
        args['new'] = getpass.getpass(colorize('New admin password: ', 'cyan'))
        pwd2 = getpass.getpass(colorize('Retype new password: ', 'cyan'))
        if args['new'] != pwd2:
            raise YunoHostError(22, _("Passwords doesn't match"))

    # Validate password length
    if len(args['new']) < 4:
        raise YunoHostError(22, _("Password is too short"))

    result = os.system('ldappasswd -h localhost -D cn=admin,dc=yunohost,dc=org -w "'+ args['old'] +'" -a "'+ args['old'] +'" -s "' + args['new'] + '"')

    if result == 0:
        win_msg(_("Admin password has been changed"))
    else:
        raise YunoHostError(22, _("Invalid password"))


def tools_maindomain(args): 
    """
    Change admin password
    
    Keyword arguments:
        args
    
    Returns: 
        dict

    """
    args = get_required_args(args, {'new_domain' : _('New main domain name')})

    if not args['old_domain']:
        with open('/usr/share/yunohost/yunohost-config/others/current_host', 'r') as f:
            args['old_domain'] = f.readline().rstrip()

    validate({ 
        args['new_domain'] : r'^([a-zA-Z0-9]{1}([a-zA-Z0-9\-]*[a-zA-Z0-9])*)(\.[a-zA-Z0-9]{1}([a-zA-Z0-9\-]*[a-zA-Z0-9])*)*(\.[a-zA-Z]{1}([a-zA-Z0-9\-]*[a-zA-Z0-9])*)$',
        args['old_domain'] : r'^([a-zA-Z0-9]{1}([a-zA-Z0-9\-]*[a-zA-Z0-9])*)(\.[a-zA-Z0-9]{1}([a-zA-Z0-9\-]*[a-zA-Z0-9])*)*(\.[a-zA-Z]{1}([a-zA-Z0-9\-]*[a-zA-Z0-9])*)$' 
    })

    config_files = [
        '/etc/postfix/main.cf',
        '/etc/dovecot/dovecot.conf',
        '/etc/mailname',
        '/etc/ejabberd/ejabberd.cfg',
        '/etc/lemonldap-ng/lemonldap-ng.ini',
        '/etc/hosts',
    ]

    config_dir = [
        '/var/lib/lemonldap-ng/conf',
        '/etc/apache2/sites-available',
    ]

    for dir in config_dir:
        for file in os.listdir(dir):
            config_files.append(dir + '/' + file)

    for file in config_files:
        with open(file, "r") as sources:
            lines = sources.readlines()
        with open(file, "w") as sources:
            for line in lines:
                sources.write(re.sub(r''+ args['old_domain'] +'', args['new_domain'], line))

    os.system('/etc/init.d/hostname.sh')
    
    # Regenerate certificate
    tmp = '/usr/share/yunohost/yunohost-config'
    a = os.system('echo "01" > '+ tmp +'/ssl/yunoCA/serial')
    b = os.system('rm '+ tmp +'/ssl/yunoCA/index.txt')
    c = os.system('touch '+ tmp +'/ssl/yunoCA/index.txt')
    d = os.system('sed -i "s/' + args['old_domain'] + '/' + args['new_domain'] + '/g" '+ tmp +'/ssl/yunoCA/openssl.cnf')
    e = os.system('openssl req -x509 -new -config '+ tmp +'/ssl/yunoCA/openssl.cnf -days 3650 -out '+ tmp +'/ssl/yunoCA/ca/cacert.pem -keyout '+ tmp +'/ssl/yunoCA/ca/cakey.pem -nodes -batch')
    f = os.system('openssl req -new -config '+ tmp +'/ssl/yunoCA/openssl.cnf -days 730 -out '+ tmp +'/ssl/yunoCA/certs/yunohost_csr.pem -keyout '+ tmp +'/ssl/yunoCA/certs/yunohost_key.pem -nodes -batch')
    g = os.system('openssl ca -config '+ tmp +'/ssl/yunoCA/openssl.cnf -days 730 -in '+ tmp +'/ssl/yunoCA/certs/yunohost_csr.pem -out '+ tmp +'/ssl/yunoCA/certs/yunohost_crt.pem -batch')
    h = os.system('cp '+ tmp +'/ssl/yunoCA/ca/cacert.pem /etc/ssl/certs/ca-yunohost_crt.pem')
    i = os.system('cp '+ tmp +'/ssl/yunoCA/certs/yunohost_key.pem /etc/ssl/private/')
    j = os.system('cp '+ tmp +'/ssl/yunoCA/newcerts/01.pem /etc/ssl/certs/yunohost_crt.pem')
    k = os.system('cp '+ tmp +'/ssl/yunoCA/newcerts/01.pem /etc/ejabberd/ejabberd.pem')
    l = os.system('echo '+ args['new_domain'] +' > /usr/share/yunohost/yunohost-config/others/current_host')

    # Restart services
    m = os.system('/etc/init.d/apache2 restart')
    n = os.system('/etc/init.d/postfix restart')
    o = os.system('/etc/init.d/ejabberd restart')

    if a == b == c == d == e == f == g == h == i == j == k == l == m == n == o:
        win_msg(_("YunoHost main domain has been successfully changed"))
    else:
        raise YunoHostError(17, _("There were a problem during domain changing"))


def tools_postinstall(args, connections):
    """
    Post-install configuration
    
    Keyword arguments:
        args
        connection
    
    Returns: 
        dict

    """
    try:
        with open('/usr/share/yunohost/yunohost-config/others/installed') as f: pass
    except IOError:
        print('Installing YunoHost')
    else:
        raise YunoHostError(17, _("YunoHost is already installed"))

    args = get_required_args(args, {'domain' : _('Main domain name'), 'password' : _('New admin password') }, True)

    # New domain config
    tools_maindomain({ 'old_domain' : 'yunohost.org', 'new_domain' : args['domain']})

    # Initialize YunoHost LDAP base
    tools_ldapinit(args, connections)

    # Change LDAP admin password
    tools_adminpw({ 'old' : 'yunohost', 'new' : args['password']})

    os.system('touch /usr/share/yunohost/yunohost-config/others/installed')
    
    win_msg(_("YunoHost has been successfully configured"))
