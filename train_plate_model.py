from ultralytics import YOLO

def main():
    print("Starting YOLOv8 training for license plate detection...")
    
    # Load the base nano model
    model = YOLO("yolov8n.pt") 
    
    # Train the model based on the extracted dataset configuration
    results = model.train(
        data="dataset/data.yaml",
        epochs=5,
        imgsz=416,
        project="runs/detect", # Default save location
        name="train"           # Default experiment name
    )

    print("Training complete! The best weights should be located at runs/detect/train/weights/best.pt")

if __name__ == "__main__":
    main()
