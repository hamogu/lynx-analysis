import os
import argparse
import copy
import numpy as np
import astropy.units as u
from astropy import table
from astropy.coordinates import SkyCoord
from marxs.simulator import Sequence
from marxs.design.tolerancing import (wiggle, moveglobal, moveindividual,
                                      varyattribute,
                                      varyorderselector,
                                      varyperiod,
                                      CaptureResAeff,
                                      run_tolerances,
                                      generate_6d_wigglelist)
from marxs.source import PointSource, FixedPointing, JitterPointing
from marxslynx.lynx import conf, conf_chirp
from marxslynx import lynx

from utils import get_path

parser = argparse.ArgumentParser(description='Run tolerancing simulations.')
parser.add_argument('scenario', choices=['default', 'chirp'])
parser.add_argument('n_photons', default=100000, type=int)
args = parser.parse_args()

if args.scenario == 'default':
    outdir = 'tolerances'
    configuration = conf
elif args.scenario == 'chirp':
    outdir = 'tolerances_chirp'
    configuration = conf_chirp

coords = SkyCoord(23., -45., unit='deg')
src = PointSource(coords=coords, energy=0.5, flux=1.)

wave = np.array([15., 25., 37.]) * u.Angstrom
energies = wave.to(u.keV, equivalencies=u.spectral())

changeglobal, changeindividual = generate_6d_wigglelist([0., .1, .2, .4, .7, 1., 2., 5., 10.] * u.mm,
                                                        [0., 2., 5., 10., 20., 40., 60., 120., 180.] * u.arcmin)

scatter = np.array([0, .1, .2, .5, 1., 3.])
scatter = np.hstack([np.vstack([scatter, np.zeros_like(scatter)]),
                     np.vstack([np.zeros_like(scatter[1:]), scatter[1:]])])
scatter = np.deg2rad(scatter / 3600.).T

instrumfull = lynx.PerfectLynx(conf=conf)
analyzer = CaptureResAeff(A_geom=instrumfull.elements[0].area.to(u.cm**2),
                          dispersion_coord='proj_x',
                          orders=np.arange(-12, 5))

def run_for_energies(instrum_before, wigglefunc, wiggleparts, parameters,
                     instrum, outfile, reset=None):
    outtabs = []
    for i, e in enumerate(energies):
        src.energy = e.to(u.keV).value
        photons_in = src.generate_photons(args.n_photons)
        photons_in = instrum_before(photons_in)
        data = run_tolerances(photons_in, instrum,
                              wigglefunc, wiggleparts,
                              parameters, analyzer)
        # convert tab into a table.
        # astropy.tables has problems with Quantities as input
        tab = table.Table([{d: data[i][d].value
                            if isinstance(data[i][d], u.Quantity) else data[i][d]
                            for d in data[i]} for i in range(len(data))])
        tab['energy'] = e
        tab['wave'] = wave[i]
        outtabs.append(tab)
    # Reset positions and stuff so that same instance of instrum can be used again
    if reset is not None:
        wigglefunc(wiggleparts, **reset)
    dettab = table.vstack(outtabs)
    # For column with dtype object
    # This happens only when the input is the orderselector, so we can special
    # special case that here
    if 'order_selector' in dettab.colnames:
        o0 = dettab['order_selector'][0]
        if hasattr(o0, 'sigma'):
            dettab['sigma'] = [o.sigma for o in dettab['order_selector']]
        elif hasattr(o0, 'tophatwidth'):
            dettab['tophatwidth'] = [o.tophatwidth for o in dettab['order_selector']]
        dettab.remove_column('order_selector')
    outfull = os.path.join(get_path(outdir), outfile)
    dettab.write(outfull, overwrite=True)
    print('Writing {}'.format(outfull))


def filter_noCCD(photons):
    '''Set probability of photons that hit neither detector to 0.'''
    for col in ['microcal_x', 'det_x']:
        if col not in photons.colnames:
            photons[col] = np.nan
    onmicrocal = np.isfinite(photons['microcal_x'])
    onXGS = np.isfinite(photons['det_x'])
    photons['probability'][~(onmicrocal | onXGS)] = 0
    return photons


class PerfectLynx(lynx.PerfectLynx):
    def post_process(self):
        return []

    def __init__(self, conf=configuration):
        super().__init__(conf=conf)
        self.elements.insert(0, FixedPointing(coords=coords))
        self.elements.append(filter_noCCD)


class Lynx(lynx.Lynx):
    def post_process(self):
        return []

    def __init__(self, conf=configuration):
        super().__init__(conf=conf)
        self.elements.insert(0, FixedPointing(coords=coords))
        self.elements.append(filter_noCCD)

reset_6d = {'dx': 0., 'dy': 0., 'dz': 0., 'rx': 0., 'ry': 0., 'rz': 0.}


# Tests are ordered by importance for the work I'm doing right now

# CATs
instrum = PerfectLynx(conf=configuration)

# Move center of rotation to hinge in Ralf's figure
epos = np.stack(instrum.elements[3].elem_pos)
shift = np.eye(4)
shift[0, 3] = np.mean(epos, axis=0)[0, 3]
shift[1, 3] = 1500.
instrum.elements[3].move_center(shift)

run_for_energies(Sequence(elements=instrum.elements[:3]), moveglobal,
                 instrum.elements[3],
                 changeglobal,
                 Sequence(elements=instrum.elements[3:]),
                 'CAT_global.fits',
                 reset=reset_6d)

run_for_energies(Sequence(elements=instrum.elements[:3]), wiggle,
                 instrum.elements[3],
                 changeindividual,
                 Sequence(elements=instrum.elements[3:]),
                 'CAT_individual.fits',
                 reset=reset6d)


# jitter
def dummy(p):
     '''Function needs something here, but nothing happens'''
     return p

instrum.elements[0] = JitterPointing(coords=coords, jitter=0)
run_for_energies(dummy, varyattribute, instrum.elements[0],
                 [{'jitter': j} for j in np.array([0., .1, .2, 0.5, 1., 1.5, 2., 5.]) * u.arcsec],
                 instrum,
                 'jitter.fits',)
instrum.elements[0] = FixedPointing(coords=coords)

# Mirror scatter
backup1 = instrum.elements[2].elements[0].elements[1].inplanescatter
backup2 = instrum.elements[2].elements[0].elements[1].perpplanescatter

run_for_energies(Sequence(elements=instrum.elements[:2]), varyattribute,
                 instrum.elements[2].elements[0].elements[1],
                 [{'inplanescatter': a, 'perpplanescatter': b} for a, b in scatter],
                 Sequence(elements=instrum.elements[2:]),
                 'scatter.fits')

instrum.elements[2].elements[0].elements[1].inplanescatter = backup1
instrum.elements[2].elements[0].elements[1].perpplanescatter = backup2

# detectors
run_for_energies(Sequence(elements=instrum.elements[:7]), moveglobal,
                 instrum.elements[7],
                 changeglobal,
                 Sequence(elements=instrum.elements[7:]),
                 'XGSdetector_global.fits',
                 reset=reset_6d)

run_for_energies(Sequence(elements=instrum.elements[:7]), moveindividual,
                 instrum.elements[7],
                 changeglobal,
                 Sequence(elements=instrum.elements[7:]),
                 'XGSdetector_individual.fits',
                  reset=reset_6d)

## STEP 2 ##
# Run default tolerance budget a few times
n_budget = 100
out = []

for i in range(n_budget):
    print('Run default tolerance budget: {}/{}'.format(i, n_budget))
    align = copy.deepcopy(lynx.align_requirement_in)
    lynx.reformat_errorbudget(align, globalfac=None)
    configuration['alignmentbudget'] = align

    if i == 0:
        instrum = PerfectLynx()
    else:
        instrum = Lynx(conf=configuration)

    for e in energies:
        src.energy = e.to(u.keV).value
        photons_in = src.generate_photons(args.n_photons)
        photons = instrum(photons_in)
        out.append(analyzer(photons))
        out[-1]['energy'] = e.value
        out[-1]['run'] = i

    tab = table.Table([{d: out[i][d].value
                        if isinstance(out[i][d], u.Quantity) else out[i][d]
                        for d in out[i]} for i in range(len(out))])

    tab['energy'].unit = u.keV
    tab['wave'] = tab['energy'].to(u.Angstrom, equivalencies=u.spectral())

    outfull = os.path.join(get_path(outdir), 'baseline_budget_.fits')
    tab.write(outfull, overwrite=True)
    print('Writing {}'.format(outfull))
