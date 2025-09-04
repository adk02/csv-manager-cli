# CSV Manager CLI

A lightweight Python console tool for full CRUD management of CSV data—view, add (auto-increment IDs), update, delete, backup, and import/export to JSON. Powered by Rich for tables and Questionary for prompts.

## Features

- View records in a formatted table
- Add records with auto-incrementing `id`
- Update existing records by `id`
- Delete records with confirmation
- Backup CSV to timestamped files
- Export to and import from JSON files
- Erase all data while preserving headers

## Prerequisites

- Python 3.7+
- Install dependencies:

```bash
pip install rich questionary
```

Alternatively, install from `requirements.txt`:

```bash
pip install -r requirements.txt
```

## Project Structure

```
csv-manager-cli/
├── .gitignore
├── README.md
├── requirements.txt
└── src/
    └── csv_manager.py  # Main application code
```

## Usage

1. Clone the repository:

   ```bash
git clone https://github.com/your-username/csv-manager-cli.git
cd csv-manager-cli
```  

2. Run the application:

   ```bash
python -m src.csv_manager
```

3. Choose from the menu:
   - **View Records**: Display all entries
   - **Add Record**: Add a new entry (auto-increment `id`)
   - **Update Record**: Modify an existing entry by `id`
   - **Delete Record**: Remove an entry by `id`
   - **Backup CSV**: Create a timestamped backup
   - **Export JSON**: Export all records to a JSON file
   - **Import JSON**: Import records from a JSON file (skip duplicates)
   - **Erase All**: Delete all records (keep header)
   - **Quit**: Exit the application

## Configuration

Default data directory:

```bash
~/Documents/CSVManager/data.csv
```  
Backup directory:

```bash
~/Documents/CSVManager/backups/
```

To customize paths or fields, edit the constants at the top of `csv_manager.py`.
