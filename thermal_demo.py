import argparse
import cairo
import cv2
import numpy as np
import os
import random
import sys

from hailo_inference import HailoInference

import gi

gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

class Demo:
    def __init__(self, source, model_path, labels_path):
        self.inited = False
        self.detections = []
        self.labels = self.get_labels(labels_path)

        random.seed(42)
        self.colors = {cls: (random.randint(0, 255),
                            random.randint(0, 255),
                            random.randint(0, 255)) for cls in self.labels}

        self.hailo_infer = HailoInference(model_path)
        
        self.input_source = source
        print(source)

        if self.input_source.startswith("/dev/video"):
            cam_pipeline = (
                f"v4l2src device={self.input_source} ! "
                "videoconvert ! videoscale ! "
                "video/x-raw,width=640,height=640 ! "
                "tee name=t "
                "t. ! queue max-size-buffers=2 leaky=2 ! "
                "cairooverlay name=drawer ! autovideosink sync=false "
                "t. ! queue max-size-buffers=2 leaky=2 ! "
                "videoconvert ! video/x-raw,format=RGB !"
                "appsink emit-signals=true drop=true max-buffers=2 name=ml_sink"
            )
        elif self.input_source.endswith(".mp4") or self.input_source.endswith(".avi"):       
            cam_pipeline = (
                f"filesrc location={self.input_source} ! "
                "qtdemux ! h264parse ! avdec_h264 ! "
                "videoconvert ! videoscale ! "
                "video/x-raw,width=640,height=640,format=RGB ! "
                "tee name=t "
                "t. ! queue ! videoconvert ! "
                "cairooverlay name=drawer ! autovideosink sync=false "
                "t. ! queue ! videoconvert ! "
                "appsink emit-signals=true drop=true max-buffers=2 name=ml_sink"
            )
        
        print(cam_pipeline)

        pipeline = Gst.parse_launch(cam_pipeline)
        pipeline.set_state(Gst.State.PLAYING)

        drawer = pipeline.get_by_name("drawer")
        drawer.connect("draw", self.draw)

        ml_sink = pipeline.get_by_name("ml_sink")
        ml_sink.connect("new-sample", self.inference)

        self.inited = True
    
    def get_labels(self, path):
        with open(path, 'r') as f:
            return [line.strip() for line in f.readlines()]

    def inference(self, data):
        detections = []

        frame = data.emit("pull-sample")

        buf = frame.get_buffer()
        caps = frame.get_caps()
        h = caps.get_structure(0).get_value("height")
        w = caps.get_structure(0).get_value("width")

        # Map GstBuffer → numpy array
        success, map_info = buf.map(Gst.MapFlags.READ)
        if not success:
            return Gst.FlowReturn.ERROR

        frame = np.frombuffer(map_info.data, dtype=np.uint8).reshape(h, w, 3)
        buf.unmap(map_info)

        detections = self.hailo_infer.run(frame)

        if detections is not None:
            self.detections = self.convert_detections(detections)

        return Gst.FlowReturn.OK
    
    def convert_detections(self, results):
        detections = []
        for i in range(results['num_detections']):
            y1, x1, y2, x2 = results['detection_boxes'][i] # change from (x1, y1, x2, y2) to (y1, x1, y2, x2)
            score = results['detection_scores'][i]
            cls = int(results['detection_classes'][i])
            detections.append([x1, y1, x2, y2, score, cls])
        return detections

    def draw(self, overlay, context, timestamp, duration):
        CLASSES = self.labels
        COLORS = self.colors
        # Set Cairo properties
        context.set_line_width(2)

        for x1, y1, x2, y2, score, cls in self.detections:
            label = f"{CLASSES[cls]} {score:.2f}"

            r, g, b = [c / 255.0 for c in COLORS[CLASSES[cls]]]

            # Draw rectangle
            context.set_source_rgb(r, g, b)
            context.rectangle(x1, y1, x2 - x1, y2 - y1)
            context.stroke()

            # Draw label
            context.move_to(x1, y1 - 5)
            context.set_font_size(16)
            context.show_text(label)

    def close(self):
        self.hailo_infer.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-s", "--source", type=str, default="/dev/video-isi-csi0", help="Video source, e.g. dev/video0 or video file path"
    )
    parser.add_argument(
        "-n","--model", type=str, default="models/mono.hef", help="Path for models and image"
    )
    parser.add_argument(
        "-l", "--labels", type=str, default="common/mono.txt", help="Path for labels"
    )
    args = parser.parse_args()

    Gst.init(None)
    demo = Demo(args.source, args.model, args.labels)

    loop = GLib.MainLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        print("Pipeline stopped by user")
    finally:
        demo.close()
        loop.quit()