"""Test for Robscript parser and logic.

@author: Sam Pottinger (samnsparky: Gleap LLC & LabJack Corp, 2014)
"""

import subprocess
import unittest

import mox

import robscript


class RobscriptTests(mox.MoxTestBase):

    def test_read_line(self):
        automaton = robscript.RobScriptBuilder(
            iter(['"\tTest status.']),
            None,
            None,
            None,
            None,
            create_log_file=False
        )
        automaton.state = robscript.STATE_READ_LINE
        automaton.read_line()

        self.assertEqual(automaton.state, robscript.STATE_CHANGE_STATUS)
        self.assertEqual(automaton.state_frame, ['Test status.'])

    def test_change_dir(self):
        automaton = robscript.RobScriptBuilder(
            iter([]),
            None,
            None,
            None,
            None,
            create_log_file=False
        )
        automaton.state = robscript.STATE_CHANGE_DIR
        automaton.state_frame = ['/test/dir']
        automaton.change_dir()

        self.assertEqual(automaton.working_dir, '/test/dir')
        self.assertEqual(automaton.state, robscript.STATE_READ_LINE)

    def test_exec_shell(self):
        self.mox.StubOutWithMock(subprocess, 'check_output')
        subprocess.check_output('test_command', cwd='/test/dir', shell=True)
        self.mox.ReplayAll()

        automaton = robscript.RobScriptBuilder(
            iter([]),
            None,
            None,
            None,
            None,
            create_log_file=False
        )
        automaton.state = robscript.STATE_TRY_EXEC_SHELL
        automaton.working_dir = '/test/dir'
        automaton.state_frame = ['test_command']
        automaton.exec_shell()

        self.assertEqual(automaton.state, robscript.STATE_READ_LINE)

    def test_upload(self):
        self.uploaded_local = None
        self.uploaded_remote = None

        def on_uploaded(new_uploaded_local, new_uploaded_remote, public, callback):
            self.uploaded_local = new_uploaded_local
            self.uploaded_remote = new_uploaded_remote

        automaton = robscript.RobScriptBuilder(
            iter([]),
            on_uploaded,
            None,
            None,
            None,
            create_log_file=False
        )
        automaton.state = robscript.STATE_CHANGE_DIR
        automaton.state_frame = ['local', 'remote']
        automaton.upload()

        self.assertEqual(automaton.state, robscript.STATE_READ_LINE)
        self.assertEqual(self.uploaded_local, 'local')
        self.assertEqual(self.uploaded_remote, 'remote')

    def test_change_status(self):
        self.status = None

        def on_status(new_status):
            self.status = new_status

        automaton = robscript.RobScriptBuilder(
            iter([]),
            None,
            on_status,
            None,
            None,
            create_log_file=False
        )
        automaton.state = robscript.STATE_CHANGE_DIR
        automaton.state_frame = ['test status']
        automaton.change_status()

        self.assertEqual(automaton.state, robscript.STATE_READ_LINE)
        self.assertEqual(self.status, 'test status')

    def test_finish(self):
        self.finished = False

        def on_finish():
            self.finished = True

        automaton = robscript.RobScriptBuilder(
            iter([]),
            None,
            None,
            None,
            on_finish,
            create_log_file=False
        )
        automaton.state = robscript.STATE_FINISH
        automaton.finish()

        self.assertEqual(automaton.state, robscript.STATE_TERMINAL)
        self.assertTrue(self.finished)

    def test_build_params_dict(self):
        params = ['test1', 2]
        names = ['param1', 'param2']
        params_dict = robscript.build_params_dict(params, names)
        self.assertEqual(params_dict, {'param1': 'test1', 'param2': 2})


if __name__ == '__main__':
    unittest.main()
