#!/usr/bin/python2

import os, sys
import logging
import filecmp
logging.basicConfig()
logger = logging.getLogger('sync-env')
level = logging.DEBUG
logger.setLevel(level)
logger.info('Running command in synchronized environment')

def parse_rc():
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
                logger.error('Unknown error occur in ~/.syncrc line %d: %s'%(lid, line))

            key = key.strip().lower()
            cont = cont.strip()
            if key in params:
                params[key] = params[key].append(cont) if type(params[key]) is list else [params[key], cont]
            else:
                params[key] = cont

    if 'user' not in params or 'source' not in params:
        logger.error('<user> and <source> required in the config file ~/.syncrc')

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

def handle_args(args, params):
    if len(args) > 0 and check_exclude_command(args[0], params.get('exclude_command', 'git')):
        return

    for arg in args:
        if not arg.startswith('-') and os.path.isfile(arg):
            logger.debug('%s is a file, processing'%arg)
            file_size = os.stat(arg).st_size
            if file_size > params.get('max_size', 1e4):
                logger.debug('File size exceeds limit, ignored')
                continue

            base_name = os.path.basename(arg)
            if check_suffix(base_name, params.get('exclude_suffix', 'bin')):
                logger.debug('suffix excluded')
                continue

            abs_name = os.path.abspath(arg)
            tmp_name = choose_tmp_filename(abs_name)

            time_limit = float(params.get('time_limit', '1'))

            cmd = 'timeout {4} scp {0}@{1}:{2} {3} >/tmp/sync-env-{0}-{1} 2>&1 '.format(params['user'], params['source'], abs_name, tmp_name, time_limit)
            flag = os.system(cmd)

            if flag > 0:
                os.system('rm %s >/dev/null 2>&1'%tmp_name)
                logger.debug('scp is unsuccessful')
                logger.debug('info: %s'%(open('/tmp/sync-env-{0}-{1}'.format(params['user'], params['source'])).read()))
                continue
            logger.debug('copy remote file %s to local'%tmp_name)

            tmp_file_size = os.stat(tmp_name).st_size
            if tmp_file_size - file_size > params.get('size_diff_thresh', 1e3):
                os.remove(tmp_name)
                logger.debug('Remote file too large, ignored')
                continue

            if filecmp.cmp(abs_name, tmp_name):
                os.remove(tmp_name)
            else:
                os.system('diff -u %s %s | colordiff | head -n 20'%(abs_name, tmp_name))
                logger.warning('Differences detected between remote file and local file.')
                choice = raw_input('Override(Y) /Anti-override(!) /Ignore')
                if choice == 'Y':
                    os.rename(tmp_name, abs_name)
                    logger.debug('Override local file')
                elif choice == '!':
                    cmd = 'scp {2} {0}@{1}:{2} >/tmp/sync-env-anti-{0}-{1} 2>&1 '.format(params['user'], params['source'], abs_name)
                    flag = os.system(cmd)
                    if flag == 0:
                        logger.info('Anti-override remote file')
                    else:
                        logger.info('Anti-overried failed! Info:')
                        logger.info('info: %s'%(open('/tmp/sync-env-anti-{0}-{1}'.format(params['user'], params['source'])).read()))

                else:
                    os.remove(tmp_name)


if __name__ == "__main__":
    args = sys.argv[1:]
    params = parse_rc()
    handle_args(args, params)
    os.system(' '.join(args))
