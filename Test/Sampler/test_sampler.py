import netket as nk
import networkx as nx
import numpy as np
import pytest
from pytest import approx

samplers = {}

# TESTS FOR SPIN HILBERT
# Constructing a 1d lattice
g = nk.graph.Hypercube(length=6, n_dim=1)

# Hilbert space of spins from given graph
hi = nk.hilbert.Spin(s=0.5, graph=g)
ma = nk.machine.RbmSpin(hilbert=hi, alpha=1)
ma.init_random_parameters(seed=1234, sigma=0.2)

sa = nk.sampler.MetropolisLocal(machine=ma)
samplers["MetropolisLocal RbmSpin"] = sa

sa = nk.sampler.MetropolisLocalPt(machine=ma, n_replicas=4)
samplers["MetropolisLocalPt RbmSpin"] = sa

ha = nk.operator.Ising(hilbert=hi, h=1.0)
sa = nk.sampler.MetropolisHamiltonian(machine=ma, hamiltonian=ha)
samplers["MetropolisHamiltonian RbmSpin"] = sa

ma = nk.machine.RbmSpinSymm(hilbert=hi, alpha=1)
ma.init_random_parameters(seed=1234, sigma=0.2)
sa = nk.sampler.MetropolisHamiltonianPt(
    machine=ma, hamiltonian=ha, n_replicas=4)
samplers["MetropolisHamiltonianPt RbmSpinSymm"] = sa

hi = nk.hilbert.Boson(graph=g, n_max=4)
ma = nk.machine.RbmSpin(hilbert=hi, alpha=1)
ma.init_random_parameters(seed=1234, sigma=0.2)
sa = nk.sampler.MetropolisLocal(machine=ma)
g = nk.graph.Hypercube(length=4, n_dim=1)
samplers["MetropolisLocal Boson"] = sa

sa = nk.sampler.MetropolisLocalPt(machine=ma, n_replicas=4)
samplers["MetropolisLocalPt Boson"] = sa

ma = nk.machine.RbmMultiVal(hilbert=hi, alpha=1)
ma.init_random_parameters(seed=1234, sigma=0.2)
sa = nk.sampler.MetropolisLocal(machine=ma)
samplers["MetropolisLocal Boson MultiVal"] = sa

hi = nk.hilbert.Spin(s=0.5, graph=g)
g = nk.graph.Hypercube(length=6, n_dim=1)
ma = nk.machine.RbmSpinSymm(hilbert=hi, alpha=1)
ma.init_random_parameters(seed=1234, sigma=0.2)
l = hi.size
X = [[0, 1],
     [1, 0]]

move_op = nk.operator.LocalOperator(hilbert=hi,
                                    operators=[X] * l,
                                    acting_on=[[i] for i in range(l)])

sa = nk.sampler.CustomSampler(machine=ma, move_operators=move_op)
samplers["CustomSampler Spin"] = sa


sa = nk.sampler.CustomSamplerPt(
    machine=ma, move_operators=move_op, n_replicas=4)
samplers["CustomSamplerPt Spin"] = sa

# Two types of custom moves
# single spin flips and nearest-neighbours exchanges
spsm = [[1, 0, 0, 0],
        [0, 0, 1, 0],
        [0, 1, 0, 0],
        [0, 0, 0, 1]]

ops = [X] * l
ops += [spsm] * l

acting_on = [[i] for i in range(l)]
acting_on += ([[i, (i + 1) % l] for i in range(l)])

move_op = nk.operator.LocalOperator(hilbert=hi,
                                    operators=ops,
                                    acting_on=acting_on)

sa = nk.sampler.CustomSampler(machine=ma, move_operators=move_op)
samplers["CustomSampler Spin 2 moves"] = sa


def test_states_in_hilbert():
    for name, sa in samplers.items():
        print("Sampler test: %s" % name)

        hi = sa.hilbert
        ma = sa.machine
        localstates = hi.local_states

        for sw in range(100):
            sa.sweep()
            visible = sa.visible
            assert(len(visible) == hi.size)
            for v in visible:
                assert(v in localstates)

            assert(np.min(sa.acceptance) >= 0 and np.max(
                sa.acceptance) <= 1.0)


# Testing that samples generated from direct sampling are compatible with those
# generated by markov chain sampling
# here we use the L_1 test presented in https://arxiv.org/pdf/1308.3946.pdf


def test_correct_sampling():
    for name, sa in samplers.items():
        print("Sampler test: %s" % name)

        hi = sa.hilbert
        ma = sa.machine

        n_states = hi.n_states

        n_samples = max(10 * n_states, 10000)

        hist_samp = np.zeros(n_states)
        # fill in the histogram for sampler
        for sw in range(n_samples):
            sa.sweep()
            visible = sa.visible
            hist_samp[hi.state_to_number(visible)] += 1

        hist_exsamp = np.zeros(n_states)
        sa = nk.sampler.ExactSampler(machine=ma)
        # fill in histogram for exact sampler
        for sw in range(n_samples):
            sa.sweep()
            visible = sa.visible
            hist_exsamp[hi.state_to_number(visible)] += 1

        print(hist_exsamp)
        print(hist_samp)

        # now test that histograms are close in norm
        delta = hist_samp - hist_exsamp
        z = np.sum(delta * delta - hist_exsamp - hist_samp)
        z = np.sqrt(np.abs(z)) / float(n_samples)

        eps = np.sqrt(1. / float(n_samples))

        assert(z == approx(0., rel=5 * eps, abs=5 * eps))
