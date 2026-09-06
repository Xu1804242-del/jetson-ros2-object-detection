#!/usr/bin/env python3
"""Minimal Jetson camera detector for ROS 2 Humble."""

from pathlib import Path
from datetime import datetime
import os
import time
from typing import Optional

import cv2
from cv_bridge import CvBridge
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Float32
from ultralytics import YOLO
from vision_msgs.msg import Detection2D, Detection2DArray, ObjectHypothesisWithPose


class DetectorNode(Node):
    """Read a USB camera, run YOLO, draw boxes and publish ROS 2 results."""

    def __init__(self) -> None:
        super().__init__("xh_detector")
        self._declare_parameters()
        self._read_parameters()

        self.bridge = CvBridge()
        self.model = YOLO(self.model_path)
        self.capture = self._open_camera()
        self.video_writer: Optional[cv2.VideoWriter] = None
        self.recording_active = self.save_video
        self.current_video_path: Optional[Path] = None
        self.last_time = time.perf_counter()
        self.fps = 0.0

        self.detections_pub = self.create_publisher(
            Detection2DArray, "/xh/detections", 10
        )
        self.image_pub = self.create_publisher(Image, "/xh/detection_image", 10)
        self.fps_pub = self.create_publisher(Float32, "/xh/fps", 10)

        period = 1.0 / max(self.camera_fps, 1.0)
        self.timer = self.create_timer(period, self._detect_once)
        self.get_logger().info(
            f"Started: camera={self.camera_device}, model={self.model_path}"
        )

    def _declare_parameters(self) -> None:
        parameters = {
            "camera_device": "/dev/video0",
            "camera_width": 640,
            "camera_height": 480,
            "camera_fps": 15.0,
            "camera_fourcc": "MJPG",
            "frame_id": "camera_link",
            "model_path": "/home/adam/Team9/xh/models/best.pt",
            "device": "0",
            "image_size": 640,
            "confidence_threshold": 0.40,
            "iou_threshold": 0.45,
            "show_window": False,
            "save_video": False,
            "output_video": "/home/adam/Team9/xh/output/detection.avi",
        }
        for name, value in parameters.items():
            self.declare_parameter(name, value)

    def _read_parameters(self) -> None:
        get = lambda name: self.get_parameter(name).value
        self.camera_device = str(get("camera_device"))
        self.camera_width = int(get("camera_width"))
        self.camera_height = int(get("camera_height"))
        self.camera_fps = float(get("camera_fps"))
        self.camera_fourcc = str(get("camera_fourcc"))
        self.frame_id = str(get("frame_id"))
        self.model_path = os.path.expanduser(str(get("model_path")))
        self.device = str(get("device"))
        self.image_size = int(get("image_size"))
        self.confidence = float(get("confidence_threshold"))
        self.iou = float(get("iou_threshold"))
        self.show_window = bool(get("show_window"))
        self.save_video = bool(get("save_video"))
        self.output_video = Path(os.path.expanduser(str(get("output_video"))))

    def _open_camera(self) -> cv2.VideoCapture:
        source = (
            int(self.camera_device)
            if self.camera_device.isdigit()
            else self.camera_device
        )
        capture = cv2.VideoCapture(source, cv2.CAP_V4L2)
        capture.set(
            cv2.CAP_PROP_FOURCC,
            cv2.VideoWriter_fourcc(*self.camera_fourcc[:4]),
        )
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.camera_width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.camera_height)
        capture.set(cv2.CAP_PROP_FPS, self.camera_fps)
        capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if not capture.isOpened():
            raise RuntimeError(f"Cannot open camera {self.camera_device}")
        return capture

    def _detect_once(self) -> None:
        ok, frame = self.capture.read()
        if not ok:
            self.get_logger().error("Camera read failed")
            return

        result = self.model.predict(
            frame,
            imgsz=self.image_size,
            conf=self.confidence,
            iou=self.iou,
            device=self.device,
            half=True,
            verbose=False,
        )[0]

        now_time = time.perf_counter()
        current_fps = 1.0 / max(now_time - self.last_time, 1e-9)
        self.last_time = now_time
        self.fps = current_fps if self.fps == 0 else 0.9 * self.fps + 0.1 * current_fps

        annotated = result.plot()
        cv2.putText(
            annotated,
            f"FPS: {self.fps:.1f}",
            (10, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )
        self._draw_recording_status(annotated)

        stamp = self.get_clock().now().to_msg()
        detection_message = self._make_detection_message(result, stamp)
        self.detections_pub.publish(detection_message)

        image_message = self.bridge.cv2_to_imgmsg(annotated, encoding="bgr8")
        image_message.header.stamp = stamp
        image_message.header.frame_id = self.frame_id
        self.image_pub.publish(image_message)
        self.fps_pub.publish(Float32(data=float(self.fps)))

        self._save_frame(annotated)
        if self.show_window:
            cv2.imshow("xh detector", annotated)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("r"), ord("R")):
                self._toggle_recording(annotated)
            elif key in (ord("q"), ord("Q")):
                rclpy.shutdown()

    def _make_detection_message(self, result, stamp) -> Detection2DArray:
        output = Detection2DArray()
        output.header.stamp = stamp
        output.header.frame_id = self.frame_id
        if result.boxes is None:
            return output

        for box in result.boxes:
            x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].cpu().tolist()]
            class_id = int(box.cls[0].item())
            score = float(box.conf[0].item())

            detection = Detection2D()
            detection.header = output.header
            detection.bbox.center.position.x = (x1 + x2) / 2.0
            detection.bbox.center.position.y = (y1 + y2) / 2.0
            detection.bbox.size_x = x2 - x1
            detection.bbox.size_y = y2 - y1

            hypothesis = ObjectHypothesisWithPose()
            hypothesis.hypothesis.class_id = str(result.names[class_id])
            hypothesis.hypothesis.score = score
            detection.results.append(hypothesis)
            output.detections.append(detection)
        return output

    def _save_frame(self, frame) -> None:
        if not self.recording_active:
            return
        if self.video_writer is None:
            self._start_recording(frame)
        if self.video_writer is not None:
            self.video_writer.write(frame)

    def _toggle_recording(self, frame) -> None:
        if self.recording_active:
            self._stop_recording()
            return
        self._start_recording(frame)
        if self.video_writer is not None:
            self.video_writer.write(frame)

    def _start_recording(self, frame) -> None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = self.output_video.suffix or ".avi"
        filename = f"{self.output_video.stem}_{timestamp}{suffix}"
        video_path = self.output_video.with_name(filename)
        video_path.parent.mkdir(parents=True, exist_ok=True)

        writer = cv2.VideoWriter(
            str(video_path),
            cv2.VideoWriter_fourcc(*"MJPG"),
            self.camera_fps,
            (frame.shape[1], frame.shape[0]),
        )
        if not writer.isOpened():
            self.get_logger().error(f"Cannot create {video_path}")
            writer.release()
            self.recording_active = False
            return

        self.video_writer = writer
        self.current_video_path = video_path
        self.recording_active = True
        self.get_logger().info(f"Recording started: {video_path}")

    def _stop_recording(self) -> None:
        if self.video_writer is not None:
            self.video_writer.release()
            self.video_writer = None
        if self.current_video_path is not None:
            self.get_logger().info(f"Recording saved: {self.current_video_path}")
        self.current_video_path = None
        self.recording_active = False

    def _draw_recording_status(self, frame) -> None:
        if self.recording_active:
            cv2.circle(frame, (18, 58), 7, (0, 0, 255), -1)
            cv2.putText(
                frame,
                "REC",
                (32, 64),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2,
                cv2.LINE_AA,
            )
        cv2.putText(
            frame,
            "R: record  Q: quit",
            (10, frame.shape[0] - 12),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )

    def close(self) -> None:
        self.capture.release()
        self._stop_recording()
        cv2.destroyAllWindows()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = DetectorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.close()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
