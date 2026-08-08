import gphoto2 as gp
import time

# Try to connect
while True:
    try:
        camera = gp.Camera()
        camera.init()
    except gp.GPhoto2Error as e:
        print(f"Error initializing camera: {e}. Retrying in 1 second...")
        time.sleep(1)
        continue

    print("Camera initialized successfully.")