import os
from data_manager import add_new_person, delete_person, list_datasets
from encoder import regenerate_encodings
from recognition import run_continuous_recognition

def display_menu():
    """Displays the main menu."""
    print("\n===== FACE RECOGNITION SYSTEM MENU =====")
    print("1. Run Face Recognition")
    print("2. Add New Face Data")
    print("3. Delete Face Data")
    print("4. View Dataset List")
    print("5. Exit")
    print("========================================")
    return input("Select an option (1-5): ")

def main():
    """Main function to run the application."""
    # Ensure the dataset directory exists
    if not os.path.exists("dataset"):
        os.makedirs("dataset")

    while True:
        choice = display_menu()

        if choice == '1':
            run_continuous_recognition()
        
        elif choice == '2':
            # If a person is added successfully, regenerate encodings automatically
            if add_new_person():
                regenerate_encodings()

        elif choice == '3':
            # If a person is deleted successfully, regenerate encodings automatically
            if delete_person():
                regenerate_encodings()

        elif choice == '4':
            list_datasets()

        elif choice == '5':
            print("Thank you for using the system. Goodbye!")
            break
        
        else:
            print("Invalid option, please try again.")

if __name__ == "__main__":
    main()
