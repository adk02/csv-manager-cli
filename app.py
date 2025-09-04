"""
CSV Manager CLI Application

A console application for managing CSV records with commands for viewing,
adding (with auto-incrementing ID), updating, deleting, backing up, and
importing/exporting data. Stores files under ~/Documents/CSVManager.
"""

import csv
import json
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
import fcntl  # for file locking on Unix
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
import questionary

# ─── CONSTANTS & PATH SETUP ──────────────────────────────────────────────────

HOME = Path.home()
BASE_DIR = HOME / "Documents" / "CSVManager"
CSV_FILE = BASE_DIR / "data.csv"
BACKUP_DIR = BASE_DIR / "backups"
FIELDNAMES = ["id", "nama kapal", "bendera", "agen", "gt",
              "muatan", "tujuan"]  # add more fields here as needed

console = Console()


def ensure_dirs() -> None:
    """Create the base and backup directories if they do not already exist."""
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


class CsvRepository:
    """Handles CSV file operations: initialize, read, write, append."""

    def __init__(self, path: Path, fieldnames: list[str]) -> None:
        """
        Initialize repository.

        Args:
            path: Path to the CSV file.
            fieldnames: List of CSV column names.
        """
        self.path = path
        self.fieldnames = fieldnames

    def _acquire_lock(self, fh) -> None:
        """
        Acquire an exclusive lock on an open file handle.

        Args:
            fh: File handle to lock.
        """
        try:
            fcntl.flock(fh, fcntl.LOCK_EX)
        except (IOError, OSError) as err:
            console.print(f"[red]Could not acquire file lock:[/] {err}")

    def _release_lock(self, fh) -> None:
        """
        Release a lock on an open file handle.

        Args:
            fh: File handle to unlock.
        """
        fcntl.flock(fh, fcntl.LOCK_UN)

    def initialize(self) -> None:
        """Create the CSV file with header row if it does not exist."""
        if not self.path.exists():
            try:
                with self.path.open("w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                    writer.writeheader()
                console.print(f"[green]Initialized CSV at:[/] {self.path}")
            except (IOError, csv.Error) as err:
                console.print(f"[red]Error initializing CSV:[/] {err}")

    def read_all(self) -> list[dict[str, str]]:
        """
        Read all records from the CSV.

        Returns:
            A list of record dicts, or empty list if file missing or header mismatch.
        """
        if not self.path.exists():
            return []
        try:
            with self.path.open("r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                if reader.fieldnames != self.fieldnames:
                    console.print("[red]CSV header mismatch[/]")
                    return []
                return list(reader)
        except (IOError, csv.Error) as err:
            console.print(f"[red]Error reading CSV:[/] {err}")
            return []

    def write_all(self, records: list[dict[str, str]]) -> None:
        """
        Atomically overwrite the CSV with a new set of records.

        Args:
            records: List of record dicts to write.
        """
        temp_fd, temp_path = tempfile.mkstemp(prefix="csvmgr_", suffix=".tmp")
        try:
            with open(temp_fd, "w", newline="", encoding="utf-8") as f:
                self._acquire_lock(f)
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                writer.writeheader()
                writer.writerows(records)
                self._release_lock(f)
            shutil.move(temp_path, str(self.path))
        except (IOError, OSError, csv.Error) as err:
            console.print(f"[red]Error writing CSV atomically:[/] {err}")
            if Path(temp_path).exists():
                Path(temp_path).unlink()

    def append(self, record: dict[str, str]) -> None:
        """
        Append a single record to the CSV.

        Args:
            record: Dict with keys matching fieldnames.
        """
        try:
            with self.path.open("a", newline="", encoding="utf-8") as f:
                self._acquire_lock(f)
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                writer.writerow(record)
                self._release_lock(f)
        except (IOError, csv.Error) as err:
            console.print(f"[red]Error appending record:[/] {err}")


def display_table(records: list[dict[str, str]]) -> None:
    """
    Render records in a rich-formatted table in the console.

    Args:
        records: List of record dicts to display.
    """
    table = Table(title=f"CSV Records ({CSV_FILE})", show_lines=True)
    for field in FIELDNAMES:
        table.add_column(field.capitalize(), justify="center")
    for r in records:
        table.add_row(*(r[field] for field in FIELDNAMES))
    console.print(table)


def get_new_record_fields() -> dict[str, str] | None:
    """
    Prompt the user for each non-ID field defined in FIELDNAMES.

    Returns:
        Dict of field values (excluding 'id'), or None if validation fails.
    """
    rec: dict[str, str] = {}
    for field in FIELDNAMES:
        if field == "id":
            continue
        answer = questionary.text(f"{field.capitalize()}:").ask()
        if not answer or not answer.strip():
            console.print(f"[red]Invalid input: {field} is required[/]")
            return None
        rec[field] = answer.strip()
    return rec


def add_record_flow(repo: CsvRepository) -> None:
    """
    Create and append a new record with automatic ascending ID.

    Args:
        repo: Instance of CsvRepository.
    """
    recs = repo.read_all()
    existing_ids = [int(r["id"]) for r in recs if r["id"].isdigit()]
    next_id = str((max(existing_ids, default=0) + 1))
    fields = get_new_record_fields()
    if not fields:
        return
    new_record = {"id": next_id, **fields}
    repo.append(new_record)
    console.print(f"[green]Added record {next_id}[/]")


def update_record(repo: CsvRepository) -> None:
    """
    Let the user pick any field (other than id) to update.

    Args:
        repo: Instance of CsvRepository.
    """
    recs = repo.read_all()
    display_table(recs)
    rid = Prompt.ask("Enter ID to update")
    record = next((r for r in recs if r["id"] == rid), None)
    if not record:
        console.print(f"[red]ID not found:[/] {rid}")
        return
    editable = [f for f in FIELDNAMES if f != "id"]
    field = questionary.select("Field to update:", editable).ask()
    new_value = Prompt.ask(f"New {field}")
    record[field] = new_value
    repo.write_all(recs)
    console.print(f"[green]Updated record {rid}[/]")


def delete_record(repo: CsvRepository) -> None:
    """
    Allow deletion of a record by ID, with confirmation prompt.

    Args:
        repo: Instance of CsvRepository.
    """
    recs = repo.read_all()
    display_table(recs)
    rid = Prompt.ask("Enter ID to delete")
    if Confirm.ask(f"Confirm delete {rid}?"):
        repo.write_all([r for r in recs if r["id"] != rid])
        console.print(f"[green]Deleted record {rid}[/]")


def backup_csv() -> None:
    """Create a timestamped backup of the main CSV."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"data_backup_{ts}.csv"
    try:
        shutil.copy(CSV_FILE, dest)
        console.print(f"[green]Backup created:[/] {dest}")
    except (IOError, OSError) as err:
        console.print(f"[red]Backup failed:[/] {err}")


def export_to_json(repo: CsvRepository) -> None:
    """
    Export all CSV records to a JSON file.

    Args:
        repo: Instance of CsvRepository.
    """
    recs = repo.read_all()
    default = BASE_DIR / "data.json"
    fname = Path(Prompt.ask("JSON filename", default=str(default)))
    try:
        with fname.open("w", encoding="utf-8") as f:
            json.dump(recs, f, indent=2, ensure_ascii=False)
        console.print(f"[green]Exported[/] {len(recs)} records to {fname}")
    except (IOError, OSError) as err:
        console.print(f"[red]Export failed:[/] {err}")


def import_from_json(repo: CsvRepository) -> None:
    """
    Import records from a JSON file into the CSV, skipping duplicates.

    Args:
        repo: Instance of CsvRepository.
    """
    default = BASE_DIR / "data.json"
    fname = Path(Prompt.ask("JSON filename", default=str(default)))
    if not fname.exists():
        console.print(f"[red]File not found:[/] {fname}")
        return
    try:
        recs = json.loads(fname.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        console.print(f"[red]Invalid JSON:[/] {err}")
        return
    orig = repo.read_all()
    count, skipped = 0, []
    for r in recs:
        if r.get("id") and not any(x["id"] == r["id"] for x in orig):
            repo.append(r)
            count += 1
        else:
            skipped.append(r.get("id", "(no id)"))
    console.print(f"[green]Imported[/] {count} new records")
    if skipped:
        console.print(
            f"[yellow]Skipped duplicates or invalid IDs:[/] {', '.join(skipped)}")


def erase_all_data(repo: CsvRepository) -> None:
    """
    Erase all data rows in the CSV, preserving only the header.

    Args:
        repo: Instance of CsvRepository.
    """
    if Confirm.ask(f"Erase all data? This will remove {len(repo.read_all())} records."):
        repo.write_all([])
        console.print("[yellow]All data erased[/]")


def main() -> None:
    """Main entry point: ensure directories, initialize repository, and handle menu."""
    ensure_dirs()
    repo = CsvRepository(CSV_FILE, FIELDNAMES)
    repo.initialize()

    while True:
        action = questionary.select(
            "Choose action:",
            choices=[
                "View Records",
                "Add Record",
                "Update Record",
                "Delete Record",
                "Backup CSV",
                "Export JSON",
                "Import JSON",
                "Erase All",
                "Quit",
            ],
        ).ask()

        if action == "View Records":
            display_table(repo.read_all())
        elif action == "Add Record":
            add_record_flow(repo)
        elif action == "Update Record":
            update_record(repo)
        elif action == "Delete Record":
            delete_record(repo)
        elif action == "Backup CSV":
            backup_csv()
        elif action == "Export JSON":
            export_to_json(repo)
        elif action == "Import JSON":
            import_from_json(repo)
        elif action == "Erase All":
            erase_all_data(repo)
        else:  # Quit
            break


if __name__ == "__main__":
    main()
