import json
from pathlib import Path

from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Line, Rectangle, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.core.window import Window
from kivy.utils import platform

# Tamanho usado somente para visualização no Ubuntu/X11.
# No Android o sistema controla o tamanho da tela.
if platform != "android":
    Window.size = (540, 960)

from android_bridge import AndroidBridge
from data_store import DataStore


NOME_APP = "Cadastro Of. Mus. Acordes"
MODELO = "Gestão musical, cadastros e relatórios"
INSTRUMENTOS = ["Violão", "Guitarra", "Contrabaixo", "Teclado", "Bateria", "Outro"]

PALETA = {
    "fundo": (0.012, 0.075, 0.105, 1),
    "painel": (0.018, 0.105, 0.145, 1),
    "texto": (0.96, 0.94, 0.85, 1),
    "texto2": (0.77, 0.84, 0.88, 1),
    "dourado": (0.94, 0.70, 0.31, 1),
    "linha": (0.80, 0.58, 0.24, 0.65),
}

CARD_DEFS = [
    ("Cadastros", "Alunos, professores,\ninstrumentos e mais", "icons/cadastros.png", (0.38, 0.23, 0.06, 1), (0.78, 0.55, 0.18, 1)),
    ("Tabelas", "Gerencie dados\nde apoio", "icons/tabelas.png", (0.02, 0.22, 0.34, 1), (0.10, 0.55, 0.78, 1)),
    ("Filtros", "Pesquise e filtre\ninformações", "icons/filtros.png", (0.02, 0.29, 0.24, 1), (0.20, 0.67, 0.53, 1)),
    ("Relatórios", "Visualize e imprima\nseus relatórios", "icons/relatorios.png", (0.43, 0.20, 0.07, 1), (0.82, 0.43, 0.16, 1)),
    ("Importar / Exportar", "Troque dados com\noutros sistemas", "icons/importar_exportar.png", (0.02, 0.21, 0.38, 1), (0.10, 0.52, 0.79, 1)),
    ("Biblioteca", "Acordes, cifras\ne materiais de estudo", "icons/biblioteca.png", (0.21, 0.13, 0.39, 1), (0.48, 0.30, 0.75, 1)),
    ("Campos Personalizados", "Configure campos\nconforme sua necessidade", "icons/campos.png", (0.39, 0.12, 0.11, 1), (0.72, 0.29, 0.24, 1)),
    ("Backup e Restauração", "Proteja e recupere\nseus dados", "icons/backup.png", (0.00, 0.28, 0.27, 1), (0.11, 0.66, 0.58, 1)),
]


def app_data_dir():
    folder = Path(App.get_running_app().user_data_dir) / "cadastro_acordes"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def clipped(value, limit=80):
    value = str(value or "")
    return value if len(value) <= limit else value[: limit - 3] + "..."


class MenuCard(ButtonBehavior, BoxLayout):
    def __init__(self, title, subtitle, icon, bg, border, action, **kwargs):
        super().__init__(orientation="horizontal", padding=(dp(12), dp(10)), spacing=dp(10), **kwargs)
        self.size_hint_y = None
        self.height = dp(112)
        self._bg = bg
        self._border = border
        self.action = action

        with self.canvas.before:
            self.bg_color = Color(*bg)
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(16)])
            self.edge_color = Color(*border)
            self.edge = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(16)), width=1.2)
        self.bind(pos=self._update_canvas, size=self._update_canvas, state=self._state_changed)

        icon_img = Image(source=icon, size_hint=(None, 1), width=dp(64), fit_mode="contain")
        self.add_widget(icon_img)

        text_box = BoxLayout(orientation="vertical", spacing=dp(2))
        title_label = Label(text=title, color=PALETA["texto"], font_size="17sp", bold=True,
                            halign="left", valign="bottom", shorten=True, shorten_from="right")
        title_label.bind(size=lambda inst, val: setattr(inst, "text_size", val))
        subtitle_label = Label(text=subtitle, color=PALETA["texto2"], font_size="12sp",
                               halign="left", valign="top")
        subtitle_label.bind(size=lambda inst, val: setattr(inst, "text_size", val))
        text_box.add_widget(title_label)
        text_box.add_widget(subtitle_label)
        self.add_widget(text_box)

        arrow = Label(text=">", size_hint=(None, 1), width=dp(24), color=border, font_size="28sp")
        self.add_widget(arrow)
        self.bind(on_release=lambda *_: self.action())

    def _update_canvas(self, *_):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self.edge.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(16))

    def _state_changed(self, *_):
        factor = 1.12 if self.state == "down" else 1.0
        self.bg_color.rgba = tuple(min(1, c * factor) for c in self._bg[:3]) + (self._bg[3],)


class QuickCard(ButtonBehavior, BoxLayout):
    def __init__(self, text, icon, bg, action, **kwargs):
        super().__init__(orientation="vertical", padding=dp(8), spacing=dp(3), **kwargs)
        self.size_hint_y = None
        self.height = dp(118)
        self._bg = bg
        with self.canvas.before:
            self.bg_color = Color(*bg)
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(14)])
            Color(1, 1, 1, .18)
            self.edge = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(14)), width=1)
        self.bind(pos=self._update_canvas, size=self._update_canvas, state=self._state_changed)
        self.add_widget(Image(source=icon, size_hint_y=.58, fit_mode="contain"))
        label = Label(text=text, color=(1,1,1,1), font_size="12sp", halign="center", valign="middle")
        label.bind(size=lambda inst, val: setattr(inst, "text_size", val))
        self.add_widget(label)
        self.bind(on_release=lambda *_: action())

    def _update_canvas(self, *_):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self.edge.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(14))

    def _state_changed(self, *_):
        factor = 1.15 if self.state == "down" else 1.0
        self.bg_color.rgba = tuple(min(1, c * factor) for c in self._bg[:3]) + (self._bg[3],)


class HeaderWidget(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="horizontal", spacing=dp(10), padding=(dp(10), dp(8)), **kwargs)
        self.size_hint_y = None
        self.height = dp(205)
        with self.canvas.before:
            Color(0.01, 0.08, 0.12, 1)
            self.bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(20)])
            self.staff_color = Color(0.78, 0.56, 0.22, .35)
            self.staff_lines = [Line(points=[], width=.7) for _ in range(5)]
            self.note_color = Color(0.92, 0.68, 0.28, .42)
            self.notes = [Ellipse(pos=(0,0), size=(dp(7),dp(6))) for _ in range(5)]
            self.piano_white = Color(.94,.92,.84,.42)
            self.keys = [Rectangle(pos=(0,0), size=(0,0)) for _ in range(8)]
            self.piano_black = Color(.02,.03,.04,.82)
            self.black_keys = [Rectangle(pos=(0,0), size=(0,0)) for _ in range(5)]
        self.bind(pos=self._update_canvas, size=self._update_canvas)

        logo_box = BoxLayout(size_hint=(None, 1), width=dp(145), padding=dp(2))
        logo = Image(
            source="assets/logo_animada.gif",
            fit_mode="contain",
            anim_delay=0.125,
            anim_loop=0,
        )
        logo_box.add_widget(logo)
        self.add_widget(logo_box)

        text_box = BoxLayout(orientation="vertical", padding=(0, dp(36), dp(2), dp(34)), spacing=dp(4))
        title = Label(text=NOME_APP, color=PALETA["texto"], font_size="23sp", bold=True,
                      halign="left", valign="bottom")
        title.bind(size=lambda inst, val: setattr(inst, "text_size", (val[0], None)))
        sub = Label(text=MODELO, color=(.72,.83,.90,1), font_size="13sp", halign="left", valign="top")
        sub.bind(size=lambda inst, val: setattr(inst, "text_size", (val[0], None)))
        text_box.add_widget(title)
        text_box.add_widget(sub)
        self.add_widget(text_box)

    def _update_canvas(self, *_):
        self.bg.pos = self.pos
        self.bg.size = self.size
        left=self.x + dp(12); right=self.right-dp(12); base=self.y+dp(45)
        gap=dp(7)
        for i,line in enumerate(self.staff_lines):
            y=base+i*gap
            line.points=[left,y,right,y]
        xs=[.24,.37,.53,.69,.82]
        ys=[1,3,0,4,2]
        for note,fx,fy in zip(self.notes,xs,ys):
            note.pos=(self.x+self.width*fx, base+fy*gap-dp(2))
        key_w=max(dp(12), self.width*.052)
        start=self.right-key_w*8-dp(8); ky=self.y+dp(6); kh=dp(34)
        for i,key in enumerate(self.keys):
            key.pos=(start+i*key_w,ky); key.size=(key_w-dp(1),kh)
        black_positions=[1,2,4,5,6]
        for rect,idx in zip(self.black_keys,black_positions):
            rect.pos=(start+idx*key_w-dp(3), ky+kh*.46); rect.size=(dp(7),kh*.55)


class SummaryPanel(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=dp(12), spacing=dp(7), **kwargs)
        self.size_hint_y = None
        self.height = dp(165)
        with self.canvas.before:
            Color(0.015,0.105,0.14,1)
            self.bg = RoundedRectangle(pos=self.pos,size=self.size,radius=[dp(16)])
            Color(*PALETA["linha"])
            self.edge = Line(rounded_rectangle=(self.x,self.y,self.width,self.height,dp(16)),width=1.1)
        self.bind(pos=self._update_canvas,size=self._update_canvas)

        title = Label(text="Resumo", color=PALETA["texto"], bold=True, font_size="17sp",
                      size_hint_y=None, height=dp(30), halign="left")
        title.bind(size=lambda inst,val:setattr(inst,"text_size",val))
        self.add_widget(title)

        row=GridLayout(cols=4,spacing=dp(6))
        self.total_label=self._metric(row,"Total", "0", PALETA["dourado"])
        self.active_label=self._metric(row,"Ativos", "0", (.35,.92,.58,1))
        self.inactive_label=self._metric(row,"Inativos", "0", (.96,.38,.34,1))
        box=BoxLayout(orientation="vertical",padding=(dp(4),0))
        cap=Label(text="Instrumentos",color=PALETA["texto2"],font_size="10sp",size_hint_y=.35)
        self.instruments_label=Label(text="—",color=PALETA["texto"],font_size="11sp",halign="center",valign="middle")
        self.instruments_label.bind(size=lambda inst,val:setattr(inst,"text_size",val))
        box.add_widget(cap); box.add_widget(self.instruments_label); row.add_widget(box)
        self.add_widget(row)

    def _metric(self,row,caption,value,color):
        box=BoxLayout(orientation="vertical",padding=(dp(4),0))
        cap=Label(text=caption,color=PALETA["texto2"],font_size="10sp",size_hint_y=.35)
        val=Label(text=value,color=color,font_size="24sp",bold=True)
        box.add_widget(cap); box.add_widget(val); row.add_widget(box)
        return val

    def _update_canvas(self,*_):
        self.bg.pos=self.pos; self.bg.size=self.size
        self.edge.rounded_rectangle=(self.x,self.y,self.width,self.height,dp(16))


class NavButton(ButtonBehavior, BoxLayout):
    def __init__(self,text,icon,action,active=False,**kwargs):
        super().__init__(orientation="vertical",padding=dp(4),spacing=0,**kwargs)
        self.size_hint_y=None; self.height=dp(72)
        color=PALETA["dourado"] if active else (.68,.75,.82,1)
        self.add_widget(Image(source=icon,size_hint_y=.58,fit_mode="contain",color=color))
        self.add_widget(Label(text=text,color=color,font_size="10sp"))
        self.bind(on_release=lambda *_:action())


class CadastroPlanilha(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.spacing = 0
        self.padding = 0
        self.store = DataStore(app_data_dir())
        self.android = AndroidBridge()
        self.sort_order = "az"

        with self.canvas.before:
            Color(*PALETA["fundo"])
            self.root_bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *_: setattr(self.root_bg, "pos", self.pos),
                  size=lambda *_: setattr(self.root_bg, "size", self.size))

        self.scroll = ScrollView(do_scroll_x=False, bar_width=dp(4))
        content = BoxLayout(orientation="vertical", spacing=dp(12), padding=(dp(12), dp(12), dp(12), dp(18)), size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))
        self.scroll.add_widget(content)
        self.add_widget(self.scroll)

        content.add_widget(HeaderWidget())

        grid = GridLayout(
            cols=2,
            spacing=dp(10),
            size_hint_y=None,
            col_force_default=True,
        )

        def ajustar_colunas(instancia, largura):
            largura_util = max(
                1,
                (largura - dp(10)) / 2
            )
            instancia.col_default_width = largura_util

        grid.bind(
            width=ajustar_colunas,
            minimum_height=grid.setter("height")
        )
        actions = {
            "Cadastros": self.open_records,
            "Tabelas": self.open_table,
            "Filtros": self.open_filters,
            "Relatórios": self.open_reports,
            "Importar / Exportar": self.open_import_export,
            "Biblioteca": self.open_library,
            "Campos Personalizados": self.open_fields,
            "Backup e Restauração": self.open_backup,
        }
        for title, subtitle, icon, bg, border in CARD_DEFS:
            grid.add_widget(MenuCard(title, subtitle, icon, bg, border, actions[title]))
        content.add_widget(grid)

        quick_title = Label(text="Ações rápidas", color=PALETA["texto"], bold=True, font_size="18sp",
                            size_hint_y=None, height=dp(36), halign="left")
        quick_title.bind(size=lambda inst,val:setattr(inst,"text_size",val))
        content.add_widget(quick_title)

        quick = GridLayout(cols=5, spacing=dp(7), size_hint_y=None, height=dp(118))
        quick_defs = [
            ("Novo\nCadastro", "icons/novo.png", (0.03,.32,.25,1), lambda: self.open_record_form(None, self.refresh_summary)),
            ("Buscar", "icons/buscar.png", (0.02,.22,.38,1), self.open_filters),
            ("Exportar\nPDF", "icons/pdf.png", (.39,.14,.12,1), lambda: self._export_file(self.store.export_pdf)),
            ("Exportar\nExcel", "icons/excel.png", (.03,.30,.22,1), lambda: self._export_file(self.store.export_xlsx)),
            ("Exportar\nCSV", "icons/csv.png", (.40,.25,.06,1), lambda: self._export_file(self.store.export_csv)),
        ]
        for text, icon, bg, action in quick_defs:
            quick.add_widget(QuickCard(text, icon, bg, action))
        content.add_widget(quick)

        self.summary_panel = SummaryPanel()
        content.add_widget(self.summary_panel)

        self.status = Label(text="Aplicativo pronto.", color=(.60,.72,.78,1), font_size="10sp",
                            size_hint_y=None, height=dp(24), halign="center")
        content.add_widget(self.status)

        nav = BoxLayout(size_hint_y=None, height=dp(78), padding=(dp(10),dp(3)), spacing=dp(4))
        with nav.canvas.before:
            Color(0.008,0.055,0.078,1)
            nav._bg = Rectangle(pos=nav.pos,size=nav.size)
            Color(.85,.65,.28,.35)
            nav._line = Line(points=[nav.x, nav.top, nav.right, nav.top],width=.8)
        nav.bind(pos=lambda *_: (setattr(nav._bg,"pos",nav.pos), setattr(nav._line,"points",[nav.x,nav.top,nav.right,nav.top])),
                 size=lambda *_: (setattr(nav._bg,"size",nav.size), setattr(nav._line,"points",[nav.x,nav.top,nav.right,nav.top])))
        nav.add_widget(NavButton("Início","icons/inicio.png",self.go_home,active=True))
        nav.add_widget(NavButton("Cadastros","icons/cadastros.png",self.open_records))
        nav.add_widget(NavButton("Relatórios","icons/relatorios.png",self.open_reports))
        nav.add_widget(NavButton("Mais","icons/mais.png",self.open_more))
        self.add_widget(nav)

        self.refresh_summary()
        Clock.schedule_interval(lambda _dt: self.refresh_summary(), 3.0)

    def go_home(self):
        self.scroll.scroll_y = 1

    def refresh_summary(self, *_):
        try:
            report = self.store.report_summary()
            self.summary_panel.total_label.text = str(report.get("total", 0))
            self.summary_panel.active_label.text = str(report.get("ativos", 0))
            self.summary_panel.inactive_label.text = str(report.get("inativos", 0))
            names = list(report.get("combos", {}).keys())
            self.summary_panel.instruments_label.text = ", ".join(names[:4]) if names else "Nenhum"
        except Exception:
            pass

    def open_more(self):
        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
        options = [
            ("IMPORTAR / EXPORTAR", self.open_import_export),
            ("BIBLIOTECA", self.open_library),
            ("CAMPOS PERSONALIZADOS", self.open_fields),
            ("BACKUP E RESTAURAÇÃO", self.open_backup),
        ]
        popup = Popup(title="Mais", content=box, size_hint=(.9,.72), auto_dismiss=False)
        for text, action in options:
            btn = Button(text=text, size_hint_y=None, height=dp(52))
            btn.bind(on_release=lambda _b, a=action: (popup.dismiss(), a()))
            box.add_widget(btn)
        close = Button(text="FECHAR", size_hint_y=None, height=dp(50))
        close.bind(on_release=popup.dismiss)
        box.add_widget(close)
        popup.open()

    def select_module(self, module):
        actions = {
            "Cadastros": self.open_records,
            "Tabelas": self.open_table,
            "Campos personalizados": self.open_fields,
            "Campos Personalizados": self.open_fields,
            "Filtros": self.open_filters,
            "Relatórios": self.open_reports,
            "Importar / Exportar": self.open_import_export,
            "Backup": self.open_backup,
            "Backup e Restauração": self.open_backup,
            "Biblioteca": self.open_library,
        }
        action = actions.get(module)
        if action:
            action()

    # ---------- UI helpers ----------
    def select_module(self, module):
        actions = {
            "Cadastros": self.open_records,
            "Tabelas": self.open_table,
            "Campos personalizados": self.open_fields,
            "Filtros": self.open_filters,
            "Relatórios": self.open_reports,
            "Importar / Exportar": self.open_import_export,
            "Backup": self.open_backup,
            "Biblioteca": self.open_library,
        }
        action = actions.get(module)
        if action:
            action()

    @staticmethod
    def vertical_scroll(spacing=6, padding=6):
        scroll = ScrollView(do_scroll_x=False)
        box = BoxLayout(orientation="vertical", spacing=dp(spacing), padding=dp(padding), size_hint_y=None)
        box.bind(minimum_height=box.setter("height"))
        scroll.add_widget(box)
        return scroll, box

    def message(self, title, text):
        box = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(12))
        label = Label(text=str(text), halign="center", valign="middle")
        label.bind(size=lambda inst, val: setattr(inst, "text_size", (val[0], None)))
        box.add_widget(label)
        close = Button(text="FECHAR", size_hint_y=None, height=dp(50))
        box.add_widget(close)
        popup = Popup(title=title, content=box, size_hint=(0.9, 0.58), auto_dismiss=False)
        close.bind(on_release=popup.dismiss)
        popup.open()
        return popup

    def confirm(self, title, text, on_yes):
        box = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(12))
        box.add_widget(Label(text=text))
        row = BoxLayout(spacing=dp(8), size_hint_y=None, height=dp(52))
        no = Button(text="CANCELAR")
        yes = Button(text="CONFIRMAR")
        row.add_widget(no)
        row.add_widget(yes)
        box.add_widget(row)
        popup = Popup(title=title, content=box, size_hint=(0.9, 0.5), auto_dismiss=False)
        no.bind(on_release=popup.dismiss)

        def run(*_):
            popup.dismiss()
            on_yes()

        yes.bind(on_release=run)
        popup.open()

    # ---------- Cadastros ----------
    def open_records(self):
        scroll, list_box = self.vertical_scroll()
        root = BoxLayout(orientation="vertical", spacing=dp(7), padding=dp(8))
        title = Label(text="CADASTROS", size_hint_y=None, height=dp(38), font_size="18sp")
        root.add_widget(title)
        root.add_widget(scroll)
        actions = BoxLayout(spacing=dp(6), size_hint_y=None, height=dp(52))
        new_btn = Button(text="NOVO")
        sort_btn = Button(text="ORDEM A-Z")
        close_btn = Button(text="FECHAR")
        actions.add_widget(new_btn)
        actions.add_widget(sort_btn)
        actions.add_widget(close_btn)
        root.add_widget(actions)
        popup = Popup(title="Cadastros", content=root, size_hint=(0.96, 0.94), auto_dismiss=False)

        def refresh(*_):
            list_box.clear_widgets()
            records = self.store.list_records(self.sort_order)
            title.text = f"CADASTROS ({len(records)})"
            if not records:
                list_box.add_widget(Label(text="Nenhum cadastro.", size_hint_y=None, height=dp(52)))
            for record in records:
                text = f"{record.get('nome','')}\n{record.get('grupo','')} • {record.get('status','Ativo')}"
                btn = Button(text=text, size_hint_y=None, height=dp(66))
                btn.bind(on_release=lambda _b, rid=record.get("id"): self.open_record_details(rid, refresh))
                list_box.add_widget(btn)

        def toggle_sort(*_):
            self.sort_order = "za" if self.sort_order == "az" else "az"
            sort_btn.text = "ORDEM Z-A" if self.sort_order == "za" else "ORDEM A-Z"
            refresh()

        new_btn.bind(on_release=lambda *_: self.open_record_form(None, refresh))
        sort_btn.bind(on_release=toggle_sort)
        close_btn.bind(on_release=popup.dismiss)
        refresh()
        popup.open()

    def open_record_form(self, record_id, on_saved):
        record = self.store.get_record(record_id) if record_id is not None else None
        root = BoxLayout(orientation="vertical", spacing=dp(7), padding=dp(10))
        scroll, form = self.vertical_scroll(spacing=8)
        root.add_widget(scroll)

        def add_label(text):
            form.add_widget(Label(text=text, size_hint_y=None, height=dp(28)))

        add_label("Nome")
        name = TextInput(text=(record or {}).get("nome", ""), multiline=False, size_hint_y=None, height=dp(50))
        form.add_widget(name)
        add_label("Contato / telefone")
        contact = TextInput(text=(record or {}).get("contato", ""), multiline=False, size_hint_y=None, height=dp(50))
        form.add_widget(contact)
        contact_pick = Button(text="ESCOLHER NOS CONTATOS DO CELULAR", size_hint_y=None, height=dp(46))
        form.add_widget(contact_pick)
        add_label("Combo / instrumento")
        group = Spinner(text=(record or {}).get("grupo", "Violão") or "Violão", values=INSTRUMENTOS, size_hint_y=None, height=dp(50))
        form.add_widget(group)
        add_label("Observações")
        notes = TextInput(text=(record or {}).get("observacoes", ""), multiline=True, size_hint_y=None, height=dp(120))
        form.add_widget(notes)
        warning = Label(text="", size_hint_y=None, height=dp(42))
        form.add_widget(warning)

        row = BoxLayout(spacing=dp(7), size_hint_y=None, height=dp(52))
        cancel = Button(text="CANCELAR")
        save = Button(text="SALVAR")
        row.add_widget(cancel)
        row.add_widget(save)
        root.add_widget(row)
        popup = Popup(title="Editar cadastro" if record else "Novo cadastro", content=root, size_hint=(0.95, 0.92), auto_dismiss=False)
        cancel.bind(on_release=popup.dismiss)

        def picked(result, error):
            def apply(*_):
                if error:
                    warning.text = error
                    return
                if result:
                    if not name.text.strip():
                        name.text = result.get("nome", "")
                    contact.text = result.get("contato", "")
            Clock.schedule_once(apply, 0)

        contact_pick.bind(on_release=lambda *_: self.android.pick_phone_contact(picked))

        def do_save(*_):
            try:
                if record:
                    self.store.update_record(
                        record_id,
                        nome=name.text,
                        contato=contact.text,
                        grupo=group.text,
                        observacoes=notes.text,
                    )
                else:
                    self.store.add_record(name.text, contact.text, group.text, notes.text)
                popup.dismiss()
                self.status.text = "Cadastro salvo com sucesso."
                on_saved()
            except Exception as exc:
                warning.text = str(exc)

        save.bind(on_release=do_save)
        popup.open()

    def open_record_details(self, record_id, on_updated):
        record = self.store.get_record(record_id)
        if not record:
            self.message("Cadastro", "Cadastro não encontrado.")
            return
        root = BoxLayout(orientation="vertical", spacing=dp(7), padding=dp(10))
        scroll, box = self.vertical_scroll(spacing=7)
        box.add_widget(Label(text=record.get("nome", ""), size_hint_y=None, height=dp(44), font_size="19sp"))
        details = [
            ("Contato", record.get("contato", "")),
            ("Combo", record.get("grupo", "")),
            ("Status", record.get("status", "Ativo")),
            ("Observações", clipped(record.get("observacoes", ""), 250)),
            ("Foto", "Anexada" if record.get("foto_uri") else "Não anexada"),
        ]
        for key, value in details:
            box.add_widget(Label(text=f"{key}: {value}", size_hint_y=None, height=dp(38)))

        root.add_widget(scroll)
        grid = GridLayout(cols=2, spacing=dp(6), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        actions = [
            ("EDITAR", lambda: self.open_record_form(record_id, on_updated)),
            ("ATIVAR/DESATIVAR", lambda: self._toggle_record(record_id, on_updated)),
            ("CAMPOS", lambda: self.open_record_fields(record_id, on_updated)),
            ("EXCLUIR", lambda: self._confirm_delete_record(record_id, on_updated)),
            ("TELEFONAR", lambda: self._dial_record(record_id)),
            ("WHATSAPP", lambda: self._whatsapp_record(record_id)),
            ("ESCOLHER FOTO", lambda: self._pick_record_photo(record_id, on_updated)),
            ("ABRIR FOTO", lambda: self._open_record_photo(record_id)),
        ]
        popup = Popup(title="Detalhes", content=root, size_hint=(0.96, 0.94), auto_dismiss=False)
        for label, func in actions:
            btn = Button(text=label, size_hint_y=None, height=dp(50))
            btn.bind(on_release=lambda _b, f=func: (popup.dismiss(), f()))
            grid.add_widget(btn)
        root.add_widget(grid)
        close = Button(text="FECHAR", size_hint_y=None, height=dp(50))
        close.bind(on_release=popup.dismiss)
        root.add_widget(close)
        popup.open()

    def _toggle_record(self, record_id, on_updated):
        try:
            self.store.toggle_record_status(record_id)
            self.status.text = "Status alterado."
            on_updated()
        except Exception as exc:
            self.message("Erro", str(exc))

    def _confirm_delete_record(self, record_id, on_updated):
        record = self.store.get_record(record_id)
        name = (record or {}).get("nome", "este cadastro")

        def delete():
            self.store.delete_record(record_id)
            self.status.text = "Cadastro excluído definitivamente."
            on_updated()

        self.confirm("Excluir cadastro", f"Excluir definitivamente {name}?", delete)

    def _dial_record(self, record_id):
        record = self.store.get_record(record_id) or {}
        ok, msg = self.android.dial(record.get("contato", ""))
        self.status.text = msg
        if not ok:
            self.message("Telefone", msg)

    def _whatsapp_record(self, record_id):
        record = self.store.get_record(record_id) or {}
        ok, msg = self.android.whatsapp(record.get("contato", ""))
        self.status.text = msg
        if not ok:
            self.message("WhatsApp", msg)

    def _pick_record_photo(self, record_id, on_updated):
        def picked(uri, error):
            def apply(*_):
                if error:
                    self.message("Foto", error)
                    return
                self.store.update_record(record_id, foto_uri=uri)
                self.status.text = "Foto vinculada ao cadastro."
                on_updated()
            Clock.schedule_once(apply, 0)

        self.android.pick_photo(picked)

    def _open_record_photo(self, record_id):
        record = self.store.get_record(record_id) or {}
        uri = record.get("foto_uri", "")
        if not uri:
            self.message("Foto", "Este cadastro não possui foto vinculada.")
            return
        ok, msg = self.android.open_uri(uri, "image/*")
        if not ok:
            self.message("Foto", msg)

    # ---------- Campos personalizados ----------
    def open_fields(self):
        root = BoxLayout(orientation="vertical", spacing=dp(7), padding=dp(8))
        scroll, box = self.vertical_scroll()
        root.add_widget(scroll)
        row = BoxLayout(spacing=dp(6), size_hint_y=None, height=dp(52))
        new_btn = Button(text="NOVO CAMPO")
        close_btn = Button(text="FECHAR")
        row.add_widget(new_btn)
        row.add_widget(close_btn)
        root.add_widget(row)
        popup = Popup(title="Campos personalizados", content=root, size_hint=(0.95, 0.92), auto_dismiss=False)

        def refresh(*_):
            box.clear_widgets()
            fields = self.store.load_fields()
            if not fields:
                box.add_widget(Label(text="Nenhum campo personalizado.", size_hint_y=None, height=dp(50)))
            for field in fields:
                text = f"{field.get('nome','')}\n{field.get('tipo','Texto')} • {field.get('status','Ativo')}"
                btn = Button(text=text, size_hint_y=None, height=dp(64))
                btn.bind(on_release=lambda _b, fid=field.get("id"): self.open_field_details(fid, refresh))
                box.add_widget(btn)

        new_btn.bind(on_release=lambda *_: self.open_field_form(None, refresh))
        close_btn.bind(on_release=popup.dismiss)
        refresh()
        popup.open()

    def open_field_form(self, field_id, on_saved):
        field = next((f for f in self.store.load_fields() if str(f.get("id")) == str(field_id)), None)
        box = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(12))
        box.add_widget(Label(text="Nome do campo", size_hint_y=None, height=dp(30)))
        name = TextInput(text=(field or {}).get("nome", ""), multiline=False, size_hint_y=None, height=dp(50))
        box.add_widget(name)
        box.add_widget(Label(text="Tipo", size_hint_y=None, height=dp(30)))
        kind = Spinner(text=(field or {}).get("tipo", "Texto"), values=("Texto", "Número", "Sim/Não"), size_hint_y=None, height=dp(50))
        box.add_widget(kind)
        warning = Label(text="", size_hint_y=None, height=dp(42))
        box.add_widget(warning)
        row = BoxLayout(spacing=dp(7), size_hint_y=None, height=dp(52))
        cancel = Button(text="CANCELAR")
        save = Button(text="SALVAR")
        row.add_widget(cancel)
        row.add_widget(save)
        box.add_widget(row)
        popup = Popup(title="Editar campo" if field else "Novo campo", content=box, size_hint=(0.9, 0.68), auto_dismiss=False)
        cancel.bind(on_release=popup.dismiss)

        def do_save(*_):
            try:
                if field:
                    self.store.update_field(field_id, nome=name.text, tipo=kind.text)
                else:
                    self.store.add_field(name.text, kind.text)
                popup.dismiss()
                on_saved()
            except Exception as exc:
                warning.text = str(exc)

        save.bind(on_release=do_save)
        popup.open()

    def open_field_details(self, field_id, on_updated):
        field = next((f for f in self.store.load_fields() if str(f.get("id")) == str(field_id)), None)
        if not field:
            return
        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
        box.add_widget(Label(text=field.get("nome", ""), font_size="19sp"))
        box.add_widget(Label(text=f"Tipo: {field.get('tipo')}\nStatus: {field.get('status','Ativo')}"))
        edit = Button(text="RENOMEAR / ALTERAR TIPO", size_hint_y=None, height=dp(52))
        status = Button(text="ATIVAR / DESATIVAR", size_hint_y=None, height=dp(52))
        delete = Button(text="EXCLUIR CAMPO", size_hint_y=None, height=dp(52))
        close = Button(text="FECHAR", size_hint_y=None, height=dp(52))
        for btn in (edit, status, delete, close):
            box.add_widget(btn)
        popup = Popup(title="Campo personalizado", content=box, size_hint=(0.9, 0.72), auto_dismiss=False)
        close.bind(on_release=popup.dismiss)
        edit.bind(on_release=lambda *_: (popup.dismiss(), self.open_field_form(field_id, on_updated)))

        def toggle(*_):
            self.store.toggle_field_status(field_id)
            popup.dismiss()
            on_updated()

        status.bind(on_release=toggle)

        def ask_delete(*_):
            popup.dismiss()
            self.confirm(
                "Excluir campo",
                "Excluir o campo e apagar seus valores de todos os cadastros?",
                lambda: (self.store.delete_field(field_id, True), on_updated()),
            )

        delete.bind(on_release=ask_delete)
        popup.open()

    def open_record_fields(self, record_id, on_updated):
        root = BoxLayout(orientation="vertical", spacing=dp(7), padding=dp(8))
        scroll, box = self.vertical_scroll()
        root.add_widget(scroll)
        close = Button(text="FECHAR", size_hint_y=None, height=dp(50))
        root.add_widget(close)
        popup = Popup(title="Campos do cadastro", content=root, size_hint=(0.94, 0.9), auto_dismiss=False)
        close.bind(on_release=popup.dismiss)

        def refresh(*_):
            box.clear_widgets()
            record = self.store.get_record(record_id) or {}
            fields = [f for f in self.store.load_fields() if f.get("status", "Ativo") == "Ativo"]
            if not fields:
                box.add_widget(Label(text="Nenhum campo ativo.", size_hint_y=None, height=dp(50)))
            for field in fields:
                value = record.get("campos", {}).get(str(field.get("id")), "")
                btn = Button(text=f"{field.get('nome')}\n{value or 'Não informado'}", size_hint_y=None, height=dp(64))
                btn.bind(on_release=lambda _b, fid=field.get("id"): self.edit_custom_value(record_id, fid, refresh))
                box.add_widget(btn)

        refresh()
        popup.open()

    def edit_custom_value(self, record_id, field_id, on_saved):
        field = next((f for f in self.store.load_fields() if str(f.get("id")) == str(field_id)), None)
        record = self.store.get_record(record_id) or {}
        if not field:
            return
        current = record.get("campos", {}).get(str(field_id), "")
        box = BoxLayout(orientation="vertical", spacing=dp(9), padding=dp(12))
        box.add_widget(Label(text=field.get("nome", ""), size_hint_y=None, height=dp(40), font_size="18sp"))
        warning = Label(text="", size_hint_y=None, height=dp(38))
        popup = Popup(title="Editar valor", content=box, size_hint=(0.9, 0.64), auto_dismiss=False)

        if field.get("tipo") == "Sim/Não":
            box.add_widget(Label(text="Valor atual: " + (current or "Não informado")))
            row = BoxLayout(spacing=dp(8), size_hint_y=None, height=dp(55))
            yes = Button(text="SIM")
            no = Button(text="NÃO")
            row.add_widget(yes)
            row.add_widget(no)
            box.add_widget(row)
            clear = Button(text="LIMPAR", size_hint_y=None, height=dp(48))
            cancel = Button(text="CANCELAR", size_hint_y=None, height=dp(48))
            box.add_widget(clear)
            box.add_widget(cancel)
            cancel.bind(on_release=popup.dismiss)

            def save_value(value):
                self.store.set_custom_value(record_id, field_id, value)
                popup.dismiss()
                on_saved()

            yes.bind(on_release=lambda *_: save_value("Sim"))
            no.bind(on_release=lambda *_: save_value("Não"))
            clear.bind(on_release=lambda *_: save_value(""))
        else:
            entry = TextInput(text=str(current), multiline=False, size_hint_y=None, height=dp(52))
            box.add_widget(entry)
            box.add_widget(warning)
            row = BoxLayout(spacing=dp(8), size_hint_y=None, height=dp(52))
            cancel = Button(text="CANCELAR")
            save = Button(text="SALVAR")
            row.add_widget(cancel)
            row.add_widget(save)
            box.add_widget(row)
            cancel.bind(on_release=popup.dismiss)

            def do_save(*_):
                try:
                    self.store.set_custom_value(record_id, field_id, entry.text)
                    popup.dismiss()
                    on_saved()
                except Exception as exc:
                    warning.text = str(exc)

            save.bind(on_release=do_save)
        popup.open()

    # ---------- Tabelas ----------
    def open_table(self):
        root = BoxLayout(orientation="vertical", spacing=dp(7), padding=dp(8))
        scroll, box = self.vertical_scroll(spacing=4)
        root.add_widget(scroll)
        close = Button(text="FECHAR", size_hint_y=None, height=dp(50))
        root.add_widget(close)
        popup = Popup(title="Tabela de cadastros", content=root, size_hint=(0.97, 0.94), auto_dismiss=False)
        close.bind(on_release=popup.dismiss)
        fields = [f for f in self.store.load_fields() if f.get("status", "Ativo") == "Ativo"]
        header = "NOME | COMBO | STATUS"
        if fields:
            header += " | " + " | ".join(f.get("nome", "") for f in fields[:2])
        box.add_widget(Label(text=header, size_hint_y=None, height=dp(45)))
        for record in self.store.list_records("az"):
            parts = [record.get("nome", ""), record.get("grupo", ""), record.get("status", "Ativo")]
            for field in fields[:2]:
                parts.append(str(record.get("campos", {}).get(str(field.get("id")), "")))
            box.add_widget(Label(text=" | ".join(parts), size_hint_y=None, height=dp(42)))
        if not self.store.load_records():
            box.add_widget(Label(text="Nenhum cadastro.", size_hint_y=None, height=dp(50)))
        popup.open()

    # ---------- Filtros ----------
    def open_filters(self):
        root = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(10))
        text = TextInput(hint_text="Pesquisar nome, contato, combo, observações ou campos", multiline=False, size_hint_y=None, height=dp(50))
        groups = ["Todos"] + sorted({r.get("grupo", "") for r in self.store.load_records() if r.get("grupo")})
        group = Spinner(text="Todos", values=groups, size_hint_y=None, height=dp(48))
        status = Spinner(text="Todos", values=("Todos", "Ativo", "Inativo"), size_hint_y=None, height=dp(48))
        fields = [f for f in self.store.load_fields() if f.get("status", "Ativo") == "Ativo"]
        field_names = ["Nenhum"] + [f.get("nome", "") for f in fields]
        field_spinner = Spinner(text="Nenhum", values=field_names, size_hint_y=None, height=dp(48))
        field_value = TextInput(hint_text="Valor do campo personalizado", multiline=False, size_hint_y=None, height=dp(48))
        for widget in (
            Label(text="Pesquisa geral", size_hint_y=None, height=dp(28)), text,
            Label(text="Combo", size_hint_y=None, height=dp(28)), group,
            Label(text="Status", size_hint_y=None, height=dp(28)), status,
            Label(text="Campo personalizado", size_hint_y=None, height=dp(28)), field_spinner, field_value,
        ):
            root.add_widget(widget)
        row = BoxLayout(spacing=dp(7), size_hint_y=None, height=dp(52))
        run = Button(text="FILTRAR")
        close = Button(text="FECHAR")
        row.add_widget(run)
        row.add_widget(close)
        root.add_widget(row)
        popup = Popup(title="Filtros", content=root, size_hint=(0.95, 0.9), auto_dismiss=False)
        close.bind(on_release=popup.dismiss)

        def execute(*_):
            field_id = None
            if field_spinner.text != "Nenhum":
                selected = next((f for f in fields if f.get("nome") == field_spinner.text), None)
                field_id = selected.get("id") if selected else None
            result = self.store.filter_records(text.text, group.text, status.text, field_id, field_value.text)
            popup.dismiss()
            self.show_filter_results(result)

        run.bind(on_release=execute)
        popup.open()

    def show_filter_results(self, records):
        root = BoxLayout(orientation="vertical", spacing=dp(7), padding=dp(8))
        root.add_widget(Label(text=f"RESULTADOS: {len(records)}", size_hint_y=None, height=dp(38)))
        scroll, box = self.vertical_scroll()
        root.add_widget(scroll)
        close = Button(text="FECHAR", size_hint_y=None, height=dp(50))
        root.add_widget(close)
        popup = Popup(title="Resultados do filtro", content=root, size_hint=(0.95, 0.92), auto_dismiss=False)
        close.bind(on_release=popup.dismiss)
        if not records:
            box.add_widget(Label(text="Nenhum resultado.", size_hint_y=None, height=dp(50)))
        for record in records:
            btn = Button(text=f"{record.get('nome')}\n{record.get('grupo')} • {record.get('status','Ativo')}", size_hint_y=None, height=dp(64))
            btn.bind(on_release=lambda _b, rid=record.get("id"): self.open_record_details(rid, lambda: None))
            box.add_widget(btn)
        popup.open()

    # ---------- Relatórios ----------
    def open_reports(self):
        report = self.store.report_summary()
        lines = [
            f"Total: {report['total']}",
            f"Ativos: {report['ativos']}",
            f"Inativos: {report['inativos']}",
            "",
            "POR COMBO / INSTRUMENTO",
        ]
        for name, count in report["combos"].items():
            lines.append(f"{name}: {count}")
        lines.extend(["", "PREENCHIMENTO DOS CAMPOS"])
        for field in report["campos"]:
            lines.append(f"{field.get('nome')}: {field.get('preenchidos')}/{field.get('total')}")
        self.message("Relatórios", "\n".join(lines))

    # ---------- Importar / Exportar ----------
    def open_import_export(self):
        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
        box.add_widget(Label(text="IMPORTAR / EXPORTAR", size_hint_y=None, height=dp(42), font_size="18sp"))
        csv_btn = Button(text="EXPORTAR CSV", size_hint_y=None, height=dp(54))
        xlsx_btn = Button(text="EXPORTAR EXCEL (.XLSX)", size_hint_y=None, height=dp(54))
        pdf_btn = Button(text="EXPORTAR PDF", size_hint_y=None, height=dp(54))
        import_btn = Button(text="IMPORTAR CSV", size_hint_y=None, height=dp(54))
        close = Button(text="FECHAR", size_hint_y=None, height=dp(50))
        for btn in (csv_btn, xlsx_btn, pdf_btn, import_btn, close):
            box.add_widget(btn)
        popup = Popup(title="Importação e exportação", content=box, size_hint=(0.92, 0.82), auto_dismiss=False)
        close.bind(on_release=popup.dismiss)
        csv_btn.bind(on_release=lambda *_: self._export_file(self.store.export_csv))
        xlsx_btn.bind(on_release=lambda *_: self._export_file(self.store.export_xlsx))
        pdf_btn.bind(on_release=lambda *_: self._export_file(self.store.export_pdf))
        import_btn.bind(on_release=lambda *_: self._pick_import_csv())
        popup.open()

    def _export_file(self, generator):
        try:
            path = generator()
            self.status.text = "Arquivo criado: " + path.name
            self.show_export_file(path)
        except Exception as exc:
            self.message("Exportação", "Erro: " + str(exc))

    def show_export_file(self, path):
        box = BoxLayout(orientation="vertical", spacing=dp(9), padding=dp(12))
        caminho = str(path)
        pdf_publico = (
            path.suffix.lower() == ".pdf"
            and caminho.startswith("/storage/emulated/0/Download/")
        )
        if pdf_publico:
            box.add_widget(Label(
                text=(
                    "PDF criado diretamente no Download, no mesmo padrão do TRIADES:\n"
                    + caminho
                )
            ))
            close = Button(text="FECHAR", size_hint_y=None, height=dp(50))
            box.add_widget(close)
            popup = Popup(title="PDF pronto", content=box, size_hint=(0.92, 0.58), auto_dismiss=False)
            close.bind(on_release=popup.dismiss)
            popup.open()
            return

        box.add_widget(Label(text=f"Arquivo criado:\n{path.name}"))
        save = Button(text="SALVAR EM DOWNLOADS", size_hint_y=None, height=dp(52))
        share = Button(text="SALVAR E COMPARTILHAR", size_hint_y=None, height=dp(52))
        close = Button(text="FECHAR", size_hint_y=None, height=dp(50))
        box.add_widget(save)
        box.add_widget(share)
        box.add_widget(close)
        popup = Popup(title="Arquivo pronto", content=box, size_hint=(0.9, 0.66), auto_dismiss=False)
        close.bind(on_release=popup.dismiss)

        def save_file(*_):
            uri, error = self.android.save_to_downloads(path)
            self.message("Downloads", error or "Arquivo salvo em Downloads/Cadastro Of. Mus. Acordes.")

        def share_file(*_):
            ok, msg = self.android.save_and_share(path)
            if not ok:
                self.message("Compartilhar", msg)

        save.bind(on_release=save_file)
        share.bind(on_release=share_file)
        popup.open()

    def _pick_import_csv(self):
        def selected(path, error):
            def apply(*_):
                if error:
                    self.message("Importar CSV", error)
                    return
                try:
                    result = self.store.import_csv(path)
                    self.status.text = "CSV importado."
                    self.message(
                        "Importação concluída",
                        f"Importados: {result['importados']}\nIgnorados: {result['ignorados']}",
                    )
                except Exception as exc:
                    self.message("Importar CSV", "Erro: " + str(exc))
            Clock.schedule_once(apply, 0)

        self.android.pick_document_to_folder(self.store.imports_dir, selected, "text/*", {".csv", ".txt"})

    # ---------- Backup / restauração ----------
    def open_backup(self):
        root = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
        root.add_widget(Label(text="BACKUP E RESTAURAÇÃO", size_hint_y=None, height=dp(42), font_size="18sp"))
        create = Button(text="CRIAR BACKUP", size_hint_y=None, height=dp(54))
        create_share = Button(text="CRIAR E COMPARTILHAR / NUVEM", size_hint_y=None, height=dp(54))
        restore_external = Button(text="RESTAURAR BACKUP DO CELULAR", size_hint_y=None, height=dp(54))
        restore_latest = Button(text="RESTAURAR ÚLTIMO BACKUP INTERNO", size_hint_y=None, height=dp(54))
        close = Button(text="FECHAR", size_hint_y=None, height=dp(50))
        for btn in (create, create_share, restore_external, restore_latest, close):
            root.add_widget(btn)
        popup = Popup(title="Backup", content=root, size_hint=(0.94, 0.84), auto_dismiss=False)
        close.bind(on_release=popup.dismiss)

        def make(*_):
            try:
                path = self.store.create_backup()
                self.status.text = "Backup criado: " + path.name
                self.show_export_file(path)
            except Exception as exc:
                self.message("Backup", str(exc))

        def make_share(*_):
            try:
                path = self.store.create_backup()
                ok, msg = self.android.save_and_share(path)
                if not ok:
                    self.message("Backup", msg)
            except Exception as exc:
                self.message("Backup", str(exc))

        def restore_latest(*_):
            backups = sorted(self.store.backups_dir.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
            if not backups:
                self.message("Restaurar", "Nenhum backup interno encontrado.")
                return
            self._confirm_restore(backups[0])

        create.bind(on_release=make)
        create_share.bind(on_release=make_share)
        restore_latest.bind(on_release=restore_latest)
        restore_external.bind(on_release=lambda *_: self._pick_backup())
        popup.open()

    def _pick_backup(self):
        def selected(path, error):
            def apply(*_):
                if error:
                    self.message("Restaurar", error)
                    return
                self._confirm_restore(path)
            Clock.schedule_once(apply, 0)

        self.android.pick_document_to_folder(self.store.imports_dir, selected, "application/zip", {".zip"})

    def _confirm_restore(self, path):
        def restore():
            try:
                safety = self.store.restore_backup(path)
                self.status.text = "Backup restaurado."
                self.message("Restauração", "Dados restaurados com sucesso.\nBackup de segurança criado: " + safety.name)
            except Exception as exc:
                self.message("Restauração", "Erro: " + str(exc))

        self.confirm("Restaurar backup", "Os dados atuais serão substituídos. Continuar?", restore)

    # ---------- Biblioteca ----------
    def _project_categories(self):
        root = Path(__file__).resolve().parent
        project = root / "projeto.json"
        categories = []
        try:
            data = json.loads(project.read_text(encoding="utf-8"))
            categories = [str(x) for x in data.get("categorias", [])]
        except Exception:
            pass
        library = root / "biblioteca"
        if library.exists():
            for folder in library.iterdir():
                if folder.is_dir() and folder.name not in categories:
                    categories.append(folder.name)
        return library, categories

    def open_library(self):
        library, categories = self._project_categories()
        root = BoxLayout(orientation="vertical", spacing=dp(7), padding=dp(8))
        scroll, box = self.vertical_scroll()
        root.add_widget(scroll)
        close = Button(text="FECHAR", size_hint_y=None, height=dp(50))
        root.add_widget(close)
        popup = Popup(title="Biblioteca", content=root, size_hint=(0.95, 0.92), auto_dismiss=False)
        close.bind(on_release=popup.dismiss)
        if not categories:
            box.add_widget(Label(text="Nenhuma categoria configurada.", size_hint_y=None, height=dp(50)))
        for category in categories:
            folder = library / category
            files = sorted([p for p in folder.glob("**/*") if p.is_file()]) if folder.exists() else []
            box.add_widget(Label(text=f"{category} ({len(files)})", size_hint_y=None, height=dp(42), font_size="17sp"))
            if not files:
                box.add_widget(Label(text="Pasta vazia.", size_hint_y=None, height=dp(36)))
            for file in files:
                btn = Button(text=file.name, size_hint_y=None, height=dp(48))
                btn.bind(on_release=lambda _b, p=file: self._open_library_file(p))
                box.add_widget(btn)
        popup.open()

    def _open_library_file(self, path):
        if not self.android.available:
            self.message("Biblioteca", "Arquivo encontrado:\n" + str(path))
            return
        uri, error = self.android.save_to_downloads(path)
        if error:
            self.message("Biblioteca", error)
            return
        mime = self.android._mime(path)
        ok, msg = self.android.open_uri(uri, mime)
        if not ok:
            self.message("Biblioteca", msg)


class AplicativoGerado(App):
    def build(self):
        from kivy.core.window import Window
        Window.clearcolor = PALETA["fundo"]
        self.title = NOME_APP
        return CadastroPlanilha()


if __name__ == "__main__":
    AplicativoGerado().run()
