import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ia_director.continuity import (
    ReconciliationEvidence, read_execution_checkpoint, reconcile_execution,
)
from ia_director.workspace import WorkspaceExecutionError, run_in_workspace


class RecoveryTests(unittest.TestCase):
    def interrupt(self, root, effect=False):
        def execute(workspace):
            record = read_execution_checkpoint(workspace)
            self.assertEqual(record['status'], 'IN_FLIGHT')
            self.assertEqual(record['workspace'], str(root.resolve()))
            self.assertTrue(record['operation_id'])
            if effect:
                (workspace / 'output').write_text('applied')
            raise ConnectionError('transport lost')
        with self.assertRaises(WorkspaceExecutionError) as caught:
            run_in_workspace('fixture', root, execute)
        self.assertEqual(caught.exception.status, 'UNKNOWN')
        return read_execution_checkpoint(root)

    def test_durable_checkpoint_and_unknown_blocks_new_callable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            record = self.interrupt(root, True)
            self.assertEqual(record['status'], 'UNKNOWN')
            self.assertEqual(record['accountability']['changes'][0]['target'], 'output')
            with self.assertRaises(WorkspaceExecutionError):
                run_in_workspace('alternate intent', root, lambda _: self.fail('alternate ran'))

    def test_safe_retry_requires_operation_bound_complete_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            record = self.interrupt(root)
            with self.assertRaises(ValueError):
                reconcile_execution(root, ReconciliationEvidence('wrong', ('observed',), True, True))
            reconciled = reconcile_execution(root, ReconciliationEvidence(
                record['operation_id'], ('executor terminated; full effect scope inspected: none applied',),
                stopped=True, no_effects=True))
            self.assertEqual(reconciled['reconciliation']['decision'], 'safe-to-retry')
            self.assertEqual(run_in_workspace('fixture', root, lambda _: 'retried').result, 'retried')
            self.assertEqual(read_execution_checkpoint(root)['previous_operation'], record['operation_id'])

    def test_already_applied_verified_prevents_duplicate_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            record = self.interrupt(root, True)
            reconciled = reconcile_execution(root, ReconciliationEvidence(
                record['operation_id'], ('terminated executor; output independently verified',),
                stopped=True, verified=True))
            self.assertEqual(reconciled['reconciliation']['decision'], 'already-applied/verified')
            with self.assertRaises(WorkspaceExecutionError):
                run_in_workspace('fixture', root, lambda _: self.fail('duplicate'))

    def test_unresolved_and_rollback_fail_closed_without_human_gate(self):
        for evidence in ({}, {'no_effects': True}, {'stopped': True, 'rollback_required': True},
                         {'stopped': True, 'verified': True, 'no_effects': True}):
            with self.subTest(evidence=evidence), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                record = self.interrupt(root)
                reconciled = reconcile_execution(root, ReconciliationEvidence(
                    record['operation_id'], ('scope observation',), **evidence))
                self.assertFalse(reconciled['human_gate']['reached'])
                with self.assertRaises(WorkspaceExecutionError):
                    run_in_workspace('fixture', root, lambda _: self.fail('unsafe retry'))

    def test_checkpoint_persistence_failure_prevents_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch('ia_director.workspace.persist_execution_checkpoint', side_effect=OSError('disk')):
                with self.assertRaises(OSError):
                    run_in_workspace('fixture', Path(tmp), lambda _: self.fail('ran without checkpoint'))

    def test_in_flight_survives_missing_interruption_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            from ia_director.continuity import persist_execution_checkpoint
            calls = 0
            def persist(workspace, record):
                nonlocal calls
                calls += 1
                if calls > 1:
                    raise OSError('storage disappeared')
                return persist_execution_checkpoint(workspace, record)
            with patch('ia_director.workspace.persist_execution_checkpoint', side_effect=persist):
                with self.assertRaises(OSError):
                    run_in_workspace('fixture', root, lambda _: (_ for _ in ()).throw(ConnectionError()))
            self.assertEqual(read_execution_checkpoint(root)['status'], 'IN_FLIGHT')
            with self.assertRaises(WorkspaceExecutionError):
                run_in_workspace('fixture', root, lambda _: self.fail('blind retry'))
