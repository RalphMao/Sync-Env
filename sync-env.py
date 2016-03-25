#!/usr/bin/env python2
__author__ = "Huizi Mao"
__email__ = "ralphmao95@gmail.com"

import os, sys
import logging
import filecmp
import log

def log_init():
    # logging.basicConfig()
    logger = logging.getLogger('sync-env')
    level = logging.DEBUG
    logger.setLevel(level)
    stream_handler = log.ColorizingStreamHandler()
    logger.addHandler(stream_handler)
    formatter = logging.Formatter("[%(name)s] %(message)s")
    stream_handler.setFormatter(formatter)
    logger.info('Running command in synchronized environment')
    return logger

def parse_rc(logger):
    params = {}
    if os.path.isfile('%s/.syncrc'%os.environ['HOME']):
        content = open('%s/.syncrc'%os.environ['HOME'])
        for lid, line in enumerate(content):
            new_line = line.split('#')[0].strip()
            if len(new_line) == 0:
                continue
            try:
                key, cont = new_line.split()
            except Exception as e:
                logger.error('Unknown error occur in ~/.syncrc, line %d: %s'%(lid, line))

            key = key.strip().lower()
            cont = cont.strip()
            if key in params:
                params[key] = params[key].append(cont) if type(params[key]) is list else [params[key], cont]
            else:
                params[key] = cont

    if 'user' not in params or 'host' not in params:
        logger.error('<user> and <host> required in the config file ~/.syncrc')

    return params

def choose_tmp_filename(filename):
    idt = 0
    dir_name = os.path.dirname(filename)
    base_name = os.path.basename(filename)

    while os.path.isfile(os.path.join(dir_name, '.'+base_name+str(idt))):
        idt += 1

    return os.path.join(dir_name, '.'+base_name+str(idt))

def check_suffix(base_name, exclude_suffix):
    if type(exclude_suffix) is not list:
        exclude_suffix = [exclude_suffix]
    return max(map(lambda x:base_name.endswith('.' + x), exclude_suffix))

def check_exclude_command(command, exclude_command):
    if type(exclude_command) is not list:
        exclude_command= [exclude_command]
    return max(map(lambda x:command == x, exclude_command))

def handle_args(args, params, logger):

    time_limit = float(params.get('time_limit', '1'))
    max_file_size = float(params.get('max_size', 1e4))
    file_diff_thresh = float(params.get('size_diff_thresh', 1e3))
    exclude_suffix = params.get('exclude_suffix', 'bin')
    exclude_command = params.get('exclude_command', 'git')
    bak_dir = params.get('bak_dir', '/tmp/sync-env')

    if not os.path.isdir(bak_dir):
        os.mkdir(bak_dir)

    if len(args) > 0 and check_exclude_command(args[0], exclude_command):
        return
    for arg in args:
        if not arg.startswith('-') and os.path.isfile(arg): # Ignore flag and non-file args
            logger.debug('%s is a file, processing'%arg)
            file_size = os.stat(arg).st_size
            if file_size > max_file_size:
                logger.debug('File size exceeds limit, ignored')
                continue

            base_name = os.path.basename(arg)
            if check_suffix(base_name, exclude_suffix):
                logger.debug('suffix excluded')
                continue

            abs_name = os.path.abspath(arg)
            tmp_name = choose_tmp_filename(abs_name)

            cmd = 'timeout {4} scp {0}@{1}:{2} {3} >{5}/scp-{0}-{1} 2>&1 '.format(params['user'], params['host'], abs_name, tmp_name, time_limit, bak_dir)
            flag = os.system(cmd)

            if flag > 0:
                os.system('rm %s >/dev/null 2>&1'%tmp_name)
                logger.warning('scp is unsuccessful. Info:')
                logger.info('%s'%(open('{2}/scp-{0}-{1}'.format(params['user'], params['host'], bak_dir)).read()))
                continue
            logger.debug('copy remote file %s to local'%tmp_name)

            tmp_file_size = os.stat(tmp_name).st_size
            if tmp_file_size - file_size > file_diff_thresh: 
                os.remove(tmp_name)
                logger.debug('Remote file too large, ignored')
                continue

            if filecmp.cmp(abs_name, tmp_name):
                os.remove(tmp_name)
            else:
                os.system('diff -u %s %s | colordiff | head -n 20'%(abs_name, tmp_name))
                logger.warning('Differences detected between remote file and local file.')
                logger.warning('Please choose: Override(Y) /Anti-override(!) /Ignore ')
                choice = raw_input()
                if choice == 'Y':
                    os.rename(abs_name, '{}/local-{}.bak'.format(bak_dir, base_name))
                    os.rename(tmp_name, abs_name)
                    logger.info('Override local file')
                elif choice == '!':
                    cmd = 'scp {2} {0}@{1}:{2} >{3}/scp-anti-{0}-{1} 2>&1 '.format(params['user'], params['host'], abs_name, bak_dir)
                    flag = os.system(cmd)
                    if flag == 0:
                        logger.info('Anti-override remote file')
                        os.rename(tmp_name, '{}/remote-{}.bak'.format(bak_dir, base_name))
                    else:
                        logger.warning('Anti-override failed! Info:')
                        logger.info('%s'%(open('{2}/sync-env-anti-{0}-{1}'.format(params['user'], params['host'], bak_dir)).read()))
                        os.remove(tmp_name)

                else:
                    logger.info('Ignored')
                    os.remove(tmp_name)


if __name__ == "__main__":
    args = sys.argv[1:]
    logger = log_init()
    params = parse_rc(logger)
    handle_args(args, params, logger)
    os.system(' '.join(args))
