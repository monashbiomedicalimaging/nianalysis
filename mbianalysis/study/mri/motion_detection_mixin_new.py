from nianalysis.dataset import DatasetSpec, FieldSpec, Field
from mbianalysis.data_format import (
    mrconvert_nifti_gz_format, text_matrix_format, directory_format, text_format,
    png_format, dicom_format, motion_mats_format)
from mbianalysis.interfaces.custom.motion_correction import (
    MeanDisplacementCalculation, MotionFraming, PlotMeanDisplacementRC,
    AffineMatAveraging, PetCorrectionFactor, FrameAlign2Reference,
    CreateMocoSeries)
from mbianalysis.citation import fsl_cite
from nianalysis.study.base import StudyMetaClass
from nianalysis.study.multi import (
    MultiStudy, SubStudySpec, MultiStudyMetaClass)
from .base import MRIStudy
from .structural.t1 import T1Study
from .structural.t2 import T2Study
from .epi import EPIStudy
from nipype.interfaces.utility import Merge
from .structural.diffusion_coreg import DWIStudy
#     CoregisteredDiffusionStudy,
#     CoregisteredDiffusionReferenceOppositeStudy,
#     CoregisteredDiffusionReferenceStudy)
from mbianalysis.requirement import fsl509_req
from nianalysis.exception import NiAnalysisNameError
from nianalysis.dataset import DatasetMatch
import logging
# from mbianalysis.study.mri.structural.ute import CoregisteredUTEStudy
from nianalysis.interfaces.utils import CopyToDir
import os
from nianalysis.option import OptionSpec
import numpy as np
# from mbianalysis.study.mri.structural.diffusion_coreg import DWIStudy


logger = logging.getLogger('NiAnalysis')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

logging.getLogger("urllib3").setLevel(logging.WARNING)

template_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../../mbianalysis',
                 'reference_data'))


class MotionReferenceT1Study(T1Study):

    __metaclass__ = StudyMetaClass

    add_data_specs = [
        DatasetSpec('wm_seg', mrconvert_nifti_gz_format, 'segmentation_pipeline'),
        DatasetSpec('motion_mats', motion_mats_format,
                    'header_info_extraction_pipeline'),
        FieldSpec('tr', dtype=float, pipeline_name='header_info_extraction_pipeline'),
        FieldSpec('start_time', str,
                  pipeline_name='header_info_extraction_pipeline'),
        FieldSpec('real_duration', str,
                  pipeline_name='header_info_extraction_pipeline'),
        FieldSpec('tot_duration', str,
                  pipeline_name='header_info_extraction_pipeline'),
        FieldSpec('ped', str, pipeline_name='header_info_extraction_pipeline'),
        FieldSpec('pe_angle', str,
                  pipeline_name='header_info_extraction_pipeline'),
        DatasetSpec('dcm_info', text_format, 'header_info_extraction_pipeline'),
        DatasetSpec('preproc', mrconvert_nifti_gz_format, 'basic_preproc_pipeline')]

    add_option_specs = [
        OptionSpec('preproc_resolution', [1])]

    def header_info_extraction_pipeline(self, **kwargs):
        return (super(MotionReferenceT1Study, self).
                header_info_extraction_pipeline_factory(
                    'primary', ref=True, multivol=False, **kwargs))

    def segmentation_pipeline(self, **kwargs):
        pipeline = super(MotionReferenceT1Study, self).segmentation_pipeline(
            img_type=1, **kwargs)
        return pipeline


class MotionReferenceT2Study(T2Study):

    __metaclass__ = StudyMetaClass

    add_data_specs = [
        DatasetSpec('wm_seg', mrconvert_nifti_gz_format, 'segmentation_pipeline'),
        DatasetSpec('motion_mats', motion_mats_format,
                    'header_info_extraction_pipeline'),
        FieldSpec('tr', dtype=float, pipeline_name='header_info_extraction_pipeline'),
        FieldSpec('start_time', str,
                  pipeline_name='header_info_extraction_pipeline'),
        FieldSpec('real_duration', str,
                  pipeline_name='header_info_extraction_pipeline'),
        FieldSpec('tot_duration', str,
                  pipeline_name='header_info_extraction_pipeline'),
        FieldSpec('ped', str, pipeline_name='header_info_extraction_pipeline'),
        FieldSpec('pe_angle', str,
                  pipeline_name='header_info_extraction_pipeline'),
        DatasetSpec('dcm_info', text_format,
                    'header_info_extraction_pipeline'),
        DatasetSpec('preproc', mrconvert_nifti_gz_format,
                    'basic_preproc_pipeline')]

    add_option_specs = [
        OptionSpec('preproc_resolution', [1])]

    def header_info_extraction_pipeline(self, **kwargs):
        return (super(MotionReferenceT2Study, self).
                header_info_extraction_pipeline_factory(
                    'primary', ref=True, multivol=False, **kwargs))

    def segmentation_pipeline(self, **kwargs):
        pipeline = super(MotionReferenceT2Study, self).segmentation_pipeline(
            img_type=2, **kwargs)
        return pipeline


class MotionDetectionMixin(MultiStudy):

    __metaclass__ = MultiStudyMetaClass

    add_sub_study_specs = []

    add_data_specs = [
        DatasetSpec('mean_displacement', text_format,
                    'mean_displacement_pipeline'),
        DatasetSpec('mean_displacement_rc', text_format,
                    'mean_displacement_pipeline'),
        DatasetSpec('mean_displacement_consecutive', text_format,
                    'mean_displacement_pipeline'),
        DatasetSpec('mats4average', text_format,
                    'mean_displacement_pipeline'),
        DatasetSpec('start_times', text_format,
                    'mean_displacement_pipeline'),
        DatasetSpec('motion_par_rc', text_format,
                    'mean_displacement_pipeline'),
        DatasetSpec('motion_par', text_format,
                    'mean_displacement_pipeline'),
        DatasetSpec('offset_indexes', text_format,
                    'mean_displacement_pipeline'),
        DatasetSpec('frame_start_times', text_format,
                    'motion_framing_pipeline'),
        DatasetSpec('frame_vol_numbers', text_format,
                    'motion_framing_pipeline'),
        DatasetSpec('timestamps', directory_format,
                    'motion_framing_pipeline'),
        DatasetSpec('mean_displacement_plot', png_format,
                    'plot_mean_displacement_pipeline'),
        DatasetSpec('average_mats', directory_format,
                    'frame_mean_transformation_mats_pipeline'),
        DatasetSpec('correction_factors', text_format,
                    'pet_correction_factors_pipeline'),
        DatasetSpec('umaps_align2ref', directory_format,
                    'frame2ref_alignment_pipeline'),
        DatasetSpec('frame2reference_mats', directory_format,
                    'frame2ref_alignment_pipeline'),
        DatasetSpec('motion_detection_output', directory_format,
                    'gather_outputs_pipeline'),
        DatasetSpec('moco_series', directory_format,
                    'create_moco_series_pipeline')]

    add_option_specs = [OptionSpec('framing_th', 2.0),
                        OptionSpec('framing_temporal_th', 30.0),
                        OptionSpec('md_framing', True),
                        OptionSpec('align_pct', False),
                        OptionSpec('align_fixed_binning', False),
                        OptionSpec('moco_template', os.path.join(
                            template_path, 'moco_template.IMA'))]

    def mean_displacement_pipeline(self, **kwargs):
        inputs = [DatasetSpec('ref_brain', mrconvert_nifti_gz_format)]
        sub_study_names = []
        for sub_study_spec in self.sub_study_specs():
            try:
                inputs.append(
                    self.data_spec(sub_study_spec.inverse_map('motion_mats')))
                inputs.append(self.data_spec(sub_study_spec.inverse_map('tr')))
                inputs.append(
                    self.data_spec(sub_study_spec.inverse_map('start_time')))
                inputs.append(
                    self.data_spec(sub_study_spec.inverse_map('real_duration')))
                sub_study_names.append(sub_study_spec.name)
            except NiAnalysisNameError:
                continue  # Sub study doesn't have motion mat

        pipeline = self.create_pipeline(
            name='mean_displacement_calculation',
            inputs=inputs,
            outputs=[DatasetSpec('mean_displacement', text_format),
                     DatasetSpec('mean_displacement_rc', text_format),
                     DatasetSpec('mean_displacement_consecutive', text_format),
                     DatasetSpec('start_times', text_format),
                     DatasetSpec('motion_par_rc', text_format),
                     DatasetSpec('motion_par', text_format),
                     DatasetSpec('offset_indexes', text_format),
                     DatasetSpec('mats4average', text_format)],
            desc=("Calculate the mean displacement between each motion"
                         " matrix and a reference."),
            version=1,
            citations=[fsl_cite],
            **kwargs)

        num_motion_mats = len(sub_study_names)
        merge_motion_mats = pipeline.create_node(Merge(num_motion_mats),
                                                 name='merge_motion_mats')
        merge_tr = pipeline.create_node(Merge(num_motion_mats),
                                        name='merge_tr')
        merge_start_time = pipeline.create_node(Merge(num_motion_mats),
                                                name='merge_start_time')
        merge_real_duration = pipeline.create_node(Merge(num_motion_mats),
                                                   name='merge_real_duration')

        for i, sub_study_name in enumerate(sub_study_names, start=1):
            spec = self.sub_study_spec(sub_study_name)
            pipeline.connect_input(
                spec.inverse_map('motion_mats'), merge_motion_mats,
                'in{}'.format(i))
            pipeline.connect_input(
                spec.inverse_map('tr'), merge_tr,
                'in{}'.format(i))
            pipeline.connect_input(
                spec.inverse_map('start_time'), merge_start_time,
                'in{}'.format(i))
            pipeline.connect_input(
                spec.inverse_map('real_duration'), merge_real_duration,
                'in{}'.format(i))

        md = pipeline.create_node(MeanDisplacementCalculation(),
                                  name='scan_time_info')
        pipeline.connect(merge_motion_mats, 'out', md, 'motion_mats')
        pipeline.connect(merge_tr, 'out', md, 'trs')
        pipeline.connect(merge_start_time, 'out', md, 'start_times')
        pipeline.connect(merge_real_duration, 'out', md, 'real_durations')
        pipeline.connect_input('ref_brain', md, 'reference')
        pipeline.connect_output('mean_displacement', md, 'mean_displacement')
        pipeline.connect_output(
            'mean_displacement_rc', md, 'mean_displacement_rc')
        pipeline.connect_output(
            'mean_displacement_consecutive', md,
            'mean_displacement_consecutive')
        pipeline.connect_output('start_times', md, 'start_times')
        pipeline.connect_output('motion_par_rc', md, 'motion_parameters_rc')
        pipeline.connect_output('motion_par', md, 'motion_parameters')
        pipeline.connect_output('offset_indexes', md, 'offset_indexes')
        pipeline.connect_output('mats4average', md, 'mats4average')
        return pipeline

    def motion_framing_pipeline(self, **kwargs):
        return self.motion_framing_pipeline_factory(
            pet_data_dir=None, pet_start_time=None, pet_duration=None,
            **kwargs)

    def motion_framing_pipeline_factory(
            self, pet_data_dir=None, pet_start_time=None, pet_duration=None,
            **kwargs):
        inputs = [DatasetSpec('mean_displacement', text_format),
                  DatasetSpec('mean_displacement_consecutive', text_format),
                  DatasetSpec('start_times', text_format)]
        if pet_data_dir is not None:
            inputs.append(DatasetSpec(pet_data_dir, directory_format))
        elif pet_start_time is not None and pet_duration is not None:
            inputs.append(FieldSpec(pet_start_time, str))
            inputs.append(FieldSpec(pet_duration, str))
        pipeline = self.create_pipeline(
            name='motion_framing',
            inputs=inputs,
            outputs=[DatasetSpec('frame_start_times', text_format),
                     DatasetSpec('frame_vol_numbers', text_format),
                     DatasetSpec('timestamps', directory_format)],
            desc=("Calculate when the head movement exceeded a "
                         "predefined threshold (default 2mm)."),
            version=1,
            citations=[fsl_cite],
            **kwargs)

        framing = pipeline.create_node(MotionFraming(), name='motion_framing')
        framing.inputs.motion_threshold = pipeline.option('framing_th')
        framing.inputs.temporal_threshold = pipeline.option('framing_temporal_th')
        pipeline.connect_input('mean_displacement', framing,
                               'mean_displacement')
        pipeline.connect_input('mean_displacement_consecutive', framing,
                               'mean_displacement_consec')
        pipeline.connect_input('start_times', framing, 'start_times')
        if pet_data_dir is not None:
            pipeline.connect_input('pet_data_dir', framing, 'pet_data_dir')
        elif pet_start_time is not None and pet_duration is not None:
            pipeline.connect_input('pet_start_time', framing, 'pet_start_time')
            pipeline.connect_input('pet_duration', framing, 'pet_duration')
#         else:
#             framing.inputs.pet_data_dir = None
        pipeline.connect_output('frame_start_times', framing,
                                'frame_start_times')
        pipeline.connect_output('frame_vol_numbers', framing,
                                'frame_vol_numbers')
        pipeline.connect_output('timestamps', framing, 'timestamps_dir')
        return pipeline

    def plot_mean_displacement_pipeline(self, **kwargs):

        pipeline = self.create_pipeline(
            name='plot_mean_displacement',
            inputs=[DatasetSpec('mean_displacement_rc', text_format),
                    DatasetSpec('offset_indexes', text_format),
                    DatasetSpec('frame_start_times', text_format)],
            outputs=[DatasetSpec('mean_displacement_plot', png_format)],
            desc=("Plot the mean displacement real clock"),
            version=1,
            citations=[fsl_cite],
            **kwargs)

        plot_md = pipeline.create_node(PlotMeanDisplacementRC(),
                                       name='plot_md')
        plot_md.inputs.framing = pipeline.option('md_framing')
        pipeline.connect_input('mean_displacement_rc', plot_md,
                               'mean_disp_rc')
        pipeline.connect_input('offset_indexes', plot_md,
                               'false_indexes')
        pipeline.connect_input('frame_start_times', plot_md,
                               'frame_start_times')
        pipeline.connect_output('mean_displacement_plot', plot_md,
                                'mean_disp_plot')
        return pipeline

    def frame_mean_transformation_mats_pipeline(self, **kwargs):

        pipeline = self.create_pipeline(
            name='frame_mean_transformation_mats',
            inputs=[DatasetSpec('mats4average', text_format),
                    DatasetSpec('frame_vol_numbers', text_format)],
            outputs=[DatasetSpec('average_mats', directory_format)],
            desc=("Average all the transformation mats within each "
                         "detected frame."),
            version=1,
            citations=[fsl_cite],
            **kwargs)

        average = pipeline.create_node(AffineMatAveraging(),
                                       name='mats_averaging')
        pipeline.connect_input('frame_vol_numbers', average,
                               'frame_vol_numbers')
        pipeline.connect_input('mats4average', average,
                               'all_mats4average')
        pipeline.connect_output('average_mats', average,
                                'average_mats')
        return pipeline

    def pet_correction_factors_pipeline(self, **kwargs):

        pipeline = self.create_pipeline(
            name='pet_correction_factors',
            inputs=[DatasetSpec('timestamps', directory_format)],
            outputs=[DatasetSpec('correction_factors', text_format)],
            desc=("Pipeline to calculate the correction factors to "
                         "account for frame duration when averaging the PET "
                         "frames to create the static PET image"),
            version=1,
            citations=[fsl_cite],
            **kwargs)

        corr_factors = pipeline.create_node(PetCorrectionFactor(),
                                            name='pet_corr_factors')
        pipeline.connect_input('timestamps', corr_factors,
                               'timestamps')
        pipeline.connect_output('correction_factors', corr_factors,
                                'corr_factors')
        return pipeline

    def frame2ref_alignment_pipeline_factory(
            self, name, average_mats, ute_regmat, ute_qform_mat,
            umap=None, **kwargs):
        inputs = [DatasetSpec(average_mats, directory_format),
                  DatasetSpec(ute_regmat, text_matrix_format),
                  DatasetSpec(ute_qform_mat, text_matrix_format)]
        outputs = [DatasetSpec('frame2reference_mats', directory_format)]
        if umap:
            inputs.append(DatasetSpec(umap, mrconvert_nifti_gz_format))
            outputs.append(DatasetSpec('umaps_align2ref', directory_format))

        pipeline = self.create_pipeline(
            name=name,
            inputs=inputs,
            outputs=outputs,
            desc=("Pipeline to create an affine mat to align each "
                         "detected frame to the reference. If umap is provided"
                         ", it will be also aligned to match the head position"
                         " in each frame and improve the static PET image "
                         "quality."),
            version=1,
            citations=[fsl_cite],
            **kwargs)

        frame_align = pipeline.create_node(
            FrameAlign2Reference(), name='frame2ref_alignment',
            requirements=[fsl509_req])
        frame_align.inputs.pct = pipeline.option('align_pct')
        frame_align.inputs.fixed_binning = pipeline.option('align_fixed_binning')
        pipeline.connect_input(average_mats, frame_align,
                               'average_mats')
        pipeline.connect_input(ute_regmat, frame_align,
                               'ute_regmat')
        pipeline.connect_input(ute_qform_mat, frame_align,
                               'ute_qform_mat')
        if umap:
            pipeline.connect_input(umap, frame_align, 'umap')
            pipeline.connect_output('umaps_align2ref', frame_align,
                                    'umaps_align2ref')
        pipeline.connect_output('frame2reference_mats', frame_align,
                                'frame2reference_mats')
        return pipeline

    def frame2ref_alignment_pipeline(self, **kwargs):
        return self.frame2ref_alignment_pipeline_factory(
            'frame2ref_alignment', 'average_mats', 'ute_reg_mat',
            'ute_qform_mat', umap='umap_nifti',
            pct=False, fixed_binning=False, **kwargs)

    def create_moco_series_pipeline(self, **kwargs):

        pipeline = self.create_pipeline(
            name='create_moco_series',
            inputs=[DatasetSpec('start_times', text_format),
                    DatasetSpec('motion_par', text_format)],
            outputs=[DatasetSpec('moco_series', directory_format)],
            desc=("Pipeline to generate a moco_series that can be then "
                         "imported back in the scanner and used to correct the"
                         " pet data"),
            version=1,
            citations=[fsl_cite],
            **kwargs)

        moco = pipeline.create_node(CreateMocoSeries(),
                                    name='create_moco_series')
        pipeline.connect_input('start_times', moco, 'start_times')
        pipeline.connect_input('motion_par', moco, 'motion_par')
        moco.inputs.moco_template = pipeline.option('moco_template')

        pipeline.connect_output('moco_series', moco, 'modified_moco')
        return pipeline

    def gather_outputs_factory(self, name, align_mats=False,
                               pet_corr_fac=False, aligned_umaps=False,
                               timestamps=False, ute=None, **kwargs):
        inputs = [DatasetSpec('mean_displacement_plot', png_format),
                  DatasetSpec('motion_par', text_format)]
        if align_mats:
            inputs.append(
                DatasetSpec('frame2reference_mats', directory_format))
        if pet_corr_fac:
            inputs.append(DatasetSpec('correction_factors', text_format))
        if aligned_umaps:
            inputs.append(
                DatasetSpec('umaps_align2ref_dicom', directory_format))
        if timestamps:
            inputs.append(DatasetSpec('timestamps', directory_format))
        if ute is not None:
            inputs.append(DatasetSpec(ute, mrconvert_nifti_gz_format))

        pipeline = self.create_pipeline(
            name=name,
            inputs=inputs,
            outputs=[DatasetSpec('motion_detection_output', directory_format)],
            desc=("Pipeline to gather together all the outputs from "
                         "the motion detection pipeline."),
            version=1,
            citations=[fsl_cite],
            **kwargs)

        merge_inputs = pipeline.create_node(Merge(len(inputs)),
                                            name='merge_inputs')
        for i, dataset in enumerate(inputs, start=1):
            pipeline.connect_input(
                dataset.name, merge_inputs, 'in{}'.format(i))

        copy2dir = pipeline.create_node(CopyToDir(), name='copy2dir')
        pipeline.connect(merge_inputs, 'out', copy2dir, 'in_files')

        pipeline.connect_output('motion_detection_output', copy2dir, 'out_dir')
        return pipeline

    def gather_outputs_pipeline(self, **kwargs):
        return self.gather_outputs_factory(
            'gather_md_outputs', pet_corr_fac=False, aligned_umaps=False,
            timestamps=False, align_mats=False, **kwargs)


def create_motion_detection_class(name, ref=None, ref_type=None, t1s=None,
                                  utes=None, t2s=None, dmris=None, epis=None,
                                  umaps=None, dynamic=False,
                                  pet_data_dir=None, pet_time_info=None):

    inputs = []
    dct = {}
    data_specs = []
    run_pipeline = False
    if pet_data_dir is not None:
        data_specs.append(DatasetSpec('pet_data_dir', directory_format))
        inputs.append(DatasetMatch('pet_data_dir', directory_format,
                                   pet_data_dir))

        def motion_framing_pipeline_altered(self, **kwargs):
            return self.motion_framing_pipeline_factory(
                pet_data_dir='pet_data_dir', **kwargs)

        dct['motion_framing_pipeline'] = motion_framing_pipeline_altered
        data_specs.append(
            DatasetSpec('frame_start_times', text_format,
                        'motion_framing_pipeline_altered'))
        data_specs.append(
            DatasetSpec('frame_vol_numbers', text_format,
                        'motion_framing_pipeline_altered'))
        data_specs.append(
            DatasetSpec('timestamps', directory_format,
                        'motion_framing_pipeline_altered'))

    if not ref:
        raise Exception('A reference image must be provided!')
    if ref_type == 't1':
        ref_study = T1Study
    elif ref_type == 't2':
        ref_study = T2Study
    else:
        raise Exception('{} is not a recognized ref_type!The available '
                        'ref_types are t1 or t2.'.format(ref_type))

    study_specs = [SubStudySpec('ref', ref_study)]
    ref_spec = {'ref_brain': 'coreg_ref_brain'}
    inputs.append(DatasetMatch('ref_primary', dicom_format, ref))

#     dct['ref_header_info_extraction_pipeline'] = MultiStudy.translate(
#         'ref', 'header_info_extraction_pipeline_factory',
#         dcm_in_name='primary', ref=True, multivol=False)

    dct['ref_motion_mats_pipeline'] = MultiStudy.translate(
        'ref', 'motion_mats_pipeline', ref=True)

#     if not utes:
#         logger.info('UTE not provided. The matrices that realign the PET image'
#                     ' in each detected frame to the reference cannot be '
#                     'generated')
# 
#         def gather_md_outputs_pipeline_altered(self, **kwargs):
#             return self.gather_outputs_factory(
#                 'gather_md_outputs', pet_corr_fac=True, aligned_umaps=False,
#                 timestamps=True, align_mats=False)
# 
#         dct['gather_outputs_pipeline'] = (
#             gather_md_outputs_pipeline_altered)
# 
#     elif utes and not umaps:
#         logger.info('Umap not provided. The umap realignment will not be '
#                     'performed. Matrices that realign each detected frame to '
#                     'the reference will be calculated.')
# 
#         study_specs.extend(
#                 [SubStudySpec('ute_{}'.format(i), CoregisteredUTEStudy,
#                               ref_spec) for i in range(len(utes))])
#         inputs.extend(DatasetMatch('ute_{}_ute'.format(i), dicom_format,
#                                    ute_scan)
#                       for i, ute_scan in enumerate(utes))
# 
#         def frame2ref_alignment_pipeline_altered(self, **kwargs):
#             return self.frame2ref_alignment_pipeline_factory(
#                 'frame2ref_alignment', 'average_mats',
#                 'ute_{}_ute_reg_mat'.format(len(utes)-1),
#                 'ute_{}_ute_qform_mat'.format(len(utes)-1), umap=None,
#                 pct=False, fixed_binning=False, **kwargs)
# 
#         def gather_md_outputs_pipeline_altered(self, **kwargs):
#             return self.gather_outputs_factory(
#                 'gather_md_outputs', pet_corr_fac=True, aligned_umaps=False,
#                 timestamps=True, align_mats=True)
# 
#         dct['gather_outputs_pipeline'] = (
#             gather_md_outputs_pipeline_altered)
#         dct['frame2ref_alignment_pipeline'] = (
#             frame2ref_alignment_pipeline_altered)
#         data_specs.append(DatasetSpec(
#             'frame2reference_mats', directory_format,
#             frame2ref_alignment_pipeline_altered))
#         run_pipeline = True
# 
#     elif utes and umaps:
#         logger.info('Umap will be realigned to match the head position in '
#                     'each frame. Matrices that realign each frame to the '
#                     'reference will be calculated.')
#         if len(umaps) > 1:
#             raise Exception('Please provide just one umap.')
#         ute_spec = ref_spec.copy()
#         ute_spec.update({'umaps_align2ref': 'umap_aligned_niftis',
#                          'umaps_align2ref_dicom': 'umap_aligned_dicoms'})
#         study_specs.extend(
#                 [SubStudySpec('ute_{}'.format(i), CoregisteredUTEStudy,
#                               ute_spec) for i in range(len(utes))])
#         inputs.extend(DatasetMatch('ute_{}_ute'.format(i), dicom_format,
#                                    ute_scan)
#                       for i, ute_scan in enumerate(utes))
# 
#         def frame2ref_alignment_pipeline_altered(self, **kwargs):
#             return self.frame2ref_alignment_pipeline_factory(
#                 'frame2ref_alignment', 'average_mats',
#                 'ute_{}_ute_reg_mat'.format(len(utes)-1),
#                 'ute_{}_ute_qform_mat'.format(len(utes)-1),
#                 umap='ute_{}_umap_nifti'.format(len(utes)-1),
#                 pct=False, fixed_binning=False, **kwargs)
# 
#         def gather_md_outputs_pipeline_altered(self, **kwargs):
#             return self.gather_outputs_factory(
#                 'gather_md_outputs', pet_corr_fac=True, aligned_umaps=True,
#                 timestamps=True, align_mats=True,
#                 ute='ute_{}_ute_preproc'.format(len(utes)-1))
# 
#         dct['gather_outputs_pipeline'] = (
#             gather_md_outputs_pipeline_altered)
#         dct['frame2ref_alignment_pipeline'] = (
#             frame2ref_alignment_pipeline_altered)
#         dct['nii2dcm_conversion_pipeline'] = MultiStudy.translate(
#             'ute_{}'.format(len(utes)-1), CoregisteredUTEStudy.
#             nifti2dcm_conversion_pipeline)
#         inputs.append(DatasetMatch('ute_{}_umap'.format(len(utes)-1),
#                                    dicom_format, umaps[0]))
#         data_specs.append(
#             DatasetSpec('frame2reference_mats', directory_format,
#                         'frame2ref_alignment_pipeline_altered'))
#         data_specs.append(
#             DatasetSpec('umaps_align2ref', directory_format,
#                         'frame2ref_alignment_pipeline_altered'))
#         data_specs.append(
#             DatasetSpec('umaps_align2ref_dicom', directory_format,
#                         dct['nii2dcm_conversion_pipeline']))
#         run_pipeline = True
# 
#     elif not utes and umaps:
#         logger.warning('Umap provided without corresponding UTE image. '
#                        'Realignment cannot be performed without UTE. Umap will'
#                        'be ignored.')
    if t1s:
        study_specs.extend(
                [SubStudySpec('t1_{}'.format(i), T1Study,
                              ref_spec) for i in range(len(t1s))])
        inputs.extend(
            DatasetMatch('t1_{}_primary'.format(i), dicom_format, t1_scan)
            for i, t1_scan in enumerate(t1s))
        run_pipeline = True

    if t2s:
        study_specs.extend(
                [SubStudySpec('t2_{}'.format(i), T2Study,
                              ref_spec) for i in range(len(t2s))])
        inputs.extend(DatasetMatch('t2_{}_primary'.format(i), dicom_format,
                                   t2_scan)
                      for i, t2_scan in enumerate(t2s))
        run_pipeline = True
    if epis:
        epi_refspec = ref_spec.copy()
        epi_refspec.update({'ref_wm_seg': 'coreg_ref_wmseg',
                            'ref_preproc': 'coreg_ref_preproc'})
        study_specs.extend([SubStudySpec('epi_{}'.format(i), EPIStudy,
                            epi_refspec)
                            for i in range(len(epis))])
        inputs.extend(
            DatasetMatch('epi_{}_primary'.format(i), dicom_format, epi_scan)
            for i, epi_scan in enumerate(epis))
        run_pipeline = True
    if dmris:
        used_dwi = []
        dmris_main = [x for x in dmris if x[-1] == '0']
        dmris_ref = [x for x in dmris if x[-1] == '1']
        dmris_opposite = [x for x in dmris if x[-1] == '-1']
        if dmris_main and not dmris_opposite:
            print ('No opposite phase encoding direction b0 provided. DWI '
                   'motion correction will be performed without distortion '
                   'correction. THIS IS SUB-OPTIMAL!')
            study_specs.extend(
                SubStudySpec('dwi_{}'.format(i), DWIStudy, ref_spec)
                 for i in range(len(dmris_main)))
            inputs.extend(
                DatasetMatch('dwi_{}_dwi_main'.format(i), dicom_format,
                             dmris_main_scan[0])
                for i, dmris_main_scan in enumerate(dmris_main))

            def dwi_main_preproc_pipeline_altered(self, **kwargs):
                return self.dwi_main_preproc_pipeline(
                    distortion_correction=False)
            dct['dwi_main_preproc_pipeline'] = (
                dwi_main_preproc_pipeline_altered)
            used_dwi.extend(scan for scan in dmris_main)
        if not dmris_main and (dmris_ref and dmris_opposite):
            min_index = min(len(dmris_opposite), len(dmris_ref))
            study_specs.extend(
                SubStudySpec('dwi_{}'.format(i), DWIStudy, ref_spec)
                 for i in range(min_index))
            inputs.extend(
                DatasetMatch('dwi_{}_dwi_ref_plus'.format(i), dicom_format,
                             dmris_ref[i][0]) for i in range(min_index))
            inputs.extend(
                DatasetMatch('dwi_{}_dwi_ref_minus'.format(i), dicom_format,
                             dmris_opposite[i][0]) for i in range(min_index))
            used_dwi.extend(scan for scan in dmris_ref[:min_index]+
                            dmris_opposite[:min_index])
        if dmris_main and dmris_opposite and not dmris_ref:
            study_specs.extend(
                SubStudySpec('dwi_{}'.format(i), DWIStudy, ref_spec)
                 for i in range(len(dmris_main)))
            inputs.extend(
                DatasetMatch('dwi_{}_dwi_main'.format(i), dicom_format,
                             dmris_main[i][0]) for i in range(len(dmris_main)))
            if len(dmris_main) <= len(dmris_opposite):
                inputs.extend(
                    DatasetMatch('dwi_{}_dwi_ref_minus'.format(i), dicom_format,
                                 dmris_opposite[i][0]) for i in range(len(dmris_main)))
                used_dwi.extend(scan for scan in dmris_main+
                                dmris_opposite[:len(dmris_main)])
            else:
                inputs.extend(
                    DatasetMatch('dwi_{}_dwi_ref_minus'.format(i), dicom_format,
                                 dmris_opposite[0][0]) for i in range(len(dmris_main)))
                used_dwi.extend(scan for scan in dmris_main+dmris_opposite[:1])
            
        if dmris_main and dmris_opposite and dmris_ref:
            study_specs.extend(
                SubStudySpec('dwi_{}'.format(i), DWIStudy, ref_spec)
                 for i in range(len(dmris_main)))
            inputs.extend(
                DatasetMatch('dwi_{}_dwi_main'.format(i), dicom_format,
                             dmris_main[i][0]) for i in range(len(dmris_main)))
            if (len(dmris_main) <= len(dmris_opposite) and
                    len(dmris_main) <= len(dmris_ref)):
                inputs.extend(
                    DatasetMatch('dwi_{}_dwi_ref_minus'.format(i), dicom_format,
                                 dmris_opposite[i][0]) for i in range(len(dmris_main)))
                inputs.extend(
                    DatasetMatch('dwi_{}_dwi_ref_plus'.format(i), dicom_format,
                                 dmris_ref[i][0]) for i in range(len(dmris_main)))
                used_dwi.extend(scan for scan in dmris_main+
                                dmris_opposite[:len(dmris_main)]+dmris_ref[:len(dmris_main)])
            else:
                inputs.extend(
                    DatasetMatch('dwi_{}_dwi_ref_minus'.format(i), dicom_format,
                                 dmris_opposite[0][0]) for i in range(len(dmris_main)))
                inputs.extend(
                    DatasetMatch('dwi_{}_dwi_ref_plus'.format(i), dicom_format,
                                 dmris_ref[0][0]) for i in range(len(dmris_main)))
                used_dwi.extend(scan for scan in dmris_main+
                                dmris_opposite[:1]+dmris_ref[:1])
        unused_dwi = [x for x in dmris if x not in used_dwi]
        if unused_dwi:
            print ('The following scans:\n{}\nwere not assigned during the DWI motion '
                   'detection initialization (probably a different number of main '
                   'DWI scans and b0 images was provided). They will be processed'
                   ' os "other" scans.'.format('\n'.join(s[0] for s in unused_dwi)))
        study_specs.extend(
            SubStudySpec('t2_{}'.format(i), T2Study, ref_spec)
            for i in range(len(t2s), len(t2s)+len(unused_dwi)))
        inputs.extend(
            DatasetMatch('t2_{}_primary'.format(i), dicom_format, scan[0])
            for i, scan in enumerate(unused_dwi, start=len(t2s)))
        run_pipeline = True

    if not run_pipeline:
        raise Exception('At least one scan, other than the reference, must be '
                        'provided!')
    dct['add_sub_study_specs'] = study_specs
    dct['add_data_specs'] = data_specs
    dct['__metaclass__'] = MultiStudyMetaClass
    return MultiStudyMetaClass(name, (MotionDetectionMixin,), dct), inputs
