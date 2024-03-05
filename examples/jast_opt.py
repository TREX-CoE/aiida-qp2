import numpy as np

from aiida.plugins import DataFactory, CalculationFactory

from aiida.orm import load_node
from aiida.orm import load_code
from aiida.engine import run
from aiida import load_profile
from aiida_qp2.utils.wavefunction_handler import wavefunction_handler

SinglefileData = DataFactory('core.singlefile')
Dict = DataFactory('core.dict')
List = DataFactory('core.list')
Code = DataFactory('core.code')

Calculation = CalculationFactory('qp2.run')


load_profile()

class JastOpt():

    def __init__(self,
                 wavefunction: SinglefileData,
                 code: Code,
                 parameter_setter: callable,
                 parameter_getter: callable = None,
                 qmcchem_prepend: list = []):

        self._wavefunction = wavefunction
        self.wavefunction = None
        self.code = code
        self.parameter_setter = parameter_setter
        self.parameter_getter = parameter_getter
        self.qmcchem_prepend = qmcchem_prepend

    def __call__(self, parameters: tuple):
        return self.run(parameters)[0]

    def run(self, parameters: dict):
        self.set_parameters(parameters)
        builder = Calculation.get_builder()
        builder.parameters = Dict({
            'run_type': 'qmcchem',
            'qp_prepend': self.qmcchem_prepend
        })
        builder.wavefunction = self.wavefunction
        builder.code = self.code
        ret = run(builder)
        return ret['output_energy'], ret['output_energy_error']

    def set_parameters(self, parameters):
        operation = self.parameter_setter(parameters)
        self.wavefunction = wavefunction_handler(self._wavefunction, operation)["wavefunction"]




if __name__ == "__main__":

    def p_setter(x):
        x = np.abs(x[0])
        operation = [ ["set", "jastrow_jast_b_up_up", x ],
                      ["set", "jastrow_jast_b_up_dn", x ],
                    ]
        return List(operation)
    wf = load_node(779)

    code = load_code('qmc-docker-new@bobor2')
    prepend = ["-t 60", "-l 10"]
    jast = JastOpt(wavefunction=wf,
                   code=code,
                   parameter_setter=p_setter,
                   qmcchem_prepend=prepend)

    data = []
    for x in np.linspace(0.001, 0.012, 5):
        print(x)
        data.append([ x.value for x in jast.run((x,))])
        print(data[-1])

    import pickle
    with open('jast_opt.pickle', 'wb') as f:
        pickle.dump(data, f)


