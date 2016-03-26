
Instructions:

Step 1: Install dependencies
    sudo apt-get install colordiff git
    sudo python setup.py install

Step 2: Create ~/.syncrc and modify it according to syncrc.example

Step 3: enable no-password scp 
    ssh-keygen 
    ssh-copy-id user@hostname

Basic usages:

se <filename> 
    Create an empty file and synchronize it with the remote file

se <command>
    Run any command in the synchronized environment. Any file in the arguments will be detected and synchronized with instructions
