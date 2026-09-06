from glob import glob
from setuptools import find_packages, setup


package_name = "xh_detector"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", glob("launch/*.launch.py")),
        ("share/" + package_name + "/config", glob("config/*.yaml")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="adam",
    maintainer_email="adam@localhost",
    description="Jetson Orin NX desktop-object detector for ROS 2 Humble",
    license="MIT",
    entry_points={
        "console_scripts": [
            "detector_node = xh_detector.detector_node:main",
        ],
    },
)

