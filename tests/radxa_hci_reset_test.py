# SPDX-License-Identifier: MIT
"""Exercise the real UART helper against a Linux pseudo-terminal controller."""
import fcntl
import os
import select
import subprocess
import tempfile
import termios
import time
import unittest


BINARY = os.environ.get("RADXA_HCI_RESET_BIN", "/tmp/radxa-hci-reset")
COMPLETE = bytes.fromhex("04 0e 04 01 03 0c 00")


class ResetTests(unittest.TestCase):
    def setUp(self):
        self.master, self.slave = os.openpty()
        self.original = termios.tcgetattr(self.slave)
        self.process = None

    def tearDown(self):
        if self.process is not None:
            if self.process.poll() is None:
                self.process.kill()
            self.process.communicate()
        os.close(self.master)
        os.close(self.slave)

    def start(self):
        self.started = time.monotonic()
        self.process = subprocess.Popen(
            [BINARY, os.ttyname(self.slave)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        command = bytearray()
        deadline = time.monotonic() + 2
        while len(command) < 4:
            remaining = deadline - time.monotonic()
            self.assertGreater(remaining, 0, "no reset command received")
            ready, _, _ = select.select([self.master], [], [], remaining)
            self.assertTrue(ready, "no reset command received")
            command.extend(os.read(self.master, 4 - len(command)))
        self.assertEqual(command, bytes.fromhex("01 03 0c 00"))
        settings = termios.tcgetattr(self.slave)
        self.assertEqual(settings[4:6], [termios.B1500000] * 2)
        self.assertTrue(settings[2] & termios.CRTSCTS)

    def finish(self, success):
        stdout, stderr = self.process.communicate(timeout=3)
        if success:
            self.assertEqual(self.process.returncode, 0, stderr)
            self.assertIn(b"HCI Reset complete", stdout)
        else:
            self.assertNotEqual(self.process.returncode, 0)
            self.assertNotIn(b"HCI Reset complete", stdout)
        self.assertLess(time.monotonic() - self.started, 3)
        self.assertEqual(termios.tcgetattr(self.slave), self.original)
        reopened = os.open(os.ttyname(self.slave), os.O_RDWR | os.O_NOCTTY)
        os.close(reopened)

    def test_success(self):
        self.start()
        os.write(self.master, COMPLETE)
        self.finish(True)

    def test_software_flow_control_is_disabled(self):
        flags = termios.IXON | termios.IXOFF | termios.IXANY
        self.original[0] |= flags
        termios.tcsetattr(self.slave, termios.TCSANOW, self.original)
        self.start()
        self.assertEqual(termios.tcgetattr(self.slave)[0] & flags, 0)
        os.write(self.master, COMPLETE)
        self.finish(True)

    def test_fragmented_and_embedded_fake_event(self):
        self.start()
        # A vendor event's payload is not a new H4 frame.
        os.write(self.master, b"\x04\xff\x07" + COMPLETE)
        for byte in COMPLETE:
            os.write(self.master, bytes([byte]))
            time.sleep(0.003)
        self.finish(True)

    def test_other_opcode_is_ignored(self):
        self.start()
        os.write(self.master, bytes.fromhex("04 0e 04 01 01 10 00") + COMPLETE)
        self.finish(True)

    def test_maximum_event_payload(self):
        self.start()
        os.write(self.master, b"\x04\xff\xff" + bytes(range(255)) + COMPLETE)
        self.finish(True)

    def test_controller_error(self):
        self.start()
        os.write(self.master, COMPLETE[:-1] + b"\x0c")
        self.finish(False)

    def test_short_reset_complete(self):
        self.start()
        os.write(self.master, bytes.fromhex("04 0e 03 01 03 0c"))
        self.finish(False)

    def test_command_status_does_not_establish_completion(self):
        self.start()
        os.write(self.master, bytes.fromhex("04 0f 04 00 01 03 0c"))
        self.finish(False)

    def test_partial_frame_times_out(self):
        self.start()
        os.write(self.master, bytes.fromhex("04 ff ff 01"))
        self.finish(False)

    def test_unrelated_events_do_not_extend_deadline(self):
        self.start()
        while self.process.poll() is None:
            os.write(self.master, bytes.fromhex("04 ff 01 00"))
            time.sleep(0.02)
        self.finish(False)

    def test_non_event_packet_rejected(self):
        self.start()
        os.write(self.master, b"\x02")
        self.finish(False)

    def test_regular_file_is_not_modified(self):
        with tempfile.NamedTemporaryFile() as file:
            file.write(b"unchanged")
            file.flush()
            result = subprocess.run([BINARY, file.name], capture_output=True, timeout=3)
            self.assertNotEqual(result.returncode, 0)
            file.seek(0)
            self.assertEqual(file.read(), b"unchanged")

    def test_exclusive_uart_is_not_changed(self):
        fcntl.ioctl(self.slave, termios.TIOCEXCL)
        try:
            result = subprocess.run(
                [BINARY, os.ttyname(self.slave)], capture_output=True, timeout=3,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(termios.tcgetattr(self.slave), self.original)
            self.assertFalse(select.select([self.master], [], [], 0)[0])
        finally:
            fcntl.ioctl(self.slave, termios.TIOCNXCL)


if __name__ == "__main__":
    unittest.main()
