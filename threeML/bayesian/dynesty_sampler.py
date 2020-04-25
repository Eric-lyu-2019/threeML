import os
import time
import numpy as np

from astromodels import ModelAssertionViolation, use_astromodels_memoization
from threeML.bayesian.sampler_base import UnitCubeSampler
from threeML.config.config import threeML_config
from threeML.parallel.parallel_client import ParallelClient

try:

    from dynesty import NestedSampler, DynamicNestedSampler

except:

    has_dynesty = False

else:

    has_dynesty = True


class DynestyNestedSampler(UnitCubeSampler):
    def __init__(self, likelihood_model=None, data_list=None, **kwargs):

        assert has_dynesty, "You must install UltraNest to use this sampler"

        super(DynestyNestedSampler, self).__init__(
            likelihood_model, data_list, **kwargs
        )

    def setup(
        self,
        n_live_points=400,
        bound="multi",
        wrapped_params=None,
        sample="auto",
        periodic=None,
        reflective=None,
        update_interval=None,
        first_update=None,
        npdim=None,
        rstate=None,
        queue_size=None,
        use_pool=None,
        live_points=None,
        logl_args=None,
        logl_kwargs=None,
        ptform_args=None,
        ptform_kwargs=None,
        gradient=None,
        grad_args=None,
        grad_kwargs=None,
        compute_jac=False,
        enlarge=None,
        bootstrap=0,
        vol_dec=0.5,
        vol_check=2.0,
        walks=25,
        facc=0.5,
        slices=5,
        fmove=0.9,
        max_move=100,
        update_func=None,
        **kwargs
    ):

        self._kwargs = {}
        self._kwargs["nlive"] = n_live_points
        self._kwargs["bound"] = bound
        self._kwargs["wrapped_params"] = wrapped_params
        self._kwargs["sample"] = sample
        self._kwargs["periodic"] = periodic
        self._kwargs["reflective"] = reflective
        self._kwargs["update_interval"] = update_interval
        self._kwargs["first_update"] = first_update
        self._kwargs["npdim"] = npdim
        self._kwargs["rstate"] = rstate
        self._kwargs["queue_size"] = queue_size
        self._kwargs["pool"] = None
        self._kwargs["use_pool"] = use_pool
        self._kwargs["live_points"] = live_points
        self._kwargs["logl_args"] = logl_args
        self._kwargs["logl_kwargs"] = logl_kwargs
        self._kwargs["ptform_args"] = ptform_args
        self._kwargs["ptform_kwargs"] = ptform_kwargs
        self._kwargs["gradient"] = gradient
        self._kwargs["grad_args"] = grad_args
        self._kwargs["grad_kwargs"] = grad_kwargs
        self._kwargs["compute_jac"] = compute_jac
        self._kwargs["enlarge"] = enlarge
        self._kwargs["bootstrap"] = bootstrap
        self._kwargs["vol_dec"] = vol_dec
        self._kwargs["vol_check"] = vol_check
        self._kwargs["walks"] = walks
        self._kwargs["facc"] = facc
        self._kwargs["slices"] = slices
        self._kwargs["fmove"] = fmove
        self._kwargs["max_move"] = max_move
        self._kwargs["update_func"] = update_func

        for k, v in kwargs.items():

            self._kwargs[k] = v

        self._is_setup = True

    def sample(self, quiet=False):
        """
        sample using the UltraNest numerical integration method
        :rtype: 

        :returns: 

        """
        if not self._is_setup:

            print("You forgot to setup the sampler!")
            return

        loud = not quiet

        self._update_free_parameters()

        param_names = list(self._free_parameters.keys())

        ndim = len(param_names)

        self._kwargs["ndim"] = ndim

        loglike, dynesty_prior = self._construct_unitcube_posterior(return_copy=False)

        # check if we are doing to do things in parallel

        if threeML_config["parallel"]["use-parallel"]:

            c = ParallelClient()
            pool = c[:]

            self._kwargs["pool"] = pool

        sampler = NestedSampler(loglike, dynesty_prior, **self._kwargs)

        with use_astromodels_memoization(False):

            sampler.run_nested()

        self._sampler = sampler

        results = self._sampler.results

        # draw posterior samples
        weights = np.exp(results["logwt"] - results["logz"][-1])

        SQRTEPS = math.sqrt(float(np.finfo(np.float64).eps))

        rstate = np.random

        if abs(np.sum(weights) - 1.0) > SQRTEPS:  # same tol as in np.random.choice.
            raise ValueError("Weights do not sum to 1.")

        # Make N subdivisions and choose positions with a consistent random offset.
        nsamples = len(weights)
        positions = (rstate.random() + np.arange(nsamples)) / nsamples

        # Resample the data.
        idx = np.zeros(nsamples, dtype=np.int)
        cumulative_sum = np.cumsum(weights)
        i, j = 0, 0
        while i < nsamples:
            if positions[i] < cumulative_sum[j]:
                idx[i] = j
                i += 1
            else:
                j += 1

        samples_dynesty = results["samples"][idx]

        self._raw_samples = samples_dynesty

        # now do the same for the log likes

        logl_dynesty = results["logl"][idx]

        self._log_like_values = logl_dynesty

        self._log_probability_values = self._log_like_values + np.array(
            [self._log_prior(samples) for samples in self._raw_samples]
        )

        self._marginal_likelihood = sampler.results["logz"] / np.log(10.0)

        self._build_results()

        # Display results
        if loud:
            self._results.display()

        # now get the marginal likelihood

        return self.samples