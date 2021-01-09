# Copyright edalize contributors
# Licensed under the 2-Clause BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-2-Clause

import logging
import os.path
import sys

from edalize.edatool import Edatool

logger = logging.getLogger(__name__)

class Diamond(Edatool):
    argtypes = ['generic', 'vlogdefine', 'vlogparam']

    @classmethod
    def get_doc(cls, api_ver):
        if api_ver == 0:
            return {'description' : "Backend for Lattice Diamond",
                    'members' : [
                        {'name' : 'part',
                         'type' : 'String',
                         'desc' : 'FPGA part number (e.g. LFE5U-45F-6BG381C)'},
                    ]}

    def configure_main(self):
        (src_files, incdirs) = self._get_fileset_files()
        has_vhdl2008 = "vhdlSource-2008" in [x.file_type for x in src_files]
            
        lpf_file = None
        prj_name = self.name.replace('.','_')
        for f in src_files:
            if f.file_type == 'LPF':
                if lpf_file:
                    logger.warning("Multiple LPF files detected. Only the first one will be used")
                else:
                    lpf_file = f.name
        #FIXME: Warn about pnr without lpf
        with open(os.path.join(self.work_root, self.name+'.tcl'), 'w') as f:
            TCL_TEMPLATE = """#Generated by Edalize
prj_project new -name {} -dev {}{} -synthesis synplify
prj_impl option top {}
{}
"""
            f.write(TCL_TEMPLATE.format(prj_name,
                                        self.tool_options['part'],
                                        " -lpf "+lpf_file if lpf_file else "",
                                        self.toplevel,
                                        "prj_strgy set_value -strategy Strategy1 syn_vhdl2008=True" if has_vhdl2008 else ""
            ))
            if incdirs:
                _s = 'prj_impl option {include path} {'
                _s += ' '.join(incdirs)
                f.write(_s + '}\n')
            if self.generic:
                _s = ';'.join(['{}={}'.format(k, self._param_value_str(v, '"')) for k,v in self.generic.items()])
                f.write('prj_impl option HDL_PARAM {')
                f.write(_s)
                f.write('}\n')
            if self.vlogparam:
                _s = ';'.join(['{}={}'.format(k, self._param_value_str(v, '"')) for k,v in self.vlogparam.items()])
                f.write('prj_impl option HDL_PARAM {')
                f.write(_s)
                f.write('}\n')
            if self.vlogdefine:
                _s = ";".join(['{}={}'.format(k,v) for k,v in self.vlogdefine.items()])
                f.write('prj_impl option VERILOG_DIRECTIVES {')
                f.write(_s)
                f.write('}\n')
            for src_file in src_files:
                _s = self.src_file_filter(src_file)
                if _s:
                    f.write(_s+'\n')
            f.write('prj_project save\nexit\n')

        with open(os.path.join(self.work_root, self.name+'_run.tcl'), 'w') as f:
            f.write("""#Generated by Edalize
prj_project open {}.ldf
prj_run Synthesis
prj_run Export -task Bitgen
prj_project save
prj_project close
""".format(prj_name))
    def src_file_filter(self, f):

        def _vhdl_source(f):
            s = 'VHDL'
            if f.logical_name:
                s += ' -work '+f.logical_name
            return s

        file_types = {
            'verilogSource'       : 'prj_src add -format Verilog',
            'systemVerilogSource' : 'prj_src add -format Verilog',
            'vhdlSource'          : 'prj_src add -format '+ _vhdl_source(f),
            'tclSource'           : 'source',
            'SDC'                 : 'prj_src add -format SDC',
        }
        _file_type = f.file_type.split('-')[0]
        if _file_type in file_types:
            return file_types[_file_type] + ' ' + f.name
        elif _file_type in ['user', 'LPF']:
            return ''
        else:
            _s = "{} has unknown file type '{}'"
            logger.warning(_s.format(f.name,
                                     f.file_type))
        return ''

    def build_main(self):
        if sys.platform == 'win32':
            tcl = 'pnmainc'
        else:
            tcl = 'diamondc'

        self._run_tool(tcl, [self.name+'.tcl'], quiet=True)
        self._run_tool(tcl, [self.name+'_run.tcl'], quiet=True)

    def run_main(self):
        pass
