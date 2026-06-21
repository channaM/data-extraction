"""
ETL Manager — PyQt6 desktop UI.

Tabs:
  1. Import  — upload an Excel file, run the ETL pipeline, view run history
  2. Records — browse, filter, edit, and save records back to PostgreSQL
"""
import sys
from decimal import Decimal

import psycopg2
import psycopg2.extras
from PyQt6.QtCore import (
    QAbstractTableModel, QModelIndex, Qt, QThread, pyqtSignal,
)
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFileDialog, QFormLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPlainTextEdit, QPushButton,
    QSpinBox, QTabWidget, QTableView, QVBoxLayout, QWidget,
)

from etl.config import Config
from etl.pipeline import run as run_pipeline

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def _connect():
    return psycopg2.connect(Config.pg_dsn())


def db_fetch_runs() -> list[dict]:
    sql = """
        SELECT id, file_name, template_type, sheet_name, status,
               rows_read, rows_loaded, started_at, finished_at, error_msg
        FROM etl_runs ORDER BY id DESC LIMIT 200
    """
    with _connect() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql)
        return [dict(r) for r in cur.fetchall()]


def db_fetch_records(search: str = "", category: str = "") -> list[dict]:
    conditions, params = [], []
    if search:
        conditions.append("(name ILIKE %s OR description ILIKE %s)")
        params += [f"%{search}%", f"%{search}%"]
    if category:
        conditions.append("category = %s")
        params.append(category)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = f"""
        SELECT id, external_id, name, category, price, quantity,
               description, record_date, extra, updated_at
        FROM records {where}
        ORDER BY id DESC LIMIT 2000
    """
    with _connect() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]


def db_fetch_categories() -> list[str]:
    sql = "SELECT DISTINCT category FROM records WHERE category IS NOT NULL ORDER BY category"
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(sql)
        return [r[0] for r in cur.fetchall()]


def db_update_record(record_id: int, fields: dict) -> None:
    sql = """
        UPDATE records
        SET name        = %(name)s,
            category    = %(category)s,
            price       = %(price)s,
            quantity    = %(quantity)s,
            description = %(description)s,
            record_date = %(record_date)s
        WHERE id = %(id)s
    """
    fields["id"] = record_id
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(sql, fields)
    conn.commit()


# ---------------------------------------------------------------------------
# QAbstractTableModel for records
# ---------------------------------------------------------------------------

RECORD_HEADERS = ["ID", "Ext ID", "Name", "Category", "Price", "Qty", "Description", "Date", "Updated"]
RECORD_KEYS    = ["id", "external_id", "name", "category", "price", "quantity", "description", "record_date", "updated_at"]

RUN_HEADERS = ["ID", "File", "Type", "Sheet", "Status", "Read", "Loaded", "Started"]
RUN_KEYS    = ["id", "file_name", "template_type", "sheet_name", "status", "rows_read", "rows_loaded", "started_at"]

STATUS_COLORS = {
    "success": QColor("#2ecc71"),
    "failed":  QColor("#e74c3c"),
    "running": QColor("#f39c12"),
}


class SimpleTableModel(QAbstractTableModel):
    def __init__(self, rows: list[dict], headers: list[str], keys: list[str]):
        super().__init__()
        self._rows = rows
        self._headers = headers
        self._keys = keys

    def rowCount(self, _=QModelIndex()) -> int:
        return len(self._rows)

    def columnCount(self, _=QModelIndex()) -> int:
        return len(self._headers)

    def headerData(self, section: int, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self._headers[section]

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        key = self._keys[index.column()]
        value = row.get(key)

        if role == Qt.ItemDataRole.DisplayRole:
            if value is None:
                return ""
            if isinstance(value, Decimal):
                return f"{value:.2f}"
            text = str(value)
            if key == "description" and len(text) > 70:
                return text[:67] + "…"
            if key in ("started_at", "finished_at", "updated_at"):
                return text[:19]
            return text

        if role == Qt.ItemDataRole.ForegroundRole and key == "status":
            return STATUS_COLORS.get(str(value))

        if role == Qt.ItemDataRole.ToolTipRole:
            error = row.get("error_msg")
            if error:
                return f"Error: {error}"
            if key == "template_type":
                return f"Template type: {row.get('template_type', 'unknown')}"

        if role == Qt.ItemDataRole.UserRole:
            return row

        return None

    def reload(self, rows: list[dict]):
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def row_data(self, row_idx: int) -> dict:
        return self._rows[row_idx]


# ---------------------------------------------------------------------------
# ETL Worker Thread
# ---------------------------------------------------------------------------

class ETLWorker(QThread):
    log_line  = pyqtSignal(str)
    finished  = pyqtSignal(dict)

    def __init__(self, file_path: str, sheet: str):
        super().__init__()
        self._file_path = file_path
        self._sheet = sheet

    def run(self):
        import logging

        class SignalHandler(logging.Handler):
            def __init__(self, signal):
                super().__init__()
                self._signal = signal

            def emit(self, record):
                self._signal.emit(self.format(record))

        handler = SignalHandler(self.log_line)
        handler.setFormatter(logging.Formatter("%(levelname)-8s %(message)s"))
        root = logging.getLogger()
        root.addHandler(handler)
        try:
            summary = run_pipeline(self._file_path, sheet_name=self._sheet)
            self.finished.emit(summary)
        except Exception as exc:
            self.finished.emit({"status": "failed", "error": str(exc),
                                "rows_read": 0, "rows_loaded": 0})
        finally:
            root.removeHandler(handler)


# ---------------------------------------------------------------------------
# Edit Dialog
# ---------------------------------------------------------------------------

class EditRecordDialog(QDialog):
    def __init__(self, parent: QWidget, record: dict):
        super().__init__(parent)
        self.setWindowTitle(f"Edit Record — ID {record['id']}")
        self.setMinimumWidth(480)
        self.result_data: dict | None = None
        self._build(record)

    def _build(self, rec: dict):
        layout = QVBoxLayout(self)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(10)

        self._name = QLineEdit(rec.get("name") or "")
        self._category = QLineEdit(rec.get("category") or "")

        self._price = QDoubleSpinBox()
        self._price.setRange(0, 9_999_999)
        self._price.setDecimals(2)
        self._price.setSpecialValueText("—")
        if rec.get("price") is not None:
            self._price.setValue(float(rec["price"]))

        self._qty = QSpinBox()
        self._qty.setRange(0, 9_999_999)
        self._qty.setSpecialValueText("—")
        if rec.get("quantity") is not None:
            self._qty.setValue(int(rec["quantity"]))

        self._description = QPlainTextEdit(rec.get("description") or "")
        self._description.setFixedHeight(80)

        self._date = QLineEdit(str(rec.get("record_date") or ""))
        self._date.setPlaceholderText("YYYY-MM-DD")

        form.addRow("Name *", self._name)
        form.addRow("Category", self._category)
        form.addRow("Price", self._price)
        form.addRow("Quantity", self._qty)
        form.addRow("Description", self._description)
        form.addRow("Record Date", self._date)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save(self):
        name = self._name.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation", "Name is required.")
            return

        price_val = self._price.value() if self._price.value() > 0 else None
        qty_val   = self._qty.value() if self._qty.value() > 0 else None
        date_val  = self._date.text().strip() or None

        self.result_data = {
            "name":        name,
            "category":    self._category.text().strip() or None,
            "price":       price_val,
            "quantity":    qty_val,
            "description": self._description.toPlainText().strip() or None,
            "record_date": date_val,
        }
        self.accept()


# ---------------------------------------------------------------------------
# Import Tab
# ---------------------------------------------------------------------------

class ImportTab(QWidget):
    def __init__(self):
        super().__init__()
        self._worker: ETLWorker | None = None
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setSpacing(10)

        # --- File picker ---
        file_group = QWidget()
        file_layout = QHBoxLayout(file_group)
        file_layout.setContentsMargins(0, 0, 0, 0)

        self._file_edit = QLineEdit()
        self._file_edit.setPlaceholderText("Path to Excel file…")
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse)

        sheet_label = QLabel("Sheet:")
        self._sheet_edit = QLineEdit("Data")
        self._sheet_edit.setFixedWidth(100)

        self._run_btn = QPushButton("Run ETL")
        self._run_btn.setFixedWidth(90)
        self._run_btn.clicked.connect(self._run_etl)

        file_layout.addWidget(self._file_edit)
        file_layout.addWidget(browse_btn)
        file_layout.addSpacing(16)
        file_layout.addWidget(sheet_label)
        file_layout.addWidget(self._sheet_edit)
        file_layout.addSpacing(8)
        file_layout.addWidget(self._run_btn)
        root.addWidget(file_group)

        # --- Log ---
        root.addWidget(QLabel("Pipeline Log"))
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumBlockCount(1000)
        self._log.setFont(QFont("Courier", 11))
        self._log.setStyleSheet(
            "background:#1e1e1e; color:#d4d4d4; border:1px solid #444;"
        )
        self._log.setFixedHeight(180)
        root.addWidget(self._log)

        # --- Run history ---
        hist_header = QHBoxLayout()
        hist_header.addWidget(QLabel("Run History"))
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setFixedWidth(80)
        refresh_btn.clicked.connect(self._refresh_history)
        hist_header.addStretch()
        hist_header.addWidget(refresh_btn)
        root.addLayout(hist_header)

        self._run_model = SimpleTableModel([], RUN_HEADERS, RUN_KEYS)
        self._run_table = QTableView()
        self._run_table.setModel(self._run_model)
        self._run_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self._run_table.horizontalHeader().setStretchLastSection(True)
        self._run_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self._run_table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self._run_table.verticalHeader().setVisible(False)
        root.addWidget(self._run_table)

        self._refresh_history()

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Template File", "",
            "All Templates (*.xlsx *.xls *.csv *.pdf);;"
            "Excel Files (*.xlsx *.xls);;"
            "CSV Files (*.csv);;"
            "PDF Files (*.pdf);;"
            "All Files (*)"
        )
        if path:
            self._file_edit.setText(path)
            # Grey out sheet field for formats that don't use sheets
            from pathlib import Path as _Path
            ext = _Path(path).suffix.lower()
            sheet_relevant = ext in (".xlsx", ".xls")
            self._sheet_edit.setEnabled(sheet_relevant)
            self._sheet_edit.setToolTip(
                "Sheet name (Excel only)" if sheet_relevant
                else "Sheet name is not applicable for this file type"
            )

    def _run_etl(self):
        path = self._file_edit.text().strip()
        sheet = self._sheet_edit.text().strip() or "Data"
        if not path:
            QMessageBox.warning(self, "Missing File", "Please select a template file first.")
            return

        self._run_btn.setEnabled(False)
        self._log.appendPlainText(f"▶ Starting ETL: {path}  (sheet={sheet})\n")

        self._worker = ETLWorker(path, sheet)
        self._worker.log_line.connect(self._log.appendPlainText)
        self._worker.finished.connect(self._etl_done)
        self._worker.start()

    def _etl_done(self, summary: dict):
        self._run_btn.setEnabled(True)
        ttype = summary.get("template_type", "unknown").upper()
        if summary.get("status") == "success":
            self._log.appendPlainText(
                f"\n✓ Done [{ttype}] — run_id={summary.get('run_id')}  "
                f"rows_read={summary.get('rows_read')}  "
                f"rows_loaded={summary.get('rows_loaded')}\n"
            )
        else:
            stage = summary.get("failed_stage") or "unknown"
            self._log.appendPlainText(
                f"\n✗ Failed [{ttype}] at stage={stage}: {summary.get('error')}\n"
            )
        self._refresh_history()

    def _refresh_history(self):
        try:
            runs = db_fetch_runs()
            self._run_model.reload(runs)
            self._run_table.resizeColumnsToContents()
        except Exception as exc:
            self._log.appendPlainText(f"[DB error] {exc}")


# ---------------------------------------------------------------------------
# Records Tab
# ---------------------------------------------------------------------------

class RecordsTab(QWidget):
    def __init__(self):
        super().__init__()
        self._records: list[dict] = []
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setSpacing(8)

        # --- Filter bar ---
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Search:"))
        self._search = QLineEdit()
        self._search.setPlaceholderText("name or description…")
        self._search.setFixedWidth(220)
        self._search.returnPressed.connect(self._load)
        filter_row.addWidget(self._search)

        filter_row.addSpacing(12)
        filter_row.addWidget(QLabel("Category:"))
        self._cat_combo = QComboBox()
        self._cat_combo.setFixedWidth(140)
        self._cat_combo.currentIndexChanged.connect(lambda _: self._load())
        filter_row.addWidget(self._cat_combo)

        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self._load)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear)
        filter_row.addWidget(search_btn)
        filter_row.addWidget(clear_btn)
        filter_row.addStretch()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._load)
        filter_row.addWidget(refresh_btn)

        edit_btn = QPushButton("Edit Selected")
        edit_btn.clicked.connect(self._edit_selected)
        filter_row.addWidget(edit_btn)
        root.addLayout(filter_row)

        # --- Table ---
        self._model = SimpleTableModel([], RECORD_HEADERS, RECORD_KEYS)
        self._table = QTableView()
        self._table.setModel(self._model)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.setSortingEnabled(False)
        self._table.doubleClicked.connect(self._on_double_click)
        root.addWidget(self._table)

        # --- Status ---
        self._status = QLabel("")
        self._status.setStyleSheet("color: #666;")
        root.addWidget(self._status)

        self._load()

    def _clear(self):
        self._search.clear()
        self._cat_combo.setCurrentIndex(0)
        self._load()

    def _load(self):
        try:
            cats = db_fetch_categories()
            current_cat = self._cat_combo.currentText()
            self._cat_combo.blockSignals(True)
            self._cat_combo.clear()
            self._cat_combo.addItem("")
            self._cat_combo.addItems(cats)
            idx = self._cat_combo.findText(current_cat)
            self._cat_combo.setCurrentIndex(max(idx, 0))
            self._cat_combo.blockSignals(False)

            self._records = db_fetch_records(
                search=self._search.text().strip(),
                category=self._cat_combo.currentText(),
            )
            self._model.reload(self._records)
            self._table.resizeColumnsToContents()
            self._status.setText(
                f"{len(self._records)} record(s)  —  double-click a row to edit"
            )
        except Exception as exc:
            QMessageBox.critical(self, "Database Error", str(exc))

    def _on_double_click(self, index: QModelIndex):
        self._open_edit(index.row())

    def _edit_selected(self):
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.information(self, "No Selection", "Select a row first.")
            return
        self._open_edit(rows[0].row())

    def _open_edit(self, row_idx: int):
        rec = self._model.row_data(row_idx)
        dlg = EditRecordDialog(self, rec)
        if dlg.exec() != QDialog.DialogCode.Accepted or dlg.result_data is None:
            return
        try:
            db_update_record(rec["id"], dlg.result_data)
            QMessageBox.information(self, "Saved", f"Record {rec['id']} updated successfully.")
            self._load()
        except Exception as exc:
            QMessageBox.critical(self, "Save Error", str(exc))


# ---------------------------------------------------------------------------
# Main Window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ETL Manager")
        self.resize(1100, 720)
        self.setMinimumSize(800, 560)
        self._build()

    def _build(self):
        tabs = QTabWidget()
        self._import_tab  = ImportTab()
        self._records_tab = RecordsTab()
        tabs.addTab(self._import_tab,  "  Import  ")
        tabs.addTab(self._records_tab, "  Records  ")
        tabs.currentChanged.connect(self._tab_changed)
        self.setCentralWidget(tabs)
        self._tabs = tabs

    def _tab_changed(self, idx: int):
        if idx == 1:
            self._records_tab._load()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
