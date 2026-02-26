#!/bin/bash

VIDEO_PATH="${1:-../../samples/video_flir_1.mp4}"

echo "Using video: $VIDEO_PATH"

if [ ! -f "$VIDEO_PATH" ]; then
  echo "Error: Video file not found: $VIDEO_PATH"
  exit 1
fi

gst-launch-1.0 \
  filesrc location="$VIDEO_PATH" ! \
  qtdemux ! h264parse ! avdec_h264 ! \
  videoconvert ! videoscale ! \
  queue leaky=no max-size-buffers=5 max-size-bytes=0 max-size-time=0 ! \
  hailonet hef-path=../../models/thermal_yolov8s.hef ! \
  queue leaky=no max-size-buffers=5 max-size-bytes=0 max-size-time=0 ! \
  hailofilter so-path=/usr/lib/hailo-post-processes/libyolo_hailortpp_post.so \
  function-name=filter config-path=../../configs/thermal.json ! \
  queue leaky=no max-size-buffers=5 max-size-bytes=0 max-size-time=0 ! \
  hailooverlay ! \
  videoconvert ! autovideosink sync=false