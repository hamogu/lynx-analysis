from mayavi import mlab
from marxs.visualization.mayavi import plot_object, plot_rays
from astropy.coordinates import SkyCoord
from marxs import source, simulator
from marxslynx import lynx

%matplotlib

instrum = lynx.PerfectLynx()

star = source.PointSource(coords=SkyCoord(30., 30., unit='deg'),
                          energy=1., flux=1.)
pointing = source.FixedPointing(coords=SkyCoord(30., 30., unit='deg'))
photons = star.generate_photons(1000)
photons = pointing(photons)
photons = instrum(photons)
ind = (photons['probability'] > 0) & (photons['facet'] >=0)
posdat = instrum.KeepPos.format_positions()[ind, :, :]

fig = mlab.figure(bgcolor=(1,1,1))
obj = plot_object(instrum, viewer=fig)


rays = plot_rays(posdat, scalar=photons['order'][ind],
                 kwargssurface={'opacity': .5,
                                'line_width': 1,
                                 'colormap': 'blue-red'})
