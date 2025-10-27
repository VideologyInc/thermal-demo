import cv2
import numpy as np
import os
import sys
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst
from hailo_platform import (
    HEF,
    ConfigureParams,
    FormatType,
    HailoSchedulingAlgorithm,
    HailoStreamInterface,
    InferVStreams,
    InputVStreamParams,
    OutputVStreamParams,
    VDevice
)
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
#from common.tracker.byte_tracker import BYTETracker
#from common.hailo_inference import HailoInfer
from common.toolbox import get_labels, load_json_file, preprocess, visualize, FrameRateTracker
from object_detection_post_process import extract_detections, draw_detections

from pathlib import Path

# LABELS = str(Path(__file__).parent / "common" / "coco.txt")
CONFIG = str(Path(__file__).parent / "common" / "config.json")

class HailoInference:
        def __init__(self, net_path: str):
            print("Start Load Hailo Model ", end='------ ')

            # self.labels = get_labels(LABELS)
            self.config_data = load_json_file(CONFIG)

            # Hailo Setup
            params = VDevice.create_params()
            params.scheduling_algorithm = HailoSchedulingAlgorithm.NONE
            self.target = VDevice(params=params)

            self.hef = HEF(net_path)

            self.configure_params = ConfigureParams.create_from_hef(hef=self.hef, interface=HailoStreamInterface.PCIe)

            self.network_groups = self.target.configure(self.hef, self.configure_params)
            self.network_group = self.network_groups[0]
            self.network_group_params = self.network_group.create_params()

            self.input_vstreams_params = InputVStreamParams.make(self.network_group, quantized=True,
                                                                format_type=FormatType.UINT8)
            self.output_vstreams_params = OutputVStreamParams.make(self.network_group, quantized=False,
                                                                format_type=FormatType.FLOAT32)

            # print("Input vstream infos")
            # for input_vstream_info in self.hef.get_input_vstream_infos():
            #     print("Name:", input_vstream_info.name)
            #     print("Shape:", input_vstream_info.shape)

            # print("Output vstream infos")
            # for output_vstream_info in self.hef.get_output_vstream_infos():
            #     print("Name:", output_vstream_info.name)
            #     print("Shape:", output_vstream_info.shape)

            self.output_name = self.hef.get_output_vstream_infos()[0].name
            print("Output vstream name:", self.output_name)

            self.network_group_context = self.network_group.activate(self.network_group_params)
            self.network_group_context.__enter__()  # 🔑 keep network active

            self.infer_pipeline = InferVStreams(self.network_group, self.input_vstreams_params, self.output_vstreams_params)
            self.infer_pipeline.__enter__()  # 🔑 keep vstreams alive

            print("Finish!")

        def run(self, frame):
            input_data = np.expand_dims(frame, axis=0).astype(np.uint8)
            try:
                infer_results = self.infer_pipeline.infer(input_data)
                if isinstance(infer_results, dict):
                    results = infer_results[self.output_name][0]
                    detections = extract_detections(frame, results, self.config_data)
                else:
                    detections = extract_detections(frame, infer_results, self.config_data)
                # print(detections)
                return detections
            except Exception as e:
                print("Inference error:", e)
                return None
            pass

        def close(self):
            if self.infer_pipeline:
                self.infer_pipeline.__exit__(None, None, None)
            if self.network_group_context:
                self.network_group_context.__exit__(None, None, None)

# Example usage
# if __name__ == "__main__":
#     hailo_models = "models/monov2.hef"
#     hailo_inference = HailoInference(hailo_models)
#     image = cv2.imread("bus.jpg")
#     image = cv2.resize(image, (640, 640))
#     detections = hailo_inference.run(image)
    
#     # Draw detections on the resized image (640x640) since coordinates are in that space
#     if detections is not None:
#         frame_with_detections = draw_detections(detections, image, hailo_inference.labels, tracker=None)
#         cv2.imwrite("output.jpg", frame_with_detections)
#         print(f"Saved output with {detections['num_detections']} detections")
#     else:
#         print("No detections found")
#     hailo_inference.close()
