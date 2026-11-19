import os
import unittest
from unittest import mock

from tests import test_m4_acceptance as acceptance


def test_full_discovery_does_not_start_a_second_unittest_suite():
    method = 'test_W_every_non_fastapi_test_module_passes'
    with mock.patch.dict(os.environ, {'OMNI_M4_ACCEPTANCE_W_DISCOVERY': '1',
                                      'OMNI_M4_ACCEPTANCE_W_NESTED': '0'}):
        with mock.patch.object(acceptance.subprocess, 'run') as run:
            case = acceptance.AcceptanceW(method)
            with unittest.TestCase().assertRaisesRegex(unittest.SkipTest, 'full unittest discovery'):
                getattr(case, method)()
            run.assert_not_called()


def test_standalone_acceptance_w_still_runs_with_original_timeout():
    method = 'test_W_every_non_fastapi_test_module_passes'
    result = mock.Mock(returncode=0, stdout='', stderr='OK')
    with mock.patch.dict(os.environ, {'OMNI_M4_ACCEPTANCE_W_DISCOVERY': '0',
                                      'OMNI_M4_ACCEPTANCE_W_NESTED': '0'}):
        with mock.patch.object(acceptance.subprocess, 'run', return_value=result) as run:
            case = acceptance.AcceptanceW(method)
            getattr(case, method)()
            run.assert_called_once()
            assert run.call_args.kwargs['timeout'] == 300
            assert run.call_args.kwargs['env']['OMNI_M4_ACCEPTANCE_W_NESTED'] == '1'
