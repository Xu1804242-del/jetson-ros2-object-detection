# XH Jetson桌面目标检测项目

本项目在Jetson Orin NX上使用YOLO11检测 `book`、`mouse`、`phone`，通过
ROS2 Humble发布检测框、类别、置信度、标注图像和FPS。

## 目录说明

```text
xh/
├── dataset/                    正式训练数据集（303张）
├── models/                     部署和预训练模型
├── src/                        ROS2实时检测源代码
├── training/                   正式训练过程、曲线和权重
├── validation/                 独立测试集验证结果
├── output/                     实时检测录像
├── error_cases/                漏检、误检和混淆案例
├── archive/                    未用于正式训练的旧数据
├── data.yaml                   正式数据集路径和类别定义
├── train.py                    YOLO训练入口
└── README.md                   本说明
```

### dataset

正式训练使用的Roboflow YOLO数据集：

```text
dataset/train/images、dataset/train/labels
dataset/valid/images、dataset/valid/labels
dataset/test/images、dataset/test/labels
```

该数据集类别编号为：`0=book、1=mouse、2=phone`。

### models

- `models/best.pt`：实时检测程序默认加载的模型。
- `models/pretrained/yolo11n.pt`：重新训练时使用的YOLO11n预训练权重。

注意：当前 `models/best.pt` 按用户提供的信息使用
`0=book、1=phone、2=mouse`，与正式数据集的后两类顺序不同。不要直接用它
对该数据集继续训练，除非先统一类别编号。

### src

ROS2软件包 `xh_detector`：

- `src/xh_detector/xh_detector/detector_node.py`：最重要的实时检测代码；读取摄像头、
  调用YOLO、绘制方框和置信度、发布ROS2消息、显示FPS并按键录像。
- `src/xh_detector/config/detector.yaml`：模型路径、摄像头、阈值、窗口和录像参数。
- `src/xh_detector/launch/detector.launch.py`：一条命令启动检测节点。
- `src/xh_detector/package.xml`：ROS2依赖声明。
- `src/xh_detector/setup.py`、`setup.cfg`：Python包和命令入口。

实时窗口按键：`R` 开始/停止录像，`Q` 退出。录像保存在
`/home/adam/Team9/xh/output/`，文件名包含时间戳。

### training

`training/desktop_objects/` 保存正式训练证据：

- `weights/best.pt`：该次训练验证指标最佳的权重。
- `weights/last.pt`：最后一轮权重，可用于恢复训练。
- `results.csv`、`results.png`：每轮损失和指标。
- `confusion_matrix*.png`：混淆矩阵。
- `val_batch*_pred.jpg`：验证集预测案例。

### validation

`validation/test_results/` 是独立测试集的评估图、混淆矩阵和预测案例。

### output

检测结果录像。运行窗口中每按一次 `R` 开始或结束一段带时间戳的录像。



## 完整流程

1. 在 `dataset/` 中准备图片和YOLO标签。
2. 检查 `data.yaml` 的路径与类别顺序。
3. 执行 `python3 train.py` 训练模型。
4. 将最佳权重复制为 `models/best.pt`。
5. 在Jetson运行 `colcon build --symlink-install` 构建ROS2包。
6. 启动实时检测并通过ROS2发布结果。
7. 保存录像、测试指标和典型错误案例。

## Jetson构建与启动

```bash
cd /home/adam/Team9/xh
source /opt/ros/humble/setup.bash
colcon build --symlink-install
python3 -m pip install --user --no-deps -e src/xh_detector

export AMENT_PREFIX_PATH="/home/adam/Team9/xh/install/xh_detector:$AMENT_PREFIX_PATH"
export PYTHONPATH="$HOME/.local/lib/python3.10/site-packages:/home/adam/Team9/xh/install/xh_detector/lib/python3.10/site-packages:$PYTHONPATH"
ros2 launch xh_detector detector.launch.py
```

ROS2话题：

```text
/xh/detections
/xh/detection_image
/xh/fps
```
