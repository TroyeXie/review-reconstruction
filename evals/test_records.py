"""Operational invariants only; not a test of scientific judgment."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('review_records',Path(__file__).resolve().parents[1]/'scripts'/'review_records.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class Records(unittest.TestCase):
    def test_shared_paper_and_unread_are_not_inflated(self):
        index=[{'编码':'A1','记录ID':'P1','PDF相对路径':'one.pdf'},
               {'编码':'B1','记录ID':'P1','PDF相对路径':'one.pdf'},
               {'编码':'A2','记录ID':'P2','PDF相对路径':'two.pdf'}]
        readings=[{'paper_id':'P1','reading_status':'full_text_read','read_scope':'PDF1–5'},
                  {'paper_id':'P1','reading_status':'full_text_read','read_scope':'shared reading'},
                  {'paper_id':'P2','reading_status':'partial_read','read_scope':'abstract'}]
        report=module.audit(index,readings)
        self.assertEqual(report['relation_count'],3)
        self.assertEqual(report['unique_record_count'],2)
        self.assertEqual(report['recorded_full_text_read_count'],1)
        self.assertEqual(report['records_without_full_read_record'],1)
        self.assertEqual(report['recorded_correction_read_count'],0)
        self.assertEqual(report['recorded_auxiliary_record_count'],0)
        self.assertNotIn('study_count',report)
        self.assertFalse(report['errors'])

    def test_claimed_read_requires_scope_and_known_id(self):
        index=[{'reference_code':'R1','paper_id':'P1','pdf_path':''}]
        readings=[{'paper_id':'P1','reading_status':'full_text_read','read_scope':''},
                  {'paper_id':'P9','reading_status':'full_text_read','read_scope':'PDF1'}]
        report=module.audit(index,readings)
        self.assertEqual(report['recorded_full_text_read_count'],0)
        self.assertEqual(len(report['errors']),2)

    def test_locate_preserves_version_ambiguity_and_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'a.pdf').write_bytes(b'local test fixture')
            rows=[{'编码':'R1','记录ID':'P1','PDF相对路径':'a.pdf'}]
            self.assertEqual(module.locate(rows,root,'P1'),root/'a.pdf')
            rows.append({'编码':'R2','记录ID':'P1','PDF相对路径':'b.pdf'})
            with self.assertRaises(ValueError):module.locate(rows,root,'P1')
            self.assertEqual(module.locate(rows,root,'R1'),root/'a.pdf')
            with self.assertRaises(ValueError):module.locate([{'编码':'R1','记录ID':'P1','PDF相对路径':'../outside.pdf'}],root,'P1')
            with self.assertRaises(FileNotFoundError):module.locate(rows,root,'R2')

if __name__=='__main__':unittest.main()
