from __future__ import print_function
from threeML import *
from .conftest import get_grb_model


# Define a dummy function to return always the same model
def get_model(id):

    return get_grb_model(Powerlaw())


def test_joint_likelihood_set(data_list_bn090217206_nai6):
    def get_data(id):
        return data_list_bn090217206_nai6

    jlset = JointLikelihoodSet(
        data_getter=get_data, model_getter=get_model, n_iterations=10
    )

    jlset.go(compute_covariance=False)


def test_joint_likelihood_set_parallel(data_list_bn090217206_nai6):
    def get_data(id):
        return data_list_bn090217206_nai6

    jlset = JointLikelihoodSet(
        data_getter=get_data, model_getter=get_model, n_iterations=10
    )

    with parallel_computation(start_cluster=False):

        res = jlset.go(compute_covariance=False)

    print(res)
