# SPDX-License-Identifier: MIT
"""Exercise the native diagnostic agent against a real private D-Bus bus."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'aa_wireless_dongle/board/radxa/zero3w/checks/aic-pairing-test.c'
DEVICE = '/org/bluez/hci0/dev_00_11_22_33_44_55'


def fake_bluez(address, scenario, report):
    from gi.repository import Gio, GLib
    flags = Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT | Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION
    connection = Gio.DBusConnection.new_for_address_sync(address, flags, None, None)
    connection.call_sync('org.freedesktop.DBus', '/org/freedesktop/DBus',
                         'org.freedesktop.DBus', 'RequestName',
                         GLib.Variant('(su)', ('org.bluez', 0)), None, 0, 2000, None)
    properties = {'Powered': False, 'Pairable': False, 'Discoverable': False,
                  'Alias': '', 'PairableTimeout': 0, 'DiscoverableTimeout': 0}
    paired = False
    owner = agent = None

    def record(event, **values):
        with Path(report).open('a') as f:
            f.write(json.dumps(dict(event=event, **values)) + '\n')

    def emit_pair():
        nonlocal paired
        paired = scenario != 'false_readback'
        path = DEVICE if scenario != 'other_adapter' else DEVICE.replace('hci0', 'hci1')
        connection.emit_signal(None, path, 'org.freedesktop.DBus.Properties',
                               'PropertiesChanged', GLib.Variant('(sa{sv}as)',
                               ('org.bluez.Device1', {'Paired': GLib.Variant('b', True)}, [])))

    def pair_attempt():
        if scenario in ('success', 'false_readback', 'rogue_sender', 'second_device', 'profile'):
            def authorized(conn, result):
                try:
                    conn.call_finish(result)
                    record('authorized')
                    if scenario in ('second_device', 'profile'):
                        method = 'RequestAuthorization' if scenario == 'second_device' else 'AuthorizeService'
                        args = GLib.Variant('(o)', (DEVICE + '_OTHER',)) if scenario == 'second_device' else GLib.Variant('(os)', (DEVICE, 'unrequested-profile'))
                        def rejected(conn, result):
                            try:
                                conn.call_finish(result)
                                record('unexpected_accept')
                            except GLib.Error:
                                record('rejected')
                            emit_pair()
                        connection.call(owner, agent, 'org.bluez.Agent1', method,
                                        args, None, 0, 2000, None, rejected)
                    else:
                        emit_pair()
                except GLib.Error:
                    record('authorization_failed')
            def authorize():
                connection.call(owner, agent, 'org.bluez.Agent1', 'RequestAuthorization',
                                GLib.Variant('(o)', (DEVICE,)), None, 0, 2000, None, authorized)
            if scenario == 'rogue_sender':
                rogue = Gio.DBusConnection.new_for_address_sync(address, flags, None, None)
                def rogue_done(conn, result):
                    try:
                        conn.call_finish(result)
                        record('unexpected_accept')
                    except GLib.Error:
                        record('rejected')
                    authorize()
                rogue.call(owner, agent, 'org.bluez.Agent1', 'RequestAuthorization',
                           GLib.Variant('(o)', (DEVICE,)), None, 0, 2000, None, rogue_done)
            else:
                authorize()
        elif scenario == 'other_adapter':
            emit_pair()
        return False

    def manager(conn, sender, path, interface, method, args, invocation):
        nonlocal owner, agent
        record(method, arguments=list(args.unpack()))
        if method == 'RegisterAgent':
            owner, agent = sender, args.unpack()[0]
        invocation.return_value(GLib.Variant('()', ()))

    def get_property(conn, sender, path, interface, name):
        if interface == 'org.bluez.Device1':
            return GLib.Variant('b', paired)
        value = properties[name]
        if name == 'Powered' and scenario == 'power_readback_false': value = False
        kind = 'b' if isinstance(value, bool) else 'u' if isinstance(value, int) else 's'
        return GLib.Variant(kind, value)

    def set_property(conn, sender, path, interface, name, value):
        properties[name] = value.unpack()
        record('set', name=name, value=value.unpack())
        if name == 'Discoverable' and value.unpack(): GLib.timeout_add(50, pair_attempt)
        return True

    manager_xml = '''<node><interface name="org.bluez.AgentManager1">
      <method name="RegisterAgent"><arg type="o" direction="in"/><arg type="s" direction="in"/></method>
      <method name="RequestDefaultAgent"><arg type="o" direction="in"/></method>
      <method name="UnregisterAgent"><arg type="o" direction="in"/></method>
      </interface></node>'''
    adapter_xml = '<node><interface name="org.bluez.Adapter1">' + ''.join(
        f'<property name="{name}" type="{kind}" access="readwrite"/>' for name, kind in
        [('Powered', 'b'), ('Pairable', 'b'), ('Discoverable', 'b'), ('Alias', 's'),
         ('PairableTimeout', 'u'), ('DiscoverableTimeout', 'u')]) + '</interface></node>'
    device_xml = '<node><interface name="org.bluez.Device1"><property name="Paired" type="b" access="read"/></interface></node>'
    for path, xml, callback in [('/org/bluez', manager_xml, manager),
                                ('/org/bluez/hci0', adapter_xml, None),
                                (DEVICE, device_xml, None)]:
        info = Gio.DBusNodeInfo.new_for_xml(xml).interfaces[0]
        connection.register_object(path, info, callback, get_property, set_property)
    record('ready')
    GLib.MainLoop().run()


class PairingAgent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.binary = Path(cls.tmp.name) / 'agent'
        flags = shlex.split(subprocess.check_output(['pkg-config', '--cflags', '--libs', 'gio-2.0'], text=True))
        subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-Wconversion',
                        '-Wshadow', str(SOURCE), '-o', str(cls.binary), *flags], check=True)

    def run_case(self, scenario):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / 'trace'
            bus = subprocess.Popen(['dbus-daemon', '--session', '--nofork', '--print-address=1'],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            server = None
            try:
                address = bus.stdout.readline().strip()
                self.assertTrue(address, bus.stderr.read() if bus.poll() is not None else 'private bus failed')
                server = subprocess.Popen([sys.executable, __file__, '--serve', address,
                                           scenario, str(report)], stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE, text=True)
                deadline = time.monotonic() + 5
                while not report.exists() and server.poll() is None and time.monotonic() < deadline:
                    time.sleep(0.01)
                self.assertTrue(report.exists(), server.communicate(timeout=1) if server.poll() is not None else 'server not ready')
                result = subprocess.run([str(self.binary), address, '1'], capture_output=True,
                                        text=True, timeout=8)
                events = [json.loads(line) for line in report.read_text().splitlines()]
                return result, events
            finally:
                for proc in (server, bus):
                    if proc is not None:
                        proc.terminate()
                        proc.communicate(timeout=3)

    def test_success_requires_authorization_and_paired_readback(self):
        result, events = self.run_case('success')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('PAIRING_RESULT=success', result.stdout)
        self.assertTrue(any(e['event'] == 'authorized' for e in events))
        self.assertTrue(any(e['event'] == 'UnregisterAgent' for e in events))
        for name in ('Discoverable', 'Pairable'):
            self.assertEqual([e['value'] for e in events if e['event'] == 'set' and e['name'] == name][-1], False)

    def test_no_paired_device_times_out_and_closes_window(self):
        result, events = self.run_case('timeout')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('PAIRING_RESULT=success', result.stdout)
        self.assertTrue(any(e.get('name') == 'Discoverable' and e['value'] is False for e in events))

    def test_other_adapter_event_cannot_pass(self):
        result, _ = self.run_case('other_adapter')
        self.assertNotEqual(result.returncode, 0)

    def test_success_signal_with_false_property_cannot_pass(self):
        result, _ = self.run_case('false_readback')
        self.assertNotEqual(result.returncode, 0)

    def test_power_readback_failure_never_opens_window(self):
        result, events = self.run_case('power_readback_false')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any(e.get('name') == 'Discoverable' and e['value'] is True for e in events))

    def test_invalid_duration_fails_before_bus_access(self):
        for duration in ('0', '181', 'garbage'):
            r = subprocess.run([str(self.binary), 'invalid-address', duration], capture_output=True, text=True)
            self.assertEqual(r.returncode, 2)

    def test_other_bus_sender_cannot_authorize_pairing(self):
        self.assert_rejected_before_success('rogue_sender')

    def test_second_candidate_cannot_authorize_pairing(self):
        self.assert_rejected_before_success('second_device')

    def test_pairing_agent_does_not_authorize_profiles(self):
        self.assert_rejected_before_success('profile')

    def assert_rejected_before_success(self, scenario):
        result, events = self.run_case(scenario)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(any(e['event'] == 'rejected' for e in events))
        self.assertFalse(any(e['event'] == 'unexpected_accept' for e in events))


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--serve':
        fake_bluez(*sys.argv[2:])
    else:
        unittest.main()
