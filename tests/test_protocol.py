import json
import tempfile
import unittest
from pathlib import Path
import sys
import os
import socket
import subprocess

from carla_agent.protocol import AgentError, load_profile, schema, validate_parameters
from carla_agent.bridge import invoke, server_identity


class ProtocolTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'profile.json'
        self.profile = {'schema_version': 1, 'client_python': sys.executable, 'output_root': self.tmp.name}

    def load(self, **extra):
        self.path.write_text(json.dumps({**self.profile, **extra}))
        return load_profile(self.path)

    def test_readonly_default(self):
        self.assertEqual(self.load()['session_policy'], 'inspect_only')
        self.assertFalse(schema('world.inspect')['mutates_world'])

    def test_reject_bad_profile_before_subprocess(self):
        for change in ({'port': True}, {'timeout_seconds': -1}, {'schema_version': True}, {'output_root': 'relative'}, {'command': 'anything'}):
            with self.subTest(change=change), self.assertRaises(AgentError):
                self.load(**change)

    def test_schema_required_and_extra(self):
        for params in ({}, {'actor_id': 1}, {'session_id': 's', 'actor_id': True}, {'session_id': 's', 'actor_id': 1, 'all': True}):
            with self.assertRaises(AgentError):
                validate_parameters('actors.destroy', params)
        validate_parameters('actors.destroy', {'session_id': 's', 'actor_id': 1})

    def test_write_does_not_spawn_worker_without_exclusive(self):
        with self.assertRaises(AgentError) as ctx:
            invoke(self.load(), 'session.open', {})
        self.assertEqual(ctx.exception.code, 'exclusive_session_required')

    def test_atomic_inspection_and_control_schemas(self):
        for operation in ('map.inspect', 'weather.inspect', 'actors.inspect', 'spectator.inspect'):
            self.assertFalse(schema(operation)['mutates_world'])
        self.assertEqual(schema('map.inspect')['parameters']['properties']['limit']['default'], 20)
        self.assertTrue(schema('vehicle.control')['mutates_world'])
        controls = schema('vehicle.control')['parameters']['properties']['control']
        self.assertFalse(controls['additionalProperties'])
        self.assertEqual(controls['properties']['gear']['minimum'], -1)
        for operation, parameters in (
                ('map.inspect', {'limit': 0}), ('map.inspect', {'limit': 501}),
                ('map.inspect', {'limit': True}), ('actors.inspect', {}),
                ('actors.inspect', {'actor_id': 0}), ('actors.inspect', {'actor_id': True}),
                ('weather.inspect', {'set': {}}), ('spectator.inspect', {'transform': {}})):
            with self.subTest(operation=operation, parameters=parameters), self.assertRaises(AgentError):
                validate_parameters(operation, parameters)
        for control in ({'throttle': True}, {'reverse': 1}, {'gear': 1.0}, {'gear': -2},
                        {'gear': 2 ** 31}, {'steer': float('nan')}, {'brake': 1.01}, {'autopilot': True}):
            with self.subTest(control=control), self.assertRaises(AgentError):
                validate_parameters('vehicle.control', {'session_id': 's', 'actor_id': 1, 'control': control})
        validate_parameters('vehicle.control', {'session_id': 's', 'actor_id': 1,
                                              'control': {'throttle': 0, 'brake': 0, 'reverse': False, 'gear': 0}})

    def test_unknown_operation_and_missing_identity(self):
        with self.assertRaises(AgentError):
            validate_parameters('world.destroy', {})
        with self.assertRaises(AgentError) as ctx:
            server_identity(self.load())
        self.assertEqual(ctx.exception.code, 'identity_unverified')

    def test_stale_capture_directory_rejected(self):
        p=self.load(session_policy='exclusive', expected_server_version='test')
        existing=Path(self.tmp.name)/'existing'
        existing.mkdir()
        with self.assertRaises(AgentError) as ctx:
            invoke(p, 'capture.run', {'recipe': {}}, existing)
        self.assertEqual(ctx.exception.code, 'output_exists')

    def test_invalid_output_does_not_create_directories(self):
        p=self.load(session_policy='exclusive', expected_server_version='test')
        p['output_root']=str(Path(self.tmp.name)/'allowed')
        outside=Path(self.tmp.name)/'outside'/'new'
        with self.assertRaises(AgentError) as ctx:
            invoke(p,'capture.run',{'recipe': {}},outside)
        self.assertEqual(ctx.exception.code,'invalid_output_path')
        self.assertFalse(outside.parent.exists())
        with self.assertRaises(AgentError):
            invoke(p,'capture.run',{'recipe': {'frames':0}})
        self.assertFalse(Path(p['output_root']).exists())

    def test_non_directory_output_root_is_structured_error(self):
        p=self.load(session_policy='exclusive', expected_server_version='test')
        root=Path(self.tmp.name)/'file';root.write_text('existing')
        p['output_root']=str(root)
        with self.assertRaises(AgentError) as ctx:
            invoke(p,'capture.run',{'recipe': {}})
        self.assertEqual(ctx.exception.code,'output_unavailable')
        self.assertEqual(root.read_text(),'existing')

    @unittest.skipUnless(sys.platform.startswith('linux'), 'Linux provenance')
    def test_process_port_on_other_address_is_not_identity(self):
        with socket.socket() as listener:
            listener.bind(('127.0.0.2',0));listener.listen()
            p=self.load(server_pid=os.getpid(),port=listener.getsockname()[1])
            with self.assertRaises(AgentError) as ctx:
                server_identity(p)
            self.assertEqual(ctx.exception.code,'identity_unverified')

    def test_legacy_bad_recipe_is_json_error(self):
        bad=Path(self.tmp.name)/'bad.json';bad.write_text('{invalid')
        r=subprocess.run([sys.executable,'-m','carla_autoresearch.experiment','--profile',str(self.path),'--recipe',str(bad)],capture_output=True,text=True)
        self.assertEqual(r.returncode,2)
        self.assertEqual(json.loads(r.stdout)['error']['code'],'invalid_json')


if __name__ == '__main__':
    unittest.main()
