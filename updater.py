import subprocess
import sys
import pkg_resources

REQUIRED_PACKAGES = {
    "transformers": "4.30.0",  # пример минимальной версии
    "torch": "2.0.0",
    "accelerate": "0.26.0",
}

def check_and_install_packages():
    for package, min_version in REQUIRED_PACKAGES.items():
        try:
            pkg = pkg_resources.get_distribution(package)
            installed_version = pkg.version
            if pkg_resources.parse_version(installed_version) < pkg_resources.parse_version(min_version):
                print(f"Обновляю {package} {installed_version} -> {min_version}+")
                subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", f"{package}>={min_version}"])
            else:
                print(f"{package} версии {installed_version} - OK")
        except pkg_resources.DistributionNotFound:
            print(f"Устанавливаю {package} версии {min_version}+")
            subprocess.check_call([sys.executable, "-m", "pip", "install", f"{package}>={min_version}"])

if __name__ == "__main__":
    check_and_install_packages()