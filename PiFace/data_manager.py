import cv2
import os
import shutil
import face_utils

DATASET_DIR = "dataset"
SAMPLES_PER_PERSON = 20

def add_new_person():
    """Captures face samples for a new person."""
    person_name = input("Enter person's name (no spaces): ").strip().title()
    if not person_name:
        print("Name cannot be empty.")
        return False

    person_path = os.path.join(DATASET_DIR, person_name)

    if os.path.exists(person_path):
        print(f"Error: Name '{person_name}' already exists in the dataset.")
        return False

    os.makedirs(person_path)
    print(f"Directory '{person_path}' created.")

    cap = cv2.VideoCapture(0)
    count = 0

    while count < SAMPLES_PER_PERSON:
        ret, frame = cap.read()
        if not ret:
            print("Failed to read frame from camera.")
            break

        frame_copy = frame.copy()
        detections = face_utils.detect_faces(frame_copy)

        # Visual feedback on screen
        status_text = f"Image {count}/{SAMPLES_PER_PERSON}"
        cv2.putText(frame, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        if detections:
            box = face_utils.get_bounding_box(frame_copy, detections[0])
            if box:
                x, y, w, h = box['xmin'], box['ymin'], box['width'], box['height']
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.imshow(f"Add Face: {person_name} - Press 's' to save", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('s') and detections:
            img_path = os.path.join(person_path, f"{count}.jpg")
            cv2.imwrite(img_path, frame_copy)
            print(f"Image {count+1} saved.")
            count += 1
        elif key == ord('q'):
            print("Process canceled.")
            shutil.rmtree(person_path) # Clean up directory if process is not completed
            cap.release()
            cv2.destroyAllWindows()
            return False

    print(f"\nDone! {count} face samples for '{person_name}' have been saved.")
    cap.release()
    cv2.destroyAllWindows()
    return True

def delete_person():
    """Deletes a person's face data from the dataset."""
    if not os.path.exists(DATASET_DIR) or not os.listdir(DATASET_DIR):
        print("Dataset is empty. No data to delete.")
        return False

    print("Select a name to delete:")
    people = [name for name in os.listdir(DATASET_DIR) if os.path.isdir(os.path.join(DATASET_DIR, name))]
    
    for i, name in enumerate(people):
        print(f"{i + 1}: {name}")
    
    try:
        choice = int(input(f"Enter number (1-{len(people)}): "))
        if 1 <= choice <= len(people):
            person_to_delete = people[choice - 1]
            confirm = input(f"Are you sure you want to delete all data for '{person_to_delete}'? (y/n): ").lower()
            if confirm == 'y':
                shutil.rmtree(os.path.join(DATASET_DIR, person_to_delete))
                print(f"Data for '{person_to_delete}' has been deleted.")
                return True
            else:
                print("Deletion canceled.")
                return False
        else:
            print("Invalid choice.")
            return False
    except ValueError:
        print("Invalid input. Please enter a number.")
        return False
    

def list_datasets():
    """Lists all people in the dataset."""
    print("\nChecking dataset...")
    if not os.path.exists(DATASET_DIR) or not os.listdir(DATASET_DIR):
        print("-> Dataset is empty. Please add new data.")
        return

    # Get only directories, sorted alphabetically
    people = sorted([name for name in os.listdir(DATASET_DIR) if os.path.isdir(os.path.join(DATASET_DIR, name))])
    
    if not people:
        print("-> Dataset does not contain valid person folders.")
        return

    print("\n===== People in Dataset =====")
    for i, name in enumerate(people):
        # Count image files in the folder for additional information
        person_path = os.path.join(DATASET_DIR, name)
        try:
            num_images = len([f for f in os.listdir(person_path) if f.endswith(('.jpg', '.png', '.jpeg'))])
            print(f"{i + 1}. {name} ({num_images} images)")
        except OSError:
            print(f"{i + 1}. {name} (Error reading folder)")

    print("============================")