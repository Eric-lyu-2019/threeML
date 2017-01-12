import pytest
from threeML import *
from threeML.plugins.OGIPLike import OGIPLike
from threeML.utils.fitted_objects.fitted_point_sources import InvalidUnitError


# TODO: add tests for area corrections

def test_mle_flux_calculations():
    # In[2]:

    triggerName = 'bn090217206'
    ra = 204.9
    dec = -8.4

    # Data are in the current directory

    datadir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../examples'))

    # Create an instance of the GBM plugin for each detector
    # Data files
    obsSpectrum = os.path.join(datadir, "bn090217206_n6_srcspectra.pha{1}")
    bakSpectrum = os.path.join(datadir, "bn090217206_n6_bkgspectra.bak{1}")
    rspFile = os.path.join(datadir, "bn090217206_n6_weightedrsp.rsp{1}")

    # Plugin instance
    NaI6 = OGIPLike("NaI6", obsSpectrum, bakSpectrum, rspFile)

    # Choose energies to use (in this case, I exclude the energy
    # range from 30 to 40 keV to avoid the k-edge, as well as anything above
    # 950 keV, where the calibration is uncertain)
    NaI6.set_active_measurements("10.0-30.0", "40.0-950.0")

    # In[3]:

    # This declares which data we want to use. In our case, all that we have already created.

    data_list = DataList(NaI6)

    # In[4]:

    powerlaw = Powerlaw() + Blackbody()

    # In[5]:

    GRB = PointSource(triggerName, ra, dec, spectral_shape=powerlaw)

    # In[6]:

    model = Model(GRB)

    # In[7]:

    jl = JointLikelihood(model, data_list, verbose=False)

    fit_results, like_frame = jl.fit()


    res = calculate_point_source_flux(10,50,jl,flux_unit='1/(s cm2)', energy_unit='keV')

    res = calculate_point_source_flux(10, 50, jl, flux_unit='erg/(s cm2)', energy_unit='keV')

    res = calculate_point_source_flux(10, 50, jl, flux_unit='erg2/(s cm2)', energy_unit='keV')

    # tests if we can use wavelength and frequency

    res = calculate_point_source_flux(10, 50, jl, flux_unit='erg2/(s cm2)', energy_unit='Hz')

    res = calculate_point_source_flux(10, 50, jl, flux_unit='erg2/(s cm2)', energy_unit='nm')


    with pytest.raises(InvalidUnitError):
        res = calculate_point_source_flux(10, 50, jl, flux_unit='erg2/(s g cm2)', energy_unit='keV')

    res = calculate_point_source_flux(10, 50, jl, use_components=True, components_to_use=['BlackBody'])

    res = calculate_point_source_flux(10, 50, jl, use_components=True, components_to_use=['BlackBody', 'total'])


def test_bayes_flux_calculations():
    # In[2]:

    triggerName = 'bn090217206'
    ra = 204.9
    dec = -8.4

    # Data are in the current directory

    datadir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../examples'))

    # Create an instance of the GBM plugin for each detector
    # Data files
    obsSpectrum = os.path.join(datadir, "bn090217206_n6_srcspectra.pha{1}")
    bakSpectrum = os.path.join(datadir, "bn090217206_n6_bkgspectra.bak{1}")
    rspFile = os.path.join(datadir, "bn090217206_n6_weightedrsp.rsp{1}")

    # Plugin instance
    NaI6 = OGIPLike("NaI6", obsSpectrum, bakSpectrum, rspFile)

    # Choose energies to use (in this case, I exclude the energy
    # range from 30 to 40 keV to avoid the k-edge, as well as anything above
    # 950 keV, where the calibration is uncertain)
    NaI6.set_active_measurements("10.0-30.0", "40.0-950.0")

    # In[3]:

    # This declares which data we want to use. In our case, all that we have already created.

    data_list = DataList(NaI6)

    # In[4]:

    powerlaw = Powerlaw() + Blackbody()

    # In[5]:

    GRB = PointSource(triggerName, ra, dec, spectral_shape=powerlaw)

    # In[6]:

    model = Model(GRB)

    powerlaw.index_1.prior = Uniform_prior(lower_bound=-5.0, upper_bound=5.0)
    powerlaw.K_1.prior = Log_uniform_prior(lower_bound=1.0, upper_bound=10)

    powerlaw.K_2.prior = Uniform_prior(lower_bound=-5.0, upper_bound=5.0)
    powerlaw.kT_2 =  Log_uniform_prior(lower_bound=1.0, upper_bound=10)

    jl = BayesianAnalysis(model, data_list)

    # In[12]:

    samples = jl.sample(n_walkers=50, burn_in=10, n_samples=10)

    res = calculate_point_source_flux(10, 50, jl, flux_unit='1/(s cm2)', energy_unit='keV')

    res = calculate_point_source_flux(10, 50, jl, flux_unit='erg/(s cm2)', energy_unit='keV')

    res = calculate_point_source_flux(10, 50, jl, flux_unit='erg2/(s cm2)', energy_unit='keV')

    # tests if we can use wavelength and frequency

    res = calculate_point_source_flux(10, 50, jl, flux_unit='erg2/(s cm2)', energy_unit='Hz')

    res = calculate_point_source_flux(10, 50, jl, flux_unit='erg2/(s cm2)', energy_unit='nm')

    with pytest.raises(InvalidUnitError):
        res = calculate_point_source_flux(10, 50, jl, flux_unit='erg2/(s g cm2)', energy_unit='keV')

    res = calculate_point_source_flux(10, 50, jl, use_components=True, components_to_use=['BlackBody'])

    res = calculate_point_source_flux(10, 50, jl, use_components=True, components_to_use=['BlackBody','total'])