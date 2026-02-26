#!/bin/bash

IMAGE_PATH="${1:-mono.png}"

echo "Using video: $IMAGE_PATH"

if [ ! -f "$IMAGE_PATH" ]; then
  echo "Error: Video file not found: $IMAGE_PATH"
  exit 1
fi

gst-launch-1.0 -e \
  filesrc location=$IMAGE_PATH ! pngdec ! \
  imagefreeze num-buffers=10 ! \
  videoscale ! videoconvert ! \
  queue ! \
  hailonet hef-path=thermal_yolov8s.hef ! \
  hailofilter so-path=/usr/lib/hailo-post-processes/libyolo_hailortpp_post.so \
    function-name=filter config-path=thermal.json ! \
  queue ! \
  hailooverlay ! \
  videoconvert ! \
  pngenc ! filesink location=output.png sync=false


