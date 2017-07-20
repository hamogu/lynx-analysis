from __future__ import print_function

import os
import json
import argparse

import numpy as np
import astropy.units as u

from mayavi import mlab
from astropy.coordinates import SkyCoord
from marxs.source import PointSource, FixedPointing
from marxs import simulator
from marxs.visualization.mayavi import plot_object, plot_rays

from marxslynx import lynx


class LynxPlot(object):
    n_photons = 1e4
    wave = np.arange(6., 60., 0.5) * u.Angstrom
    energies = wave.to(u.keV, equivalencies=u.spectral()).value
    instrument = lynx.default

    @property
    def filename(self):
        return self.__class__.__name__.lower()

    @property
    def source(self):
        return PointSource(coords=SkyCoord(30. * u.deg, 30. * u.deg),
                           energy={'energy': self.energies[::-1],
                                   'flux': np.ones_like(self.energies) / self.energies ** 2},
                           flux=1.)

    pointing = FixedPointing(coords=SkyCoord(30 * u.deg, 30. * u.deg))

    def __init__(self, outpath):
        self.outpath = outpath

    def simulation(self):
        self.keeppos = simulator.KeepCol('pos')
        self.keepprob = simulator.KeepCol('probability')
        self.instrument.postprocess_steps = [self.keeppos, self.keepprob]
        source = self.source
        self.photons = source.generate_photons(self.n_photons)
        self.photons = self.pointing(self.photons)
        self.photons = self.instrument(self.photons)

    def get_filename(self, index):
        '''Can be overwritten for classes that generate multiple outputs'''
        return self.filename

    def get_jsondata(self, index):
        '''Can be overwritten for classes that generate multiple outputs'''
        return self.jsondata()

    def jsondata(self):
        self.data['path'] = os.path.join(self.outpath, self.filename)
        return self.data

    def save_html_data(self, index=None):
        '''Save text like page title etc. that is defined in class.

        This writes a json file at the same location as the other output.
        The script that makes the website can then parse that json file and
        fill in the values in the website template.
        This way, the code that generates the figure and the text for the
        caption are in the same place and the website generator does not have
        to read in this class again.

        Parameters
        ----------
        index : int
            Index for the plot number. Only used for classes that generate
            more than one plot (in most cases each class is responsible for
            exactly one plot)
        '''
        obj = self.get_jsondata(index)
        filename = os.path.join(self.outpath, self.get_filename(index) + '.json')
        with open(filename, 'w') as f:
            json.dump(obj, f, indent=2)


class X3d(LynxPlot):
    pass


class XBasicFlat(X3d):
    plot_col_color = 'energy'

    data = {'name': 'xbasicflat',
            'caption': 'Ray-trace components',
            'title': '',
            'figcaption': '''
            <p> Basic design for Lynx spectrometer showing a ray-trace for a
            simple point source at infinity with a flat spectrum.  </p>

            <p> Rays start in the aperture, which is shaped like a
            ring. Dimensions are somewhat arbitrary at this point, since no
            mirror design has been selected yet. For most type of X-ray mirrors
            photons bounce of their mirrors twice in a Wolter type I like
            geometry. However, in this simulation the SPOs are somewhat
            simplified such that the reflection actually happens in a single
            plane, shown in white.  Rays are imaged onto detectors (yellow).
            </p> '''
            }

    def plot(self):
        ind = (self.photons['probability'] > 0)
        posdat = self.keeppos.format_positions()[ind, :, :]
        fig = mlab.figure()
        obj = plot_object(self.instrument, viewer=fig)
        rays = plot_rays(posdat, scalar=self.photons[self.plot_col_color][ind])
        mlab.savefig(os.path.join(self.outpath, self.filename + '.x3d'))


class XSingleEnergy(XBasicFlat):
    plot_col_color = 'order'

    data = {'name': 'singlenergy',
            'caption': 'Single energy',
            'title': '',
            'figcaption': '''
            <p>
            Basic design for a Lynx CAT grating spectrometer, showing a ray-trace for an on-axis point
            source with a monochromatic emission at 0.5 keV = 24.8 Angstrom.
            </p>

            <p> Rays start in the aperture, which is shaped like a
            ring. Dimensions are somewhat arbitrary at this point, since no
            mirror design has been selected yet. For most type of X-ray mirrors
            photons bounce of their mirrors twice in a Wolter type I like
            geometry. However, in this simulation the SPOs are somewhat
            simplified such that the reflection actually happens in a single
            plane, shown in white.  Rays are imaged onto detectors (yellow).
            </p>

            <p>
            A closer look at the detectors shows that several
            grating orders are detected at the same time.
            </p>

            '''}

    @property
    def source(self):
        return PointSource(coords=SkyCoord(30. * u.deg, 30. * u.deg),
                           energy=0.5,
                           flux=1.)


all_plots = ['XBasicFlat']

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='''
    Run plotting scripts to make output for website.
    ''')
    parser.add_argument('outpath',
                        help='base directory for output')
    parser.add_argument('-p', '--plot', nargs='+',
                        help='name specific plots that should be generated')
    args = parser.parse_args()

    plot = args.plot if args.plot is not None else all_plots
    for plotname in plot:
        a = globals()[plotname](args.outpath)
        print('Running {}'.format(a.filename))
        a.simulation()
        a.plot()
        a.save_html_data()
