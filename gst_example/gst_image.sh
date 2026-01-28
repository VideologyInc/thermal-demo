#!/bin/bash

gst-launch-1.0 -e \
  filesrc location=mono.png ! pngdec ! \
  imagefreeze ! \
  videoscale ! videoconvert ! \
  queue ! \
  hailonet hef-path=thermal_yolov8s.hef ! \
  hailofilter so-path=/usr/lib/hailo-post-processes/libyolo_hailortpp_post.so \
    function-name=filter config-path=thermal.json ! \
  queue ! \
  hailooverlay ! \
  videoconvert ! \
  pngenc ! filesink location=output.png sync=false


