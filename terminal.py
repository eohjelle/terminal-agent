# Create a class that simulates a terminal
import pexpect
import os
from socket import gethostname
import re

ANSI_REGEX = r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])'

class Terminal:
    """
    A class that simulates a terminal.

    The logfile is used to store the terminal input and output. It contains ANSI escape codes, but will be displayed nicely if opened with `cat` in the terminal.
    """

    def __init__(self, logfile: str = "session.log"):
        self.logger = open(logfile, 'w') if logfile is not None else None
        self.shell = pexpect.spawn('/bin/zsh', ['-i', '+Z'], logfile=self.logger, encoding='utf-8', echo=False)
        # self.shell.logfile_read = sys.stdout.buffer
        # self.shell.logfile_read = open('logfile_read.txt', 'w')
        self.test_output = open('test_output.txt', 'w') # todo: remove
        self.shell.logfile_send = open('logfile_send.txt', 'w')

        print("\nInitializing terminal...\n=== Terminal ===\n")
        self.shell.expect(self._prompt_regex())
        self.execute("stty -icanon") # Disable canonical mode to enable long commands
        # Add more commands here if needed. Could loop through an "initial commands" list.

    def _prompt_regex(self):
        return fr'{os.environ.get('USER')}@{gethostname().replace('.local', '')}\s\S+\s%\s'

    def execute(self, command):
        self.test_output.write('\n\n\nNEW COMMAND\n\n\n')

        # Print remaining output from previous command (essentially the prompt in the terminal), followed by the command
        output = self.shell.before + self.shell.after + command + '\n'
        print(output, end='')

        command = re.sub(r'(?<!\\)\n', r'\\n', command) # Escape newlines in command when sending to shell
        self.shell.sendline(command)
        while True:
            index = self.shell.expect(['\r\n', pexpect.TIMEOUT, self._prompt_regex(), pexpect.EOF], timeout=15)
            match index:
                case 0:
                    pass
                case 1:
                    if self.shell.buffer != '':
                        self.shell.expect(r'.+') # Flush the buffer
                    else:
                        self.shell.before, self.shell.after = '', ''
                        break
                case _:
                    break
            output += self.shell.before + self.shell.after
            print(self.shell.before + self.shell.after, end='')
        output = re.sub(ANSI_REGEX, '', output)
        self.test_output.write(output)
        return output
    
    def close(self):
        self.shell.close()

# Test cases
if __name__ == "__main__":
    # Create a test terminal
    terminal = Terminal("test_session.log")
    
    # Test basic command execution
    output = terminal.execute("echo 'Hello, world!'")
    # print(f"OUTPUT: {output}")
    assert "Hello, world!" in output, "Basic echo command failed"
    
    # # Test command with multiple lines of output
    # output = terminal.execute("ls -la")
    # # print(f"OUTPUT: {output}")
    # assert len(output.split('\n')) > 1, "Multi-line output failed"

    # # Test command that uses environment variables
    # output = terminal.execute("echo $HOME")
    # # print(f"OUTPUT: {output}")
    # assert output.strip() != "", "Environment variable expansion failed"

    # Test a long command
    command = open("snake.txt").read()
    output = terminal.execute(command)
    print(f"OUTPUT: {output}")
    assert output.strip() != "", "Long command failed"

    # Test a long command with invalid syntax
    command = open("invalid-snake.txt").read()
    output = terminal.execute(command)
    print(f"OUTPUT: {output}")
    assert output.strip() != "", "Long command with invalid syntax failed"
    
    # Test closing the terminal
    terminal.close()
    try:
        terminal.execute("echo 'Should fail'")
        assert False, "Terminal should be closed"
    except:
        pass
    
    print("All tests passed!")
