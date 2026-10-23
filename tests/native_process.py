# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SPIKE-GROUNDTRUTH — isolated interpreter coverage instrumentation

"""Run real site-package-free interpreters while retaining exact instrumentation."""

import subprocess
import sys
from pathlib import Path

import coverage


def run_isolated(command: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    """Run an actual command with only the verified coverage instrument loaded.

    Parameters
    ----------
    command : Path
        Real production command script.
    *arguments : str
        Literal command arguments, without shell interpolation.

    Returns
    -------
    subprocess.CompletedProcess[str]
        Reaped isolated interpreter output and actual exit.
    """
    return run_isolated_program(
        "import runpy, sys; command = sys.argv[1]; sys.path.insert(0, str(__import__('pathlib').Path(command).parent)); sys.argv = sys.argv[1:]; runpy.run_path(command, run_name='__main__')",
        str(command),
        *arguments,
    )


def run_isolated_program(program: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    """Run an authored public-API probe in an actual site-package-free interpreter.

    Parameters
    ----------
    program : str
        Literal test caller code invoking actual production APIs.
    *arguments : str
        Literal caller arguments, without shell interpolation.

    Returns
    -------
    subprocess.CompletedProcess[str]
        Actual reaped output with only the exact coverage instrument loaded.
    """
    instrument = """
import importlib.util, sys
spec = importlib.util.spec_from_file_location('coverage', sys.argv[1])
module = importlib.util.module_from_spec(spec)
sys.modules['coverage'] = module
spec.loader.exec_module(module)
tracker = module.Coverage(data_suffix=True)
program = sys.argv[2]
sys.argv = ['isolated-native-api', *sys.argv[3:]]
tracker.start()
try:
    exec(compile(program, '<isolated-public-api-caller>', 'exec'))
finally:
    tracker.stop()
    tracker.save()
"""
    return subprocess.run(
        [sys.executable, "-S", "-c", instrument, str(coverage.__file__), program, *arguments],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
