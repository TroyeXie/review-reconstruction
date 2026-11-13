"""Compatibility and provenance invariants for canonical reading records."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('review_records_canonical',Path(__file__).resolve().parents[1]/'scripts'/'review_records.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def source(code,pid,scope='main',path='one.pdf',digest='a'*64,page='1'):
    return {'编码':code,'记录ID':pid,'范围':scope,'PDF相对路径':path,'SHA256':digest,'PDF起始页':page}


def reading(pid,status='MAIN_TEXT_READ',kind='literature',scope='PDF1–5'):
    return {'paper_id':pid,'reading_status':status,'record_kind':kind,'read_scope':scope}


class CanonicalRecords(unittest.TestCase):
    def test_kinds_and_version_states_do_not_share_a_denominator(self):
        index=[source('A1','P1'),source('A2','P2'),source('A3','P3'),source('A4','P4'),source('REG1','R1','registry')]
        readings=[reading('P1'),reading('P1'),reading('P1','PROVIDED_VERSION_MAIN_TEXT_READ_VOR_UNVERIFIED'),
                  reading('P2','PROVIDED_VERSION_MAIN_TEXT_READ_VOR_UNVERIFIED'),reading('P3','PARTIAL_READ'),
                  reading('P4','PUBLISHED_ABSTRACT_READ'),reading('M1',kind='mother_review'),
                  reading('M1',kind='mother_review'),reading('MS1',kind='mother_supplement'),
                  reading('MS2','PROVIDED_VERSION_MAIN_TEXT_READ_VOR_UNVERIFIED','mother_supplement'),
                  reading('R1','REGISTRY_CURRENT_RECORD_READ_HISTORY_UNVERIFIED','registry')]
        result=module.audit(index,readings)
        self.assertFalse(result['errors'])
        self.assertEqual((result['indexed_literature_count'],result['indexed_registry_count']),(4,1))
        self.assertEqual((result['recorded_full_text_read_count'],result['recorded_provided_version_main_text_read_vor_unverified_count']),(1,1))
        self.assertEqual(result['recorded_any_provided_version_main_text_read_count'],2)
        self.assertEqual((result['recorded_mother_read_count'],result['recorded_mother_supplement_read_count'],result['recorded_registry_read_count']),(1,1,1))
        self.assertEqual(result['recorded_mother_supplement_provided_version_read_vor_unverified_count'],1)
        self.assertEqual(result['records_without_full_read_record'],2)

    def test_unknown_values_and_missing_canonical_kind_are_not_guessed(self):
        index=[source('A1','P1'),source('R1','R1','registry')]
        cases=[reading('P1','main_text_read'),reading('P1',kind='unknown'),
               {'paper_id':'P1','reading_status':'MAIN_TEXT_READ','read_scope':'PDF1'},
               reading('R1',kind='registry'),reading('P1',scope=''),
               reading('P1','REGISTRY_REVIEW_PENDING')]
        for row in cases:
            with self.subTest(row=row):
                result=module.audit(index,[row])
                self.assertTrue(result['errors'])
                self.assertEqual(result['recorded_any_provided_version_main_text_read_count'],0)

    def test_unindexed_supplement_requires_explicit_kind(self):
        index=[source('A1','P1')]
        unclassified=reading('T10-SUPPLEMENT1')
        result=module.audit(index,[unclassified])
        self.assertEqual(result['unindexed_reading_ids'],['T10-SUPPLEMENT1'])
        self.assertTrue(result['errors'])
        self.assertEqual(result['recorded_mother_supplement_read_count'],0)
        classified=dict(unclassified,record_kind='mother_supplement')
        result=module.audit(index,[classified])
        self.assertFalse(result['errors'])
        self.assertEqual(result['recorded_mother_supplement_read_count'],1)
        self.assertEqual(result['recorded_any_provided_version_main_text_read_count'],0)

    def alias_fixture(self):
        index=[source('C','P1'),source('A','A1'),source('B','A2'),
               source('D','P2',path='two.pdf',digest='b'*64),source('E','A3',path='two.pdf',digest='b'*64)]
        readings=[reading('P1'),reading('A2'),reading('P2','PROVIDED_VERSION_MAIN_TEXT_READ_VOR_UNVERIFIED')]
        return index,readings

    def test_explicit_aliases_add_coverage_without_fabricating_reads(self):
        index,readings=self.alias_fixture()
        direct=module.audit(index,readings)
        self.assertEqual(direct['recorded_any_provided_version_main_text_read_count'],3)
        self.assertFalse(direct['alias_mapping_supplied'])
        result=module.audit(index,readings,{'A1':'P1','A2':'P1','A3':'P2'})
        self.assertFalse(result['errors'])
        self.assertEqual(result['recorded_any_provided_version_main_text_read_count'],3)
        self.assertEqual(result['alias_added_main_coverage_count'],2)
        self.assertEqual(result['literature_main_text_covered_with_aliases'],3)
        self.assertEqual(result['literature_provided_version_unverified_covered_with_aliases'],2)
        self.assertEqual(result['literature_any_provided_version_main_text_covered_with_aliases'],5)

    def test_alias_metadata_or_endpoint_failure_prevents_partial_application(self):
        for alteration,mapping in [('hash',{'A1':'P1','A3':'P2'}),('page',{'A1':'P1'}),
                                   ('none',{'A1':'UNKNOWN'}),('none',{'P1':'A1'}),
                                   ('none',{'A1':'A2','A2':'P1'})]:
            with self.subTest(alteration=alteration,mapping=mapping):
                index,readings=self.alias_fixture()
                if alteration=='hash':index[1]['SHA256']='f'*64
                if alteration=='page':index[1]['PDF起始页']='27'
                result=module.audit(index,readings,mapping)
                self.assertTrue(result['errors'])
                self.assertEqual(result['alias_added_main_coverage_count'],0)
                self.assertEqual(result['validated_alias_mapping_count'],0)
                self.assertEqual(result['literature_any_provided_version_main_text_covered_with_aliases'],3)

    def test_alias_loader_accepts_checkpoint_but_rejects_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'aliases.json'
            path.write_text(json.dumps({'updated_at':'example','reviewed_shared_evidence_aliases':{'A1':'P1'}}),encoding='utf-8')
            self.assertEqual(module.load_aliases(path),{'A1':'P1'})
            path.write_text('{"A1":"P1","A1":"P2"}',encoding='utf-8')
            with self.assertRaises(ValueError):module.load_aliases(path)


    def test_correction_is_read_without_becoming_main_text(self):
        index=[source('P','P1'),source('C','C1'),source('U','U1')]
        rows=[reading('P1'),reading('C1','PUBLISHED_CORRECTION_READ','correction'),
              reading('C1','PUBLISHED_CORRECTION_READ','correction')]
        result=module.audit(index,rows)
        self.assertFalse(result['errors'])
        self.assertEqual(result['indexed_literature_count'],3)
        self.assertEqual(result['recorded_any_provided_version_main_text_read_count'],1)
        self.assertEqual(result['recorded_correction_read_count'],1)
        self.assertEqual(result['records_without_full_read_record'],2)
        self.assertEqual(result['unread_literature_record_count'],1)
        self.assertEqual(result['unread_literature_records_after_explicit_aliases'],1)

    def test_auxiliary_reading_stays_outside_original_coverage(self):
        index=[source('P','P1')]
        rows=[reading('A1','PARTIAL_READ','analyst_associated_literature'),
              reading('A1','PARTIAL_READ','analyst_associated_literature'),
              reading('A2','MAIN_TEXT_READ','analyst_associated_literature')]
        result=module.audit(index,rows)
        self.assertFalse(result['errors'])
        self.assertEqual(result['indexed_literature_count'],1)
        self.assertEqual(result['recorded_any_provided_version_main_text_read_count'],0)
        self.assertEqual(result['recorded_partial_read_only_count'],0)
        self.assertEqual(result['unread_literature_record_count'],1)
        self.assertEqual(result['recorded_auxiliary_record_count'],2)
        self.assertEqual(result['auxiliary_reading_counts']['partial_read_only'],1)
        self.assertEqual(result['auxiliary_reading_counts']['main_text_read'],1)

    def test_correction_and_auxiliary_invalid_combinations_are_rejected(self):
        index=[source('P','P1'),source('REG','R1','registry')]
        invalid=[reading('P1','PUBLISHED_CORRECTION_READ'),
                 reading('P1','MAIN_TEXT_READ','correction'),
                 reading('P1','PARTIAL_READ','correction'),
                 reading('P1','PUBLISHED_CORRECTION_READ','correction',scope=''),
                 reading('OUT','PUBLISHED_CORRECTION_READ','correction'),
                 reading('R1','PUBLISHED_CORRECTION_READ','correction'),
                 reading('P1','PARTIAL_READ','analyst_associated_literature'),
                 reading('OUT','REGISTRY_REVIEW_PENDING','analyst_associated_literature'),
                 reading('OUT','PUBLISHED_CORRECTION_READ','analyst_associated_literature'),
                 reading('OUT','PARTIAL_READ','aux'),
                 reading('OUT','unknown','analyst_associated_literature')]
        for row in invalid:
            with self.subTest(row=row):
                result=module.audit(index,[row])
                self.assertTrue(result['errors'])
                self.assertEqual(result['recorded_any_provided_version_main_text_read_count'],0)
                self.assertEqual(result['recorded_correction_read_count'],0)
                self.assertEqual(result['recorded_auxiliary_record_count'],0)
        bad_index=[dict(source('A','A1'),record_kind='analyst_associated_literature')]
        self.assertTrue(module.audit(bad_index,[])['errors'])

    def test_aliases_cannot_promote_corrections_or_auxiliary_records(self):
        index=[source('P','P1'),source('C','C1'),source('A','A1')]
        rows=[reading('P1'),reading('C1','PUBLISHED_CORRECTION_READ','correction'),
              reading('OUT','MAIN_TEXT_READ','analyst_associated_literature')]
        for mapping in [{'C1':'P1'},{'A1':'C1'},{'A1':'OUT'},{'OUT':'P1'},
                        {'A1':'P1','C1':'P1'}]:
            with self.subTest(mapping=mapping):
                result=module.audit(index,rows,mapping)
                self.assertTrue(result['errors'])
                self.assertEqual(result['validated_alias_mapping_count'],0)
                self.assertEqual(result['alias_added_main_coverage_count'],0)
                self.assertEqual(result['literature_any_provided_version_main_text_covered_with_aliases'],1)
                self.assertEqual(result['recorded_correction_read_count'],1)
                self.assertEqual(result['unread_literature_records_after_explicit_aliases'],1)

    def test_conflicting_correction_and_main_declarations_do_not_gain_coverage(self):
        index=[source('P','P1'),source('A','A1')]
        rows=[reading('P1'),reading('P1','PUBLISHED_CORRECTION_READ','correction')]
        result=module.audit(index,rows,{'A1':'P1'})
        self.assertTrue(result['errors'])
        self.assertEqual(result['recorded_any_provided_version_main_text_read_count'],0)
        self.assertEqual(result['recorded_correction_read_count'],0)
        self.assertEqual(result['alias_added_main_coverage_count'],0)
        self.assertEqual(result['unread_literature_record_count'],2)


if __name__=='__main__':unittest.main()
