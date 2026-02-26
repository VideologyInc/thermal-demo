#!/bin/bash

gst-launch-1.0 \
    filesrc location=../../sample/mono2.png ! pngdec ! videoscale ! videoconvert ! video/x-raw,width=640,height=640 ! tee name=t \
    t. ! queue leaky=2 max-size-buffers=2 ! videoscale ! videoconvert ! video/x-raw,width=320,height=320,format=RGB ! \
    tensor_converter ! \
    queue leaky=2 max-size-buffers=2 ! \
    tensor_filter latency=1 framework=tensorflow2-lite model=../../models/thermal_yolov8n_320.tflite \
    custom=Delegate:External,ExtDelegateLib:libvx_delegate.so ! \
    tensor_transform mode=transpose option=1:0:2:3 ! \
    queue leaky=2 max-size-buffers=2 ! \
    tensor_transform mode=arithmetic option=typecast:float32,add:-17,mul:0.006334480829536915 ! \
    tensor_decoder mode=bounding_boxes option1=yolov8 option2=../../configs/thermal.txt option4=640:640 option5=320:320 ! \
    videoscale ! videoconvert ! video/x-raw,width=640,height=640,format=RGBA ! compositor.sink_1 \
    t. ! queue leaky=2 max-size-buffers=2 ! videoconvert ! video/x-raw,width=640,height=640,format=RGBA ! compositor.sink_0 \
    compositor name=compositor sink_1::zorder=2 sink_0::zorder=1 ! \
    queue leaky=2 max-size-buffers=2 ! \
    videoconvert ! pngenc ! filesink location=output.png
