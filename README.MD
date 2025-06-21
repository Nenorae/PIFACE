# PIFACE

A face recognition system built with Python that consists of a client-server architecture for real-time face detection and recognition.

## 🚀 Features

- Real-time face detection and recognition
- Client-server architecture for distributed processing
- Python-based implementation
- Modular design with separate components

## 📋 Prerequisites

- Python 3.11.x (recommended for optimal performance)
- Git
- pip (Python package manager)
- Webcam or camera device (for face detection)

## 🛠️ Installation

### 1. Clone the Repository

```bash
git clone https://github.com/Nenorae/PIFACE.git
cd PIFACE
```

### 2. Setup PiFace Client

Navigate to the PiFace directory and create a virtual environment:

```bash
cd PiFace
python3.11 -m venv raspi
```

Activate the virtual environment:

**Linux/MacOS:**
```bash
source raspi/bin/activate
```

**Windows:**
```bash
raspi\Scripts\activate
```

Install dependencies:
```bash
pip install -r requirements.txt
```

### 3. Setup PiFace Server

Open a new terminal and navigate to the server directory:

```bash
cd PIFACE/server-piface
python3.11 -m venv server
```

Activate the virtual environment:

**Linux/MacOS:**
```bash
source server/bin/activate
```

**Windows:**
```bash
server\Scripts\activate
```

Install dependencies:
```bash
pip install -r requirements.txt
```

## 🚀 Usage

### Starting the Server

In the first terminal (server-piface directory):

```bash
cd server-piface
source server/bin/activate  # Linux/MacOS
# or
server\Scripts\activate     # Windows

python main.py
```

### Starting the Client

In the second terminal (PiFace directory):

```bash
cd PiFace
source raspi/bin/activate   # Linux/MacOS
# or
raspi\Scripts\activate      # Windows

python main.py
```

## 📁 Project Structure

```
PIFACE/
├── PiFace/                 # Client application
│   ├── raspi/             # Virtual environment
│   ├── requirements.txt   # Client dependencies
│   ├── main.py           # Client entry point
│   └── ...
├── server-piface/         # Server application
│   ├── server/           # Virtual environment
│   ├── requirements.txt  # Server dependencies
│   ├── main.py          # Server entry point
│   └── ...
└── README.md
```

## 🔧 Configuration

- Ensure both server and client are running simultaneously
- Configure network settings if running on different machines
- Adjust camera settings in the client configuration

## 🐛 Troubleshooting

### Common Issues

**Python Version Issues:**
```bash
python --version  # Should show Python 3.11.x
```

**Virtual Environment Issues:**
- Make sure to activate the correct virtual environment for each component
- Each folder requires its own separate virtual environment

**Dependency Installation Issues:**
- On Windows, you may need Visual Studio Build Tools for some packages
- Ensure stable internet connection during installation

**Camera Issues:**
- Verify camera permissions and availability
- Check if other applications are using the camera

### Deactivating Virtual Environment

When done working with the project:
```bash
deactivate
```

## 📚 Dependencies

Dependencies are listed in the `requirements.txt` files in each directory:
- `PiFace/requirements.txt` - Client dependencies
- `server-piface/requirements.txt` - Server dependencies

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👥 Authors

- **Nenorae** - Initial work - [Nenorae](https://github.com/Nenorae)

## 🙏 Acknowledgments

- Thanks to all contributors who helped build this project
- Special thanks to the open-source community for the tools and libraries used

## 📞 Support

If you encounter any issues or have questions, please:
1. Check the troubleshooting section above
2. Search existing issues on GitHub
3. Create a new issue with detailed information about your problem

---

**Note:** This project requires both server and client components to be running for full functionality. Make sure to follow the installation steps carefully and maintain separate virtual environments for each component.
