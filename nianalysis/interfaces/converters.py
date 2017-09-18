import os.path
import re
from nipype.interfaces.base import (
    TraitedSpec, File, Directory, CommandLineInputSpec, CommandLine, isdefined,
    traits)
from nianalysis.utils import split_extension
from nianalysis.exceptions import NiAnalysisError
import numpy as np
import nibabel as nib


class Dcm2niixInputSpec(CommandLineInputSpec):
    input_dir = Directory(mandatory=True, desc='directory name', argstr='%s',
                          position=-1)
    compression = traits.Str(argstr='-z %s', desc='type of compression')
    filename = File(genfile=True, argstr='-f %s', desc='output file name')
    out_dir = Directory(genfile=True, argstr='-o %s', desc="output directory")


class Dcm2niixOutputSpec(TraitedSpec):
    converted = File(exists=True, desc="The converted file")


class Dcm2niix(CommandLine):
    """Convert a DICOM folder to a nifti_gz file"""

    _cmd = 'dcm2niix'
    input_spec = Dcm2niixInputSpec
    output_spec = Dcm2niixOutputSpec

    def _list_outputs(self):
        if (not isdefined(self.inputs.compression) or
                (self.inputs.compression == 'y' or
                 self.inputs.compression == 'i')):
            im_ext = '.nii.gz'
        else:
            im_ext = '.nii'
        outputs = self._outputs().get()
        # As Dcm2niix sometimes prepends a prefix onto the filenames to avoid
        # name clashes with multiple echos, we need to check the output folder
        # for all filenames that end with the "generated filename".
        out_dir = self._gen_filename('out_dir')
        fname = self._gen_filename('filename') + im_ext
        base, ext = split_extension(fname)
        match_re = re.compile(r'(_[ec]\d+)?{}(_e\d)?{}'
                              .format(base, ext if ext is not None else ''))
        products = [os.path.join(out_dir, f) for f in os.listdir(out_dir)
                    if match_re.match(f) is not None]
        if len(products) == 1:
            converted = products[0]
        elif len(products) > 1:
            ex_file = nib.load(products[0])
            data = ex_file.get_data()
            merged_file = np.zeros((data.shape[0], data.shape[1],
                                    data.shape[2], len(products)))
            for i, el in enumerate(products):
                f = nib.load(el)
                merged_file[:, :, :, i] = f.get_data()
            im2save = nib.Nifti1Image(merged_file, ex_file.affine)
            nib.save(im2save, out_dir + fname)
            converted = out_dir + fname
        else:
            raise NiAnalysisError("No products produced by dcm2niix ({})"
                                  .format(', '.join(os.listdir(out_dir))))
        outputs['converted'] = converted
        return outputs

    def _gen_filename(self, name):
        if name == 'out_dir':
            fname = self._gen_outdirname()
        elif name == 'filename':
            fname = self._gen_outfilename()
        else:
            assert False
        return fname

    def _gen_outdirname(self):
        if isdefined(self.inputs.out_dir):
            out_name = self.inputs.out_dir
        else:
            out_name = os.path.join(os.getcwd())
        return out_name

    def _gen_outfilename(self):
        if isdefined(self.inputs.filename):
            out_name = self.inputs.filename
        else:
            out_name = os.path.basename(self.inputs.input_dir)
        return out_name
