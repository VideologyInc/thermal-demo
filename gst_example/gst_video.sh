#!/bin/bash

gst-launch-1.0 \
  filesrc location=video_flir_1.mp4 ! \
  qtdemux ! h264parse ! avdec_h264 ! \
  videoconvert ! videoscale ! \
  queue leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
  hailonet hef-path=thermal_yolov8s.hef ! \
  queue leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
  hailofilter so-path=/usr/lib/hailo-post-processes/libyolo_hailortpp_post.so \
  function-name=filter config-path=thermal.json ! \
  queue leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
  hailooverlay ! \
  videoconvert ! autovideosink sync=false