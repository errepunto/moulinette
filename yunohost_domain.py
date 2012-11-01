# -*- coding: utf-8 -*-

import os
import sys
import datetime
import requests
from yunohost import YunoHostError, win_msg, colorize, validate, get_required_args

def domain_list(args, connections):
    """
    List YunoHost domains

    Keyword argument:
        args -- Dictionnary of values (can be empty)
        connections -- LDAP connection

    Returns:
        Dict
    """
    yldap = connections['ldap']
    result_dict = {}
    if args['offset']: offset = int(args['offset'])
    else: offset = 0
    if args['limit']: limit = int(args['limit'])
    else: limit = 1000
    if args['filter']: filter = args['filter']
    else: filter = 'virtualdomain=*'

    result = yldap.search('ou=domains,dc=yunohost,dc=org', filter, attrs=['virtualdomain'])
    
    if result and len(result) > (0 + offset) and limit > 0:
        i = 0 + offset
        for domain in result[i:]:
            if i < limit:
                result_dict[str(i)] = domain['virtualdomain']
                i += 1
    else:
        raise YunoHostError(167, _("No domain found"))

    return result_dict


def domain_add(args, connections):
    """
    Add one or more domains

    Keyword argument:
        args -- Dictionnary of values (can be empty)
        connections -- LDAP connection

    Returns:
        Dict
    """
    yldap = connections['ldap']
    attr_dict = { 'objectClass' : ['mailDomain', 'top'] }
    request_ip = requests.get('http://ip.yunohost.org')
    ip = str(request_ip.text)
    now = datetime.datetime.now()
    timestamp = str(now.year) + str(now.month) + str(now.day) 
    result = []

    args = get_required_args(args, { 'domain' : _('New domain') })
    if not isinstance(args['domain'], list):
        args['domain'] = [ args['domain'] ]
    
    for domain in args['domain']: 
        validate({ domain : r'^([a-zA-Z0-9]{1}([a-zA-Z0-9\-]*[a-zA-Z0-9])*)(\.[a-zA-Z0-9]{1}([a-zA-Z0-9\-]*[a-zA-Z0-9])*)*(\.[a-zA-Z]{1}([a-zA-Z0-9\-]*[a-zA-Z0-9])*)$' })
        yldap.validate_uniqueness({ 'virtualdomain' : domain })
        attr_dict['virtualdomain'] = domain

        try:
            with open('/var/lib/bind/'+ domain +'.zone') as f: pass
        except IOError as e:
            zone_lines = [
             '$TTL    38400',
             domain +'.      IN SOA ns.'+ domain +'. root.'+ domain +'. '+ timestamp +' 10800 3600 604800 38400',
             domain +'.      IN NS  ns.'+ domain +'.',
             domain +'.      IN A   '+ ip,
             domain +'.      IN MX  5 mail.'+ domain +'.',
             domain +'.      IN TXT "v=spf1 a mx a:'+ domain +' ?all"',
             'mail.'+ domain +'. IN A   '+ ip,
             'ns.'+ domain +'.   IN A   '+ ip,
             'root.'+ domain +'. IN A   '+ ip
            ]
            with open('/var/lib/bind/' + domain + '.zone', 'w') as zone:
                for line in zone_lines:
                    zone.write(line + '\n')
        else:
            raise YunoHostError(17, _("Zone file already exists for ") + domain)

        if yldap.add('virtualdomain=' + domain + ',ou=domains', attr_dict):
            result.append(domain)
            continue
        else:
            raise YunoHostError(169, _("An error occured during domain creation"))

    win_msg(_("Domain(s) successfully created"))

    return { 'Domains' : result } 


def domain_remove(args, connections):
    """
    Remove domain from LDAP

    Keyword argument:
        args -- Dictionnary of values
        connections -- LDAP connection

    Returns:
        Dict
    """
    yldap = connections['ldap']
    result = []

    args = get_required_args(args, { 'domain' : _('Domain to remove') })
    if not isinstance(args['domain'], list):
        args['domain'] = [ args['domain'] ]

    for domain in args['domain']:
        validate({ domain : r'^([a-zA-Z0-9]{1}([a-zA-Z0-9\-]*[a-zA-Z0-9])*)(\.[a-zA-Z0-9]{1}([a-zA-Z0-9\-]*[a-zA-Z0-9])*)*(\.[a-zA-Z]{1}([a-zA-Z0-9\-]*[a-zA-Z0-9])*)$' })
        if yldap.remove('virtualdomain=' + domain + ',ou=domains'):
            try:
                os.remove('/var/lib/bind/'+ domain +'.zone')
            except:
                pass
            result.append(domain)
            continue
        else:
            raise YunoHostError(169, _("An error occured during domain deletion"))

    win_msg(_("Domain(s) successfully deleted"))
    return { 'Domains' : result }