from banana.analysis.mri.base import MriAnalysis
from banana.utils.testing import AnalysisTester, PipelineTester, TEST_CACHE_DIR
from banana import FilesetFilter
from arcana.repository.xnat import XnatRepo


class TestMriBaseDefault(AnalysisTester):

    analysis_class = MriAnalysis
    parameters = {'mni_tmpl_resolution': 1}
    inputs = ['magnitude', 'coreg_ref']


class TestMriAnalysis(PipelineTester):

    name = 'BaseMri'
    analysis_class = MriAnalysis
    ref_repo = XnatRepo(server='https://mbi-xnat.erc.monash.edu.au',
                        project_id='TESTBANANAMRI',
                        cache_dir=TEST_CACHE_DIR)
    parameters = {
        'mni_tmpl_resolution': 1}

    def test_preprocess_channels_pipeline(self):
        pass  # Need to upload some raw channel data for this

    def test_coreg_pipeline(self):
        self.run_pipeline_test('coreg_pipeline')

    def test_brain_extraction_pipeline(self):
        self.run_pipeline_test('brain_extraction_pipeline')

    def test_brain_coreg_pipeline(self):
        self.run_pipeline_test('brain_coreg_pipeline',
                               add_inputs=['coreg_ref'])

    def test_coreg_fsl_mat_pipeline(self):
        self.run_pipeline_test('coreg_fsl_mat_pipeline',
                               add_inputs=['coreg_ref'])

    def test_coreg_ants_mat_pipeline(self):
        self.run_pipeline_test('coreg_ants_mat_pipeline',
                               add_inputs=['coreg_ref'])

    def test_coreg_to_tmpl_pipeline(self):
        self.run_pipeline_test('coreg_to_tmpl_pipeline',
                               add_inputs=['coreg_ref'],
                               test_criteria={
                                   'coreg_to_tmpl': {'rms_tol': 20000}})

    def test_qform_transform_pipeline(self):
        self.run_pipeline_test('qform_transform_pipeline',
                               add_inputs=['coreg_ref'])

    def test_preprocess_pipeline(self):
        self.run_pipeline_test('preprocess_pipeline')

    def test_header_extraction_pipeline(self):
        self.run_pipeline_test('header_extraction_pipeline')

    def test_motion_mat_pipeline(self):
        self.run_pipeline_test('motion_mat_pipeline')
