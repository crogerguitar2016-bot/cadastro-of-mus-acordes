import mimetypes
import os
import re
from pathlib import Path


class AndroidBridge:
    """Integrações Android isoladas para o restante do app continuar testável."""

    def __init__(self):
        self.available = False
        self.activity = None
        self._handlers = {}
        self._next_request = 6100
        self.last_error = ""
        try:
            from jnius import autoclass  # noqa: F401
            from android import activity
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            self.activity = PythonActivity.mActivity
            activity.bind(on_activity_result=self._on_activity_result)
            self.available = True
        except Exception as exc:
            self.last_error = str(exc)

    def _request_code(self, handler):
        self._next_request += 1
        code = self._next_request
        self._handlers[code] = handler
        return code

    def _on_activity_result(self, request_code, result_code, intent):
        handler = self._handlers.pop(request_code, None)
        if handler is None:
            return
        try:
            handler(result_code, intent)
        except Exception as exc:
            self.last_error = str(exc)

    @staticmethod
    def _mime(path):
        mime, _ = mimetypes.guess_type(str(path))
        return mime or "application/octet-stream"

    @staticmethod
    def _clean_name(name):
        name = os.path.basename(str(name or "arquivo"))
        name = re.sub(r"[^\w\-. ()]+", "_", name, flags=re.UNICODE)
        return name or "arquivo"

    # ---------- Ações simples ----------
    def dial(self, phone):
        if not self.available:
            return False, "Recurso disponível somente no Android."
        try:
            from jnius import autoclass
            Intent = autoclass("android.content.Intent")
            Uri = autoclass("android.net.Uri")
            digits = re.sub(r"[^0-9+]", "", str(phone or ""))
            if not digits:
                return False, "Contato sem número de telefone."
            intent = Intent(Intent.ACTION_DIAL, Uri.parse("tel:" + digits))
            self.activity.startActivity(intent)
            return True, "Discador aberto."
        except Exception as exc:
            return False, str(exc)

    def whatsapp(self, phone, text=""):
        if not self.available:
            return False, "Recurso disponível somente no Android."
        try:
            from urllib.parse import quote
            from jnius import autoclass
            Intent = autoclass("android.content.Intent")
            Uri = autoclass("android.net.Uri")
            digits = re.sub(r"\D", "", str(phone or ""))
            if len(digits) in (10, 11):
                digits = "55" + digits
            if not digits:
                return False, "Contato sem número de telefone."
            url = "https://wa.me/" + digits
            if text:
                url += "?text=" + quote(str(text))
            intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
            self.activity.startActivity(intent)
            return True, "WhatsApp aberto."
        except Exception as exc:
            return False, str(exc)

    def open_uri(self, uri_text, mime="*/*"):
        if not self.available:
            return False, "Recurso disponível somente no Android."
        try:
            from jnius import autoclass
            Intent = autoclass("android.content.Intent")
            Uri = autoclass("android.net.Uri")
            uri = Uri.parse(str(uri_text))
            intent = Intent(Intent.ACTION_VIEW)
            intent.setDataAndType(uri, mime)
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            self.activity.startActivity(intent)
            return True, "Arquivo aberto."
        except Exception as exc:
            return False, str(exc)

    # ---------- Picker de foto ----------
    def pick_photo(self, callback):
        if not self.available:
            callback(None, "Recurso disponível somente no Android.")
            return
        try:
            from jnius import autoclass
            Intent = autoclass("android.content.Intent")
            result_ok = autoclass("android.app.Activity").RESULT_OK

            def handler(result_code, data):
                if result_code != result_ok or data is None:
                    callback(None, "Seleção cancelada.")
                    return
                uri = data.getData()
                if uri is None:
                    callback(None, "Nenhuma imagem selecionada.")
                    return
                try:
                    flags = data.getFlags() & (
                        Intent.FLAG_GRANT_READ_URI_PERMISSION
                        | Intent.FLAG_GRANT_WRITE_URI_PERMISSION
                    )
                    self.activity.getContentResolver().takePersistableUriPermission(uri, flags)
                except Exception:
                    pass
                callback(str(uri.toString()), None)

            code = self._request_code(handler)
            intent = Intent(Intent.ACTION_OPEN_DOCUMENT)
            intent.addCategory(Intent.CATEGORY_OPENABLE)
            intent.setType("image/*")
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION)
            self.activity.startActivityForResult(intent, code)
        except Exception as exc:
            callback(None, str(exc))

    # ---------- Picker de contato ----------
    def pick_phone_contact(self, callback):
        if not self.available:
            callback(None, "Recurso disponível somente no Android.")
            return
        try:
            from jnius import autoclass
            Intent = autoclass("android.content.Intent")
            Phone = autoclass("android.provider.ContactsContract$CommonDataKinds$Phone")
            Activity = autoclass("android.app.Activity")

            def handler(result_code, data):
                if result_code != Activity.RESULT_OK or data is None:
                    callback(None, "Seleção cancelada.")
                    return
                uri = data.getData()
                cursor = None
                try:
                    cursor = self.activity.getContentResolver().query(uri, None, None, None, None)
                    if cursor is None or not cursor.moveToFirst():
                        callback(None, "Não foi possível ler o contato.")
                        return
                    idx_name = cursor.getColumnIndex(Phone.DISPLAY_NAME)
                    idx_phone = cursor.getColumnIndex(Phone.NUMBER)
                    result = {
                        "nome": str(cursor.getString(idx_name)) if idx_name >= 0 else "",
                        "contato": str(cursor.getString(idx_phone)) if idx_phone >= 0 else "",
                    }
                    callback(result, None)
                except Exception as exc:
                    callback(None, str(exc))
                finally:
                    try:
                        if cursor is not None:
                            cursor.close()
                    except Exception:
                        pass

            code = self._request_code(handler)
            intent = Intent(Intent.ACTION_PICK, Phone.CONTENT_URI)
            self.activity.startActivityForResult(intent, code)
        except Exception as exc:
            callback(None, str(exc))

    # ---------- Seleção/cópia de documentos ----------
    def _display_name(self, uri):
        try:
            from jnius import autoclass
            OpenableColumns = autoclass("android.provider.OpenableColumns")
            cursor = self.activity.getContentResolver().query(uri, None, None, None, None)
            if cursor is not None and cursor.moveToFirst():
                idx = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                name = str(cursor.getString(idx)) if idx >= 0 else "arquivo"
                cursor.close()
                return self._clean_name(name)
        except Exception:
            pass
        return "arquivo"

    def _copy_uri_to_file(self, uri, destination):
        from jnius import autoclass
        BufferedInputStream = autoclass("java.io.BufferedInputStream")
        BufferedOutputStream = autoclass("java.io.BufferedOutputStream")
        FileOutputStream = autoclass("java.io.FileOutputStream")

        resolver = self.activity.getContentResolver()
        input_stream = BufferedInputStream(resolver.openInputStream(uri))
        output_stream = BufferedOutputStream(FileOutputStream(str(destination)))
        try:
            while True:
                value = input_stream.read()
                if value == -1:
                    break
                output_stream.write(value)
            output_stream.flush()
        finally:
            try:
                input_stream.close()
            except Exception:
                pass
            try:
                output_stream.close()
            except Exception:
                pass

    def pick_document_to_folder(self, folder, callback, mime="*/*", allowed_suffixes=None):
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        if not self.available:
            callback(None, "Recurso disponível somente no Android.")
            return
        try:
            from jnius import autoclass
            Intent = autoclass("android.content.Intent")
            Activity = autoclass("android.app.Activity")

            def handler(result_code, data):
                if result_code != Activity.RESULT_OK or data is None:
                    callback(None, "Seleção cancelada.")
                    return
                uri = data.getData()
                try:
                    name = self._display_name(uri)
                    if allowed_suffixes:
                        suffix = Path(name).suffix.lower()
                        allowed = {s.lower() for s in allowed_suffixes}
                        if suffix not in allowed:
                            callback(None, "Tipo de arquivo não permitido: " + suffix)
                            return
                    destination = folder / name
                    self._copy_uri_to_file(uri, destination)
                    callback(destination, None)
                except Exception as exc:
                    callback(None, str(exc))

            code = self._request_code(handler)
            intent = Intent(Intent.ACTION_OPEN_DOCUMENT)
            intent.addCategory(Intent.CATEGORY_OPENABLE)
            intent.setType(mime)
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            self.activity.startActivityForResult(intent, code)
        except Exception as exc:
            callback(None, str(exc))

    # ---------- Downloads / compartilhamento ----------
    def save_to_downloads(self, local_path, callback=None):
        local_path = Path(local_path)
        if not self.available:
            result = (None, "Recurso disponível somente no Android.")
            if callback:
                callback(*result)
            return result
        try:
            from jnius import autoclass
            Build = autoclass("android.os.Build")
            if Build.VERSION.SDK_INT < 29:
                result = (None, "Salvar em Downloads requer Android 10 ou superior nesta versão.")
                if callback:
                    callback(*result)
                return result

            MediaStoreDownloads = autoclass("android.provider.MediaStore$Downloads")
            ContentValues = autoclass("android.content.ContentValues")
            MediaStoreMediaColumns = autoclass("android.provider.MediaStore$MediaColumns")
            Environment = autoclass("android.os.Environment")
            BufferedInputStream = autoclass("java.io.BufferedInputStream")
            BufferedOutputStream = autoclass("java.io.BufferedOutputStream")
            FileInputStream = autoclass("java.io.FileInputStream")

            values = ContentValues()
            values.put(MediaStoreMediaColumns.DISPLAY_NAME, local_path.name)
            values.put(MediaStoreMediaColumns.MIME_TYPE, self._mime(local_path))
            values.put(MediaStoreMediaColumns.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS + "/Cadastro Of. Mus. Acordes")
            resolver = self.activity.getContentResolver()
            uri = resolver.insert(MediaStoreDownloads.EXTERNAL_CONTENT_URI, values)
            if uri is None:
                raise RuntimeError("O Android não criou o arquivo em Downloads.")

            source = BufferedInputStream(FileInputStream(str(local_path)))
            target = BufferedOutputStream(resolver.openOutputStream(uri))
            try:
                while True:
                    value = source.read()
                    if value == -1:
                        break
                    target.write(value)
                target.flush()
            finally:
                try:
                    source.close()
                except Exception:
                    pass
                try:
                    target.close()
                except Exception:
                    pass
            result = (str(uri.toString()), None)
            if callback:
                callback(*result)
            return result
        except Exception as exc:
            result = (None, str(exc))
            if callback:
                callback(*result)
            return result

    def share_uri(self, uri_text, mime="application/octet-stream", title="Compartilhar arquivo"):
        if not self.available:
            return False, "Recurso disponível somente no Android."
        try:
            from jnius import autoclass
            Intent = autoclass("android.content.Intent")
            Uri = autoclass("android.net.Uri")
            uri = Uri.parse(str(uri_text))
            intent = Intent(Intent.ACTION_SEND)
            intent.setType(mime or "application/octet-stream")
            intent.putExtra(Intent.EXTRA_STREAM, uri)
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            self.activity.startActivity(Intent.createChooser(intent, title))
            return True, "Compartilhamento aberto."
        except Exception as exc:
            return False, str(exc)

    def save_and_share(self, local_path):
        uri, error = self.save_to_downloads(local_path)
        if error:
            return False, error
        return self.share_uri(uri, self._mime(local_path), "Compartilhar " + Path(local_path).name)
