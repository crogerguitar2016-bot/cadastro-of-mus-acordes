import csv
import io
import json
import re
import zipfile
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape


CORE_COLUMNS = ["Nome", "Contato", "Combo", "Status", "Observações"]


def _text(value):
    if value is None:
        return ""
    return str(value)


def _norm(value):
    return _text(value).strip().casefold()


def safe_filename(name):
    name = re.sub(r"[^\w\-. ]+", "", _text(name), flags=re.UNICODE).strip()
    name = re.sub(r"\s+", "_", name)
    return name or "arquivo"


class DataStore:
    """Persistência e regras do Cadastro Of. Mus. Acordes."""

    def __init__(self, base_dir):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.cadastros_path = self.base_dir / "cadastros.json"
        self.campos_path = self.base_dir / "campos.json"
        self.exports_dir = self.base_dir / "exports"
        self.backups_dir = self.base_dir / "backups"
        self.imports_dir = self.base_dir / "imports"
        for folder in (self.exports_dir, self.backups_dir, self.imports_dir):
            folder.mkdir(parents=True, exist_ok=True)

    # ---------- JSON seguro ----------
    @staticmethod
    def _read_list(path):
        path = Path(path)
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    @staticmethod
    def _atomic_write_json(path, data):
        path = Path(path)
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp.replace(path)

    def load_records(self):
        records = self._read_list(self.cadastros_path)
        changed = False
        for item in records:
            if not isinstance(item.get("campos"), dict):
                item["campos"] = {}
                changed = True
            item.setdefault("status", "Ativo")
            item.setdefault("foto_uri", "")
        if changed:
            self.save_records(records)
        return records

    def save_records(self, records):
        self._atomic_write_json(self.cadastros_path, records)

    def load_fields(self):
        fields = self._read_list(self.campos_path)
        for field in fields:
            field.setdefault("status", "Ativo")
            field.setdefault("tipo", "Texto")
        return fields

    def save_fields(self, fields):
        self._atomic_write_json(self.campos_path, fields)

    @staticmethod
    def _next_id(items):
        ids = []
        for item in items:
            try:
                ids.append(int(item.get("id", 0)))
            except Exception:
                pass
        return max(ids, default=0) + 1

    # ---------- Cadastros ----------
    def list_records(self, sort="az"):
        records = self.load_records()
        reverse = sort == "za"
        return sorted(records, key=lambda x: _norm(x.get("nome")), reverse=reverse)

    def get_record(self, record_id):
        for record in self.load_records():
            if str(record.get("id")) == str(record_id):
                return record
        return None

    def add_record(self, nome, contato="", grupo="", observacoes="", status="Ativo", foto_uri=""):
        nome = _text(nome).strip()
        grupo = _text(grupo).strip()
        if not nome:
            raise ValueError("O nome é obrigatório.")
        if not grupo:
            raise ValueError("O combo/instrumento é obrigatório.")
        records = self.load_records()
        record = {
            "id": self._next_id(records),
            "nome": nome,
            "contato": _text(contato).strip(),
            "grupo": grupo,
            "observacoes": _text(observacoes).strip(),
            "status": status if status in ("Ativo", "Inativo") else "Ativo",
            "campos": {},
            "foto_uri": _text(foto_uri).strip(),
        }
        records.append(record)
        self.save_records(records)
        return record

    def update_record(self, record_id, **changes):
        allowed = {"nome", "contato", "grupo", "observacoes", "status", "foto_uri"}
        records = self.load_records()
        found = None
        for record in records:
            if str(record.get("id")) == str(record_id):
                for key, value in changes.items():
                    if key in allowed:
                        record[key] = _text(value).strip() if key != "status" else value
                if not _text(record.get("nome")).strip():
                    raise ValueError("O nome é obrigatório.")
                if not _text(record.get("grupo")).strip():
                    raise ValueError("O combo/instrumento é obrigatório.")
                found = record
                break
        if found is None:
            raise KeyError("Cadastro não encontrado.")
        self.save_records(records)
        return found

    def delete_record(self, record_id):
        records = self.load_records()
        new_records = [r for r in records if str(r.get("id")) != str(record_id)]
        if len(new_records) == len(records):
            return False
        self.save_records(new_records)
        return True

    def toggle_record_status(self, record_id):
        record = self.get_record(record_id)
        if not record:
            raise KeyError("Cadastro não encontrado.")
        new_status = "Inativo" if record.get("status", "Ativo") == "Ativo" else "Ativo"
        return self.update_record(record_id, status=new_status)

    # ---------- Campos personalizados ----------
    def add_field(self, nome, tipo="Texto"):
        nome = _text(nome).strip()
        if not nome:
            raise ValueError("O nome do campo é obrigatório.")
        if tipo not in ("Texto", "Número", "Sim/Não"):
            tipo = "Texto"
        fields = self.load_fields()
        if any(_norm(f.get("nome")) == _norm(nome) for f in fields):
            raise ValueError("Já existe um campo com esse nome.")
        field = {"id": self._next_id(fields), "nome": nome, "tipo": tipo, "status": "Ativo"}
        fields.append(field)
        self.save_fields(fields)
        return field

    def update_field(self, field_id, nome=None, tipo=None, status=None):
        fields = self.load_fields()
        found = None
        for field in fields:
            if str(field.get("id")) == str(field_id):
                if nome is not None:
                    nome = _text(nome).strip()
                    if not nome:
                        raise ValueError("O nome do campo é obrigatório.")
                    if any(
                        str(other.get("id")) != str(field_id)
                        and _norm(other.get("nome")) == _norm(nome)
                        for other in fields
                    ):
                        raise ValueError("Já existe outro campo com esse nome.")
                    field["nome"] = nome
                if tipo in ("Texto", "Número", "Sim/Não"):
                    field["tipo"] = tipo
                if status in ("Ativo", "Inativo"):
                    field["status"] = status
                found = field
                break
        if found is None:
            raise KeyError("Campo não encontrado.")
        self.save_fields(fields)
        return found

    def toggle_field_status(self, field_id):
        field = next((f for f in self.load_fields() if str(f.get("id")) == str(field_id)), None)
        if not field:
            raise KeyError("Campo não encontrado.")
        return self.update_field(
            field_id,
            status="Inativo" if field.get("status", "Ativo") == "Ativo" else "Ativo",
        )

    def delete_field(self, field_id, remove_values=True):
        fields = self.load_fields()
        new_fields = [f for f in fields if str(f.get("id")) != str(field_id)]
        if len(new_fields) == len(fields):
            return False
        self.save_fields(new_fields)
        if remove_values:
            records = self.load_records()
            key = str(field_id)
            for record in records:
                record.setdefault("campos", {}).pop(key, None)
            self.save_records(records)
        return True

    def set_custom_value(self, record_id, field_id, value):
        fields = self.load_fields()
        field = next((f for f in fields if str(f.get("id")) == str(field_id)), None)
        if not field:
            raise KeyError("Campo não encontrado.")
        value = _text(value).strip()
        if field.get("tipo") == "Número" and value:
            try:
                float(value.replace(",", "."))
            except Exception as exc:
                raise ValueError("Valor numérico inválido.") from exc
        if field.get("tipo") == "Sim/Não" and value not in ("", "Sim", "Não"):
            raise ValueError("Use Sim ou Não.")
        records = self.load_records()
        for record in records:
            if str(record.get("id")) == str(record_id):
                record.setdefault("campos", {})[str(field_id)] = value
                self.save_records(records)
                return record
        raise KeyError("Cadastro não encontrado.")

    # ---------- Filtros ----------
    def filter_records(self, texto="", grupo="Todos", status="Todos", field_id=None, field_value=""):
        texto_n = _norm(texto)
        field_value_n = _norm(field_value)
        result = []
        for record in self.load_records():
            if grupo != "Todos" and _norm(record.get("grupo")) != _norm(grupo):
                continue
            if status != "Todos" and record.get("status", "Ativo") != status:
                continue
            if texto_n:
                haystack = " ".join(
                    [
                        _text(record.get("nome")),
                        _text(record.get("contato")),
                        _text(record.get("grupo")),
                        _text(record.get("observacoes")),
                        " ".join(_text(v) for v in record.get("campos", {}).values()),
                    ]
                ).casefold()
                if texto_n not in haystack:
                    continue
            if field_id is not None:
                value = _norm(record.get("campos", {}).get(str(field_id), ""))
                if field_value_n and field_value_n not in value:
                    continue
                if not field_value_n and not value:
                    continue
            result.append(record)
        return sorted(result, key=lambda x: _norm(x.get("nome")))

    # ---------- Relatórios ----------
    def report_summary(self):
        records = self.load_records()
        ativos = sum(1 for r in records if r.get("status", "Ativo") == "Ativo")
        combos = {}
        for record in records:
            key = _text(record.get("grupo")).strip() or "Não informado"
            combos[key] = combos.get(key, 0) + 1
        fields = self.load_fields()
        fill = []
        for field in fields:
            field_id = str(field.get("id"))
            filled = sum(1 for r in records if _text(r.get("campos", {}).get(field_id)).strip())
            fill.append({**field, "preenchidos": filled, "total": len(records)})
        return {
            "total": len(records),
            "ativos": ativos,
            "inativos": len(records) - ativos,
            "combos": dict(sorted(combos.items(), key=lambda x: x[0].casefold())),
            "campos": fill,
        }

    # ---------- Importação / exportação ----------
    def _columns(self, active_only=True):
        fields = self.load_fields()
        if active_only:
            fields = [f for f in fields if f.get("status", "Ativo") == "Ativo"]
        return fields, CORE_COLUMNS + [f.get("nome", "") for f in fields]

    def _rows(self, active_only=True):
        fields, header = self._columns(active_only=active_only)
        rows = []
        for record in self.list_records("az"):
            values = record.get("campos", {}) if isinstance(record.get("campos"), dict) else {}
            row = [
                _text(record.get("nome")),
                _text(record.get("contato")),
                _text(record.get("grupo")),
                _text(record.get("status", "Ativo")),
                _text(record.get("observacoes")),
            ]
            row.extend(_text(values.get(str(field.get("id")), "")) for field in fields)
            rows.append(row)
        return header, rows

    def export_csv(self, name="Cadastro_Acordes_cadastros.csv"):
        path = self.exports_dir / safe_filename(name)
        if path.suffix.lower() != ".csv":
            path = path.with_suffix(".csv")
        header, rows = self._rows(active_only=True)
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f, delimiter=";", quoting=csv.QUOTE_MINIMAL)
            writer.writerow(header)
            writer.writerows(rows)
        return path

    def import_csv(self, path, skip_duplicates=True):
        path = Path(path)
        raw = path.read_text(encoding="utf-8-sig", errors="replace")
        sample = raw[:4096]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=";,\t,")
            delimiter = dialect.delimiter
        except Exception:
            delimiter = ";"
        reader = csv.DictReader(io.StringIO(raw), delimiter=delimiter)
        if not reader.fieldnames:
            raise ValueError("CSV sem cabeçalho.")

        aliases = {
            "nome": "Nome",
            "contato": "Contato",
            "telefone": "Contato",
            "combo": "Combo",
            "grupo": "Combo",
            "instrumento": "Combo",
            "status": "Status",
            "observacoes": "Observações",
            "observações": "Observações",
        }
        normalized_headers = {h: aliases.get(_norm(h), h.strip()) for h in reader.fieldnames}
        core_names = set(CORE_COLUMNS)

        fields = self.load_fields()
        field_by_name = {_norm(f.get("nome")): f for f in fields}
        for original, canonical in normalized_headers.items():
            if canonical in core_names:
                continue
            if _norm(canonical) not in field_by_name:
                field = {"id": self._next_id(fields), "nome": canonical, "tipo": "Texto", "status": "Ativo"}
                fields.append(field)
                field_by_name[_norm(canonical)] = field
        self.save_fields(fields)

        records = self.load_records()
        existing = {(_norm(r.get("nome")), _norm(r.get("contato"))) for r in records}
        imported = 0
        skipped = 0
        for source_row in reader:
            row = {normalized_headers.get(k, k): _text(v).strip() for k, v in source_row.items() if k is not None}
            nome = row.get("Nome", "").strip()
            if not nome:
                skipped += 1
                continue
            contato = row.get("Contato", "")
            identity = (_norm(nome), _norm(contato))
            if skip_duplicates and identity in existing:
                skipped += 1
                continue
            grupo = row.get("Combo", "").strip() or "Não informado"
            status = row.get("Status", "Ativo")
            status = status if status in ("Ativo", "Inativo") else "Ativo"
            record = {
                "id": self._next_id(records),
                "nome": nome,
                "contato": contato,
                "grupo": grupo,
                "status": status,
                "observacoes": row.get("Observações", ""),
                "campos": {},
                "foto_uri": "",
            }
            for canonical, value in row.items():
                if canonical in core_names:
                    continue
                field = field_by_name.get(_norm(canonical))
                if field:
                    record["campos"][str(field.get("id"))] = value
            records.append(record)
            existing.add(identity)
            imported += 1
        self.save_records(records)
        return {"importados": imported, "ignorados": skipped}

    def export_xlsx(self, name="Cadastro_Acordes_cadastros.xlsx"):
        path = self.exports_dir / safe_filename(name)
        if path.suffix.lower() != ".xlsx":
            path = path.with_suffix(".xlsx")
        header, rows = self._rows(active_only=True)
        all_rows = [header] + rows

        def col_letter(n):
            result = ""
            while n:
                n, rem = divmod(n - 1, 26)
                result = chr(65 + rem) + result
            return result

        sheet_rows = []
        for r_index, row in enumerate(all_rows, start=1):
            cells = []
            for c_index, value in enumerate(row, start=1):
                ref = f"{col_letter(c_index)}{r_index}"
                style = ' s="1"' if r_index == 1 else ""
                text = xml_escape(_text(value))
                cells.append(f'<c r="{ref}" t="inlineStr"{style}><is><t xml:space="preserve">{text}</t></is></c>')
            sheet_rows.append(f'<row r="{r_index}">' + "".join(cells) + "</row>")

        content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>'''
        root_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>'''
        workbook = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Cadastros" sheetId="1" r:id="rId1"/></sheets></workbook>'''
        workbook_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>'''
        styles = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts><fills count="1"><fill><patternFill patternType="none"/></fill></fills><borders count="1"><border/></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs></styleSheet>'''
        sheet = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>{''.join(sheet_rows)}</sheetData></worksheet>'''

        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", content_types)
            zf.writestr("_rels/.rels", root_rels)
            zf.writestr("xl/workbook.xml", workbook)
            zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
            zf.writestr("xl/styles.xml", styles)
            zf.writestr("xl/worksheets/sheet1.xml", sheet)
        return path

    def export_pdf(self, name="Cadastro_Of_Mus_Acordes_relatorio.pdf"):
        # Mesmo método do projeto TRIADES: ReportLab/A4 + gravação direta
        # no Download público quando executado no Android.
        from pdf_export import gerar_pdf_cadastros
        return gerar_pdf_cadastros(self, name)

    # ---------- Backup / restauração ----------
    def create_backup(self, name=None):
        if not name:
            name = "Cadastro_Acordes_backup_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".zip"
        path = self.backups_dir / safe_filename(name)
        if path.suffix.lower() != ".zip":
            path = path.with_suffix(".zip")
        metadata = {
            "app": "Cadastro Of. Mus. Acordes",
            "format": 2,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("backup_info.json", json.dumps(metadata, ensure_ascii=False, indent=2))
            zf.writestr("cadastros.json", json.dumps(self.load_records(), ensure_ascii=False, indent=2))
            zf.writestr("campos.json", json.dumps(self.load_fields(), ensure_ascii=False, indent=2))
        return path

    def restore_backup(self, path):
        path = Path(path)
        with zipfile.ZipFile(path, "r") as zf:
            names = set(zf.namelist())
            if not {"cadastros.json", "campos.json"}.issubset(names):
                raise ValueError("Backup inválido: faltam cadastros.json ou campos.json.")
            records = json.loads(zf.read("cadastros.json").decode("utf-8"))
            fields = json.loads(zf.read("campos.json").decode("utf-8"))
            if not isinstance(records, list) or not isinstance(fields, list):
                raise ValueError("Backup inválido.")
        # proteção antes de substituir
        safety = self.create_backup("backup_antes_de_restaurar_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".zip")
        self.save_records(records)
        self.save_fields(fields)
        return safety
