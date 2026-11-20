import os
from unittest.mock import patch

import pytest

from tests import test_m4_acceptance as acceptance


def test_offline_acceptance_fails_on_a_real_inner_test_failure(tmp_path):
    (tmp_path / 'test_broken.py').write_text('def test_broken():\n    assert False\n')
    run_real = acceptance.subprocess.run

    def run_small_suite(command, **kwargs):
        assert command[1:] == ['-m', 'pytest', '-q', 'tests', '-m', 'not needs_env']
        return run_real([*command[:4], str(tmp_path), *command[5:]], **kwargs)

    method = 'test_W_every_non_fastapi_test_module_passes'
    with patch.dict(os.environ, {'OMNI_M4_ACCEPTANCE_W_NESTED': '0',
                                 'OMNI_M4_ACCEPTANCE_W_DISCOVERY': '0'}):
        with patch.object(acceptance, 'find_spec', return_value=None):
            with patch.object(acceptance.subprocess, 'run', side_effect=run_small_suite):
                case = acceptance.AcceptanceW(method)
                with pytest.raises(AssertionError, match='offline regression suite failed'):
                    getattr(case, method)()
