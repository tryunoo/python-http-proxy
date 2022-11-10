from termcolor import colored

def print_error_exit(msg):
    print(colored(msg, 'red'))
    exit()
