from datetime import datetime, timedelta
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'deploy'))
import dashboard_maintenance as maintenance


class MaintenanceTests(unittest.TestCase):
    def test_daily_deadline_and_weekly_schedule_in_korea_time(self):
        kst = maintenance.KST
        previous = datetime(2026, 11, 7, 4, tzinfo=kst)
        sunday = datetime(2026, 11, 8, 7, 59, tzinfo=kst)
        collect = maintenance.JOBS['collect']
        self.assertIsNone(maintenance.job_issue(sunday, collect, previous, 'activating', 'success'))
        self.assertEqual(maintenance.job_issue(sunday, collect, previous, 'failed', 'exit-code'), '실패')
        self.assertEqual(maintenance.job_issue(sunday + timedelta(minutes=1), collect, previous, 'inactive', 'success'),
                         '완료 기한 초과')
        restore = maintenance.JOBS['restore']
        self.assertEqual(maintenance.scheduled_due(sunday, *restore).day, 1)
        self.assertEqual(maintenance.scheduled_due(sunday.replace(hour=12), *restore).day, 8)

    def test_monitor_alerts_on_new_problem_and_recovery_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            with patch.object(maintenance, 'notify') as notify, patch.object(maintenance, 'read_job') as read:
                read.side_effect = lambda job, *_: '실패' if job == 'collect' else None
                maintenance.monitor(state)
                maintenance.monitor(state)
                read.side_effect = None
                read.return_value = None
                maintenance.monitor(state)
                self.assertEqual(notify.call_count, 2)
                self.assertIn('정상 복구', notify.call_args.args[0])

    def test_retention_preserves_minimum_and_ignores_other_files(self):
        now = datetime(2026, 11, 8, tzinfo=maintenance.KST)
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            for day in (1, 2, 3):
                path = directory/f'safehome-2026090{day}T013000000000Z.dump'
                path.touch()
                os.utime(path, (0, 0))
            unrelated = directory/'manual.dump'
            unrelated.touch()
            self.assertEqual(maintenance.prune(directory, now, 30, 2), 1)
            self.assertTrue(unrelated.is_file())
            self.assertEqual(len(maintenance.archives(directory)), 2)

    def test_s3_checksum_mismatch_stops_before_local_pruning(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            archive = directory/'safehome-20261108T013000000000Z.dump'
            archive.write_bytes(b'archive')
            with patch.dict(os.environ, {'SAFEHOME_BACKUP_S3_BUCKET': 'test'}), \
                 patch.object(maintenance, 'command', side_effect=[str(archive), '', 'wrong']), \
                 patch.object(maintenance, 'prune') as prune:
                with self.assertRaisesRegex(RuntimeError, '체크섬 불일치'):
                    maintenance.daily_backup(directory)
                prune.assert_not_called()
