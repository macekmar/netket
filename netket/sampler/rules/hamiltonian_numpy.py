# Copyright 2021 The NetKet Authors - All rights reserved.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import Any
import math

from numba import jit

import numpy as np
from flax import struct

from netket.legacy import random as _random
from netket.operator import AbstractOperator


from ..metropolis import MetropolisRule


@struct.dataclass
class HamiltonianRuleState:
    sections: np.ndarray
    """Preallocated array for sections"""


@struct.dataclass
class HamiltonianRuleNumpy(MetropolisRule):
    """
    Rule for Numpy sampler backend proposing moves according to the terms in an operator.

    In this case, the transition matrix is taken to be:

    .. math::
       T( \mathbf{s} \rightarrow \mathbf{s}^\prime) = \frac{1}{\mathcal{N}(\mathbf{s})}\theta(|H_{\mathbf{s},\mathbf{s}^\prime}|),
    """

    Ô: Any = struct.field(pytree_node=False)

    def __post_init__(self):
        # Raise errors if hilbert is not an Hilbert
        if not isinstance(self.Ô, AbstractOperator):
            raise TypeError(
                "Argument to HamiltonianRuleNumpy must be a valid operator.".format(
                    type(operator)
                )
            )

    def init_state(rule, sampler, machine, params, key):
        return HamiltonianRuleState(
            sections=np.empty(sampler.n_batches, dtype=np.int32)
        )

    def transition(rule, sampler, machine, parameters, state, rng, σ):
        σ = state.σ
        σ1 = state.σ1
        log_prob_corr = state.log_prob_corr

        sections = state.rule_state.sections
        σp = rule.Ô.get_conn_flattened(σ, sections)[0]

        rand_vec = rng.uniform(0, 1, size=σ.shape[0])

        _choose(σp, sections, σ1, log_prob_corr, rand_vec)
        rule.Ô.n_conn(σ1, sections)
        log_prob_corr -= np.log(sections)


@jit(nopython=True)
def _choose(states, sections, out, w, rand_vec):
    low_range = 0
    for i, s in enumerate(sections):
        n_rand = low_range + int(np.floor(rand_vec[i] * (s - low_range)))
        out[i] = states[n_rand]
        w[i] = math.log(s - low_range)
        low_range = s