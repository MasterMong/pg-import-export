# PostgreSQL Import/Export Tool

A user-friendly simple GUI application for importing and exporting PostgreSQL databases.

## Features

- Connection profile management (save, load, delete)
- Secure password storage using system keyring
- Database selection dialog
- Multiple export options:
  - Full backup
  - Schema only
  - Data only
- Import SQL files into databases
- Test connection functionality
- Real-time status updates
- Progress indication

## Requirements

- Python 3.6+
- PostgreSQL client tools (`psql`, `pg_dump`)
- Required Python packages:
  - tkinter
  - keyring

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/pg-import-export.git
cd pg-import-export
```

2. Install required Python packages:
```bash
pip install keyring
```

3. Ensure PostgreSQL client tools are installed:
   - For Ubuntu/Debian: `sudo apt-get install postgresql-client`
   - For macOS with Homebrew: `brew install postgresql`
   - For Windows: Install from the PostgreSQL installer

## Usage

1. Run the application:
```bash
python main.py
```

2. Create a new connection profile:
   - Click "New Profile"
   - Enter connection details
   - Optionally save password
   - Click "Save Profile"

3. Export a database:
   - Select export type (Full/Schema/Data)
   - Click "Export Database"
   - Choose save location
   - Wait for completion

4. Import a database:
   - Click "Import Database"
   - Select SQL file
   - Confirm import
   - Wait for completion

## Security Notes

- Passwords are stored securely using the system's keyring
- Connection profiles are saved in `db_profiles.json`
- Saved passwords are not stored in plain text

## License

MIT License - See LICENSE file for details
