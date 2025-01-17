# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import unittest

import torch
from executorch.backends.xnnpack.test.tester import Tester


class TestMaxPool2d(unittest.TestCase):
    class MaxPool2d(torch.nn.Module):
        def __init__(self, kernel_size=3, stride=1, padding=0, dilation=1):
            super().__init__()
            self.max_pool2d_module = torch.nn.MaxPool2d(
                kernel_size=kernel_size,
                stride=stride,
                padding=padding,
                dilation=dilation,
            )

        def forward(self, x):
            return self.max_pool2d_module(x)

    class MaxPool2dUnsupported(torch.nn.Module):
        def __init__(self, kernel_size=3, stride=1, padding=0, dilation=1):
            super().__init__()
            self.max_pool2d_module = torch.nn.MaxPool2d(
                kernel_size=kernel_size,
                stride=stride,
                padding=padding,
                dilation=dilation,
                return_indices=True,
            )

        def forward(self, x):
            return self.max_pool2d_module(x)[1]

    def test_fp32_maxpool2d(self):
        """
        Note that the export process generates aten.max_pool2d_with_indices. The remove_getitem_op
        pass transforms it into aten.max_pool2d (if supported).
        """
        inputs = (torch.randn(4, 3, 24, 24),)
        (
            Tester(self.MaxPool2d(3, 1, 0, 1), inputs)
            .export()
            .check_count({"torch.ops.aten.max_pool2d_with_indices.default": 1})
            .check(["getitem"])
            .to_edge()
            .check_count(
                {
                    "executorch_exir_dialects_edge__ops_aten_max_pool2d_with_indices_default": 1,
                }
            )
            .check(["getitem"])
            .partition()
            .check_count({"torch.ops.higher_order.executorch_call_delegate": 1})
            .check_not(
                [
                    "executorch_exir_dialects_edge__ops_aten_max_pool2d_with_indices_default"
                ]
            )
            .to_executorch()
            .serialize()
            .run_method()
            .compare_outputs()
        )

    def test_fp32_maxpool2d_unsupported(self):
        """
        MaxPool2d with return_indices is not generally supported (see maxpool2d_with_indices constraint).
        """
        inputs = (torch.randn(4, 3, 24, 24),)
        (
            Tester(self.MaxPool2dUnsupported(), inputs)
            .export()
            .check_count({"torch.ops.aten.max_pool2d_with_indices.default": 1})
            .to_edge()
            .check_count(
                {
                    "executorch_exir_dialects_edge__ops_aten_max_pool2d_with_indices_default": 1
                }
            )
            .partition()
            # We expect it not be be delegated.
            .check_count(
                {
                    "executorch_exir_dialects_edge__ops_aten_max_pool2d_with_indices_default": 1
                }
            )
        )
