from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    default_config = os.path.join(
        get_package_share_directory("xh_detector"),
        "config",
        "detector.yaml",
    )

    config_arg = DeclareLaunchArgument(
        "config",
        default_value=default_config,
        description="Absolute path to detector YAML configuration",
    )

    detector = Node(
        package="xh_detector",
        executable="detector_node",
        name="xh_detector",
        output="screen",
        emulate_tty=True,
        parameters=[LaunchConfiguration("config")],
    )

    return LaunchDescription([config_arg, detector])

