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

    def __init__(self, logfile: str | None = None):
        self.logger = open(logfile, 'w') if logfile is not None else None
        self.shell = pexpect.spawn('/bin/zsh', ['-i', '+Z'], logfile=self.logger, encoding='utf-8', echo=True)

        print("\nInitializing terminal...\n=== Terminal ===\n")
        self.shell.expect(self._prompt_regex())
        print(self.shell.before, end='')

        # Initial commands
        self.execute("stty -icanon") # Disable canonical mode to enable long commands
        # Add more commands here if needed. Could loop through an "initial commands" list.

    def _prompt_regex(self):
        return fr'(\([^)]+\)\s+)?({os.environ.get('USER')}@{gethostname().replace('.local', '')}\s+\S+\s+%\s+)'

    def execute(self, command):
        # Print remaining output from previous command (essentially the prompt in the terminal)
        output = self.shell.after
        print(output, end='')
        lines, idx = command.split('\n'), 0
        while True:
            if idx < len(lines):
                self.shell.sendline(lines[idx])
                idx += 1
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
                    output += self.shell.before 
                    print(self.shell.before, end='')
                    break
            output += self.shell.before + self.shell.after
            print(self.shell.before + self.shell.after, end='')
        output = re.sub(ANSI_REGEX, '', output)
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
    
    # Test command with multiple lines of output
    output = terminal.execute("ls -la")
    # print(f"OUTPUT: {output}")
    assert len(output.split('\n')) > 1, "Multi-line output failed"

    # Test command that uses environment variables
    output = terminal.execute("echo $HOME")
    # print(f"OUTPUT: {output}")
    assert output.strip() != "", "Environment variable expansion failed"

    # Test a long command
    command = 'echo "' + ''.join([f"\n{n} abcdefghijklmnopqrstuvwxyz" for n in range(200)]) + '"'
    output = terminal.execute(command)
    # print(f"OUTPUT: {output}")
    assert output.strip() != "", "Long command failed"
    
    # Test closing the terminal
    terminal.close()
    try:
        terminal.execute("echo 'Should fail'")
        assert False, "Terminal should be closed"
    except:
        pass
    
    print("All tests passed!")
