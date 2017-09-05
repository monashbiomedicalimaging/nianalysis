from nipype.interfaces.fsl.model import FEAT, MELODIC
from nipype.interfaces.fsl.epi import PrepareFieldmap
from nipype.interfaces.fsl.preprocess import (
    BET, FUGUE, FLIRT, FNIRT, ApplyWarp)
from nipype.interfaces.afni.preprocess import Volreg, BlurToFWHM
from nipype.interfaces.fsl.utils import (SwapDimensions, InvWarp, ImageMaths,
                                         ConvertXFM)
from nianalysis.interfaces.fsl import (MelodicL1FSF, FSLFIX, CheckLabelFile,
                                       FSLFixTraining, FSLSlices)
from nipype.interfaces.ants.resampling import ApplyTransforms
from nianalysis.dataset import DatasetSpec
from nianalysis.study.base import set_dataset_specs
from ..base import MRIStudy
from nianalysis.requirements import fsl5_req, ants2_req, afni_req, fix_req
from nianalysis.citations import fsl_cite
from nianalysis.data_formats import (
    nifti_gz_format, rdata_format, directory_format,
    zip_format, text_matrix_format, par_format, gif_format)
from nianalysis.interfaces.ants import AntsRegSyn
from nianalysis.interfaces.afni import Tproject
from nianalysis.interfaces.utils import MakeDir, CopyFile, CopyDir, Merge
import os
import subprocess as sp


class FunctionalMRIStudy(MRIStudy):

    def feat_pipeline(self, **options):
        pipeline = self.create_pipeline(
            name='feat',
            inputs=[DatasetSpec('field_map_mag', nifti_gz_format),
                    DatasetSpec('field_map_phase', nifti_gz_format),
                    DatasetSpec('t1', nifti_gz_format),
                    DatasetSpec('rs_fmri', nifti_gz_format),
                    DatasetSpec('rs_fmri_ref', nifti_gz_format)],
            outputs=[DatasetSpec('feat_dir', directory_format)],
            description="MELODIC Level 1",
            default_options={'brain_thresh_percent': 5},
            version=1,
            citations=[fsl_cite],
            options=options)
        swap_dims = pipeline.create_node(SwapDimensions(), "swap_dims")
        swap_dims.inputs.new_dims = ('LR', 'PA', 'IS')
        pipeline.connect_input('t1', swap_dims, 'in_file')

        bet = pipeline.create_node(interface=BET(), name="bet",
                                   requirements=[fsl5_req])
        bet.inputs.frac = 0.2
        bet.inputs.reduce_bias = True
        pipeline.connect_input('field_map_mag', bet, 'in_file')

        bet2 = pipeline.create_node(BET(), "bet2", [fsl5_req])
        bet2.inputs.frac = 0.2
        bet2.inputs.reduce_bias = True
        bet2.inputs.output_type = 'NIFTI_GZ'
        pipeline.connect(swap_dims, "out_file", bet2, "in_file")
        create_fmap = pipeline.create_node(PrepareFieldmap(), "prepfmap")
#       create_fmap.inputs.in_magnitude = fmap_mag[0]

        create_fmap.inputs.delta_TE = 2.46
        pipeline.connect(bet, "out_file", create_fmap, "in_magnitude")
        pipeline.connect_input('field_map_phase', create_fmap, 'in_phase')

        mel = MelodicL1FSF()
        mel.inputs.brain_thresh = pipeline.option('brain_thresh_percent')
        ml1 = pipeline.create_node(mel, "mL1FSF", [fsl5_req])
        ml1.inputs.tr = 0.754
        ml1.inputs.dwell_time = 0.39
        ml1.inputs.te = 21
        ml1.inputs.unwarp_dir = "x"
        ml1.inputs.sfwhm = 3
        ml1.inputs.output_type = 'NIFTI_GZ'
        pipeline.connect_input('rs_fmri', ml1, 'fmri')
        pipeline.connect_input('rs_fmri_ref', ml1, 'fmri_ref')
#        ml1.inputs.fmap_mag = [0]
#        ml1.inputs.structural = struct[0]
        ml1.inputs.high_pass = 75
        pipeline.connect(create_fmap, "out_fieldmap", ml1, "fmap")
        pipeline.connect(bet, "out_file", ml1, "fmap_mag")
        pipeline.connect(bet2, "out_file", ml1, "structural")
        ml1.inputs.output_dir = ("/mnt/rar/project/test_ASPREE/test_pipeline"
                                 "/T1/melodic.ica")
        # fix next
        feat = pipeline.create_node(FEAT(), "featL1", [fsl5_req])
        feat.inputs.terminal_output = 'none'
        feat.inputs.output_type = 'NIFTI_GZ'
        pipeline.connect(ml1, 'fsf_file', feat, 'fsf_file')
        pipeline.connect_output('feat_dir', feat, 'feat_dir')

        pipeline.assert_connected()
        return pipeline

    def fix_pipeline(self, **options):

        pipeline = self.create_pipeline(
            name='fix',
            # inputs=['fear_dir', 'train_data'],
            inputs=[DatasetSpec('train_data', rdata_format),
                    DatasetSpec('fix_dir', directory_format)],
            outputs=[DatasetSpec('cleaned_file', nifti_gz_format)],
            description=("Automatic classification and removal of noisy"
                         "components from the rsfMRI data"),
            default_options={'component_threshold': 20, 'motion_reg': True},
            version=1,
            citations=[fsl_cite],
            options=options)

        fix = pipeline.create_node(FSLFIX(), name="fix", wall_time=5,
                                   requirements=[fsl5_req, fix_req])
        pipeline.connect_input("fix_dir", fix, "feat_dir")
        pipeline.connect_input("train_data", fix, "train_data")
        fix.inputs.component_threshold = pipeline.option(
            'component_threshold')
        fix.inputs.motion_reg = pipeline.option('motion_reg')
        fix.inputs.highpass = 200

        pipeline.connect_output('cleaned_file', fix, 'output')

        pipeline.assert_connected()
        return pipeline

    def optiBET(self, **options):

        pipeline = self.create_pipeline(
            name='optiBET',
            inputs=[DatasetSpec('t1', nifti_gz_format)],
            outputs=[DatasetSpec('betted_file', nifti_gz_format),
                     DatasetSpec('betted_mask', nifti_gz_format),
                     DatasetSpec('optiBET_report', gif_format)],
            description=("python implementation of optiBET.sh"),
            default_options={'MNI_template': os.environ['FSLDIR']+'/data/'
                             'standard/MNI152_T1_2mm_brain.nii.gz',
                             'MNI_template_mask': os.environ['FSLDIR']+'/data/'
                             'standard/MNI152_T1_2mm_brain_mask.nii.gz'},
            version=1,
            citations=[fsl_cite],
            options=options)

        bet1 = pipeline.create_node(
            BET(frac=0.1, reduce_bias=True), name='bet', wall_time=10,
            requirements=[fsl5_req])
        pipeline.connect_input('t1', bet1, 'in_file')
        flirt = pipeline.create_node(
            FLIRT(out_matrix_file='linear_mat.mat',
                  out_file='linear_reg.nii.gz', searchr_x=[-30, 30],
                  searchr_y=[-30, 30], searchr_z=[-30, 30]), name='flirt',
            wall_time=5, requirements=[fsl5_req])
        flirt.inputs.reference = pipeline.option('MNI_template')
        pipeline.connect(bet1, 'out_file', flirt, 'in_file')
        fnirt = pipeline.create_node(
            FNIRT(config_file='T1_2_MNI152_2mm',
                  fieldcoeff_file='warp_file.nii.gz'), name='fnirt',
            wall_time=15, requirements=[fsl5_req])
        fnirt.inputs.ref_file = pipeline.option('MNI_template')
        pipeline.connect(flirt, 'out_matrix_file', fnirt, 'affine_file')
        pipeline.connect_input('t1', fnirt, 'in_file')
        invwarp = pipeline.create_node(InvWarp(), name='invwarp', wall_time=5,
                                       requirements=[fsl5_req])
        pipeline.connect(fnirt, 'fieldcoeff_file', invwarp, 'warp')
        pipeline.connect_input('t1', invwarp, 'reference')
        applywarp = pipeline.create_node(
            ApplyWarp(interp='nn', out_file='warped_file.nii.gz'),
            name='applywarp', wall_time=5, requirements=[fsl5_req])
        applywarp.inputs.in_file = pipeline.option('MNI_template_mask')
        pipeline.connect_input('t1', applywarp, 'ref_file')
        pipeline.connect(invwarp, 'inverse_warp', applywarp, 'field_file')
        maths1 = pipeline.create_node(
            ImageMaths(suffix='_optiBET_brain_mask', op_string='-bin'),
            name='binarize', wall_time=5, requirements=[fsl5_req])
        pipeline.connect(applywarp, 'out_file', maths1, 'in_file')
        maths2 = pipeline.create_node(
            ImageMaths(suffix='_optiBET_brain', op_string='-mas'),
            name='mask', wall_time=5, requirements=[fsl5_req])
        pipeline.connect_input('t1', maths2, 'in_file')
        pipeline.connect(maths1, 'out_file', maths2, 'in_file2')

        slices = pipeline.create_node(FSLSlices(), name='slices', wall_time=5,
                                      requirements=[fsl5_req])
        slices.inputs.outname = 'optiBET_report.gif'
        pipeline.connect_input('t1', slices, 'im1')
        pipeline.connect(maths2, 'out_file', slices, 'im2')

        pipeline.connect_output('betted_mask', maths1, 'out_file')
        pipeline.connect_output('betted_file', maths2, 'out_file')
        pipeline.connect_output('optiBET_report', slices, 'report')

        pipeline.assert_connected()
        return pipeline

    def ANTsRegistration(self, **options):

        try:
            cmd = 'which ANTS'
            antspath = sp.check_output(cmd, shell=True)
            antspath = '/'.join(antspath.split('/')[0:-1])
            os.environ['ANTSPATH'] = antspath
            print antspath
        except ImportError:
            print "NO ANTs module found. Please ensure to have it in you PATH."

        pipeline = self.create_pipeline(
            name='ANTsReg',
            inputs=[DatasetSpec('betted_file', nifti_gz_format),
                    DatasetSpec('unwarped_file', nifti_gz_format)],
            outputs=[DatasetSpec('epi2T1', nifti_gz_format),
                     DatasetSpec('epi2T1_mat', text_matrix_format),
                     DatasetSpec('T12MNI_reg', nifti_gz_format),
                     DatasetSpec('T12MNI_mat', text_matrix_format),
                     DatasetSpec('T12MNI_warp', nifti_gz_format),
                     DatasetSpec('T12MNI_invwarp', nifti_gz_format),
                     DatasetSpec('T12MNI_reg_report.gif', gif_format)],
            description=("python implementation of antsRegistrationSyN.sh"),
            default_options={'MNI_template': os.environ['FSLDIR']+'/data/'
                             'standard/MNI152_T1_2mm_brain.nii.gz'},
            version=1,
            citations=[fsl_cite],
            options=options)

        bet_rsfmri = pipeline.create_node(BET(), name="bet_rsfmri",
                                          wall_time=5, requirements=[fsl5_req])
        bet_rsfmri.inputs.robust = True
        bet_rsfmri.inputs.frac = 0.4
        bet_rsfmri.inputs.mask = True
        pipeline.connect_input('unwarped_file', bet_rsfmri, 'in_file')
        epireg = pipeline.create_node(
            AntsRegSyn(num_dimensions=3, transformation='r',
                       out_prefix='epi2T1'), name='ANTsReg', wall_time=7,
            requirements=[ants2_req])
        pipeline.connect_input('betted_file', epireg, 'ref_file')
        pipeline.connect(bet_rsfmri, 'out_file', epireg, 'input_file')

        t1reg = pipeline.create_node(
            AntsRegSyn(num_dimensions=3, transformation='s',
                       out_prefix='T12MNI'), name='T1_reg', wall_time=20,
            requirements=[ants2_req])
        t1reg.inputs.ref_file = pipeline.option('MNI_template')
        pipeline.connect_input('betted_file', t1reg, 'input_file')

        slices = pipeline.create_node(FSLSlices(), name='slices', wall_time=1,
                                      requirements=[fsl5_req])
        slices.inputs.outname = 'T12MNI_reg_report.gif'
        slices.inputs.im1 = pipeline.option('MNI_template')
        pipeline.connect(t1reg, 'reg_file', slices, 'im2')

        pipeline.connect_output('epi2T1', epireg, 'reg_file')
        pipeline.connect_output('epi2T1_mat', epireg, 'regmat')
        pipeline.connect_output('T12MNI_reg', t1reg, 'reg_file')
        pipeline.connect_output('T12MNI_mat', t1reg, 'regmat')
        pipeline.connect_output('T12MNI_warp', t1reg, 'warp_file')
        pipeline.connect_output('T12MNI_invwarp', t1reg, 'inv_warp')
        pipeline.connect_output('T12MNI_reg_report', slices, 'report')

        pipeline.assert_connected()
        return pipeline

    def MelodicL1(self, **options):

        pipeline = self.create_pipeline(
            name='MelodicL1',
            inputs=[DatasetSpec('filtered_data', nifti_gz_format)],
            outputs=[DatasetSpec('melodic_ica', directory_format)],
            description=("python implementation of Melodic"),
            default_options={'brain_thresh_percent': 5},
            version=1,
            citations=[fsl_cite],
            options=options)

        mel = pipeline.create_node(MELODIC(), name='fsl-MELODIC', wall_time=10,
                                   requirements=[fsl5_req])
        mel.inputs.no_bet = True
        mel.inputs.bg_threshold = pipeline.option('brain_thresh_percent')
        mel.inputs.tr_sec = 2.45
        mel.inputs.report = True
        mel.inputs.out_stats = True
        mel.inputs.mm_thresh = 0.5
        mel.inputs.out_dir = 'melodic.ica'
#         pipeline.connect(mkdir, 'new_dir', mel, 'out_dir')
        pipeline.connect_input('filtered_data', mel, 'in_files')

        pipeline.connect_output('melodic_ica', mel, 'out_dir')

        pipeline.assert_connected()
        return pipeline

    def rsfMRI_filtering(self, **options):

        pipeline = self.create_pipeline(
            name='rsfMRI_filtering',
            inputs=[DatasetSpec('field_map_mag', nifti_gz_format),
                    DatasetSpec('field_map_phase', nifti_gz_format),
                    DatasetSpec('rs_fmri', nifti_gz_format),
                    DatasetSpec('betted_file', nifti_gz_format)],
            outputs=[DatasetSpec('filtered_data', nifti_gz_format),
                     DatasetSpec('hires2example', text_matrix_format),
                     DatasetSpec('rsfmri_mask', nifti_gz_format),
                     DatasetSpec('mc_par', par_format),
                     DatasetSpec('unwarped_file', nifti_gz_format)],
            description=("Spatial and temporal rsfMRI filtering"),
            default_options={'MNI_template': os.environ['FSLDIR']+'/data/'
                             'standard/MNI152_T1_2mm_brain.nii.gz',
                             'MNI_template_mask': os.environ['FSLDIR']+'/data/'
                             'standard/MNI152_T1_2mm_brain_mask.nii.gz'},
            version=1,
            citations=[fsl_cite],
            options=options)
        bet = pipeline.create_node(BET(), name="bet", wall_time=5,
                                   requirements=[fsl5_req])
        bet.inputs.robust = True
        pipeline.connect_input('field_map_mag', bet, 'in_file')

        bet_rsfmri = pipeline.create_node(BET(), name="bet_rsfmri",
                                          wall_time=5, requirements=[fsl5_req])
        bet_rsfmri.inputs.robust = True
        bet_rsfmri.inputs.frac = 0.4
        bet_rsfmri.inputs.mask = True
        pipeline.connect_input('rs_fmri', bet_rsfmri, 'in_file')

        create_fmap = pipeline.create_node(PrepareFieldmap(), name="prepfmap",
                                           wall_time=5,
                                           requirements=[fsl5_req])
        create_fmap.inputs.delta_TE = 2.46
        pipeline.connect(bet, "out_file", create_fmap, "in_magnitude")
        pipeline.connect_input('field_map_phase', create_fmap, 'in_phase')

        fugue = pipeline.create_node(FUGUE(), name='fugue', wall_time=5,
                                     requirements=[fsl5_req])
        fugue.inputs.unwarp_direction = 'x'
        fugue.inputs.dwell_time = 0.00039
        fugue.inputs.unwarped_file = 'example_func.nii.gz'
        pipeline.connect(create_fmap, 'out_fieldmap', fugue, 'fmap_in_file')
        pipeline.connect_input('rs_fmri', fugue, 'in_file')

        flirt_t1 = pipeline.create_node(FLIRT(), name='FLIRT_T1', wall_time=5,
                                        requirements=[fsl5_req])
        flirt_t1.inputs.dof = 6
        flirt_t1.inputs.out_matrix_file = 'example2hires.mat'
        pipeline.connect_input('betted_file', flirt_t1, 'reference')
        pipeline.connect(bet_rsfmri, 'out_file', flirt_t1, 'in_file')

        convxfm = pipeline.create_node(ConvertXFM(), name='convertxfm',
                                       wall_time=1, requirements=[fsl5_req])
        convxfm.inputs.invert_xfm = True
        convxfm.inputs.out_file = 'hires2example.mat'
        pipeline.connect(flirt_t1, 'out_matrix_file', convxfm, 'in_file')

        afni_mc = pipeline.create_node(Volreg(), name='AFNI_MC', wall_time=5,
                                       requirements=[afni_req])
        afni_mc.inputs.zpad = 1
        afni_mc.inputs.out_file = 'rsfmri_mc.nii.gz'
        afni_mc.inputs.oned_file = 'prefiltered_func_data_mcf.par'
#         afni_mc.inputs.oned_matrix_save = 'motion_matrices.mat'
        pipeline.connect(fugue, 'unwarped_file', afni_mc, 'in_file')

        filt = pipeline.create_node(Tproject(), name='Tproject', wall_time=5,
                                    requirements=[afni_req])
        filt.inputs.stopband = (0, 0.01)
        filt.inputs.delta_t = 2.45
        filt.inputs.polort = 3
        filt.inputs.blur = 3
        filt.inputs.out_file = 'filtered_func_data.nii.gz'
        pipeline.connect(afni_mc, 'out_file', filt, 'in_file')
        pipeline.connect(bet_rsfmri, 'mask_file', filt, 'mask')

        meanfunc = pipeline.create_node(
            ImageMaths(op_string='-Tmean', suffix='_mean'), name='meanfunc',
            wall_time=5, requirements=[fsl5_req])
        pipeline.connect(afni_mc, 'out_file', meanfunc, 'in_file')

        add_mean = pipeline.create_node(
            ImageMaths(op_string='-add'), name='add_mean', wall_time=5,
            requirements=[fsl5_req])
        pipeline.connect(filt, 'out_file', add_mean, 'in_file')
        pipeline.connect(meanfunc, 'out_file', add_mean, 'in_file2')

        pipeline.connect_output('filtered_data', add_mean, 'out_file')
        pipeline.connect_output('hires2example', convxfm, 'out_file')
        pipeline.connect_output('rsfmri_mask', bet_rsfmri, 'mask_file')
        pipeline.connect_output('mc_par', afni_mc, 'oned_file')
        pipeline.connect_output('unwarped_file', fugue, 'unwarped_file')

        pipeline.assert_connected()
        return pipeline

    def applyTransform(self, **options):

        pipeline = self.create_pipeline(
            name='ANTsApplyTransform',
            inputs=[DatasetSpec('cleaned_file', nifti_gz_format),
                    DatasetSpec('T12MNI_warp', nifti_gz_format),
                    DatasetSpec('T12MNI_mat', text_matrix_format),
                    DatasetSpec('epi2T1_mat', text_matrix_format)],
            outputs=[DatasetSpec('registered_file', nifti_gz_format)],
            description=("Spatial and temporal rsfMRI filtering"),
            default_options={'MNI_template': os.environ['FSLDIR']+'/data/'
                             'standard/MNI152_T1_2mm_brain.nii.gz'},
            version=1,
            citations=[fsl_cite],
            options=options)

        merge_trans = pipeline.create_node(Merge(3), name='merge_transforms',
                                           wall_time=1)
        pipeline.connect_input('T12MNI_warp', merge_trans, 'in1')
        pipeline.connect_input('T12MNI_mat', merge_trans, 'in2')
        pipeline.connect_input('epi2T1_mat', merge_trans, 'in3')

        apply_trans = pipeline.create_node(
            ApplyTransforms(), name='ApplyTransform', wall_time=7,
            requirements=[ants2_req])
        apply_trans.inputs.reference_image = pipeline.option('MNI_template')
#         apply_trans.inputs.dimension = 3
        apply_trans.inputs.interpolation = 'Linear'
        apply_trans.inputs.input_image_type = 3
        pipeline.connect(merge_trans, 'out', apply_trans, 'transforms')
        pipeline.connect_input('cleaned_file', apply_trans, 'input_image')

        pipeline.connect_output('registered_file', apply_trans, 'output_image')

        pipeline.assert_connected()
        return pipeline

    def applySmooth(self, **options):

        pipeline = self.create_pipeline(
            name='3dBlurToFWHM',
            inputs=[DatasetSpec('registered_file', nifti_gz_format)],
            outputs=[DatasetSpec('smoothed_file', nifti_gz_format)],
            description=("Spatial and temporal rsfMRI filtering"),
            default_options={'MNI_template_mask': os.environ['FSLDIR']+'/data/'
                             'standard/MNI152_T1_2mm_brain_mask.nii.gz'},
            version=1,
            citations=[fsl_cite],
            options=options)

        smooth = pipeline.create_node(BlurToFWHM(), name='3dBlurToFWHM',
                                      wall_time=5, requirements=[afni_req])
        smooth.inputs.fwhm = 5
        smooth.inputs.out_file = 'rs-fmri_filtered_reg_smooth.nii.gz'
        smooth.inputs.mask = pipeline.option('MNI_template_mask')
        pipeline.connect_input('registered_file', smooth, 'in_file')

        pipeline.connect_output('smoothed_file', smooth, 'out_file')

        pipeline.assert_connected()
        return pipeline

    def PrepareFix(self, **options):

        pipeline = self.create_pipeline(
            name='prepare_fix',
            # inputs=['fear_dir', 'train_data'],
            inputs=[DatasetSpec('melodic_ica', directory_format),
                    # DatasetSpec('train_data', rdata_format),
                    DatasetSpec('filtered_data', nifti_gz_format),
                    DatasetSpec('hires2example', text_matrix_format),
                    DatasetSpec('unwarped_file', nifti_gz_format),
                    DatasetSpec('betted_file', nifti_gz_format),
                    DatasetSpec('mc_par', par_format),
                    DatasetSpec('rsfmri_mask', nifti_gz_format),
                    DatasetSpec('rs_fmri', nifti_gz_format)],
            outputs=[DatasetSpec('fix_dir', directory_format)],
            description=("Automatic classification and removal of noisy"
                         "components from the rsfMRI data"),
            default_options={'MNI_template': os.environ['FSLDIR']+'/data/'
                             'standard/MNI152_T1_2mm_brain.nii.gz'},
            version=1,
            citations=[fsl_cite],
            options=options)

        t12MNI = pipeline.create_node(FLIRT(), name='t12MNI_reg')
        t12MNI.inputs.reference = pipeline.option('MNI_template')
        t12MNI.inputs.out_matrix_file = 'T12MNI.mat'
        pipeline.connect_input('betted_file', t12MNI, 'in_file')

        MNI2t1 = pipeline.create_node(ConvertXFM(), name='MNI2t1')
        MNI2t1.inputs.invert_xfm = True
        MNI2t1.inputs.out_file = 'MNI2T1.mat'
        pipeline.connect(t12MNI, 'out_matrix_file', MNI2t1, 'in_file')

        epi2t1 = pipeline.create_node(ConvertXFM(), name='epi2t1')
        epi2t1.inputs.invert_xfm = True
        epi2t1.inputs.out_file = 'epi2T1.mat'
        pipeline.connect_input('hires2example', epi2t1, 'in_file')

        mkdir1 = pipeline.create_node(MakeDir(), name='makedir1')
        mkdir1.inputs.name_dir = 'reg'
        pipeline.connect_input('melodic_ica', mkdir1, 'base_dir')

        cp0 = pipeline.create_node(CopyFile(), name='copyfile0')
        cp0.inputs.dst = 'reg/highres2std.mat'
        pipeline.connect(t12MNI, 'out_matrix_file', cp0, 'src')
        pipeline.connect(mkdir1, 'new_dir', cp0, 'base_dir')

        cp00 = pipeline.create_node(CopyFile(), name='copyfile00')
        cp00.inputs.dst = 'reg/std2highres.mat'
        pipeline.connect(MNI2t1, 'out_file', cp00, 'src')
        pipeline.connect(cp0, 'basedir', cp00, 'base_dir')

        cp000 = pipeline.create_node(CopyFile(), name='copyfile000')
        cp000.inputs.dst = 'reg/example_func2highres.mat'
        pipeline.connect(epi2t1, 'out_file', cp000, 'src')
        pipeline.connect(cp00, 'basedir', cp000, 'base_dir')

        cp1 = pipeline.create_node(CopyFile(), name='copyfile1')
        cp1.inputs.dst = 'reg/highres.nii.gz'
        pipeline.connect_input('betted_file', cp1, 'src')
        pipeline.connect(cp000, 'basedir', cp1, 'base_dir')

        cp2 = pipeline.create_node(CopyFile(), name='copyfile2')
        cp2.inputs.dst = 'reg/example_func.nii.gz'
        pipeline.connect_input('unwarped_file', cp2, 'src')
        pipeline.connect(cp1, 'basedir', cp2, 'base_dir')

        cp3 = pipeline.create_node(CopyFile(), name='copyfile3')
        cp3.inputs.dst = 'reg/highres2example_func.mat'
        pipeline.connect_input('hires2example', cp3, 'src')
        pipeline.connect(cp2, 'basedir', cp3, 'base_dir')

        mkdir2 = pipeline.create_node(MakeDir(), name='makedir2')
        mkdir2.inputs.name_dir = 'mc'
        pipeline.connect(cp3, 'basedir', mkdir2, 'base_dir')

        cp4 = pipeline.create_node(CopyFile(), name='copyfile4')
        cp4.inputs.dst = 'mc/prefiltered_func_data_mcf.par'
        pipeline.connect_input('mc_par', cp4, 'src')
        pipeline.connect(mkdir2, 'new_dir', cp4, 'base_dir')

        cp5 = pipeline.create_node(CopyFile(), name='copyfile5')
        cp5.inputs.dst = 'mask.nii.gz'
        pipeline.connect_input('rsfmri_mask', cp5, 'src')
        pipeline.connect(cp4, 'basedir', cp5, 'base_dir')

        meanfunc = pipeline.create_node(
            ImageMaths(op_string='-Tmean', suffix='_mean'), name='meanfunc')
        pipeline.connect_input('rs_fmri', meanfunc, 'in_file')

        cp6 = pipeline.create_node(CopyFile(), name='copyfile6')
        cp6.inputs.dst = 'mean_func.nii.gz'
        pipeline.connect(meanfunc, 'out_file', cp6, 'src')
        pipeline.connect(cp5, 'basedir', cp6, 'base_dir')

        mkdir3 = pipeline.create_node(MakeDir(), name='makedir3')
        mkdir3.inputs.name_dir = 'filtered_func_data.ica'
        pipeline.connect(cp6, 'basedir', mkdir3, 'base_dir')

        cp7 = pipeline.create_node(CopyDir(), name='copyfile7')
        cp7.inputs.dst = 'filtered_func_data.ica'
        cp7.inputs.method = 1
        pipeline.connect_input('melodic_ica', cp7, 'src')
        pipeline.connect(mkdir3, 'new_dir', cp7, 'base_dir')

        cp8 = pipeline.create_node(CopyFile(), name='copyfile8')
        cp8.inputs.dst = 'filtered_func_data.nii.gz'
        pipeline.connect_input('filtered_data', cp8, 'src')
        pipeline.connect(cp7, 'basedir', cp8, 'base_dir')

        pipeline.connect_output('fix_dir', cp8, 'basedir')

        pipeline.assert_connected()
        return pipeline

    def TrainingFix(self, **options):

        pipeline = self.create_pipeline(
            name='training_fix',
            # inputs=['fear_dir', 'train_data'],
            inputs=[DatasetSpec('fix_dir', directory_format)],
            outputs=[DatasetSpec('train_data', rdata_format)],
            description=("Automatic classification and removal of noisy"
                         "components from the rsfMRI data"),
            default_options={'MNI_template': os.environ['FSLDIR']+'/data/'
                             'standard/MNI152_T1_2mm_brain.nii.gz'},
            version=1,
            citations=[fsl_cite],
            options=options)
        labeled_sub = pipeline.create_join_subjects_node(
            CheckLabelFile(), joinfield='in_list', name='labeled_subjects')
        pipeline.connect_input('fix_dir', labeled_sub, 'in_list')

        fix_training = pipeline.create_node(
            FSLFixTraining(), name='fix_training', wall_time=20,
            requirements=[fix_req])
        fix_training.inputs.outname = 'FIX_training_set'
        fix_training.inputs.training = True
        pipeline.connect(labeled_sub, 'out_list', fix_training, 'list_dir')

        pipeline.connect_output('train_data', fix_training, 'training_set')

        pipeline.assert_connected()
        return pipeline

    _dataset_specs = set_dataset_specs(
        DatasetSpec('field_map_mag', nifti_gz_format),
        DatasetSpec('field_map_phase', nifti_gz_format),
        DatasetSpec('t1', nifti_gz_format),
        DatasetSpec('rs_fmri', nifti_gz_format),
        DatasetSpec('melodic_dir', zip_format, feat_pipeline),
        DatasetSpec('train_data', rdata_format, TrainingFix),
        DatasetSpec('cleaned_file', nifti_gz_format, fix_pipeline),
        DatasetSpec('betted_file', nifti_gz_format, optiBET),
        DatasetSpec('betted_mask', nifti_gz_format, optiBET),
        DatasetSpec('optiBET_report', gif_format, optiBET),
        DatasetSpec('epi2T1', nifti_gz_format, ANTsRegistration),
        DatasetSpec('epi2T1_mat', text_matrix_format, ANTsRegistration),
        DatasetSpec('T12MNI_reg', nifti_gz_format, ANTsRegistration),
        DatasetSpec('T12MNI_mat', text_matrix_format, ANTsRegistration),
        DatasetSpec('T12MNI_warp', nifti_gz_format, ANTsRegistration),
        DatasetSpec('T12MNI_invwarp', nifti_gz_format, ANTsRegistration),
        DatasetSpec('T12MNI_reg_report', gif_format, ANTsRegistration),
        DatasetSpec('filtered_data', nifti_gz_format, rsfMRI_filtering),
        DatasetSpec('hires2example', text_matrix_format, rsfMRI_filtering),
        DatasetSpec('mc_par', par_format, rsfMRI_filtering),
        DatasetSpec('rsfmri_mask', nifti_gz_format, rsfMRI_filtering),
        DatasetSpec('unwarped_file', nifti_gz_format, rsfMRI_filtering),
        DatasetSpec('melodic_ica', zip_format, MelodicL1),
        DatasetSpec('registered_file', nifti_gz_format, applyTransform),
        DatasetSpec('fix_dir', zip_format, PrepareFix),
        DatasetSpec('smoothed_file', nifti_gz_format, applySmooth))
