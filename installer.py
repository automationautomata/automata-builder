"""Package building and installation.

to verbolse output use -v flag as arg.
"""

import importlib.util
import os
import shutil
import subprocess
import sys

RED_COLOR = "\033[31m"
BLUE_COLOR = "\033[34m"
GREEN_COLOR = "\033[32m"
RESET_COLOR = "\033[0m"


def color_text(text: str, color_code: str = ""):
    if not color_code:
        return text
    return f"{color_code}{text}{RESET_COLOR}"


def clean_build_artifacts():
    """Removing build, dist and *.egg-info directories."""
    folders = ["build", "dist"]

    egg_info_dirs = []
    for dirpath, dirnames, _ in os.walk("."):
        for d in dirnames:
            if d.endswith(".egg-info"):
                egg_info_dirs.append(os.path.join(dirpath, d))

    for folder in folders + egg_info_dirs:
        if os.path.exists(folder):
            print(f"Removing {folder}...")
            shutil.rmtree(folder)


def install(package_name: str, verbose: bool = False):
    """Build and install the current package using the build packege
    (if it does not exist, it is installed)

    verbose - set True to print output of commands to console, deafult - False.
    """
    run_kwargs = dict(check=True, stdout=subprocess.DEVNULL)
    if verbose:
        run_kwargs.update(stdout=sys.stdout)

    try:
        python_cmd = sys.executable
        pip_cmd = [python_cmd, "-m", "pip", "install", "--disable-pip-version-check"]

        if not importlib.util.find_spec("build"):
            print("The 'build' package is not installed. Installing it now...")
            subprocess.run([*pip_cmd, "build"], **run_kwargs)

        # problem of using build.ProjectBuilder(".").build("wheel", "dist")
        # is output redirection (contextlib is needed)
        print("Building the project...")
        subprocess.run([python_cmd, "-m", "build"], **run_kwargs)

        print(color_text("Build completed.", GREEN_COLOR))

        subprocess.run([*pip_cmd, "-e", "."], **run_kwargs)
        print(color_text("Installation completed.", GREEN_COLOR))

        print(color_text(f"To run use {package_name} command in console", BLUE_COLOR))
        print(color_text(f"{python_cmd} -m {package_name}", BLUE_COLOR))

    except subprocess.TimeoutExpired:
        print(color_text("Installation error: timeout expired", RED_COLOR))
    except (subprocess.CalledProcessError, OSError) as e:
        print()
        print(color_text("Installation can't be finished", RED_COLOR))
        print(color_text("ERROR:", RED_COLOR))
        print(e.stderr if isinstance(e, subprocess.CalledProcessError) else e)
    finally:
        print()
        print("Cleaninig build artifacts...")
        clean_build_artifacts()
        print("Artifacts cleaned.")


if __name__ == "__main__":
    verbose_flag = "-v"
    # using -v flag for verbose installation
    cmd_args = sys.argv[1::]
    verbose = verbose_flag in cmd_args
    install("automata_builder", verbose)
