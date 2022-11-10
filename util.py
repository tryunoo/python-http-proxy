from termcolor import colored


def print_error(msg):
    print(colored(msg, 'red'))


def print_error_exit(msg):
    print_error(msg)
    exit()
