from ultralytics import YOLO
import traceback

try:
    print("Loading model...")
    model = YOLO('model/best.pt')
    print("Success")
except Exception as e:
    print("Error:")
    traceback.print_exc()
