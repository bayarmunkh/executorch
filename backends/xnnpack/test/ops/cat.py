# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import unittest

import torch
from executorch.backends.xnnpack.test.tester import Tester


class TestCat(unittest.TestCase):
    class Cat(torch.nn.Module):
        def forward(self, xs):
            return torch.cat(xs)

    def _test_cat(self, module, inputs, quant=False):
        tester = Tester(module, inputs)

        if quant:
            tester.quantize()

        tester.export().check_count({"torch.ops.aten.cat": 1})

        if quant:
            tester.check(["torch.ops.quantized_decomposed"])

        (
            tester.to_edge()
            .check_count({"executorch_exir_dialects_edge__ops_aten_cat": 1})
            .partition()
        )

        if quant:
            tester.check_not(["torch.ops.quantized_decomposed"])

        (
            tester.check_count({"torch.ops.higher_order.executorch_call_delegate": 1})
            .check_not(["executorch_exir_dialects_edge__ops_aten_cat"])
            .to_executorch()
            .serialize()
            .run_method()
            .compare_outputs()
        )

    def test_fp32_cat2(self):
        inputs = ((torch.ones(1, 2, 3), torch.ones(3, 2, 3)),)
        self._test_cat(self.Cat(), inputs)

    def test_fp32_cat3(self):
        inputs = ((torch.ones(1, 2, 3), torch.ones(3, 2, 3), torch.ones(2, 2, 3)),)
        self._test_cat(self.Cat(), inputs)

    def test_fp32_cat4(self):
        inputs = (
            (
                torch.ones(1, 2, 3),
                torch.ones(3, 2, 3),
                torch.ones(2, 2, 3),
                torch.ones(5, 2, 3),
            ),
        )
        self._test_cat(self.Cat(), inputs)

    def test_fp32_cat_unsupported(self):
        """
        XNNPACK only supports concatenating up to 4 values, so it should not delegate here.
        """
        inputs = (
            (
                torch.ones(1, 2, 3),
                torch.ones(3, 2, 3),
                torch.ones(2, 2, 3),
                torch.ones(5, 2, 3),
                torch.ones(1, 2, 3),
            ),
        )
        (
            Tester(self.Cat(), inputs)
            .export()
            .check_count({"torch.ops.aten.cat": 1})
            .to_edge()
            .check_count({"executorch_exir_dialects_edge__ops_aten_cat": 1})
            .partition()
            .check_not(["torch.ops.higher_order.executorch_call_delegate"])
        )

    class CatNegativeDim(torch.nn.Module):
        def __init__(self):
            super().__init__()

        def forward(self, x, y):
            return torch.cat([x, y], -1)

    def test_fp32_cat_negative_dim(self):
        inputs = (torch.ones(3, 2, 3), torch.ones(3, 2, 1))
        self._test_cat(self.CatNegativeDim(), inputs)

    class CatNhwc(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.conv = torch.nn.Conv2d(
                in_channels=1,
                out_channels=3,
                kernel_size=(3, 3),
                padding=1,
                bias=False,
            )

        def forward(self, x, y):
            x = self.conv(x)
            return torch.concatenate((y, x, y, x), 1)

    def test_qs8_cat_nhwc(self):
        inputs = (torch.randn(1, 1, 3, 3), torch.randn(1, 1, 3, 3))
        self._test_cat(self.CatNhwc(), inputs, quant=True)

    class CatNhwc2(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.conv = torch.nn.Conv2d(
                in_channels=1,
                out_channels=3,
                kernel_size=(3, 3),
                padding=1,
                bias=False,
            )

        def forward(self, x, y):
            x = self.conv(x)
            y = self.conv(y)
            return torch.concatenate((y, x, y, x), 3)

    def test_qs8_cat_nhwc2(self):
        inputs = (torch.randn(1, 1, 3, 3), torch.randn(1, 1, 3, 3))
        self._test_cat(self.CatNhwc(), inputs, quant=True)
