**NovaCrack** is a Python-based desktop application designed for password recovery of encrypted files using dictionary-based password testing.

It provides a graphical interface, real-time performance monitoring, and multiprocessing support for selected archive formats.

## Features

- **Multiple File Formats:** Supports ZIP, RAR, 7Z, PDF, and Microsoft Office documents.
- **Dictionary-Based Recovery:** Uses user-provided password lists.
- **Multiprocessing:** Parallel password testing for RAR and 7Z archives.
- **Performance Monitoring:** Displays CPU usage, tested passwords, and testing speed.
- **Graphical Interface:** Built with CustomTkinter.
- **Live Logging:** Displays operation status and results.
- **Process Control:** Allows users to stop ongoing operations.

## Supported Formats

| Format                   | Support |
| ------------------------ | ------- |
| ZIP                      | ✅       |
| RAR                      | ✅       |
| 7Z                       | ✅       |
| PDF                      | ✅       |
| Word (.doc, .docx)       | ✅       |
| Excel (.xls, .xlsx)      | ✅       |
| PowerPoint (.ppt, .pptx) | ✅       |

## Technologies

- Python
- Tkinter
- CustomTkinter
- PyZipper
- PyPDF
- msoffcrypto-tool
- psutil
- Pillow
- Multiprocessing

## Requirements

- Python 3.10+
- Windows
- WinRAR (for RAR support)
- 7-Zip (for 7Z support)

Some file formats require additional Python packages.

## Installation

Clone the repository:

```bash
git clone https://github.com/kayaslxs/NovaCrack.git
```

Navigate to the project directory:

```bash
cd NovaCrack
```

Install the dependencies:

```bash
pip install customtkinter psutil pyzipper pillow pypdf msoffcrypto-tool
```

Run the application:

```bash
python main.py
```

## Usage

1. Launch NovaCrack.
2. Select an encrypted file.
3. Select a TXT password dictionary.
4. Start the recovery process.
5. Monitor the progress through the statistics panel.
6. Stop the operation whenever necessary.

## Disclaimer

NovaCrack is intended for educational purposes and authorized password recovery of files owned by the user or for which the user has explicit permission.

The developer is not responsible for unauthorized use or misuse of this software.

## License

This project is licensed under the MIT License.

See the [LICENSE](LICENSE) file for details.

---

**Developed by KAYASLXS**
