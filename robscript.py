"""Library / stand alone command line utility for running ROB-scripts.

Library and stand alone command line utility for running ROB-scripts, glorified
bash scripts that allow for remote orchestrated builds across many platforms,
decreasing LabJack suck at building / maintaining cross platform software with
occasionally burdensome build processes.

Running from the command line?

python robscript.py [path to robscript file] [path to JSON file with config]

@author: Sam Pottinger (samnsparky: Gleap LLC & LabJack Corp, 2014)
"""

import json
import StringIO
import subprocess
import sys

import jinja2
from jinja2 import Environment, meta

STATE_READ_LINE = 1
STATE_CHANGE_DIR = 2
STATE_EXEC_SHELL = 3
STATE_UPLOAD = 4
STATE_CHANGE_STATUS = 5
STATE_SEND_LOG = 6
STATE_FINISH = 7
STATE_TERMINAL = 8
STATE_SEND_LOG_TERMINAL = 9
STATE_FINISH_ERROR = 10
STATE_TRY_EXEC_SHELL = 11

COMMAND_STATES = {
    '%': STATE_SEND_LOG,
    '"': STATE_CHANGE_STATUS,
    '/': STATE_CHANGE_DIR,
    '>': STATE_EXEC_SHELL,
    '^': STATE_UPLOAD,
    '?': STATE_TRY_EXEC_SHELL
}

LOG_FILE_SRC = 'robscript_build_log.txt'


class RobScriptBuilder:
    """Automaton that parses and executes rob-scripts.

    "Simple finite automaton" that reads and executes rob-scripts, including
    file uploads and logging. Note that this automaton saves some additional
    information to itself other than a state identifier but, being an SFA, does
    not have a stack or, obviously, support recursion in the regular language
    that runs it.
    """

    def __init__(self, script, send_upload, on_status_update, on_error,
        on_finish, worker_name='', create_log_file=True):
        """Create a new rob script reader automaton.

        @param script: Iterator (file like or iter(list-like)) over a series of
            strings. For example, this could be the file object for the file
            with the robscript to run.
        @type script: Iterator
        @param send_upload: Function to call when sending an upload to ROB's
            central repository of built stuff.
        @type send_upload: function
        @param on_status_update: The function to call with a status update.
        @type on_status_update: function
        @param on_error: The function to call when an error is encountered.
        @type on_error: function
        @param on_finish: The function to call after the rob script finishes.
        @type on_finish: function
        @keyword worker_name: The name to identify this worker as when
            communicating with ROB central dispatch. Not used if run as a
            stand-alone utility from the command line. Defaults to empty string.
        @type worker_name: str
        """
        self.script = script
        self.send_upload = send_upload
        self.on_status_update = on_status_update
        self.on_error = on_error
        self.on_finish = on_finish
        self.state_frame = None
        self.state = STATE_READ_LINE
        if create_log_file: self.log_file = open(LOG_FILE_SRC, 'w')
        else: self.log_file = StringIO.StringIO()
        self.working_dir = None
        self.worker_name = worker_name

        self.step_strategies = {
            STATE_READ_LINE: self.read_line,
            STATE_CHANGE_DIR: self.change_dir,
            STATE_EXEC_SHELL: self.exec_shell,
            STATE_UPLOAD: self.upload,
            STATE_CHANGE_STATUS: self.change_status,
            STATE_SEND_LOG: self.send_log,
            STATE_FINISH: self.finish,
            STATE_SEND_LOG_TERMINAL: self.send_log,
            STATE_FINISH_ERROR: self.finish,
            STATE_TRY_EXEC_SHELL: self.exec_shell
        }

    def step(self):
        """Execute steps for this automaton until reaching a terminal state.

        Executes the code associated with the current state of this automaton,
        constituting a "step". This will continue "stepping" until the
        automaton reaches a terminal state.
        """
        while self.state != STATE_TERMINAL:
            self.step_strategies[self.state]()

    def read_line(self):
        """Read the next command of the currently executing robscript.

        This will change the state of this automaton, reading the next command
        to execute and saving the parameters of that command to the state of
        this automaton. Notice that this is not a push down automaton and, thus,
        non-recursive.
        """
        cur_line = None
        try:
            cur_line = self.script.next()
        except StopIteration:
            self.state = STATE_FINISH
            return

        command_elements = cur_line.split('\t')
        command_type = command_elements[0]
        if command_type in COMMAND_STATES:
            self.state = COMMAND_STATES[command_type]
            self.state_frame = command_elements[1:]

    def change_dir(self):
        """Change the working directory where robscript commands are executed.

        This will change the working directory of where this automaton executes 
        commands for the currently running robscript.
        """
        self.working_dir = self.state_frame[0]
        self.state = STATE_READ_LINE

    def exec_shell(self):
        """Execute a command on the shell.

        Executes a raw command on the shell from the working directory specified
        in the robscript. Note that this expects exactly one parameter read from
        the robscript (saved to self.state_frame): the raw string with the
        command to be executed.
        """
        command = self.state_frame[0]
        required = self.state == STATE_EXEC_SHELL

        try:
            results = subprocess.check_output(
                command,
                cwd=self.working_dir,
                shell=True
            )
            self.log_file.write(results)
            self.state = STATE_READ_LINE
        except subprocess.CalledProcessError as e:
            self.log_file.write('[ERROR] ' + str(e))
            self.state_frame = [self.worker_name + '.txt']
            if required:
                self.state = STATE_SEND_LOG_TERMINAL
            else:
                self.state = STATE_READ_LINE

    def upload(self):
        """Upload a file to ROB's grand for stuff.

        Uploads a file to ROB's central repository for built stuff on S3. Note
        that this expects two parameters read from the robscript command:
         - The FULL (str) path to the file that should be uploaded.
         - The FULL (str) name to give the file within the central repository.
        """
        # TODO: Should CD to the working directory set by the robscript.
        src = self.state_frame[0]
        dest = self.state_frame[1]
        self.send_upload(src, dest, True, None)
        self.state = STATE_READ_LINE

    def change_status(self):
        """Change the status reported to ROB central command.

        Updates the status for this worker on ROB central command. Expects one
        parameter read from the robscript command: the string message to report.
        """
        message = self.state_frame[0]
        self.on_status_update(message)
        self.state = STATE_READ_LINE

    def send_log(self):
        """Upload a build log to ROB repository for built things.

        Uploads the build log to the ROB repository for built things, Expects
        one parameter read from the robscript command: the full name to give the
        log within ROB's repository for built things.
        """
        self.on_status_update('Sending log...')
        dest = self.state_frame[0]
        self.log_file.flush()
        self.send_upload(LOG_FILE_SRC, dest, True, None)
        if self.state == STATE_SEND_LOG:
            self.state = STATE_READ_LINE
        else:
            self.state = STATE_FINISH_ERROR

    def finish(self):
        """Report to ROB central command that the script finished."""
        if self.state == STATE_FINISH_ERROR:
            self.on_error('Something went wrong. :( Please see log.')
        else:
            self.on_finish()
        self.log_file.close()
        self.state = STATE_TERMINAL


def build_params_dict(params, param_names):
    """Build a dictionary that maps parameter name to parameter.

    Build a dictionary that maps parameter name to parameter. Should be given
    two collections (iterables) of equal length: the first being the parameters
    and the second being the corresponding parameter names. param_names[0]
    should be the name of the parameter whose value is at params[0].

    @param params: Iterable of parameters.
    @type params: Iterable
    @param param_names: The corresponding name of each parameter.
    @type param_names: Iterable of str.
    @return: Dictionary mapping parameter name to value.
    @rtype: dict
    """
    if len(params) != len(param_names):
        raise ValueError('Parameter and parameter name length mismatch.')
    return dict(zip(param_names, params))


def run_job(script, send_upload, on_status_update, on_error, on_finish,
    worker_name):
    """Run a robscript.

    @param script: String with the script to run.
    @type script: str
    @param send_upload: Function to call when sending an upload to ROB's central
        repository of built stuff.
    @type send_upload: function
    @param on_status_update: The function to call with a status update.
    @type on_status_update: function
    @param on_error: The function to call when an error is encountered.
    @type on_error: function
    @param on_finish: The function to call after the rob script finishes.
    @type on_finish: function
    @keyword worker_name: The name to identify this worker as when communicating
        with ROB central dispatch. Not used if run as a stand-alone utility from
        the command line. Defaults to empty string.
    @type worker_name: str
    """
    builder = RobScriptBuilder(
        iter(script.split('\n')),
        send_upload,
        on_status_update,
        on_error,
        on_finish,
        worker_name
    )
    builder.step()


def create_print(prefix):
    """Returns a function that print whatever was given to it with a prefix.

    @param prefix: The prefix to prepend to the strings printed by the returned
        function.
    @type prefix: str
    @return: Function that prints whatever was given to it along with the
        provided prefix.
    @rtype: function
    """
    def inner(*args):
        print prefix + str(args)
    return inner


def check_sanity(template, context):
    """Check the sanity of a template, given a context to render that template.

    @type template: str
    @type context: dict
    """
    env = Environment()

    contexted_templ = ''
    for key, val in context.iteritems():

        # Filter out empty strings. Checking the truthy-ness is not correct
        # because the value `false` is a valid value.
        if val != "":
            contexted_templ += '{%% set %s = "%s" %%}\n' % (str(key), str(val))

    contexted_templ += template

    ast = env.parse(contexted_templ)
    undeclared = meta.find_undeclared_variables(ast)

    if len(undeclared) > 0:
        raise ValueError('Undeclared variables : %s' % (str(undeclared)))


def read_file(to_read):
    with open(to_read) as f:
        return f.read()


def render_template(script, context):
    check_sanity(script, context)
    return jinja2.Template(script).render(context)


def main(script, context):
    """Main program logic, given a script and a context / parameters.

    @param script, The robscript template to render and execute.
    @type script, str
    @param context, The parameters to use to render the robscript template.
    @type context, dict
    """
    send_upload = create_print('[UPLOAD] ')
    on_status_update = create_print('[STATUS] ')
    on_error = create_print('[ERROR] ')
    on_finish = create_print('Finished. ')

    script = render_template(script, context)

    run_job(script, send_upload, on_status_update, on_error, on_finish, '')


if __name__ == '__main__':
    """Main program logic called if running this module stand-alone from CMD.

    Main program logic called if running this module as a stand-alone module
    run from the command line.
    """
    if len(sys.argv) < 3:
        print 'USAGE: python robscript.py script params_json'
        sys.exit(1)

    script_loc = sys.argv[1]
    context_json_loc = sys.argv[2]

    context = None
    with open(context_json_loc) as f:
        context = json.load(f)

    script = read_file(script_loc)

    main(script, context)
