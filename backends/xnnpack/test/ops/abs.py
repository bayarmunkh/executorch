# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import unittest

import torch
from executorch.backends.xnnpack.test.tester import Tester


class TestAbs(unittest.TestCase):
    class Abs(torch.nn.Module):
        def __init__(self):
            super().__init__()

        def forward(self, x):
            z = torch.abs(x)
            return z

    def test_fp32_abs(self):
        inputs = (
            torch.Tensor(
                [
                    [0.0, 0.1, 0.5, 0.499],
                    [-0.6, -0.4, 100.1, -1000.1],
                ],
            ),
        )
        (
            Tester(self.Abs(), inputs)
            .export()
            .check_count({"torch.ops.aten.abs.default": 1})
            .to_edge()
            .check_count({"executorch_exir_dialects_edge__ops_aten_abs_default": 1})
            .partition()
            .check_count({"torch.ops.higher_order.executorch_call_delegate": 1})
            .check_not(["executorch_exir_dialects_edge__ops_aten_abs_default"])
            .to_executorch()
            .serialize()
            .run_method()
            .compare_outputs()
        )
