import os
import subprocess
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class CustomHook(BuildHookInterface):
    def finalize(self, version, build_data, artifact_path):
        # Only run for wheels
        if self.target_name != "wheel":
            return

        # Get the site-packages directory
        # This is a bit of a hack, but it's the most reliable way to get it
        site_packages = subprocess.check_output(["python", "-c", "import site; print(site.getsitepackages()[0])"]).decode().strip()

        # Create the activation script
        script = f'eval "$(register-python-argcomplete nora)"'

        # Write the script to a file in the bin directory
        bin_dir = os.path.join(site_packages, "..", "..", "bin")
        if not os.path.exists(bin_dir):
            os.makedirs(bin_dir)

        with open(os.path.join(bin_dir, "nora-completion.sh"), "w") as f:
            f.write(script)
