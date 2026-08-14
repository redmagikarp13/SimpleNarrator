"""
Janela principal do SimpleNarrator.
Interface em CustomTkinter com abas para Narrador, Processamento em Lote e Modelos.
"""

import logging
import os
import tempfile
import threading
import sys
from typing import Optional
from pathlib import Path

import customtkinter as ctk
from tkinter import filedialog, messagebox

from engines.base_engine import BaseEngine, VoiceInfo
from engines.native_engine import NativeEngine
from engines.piper_engine import PiperEngine
from audio.chunker import chunk_text
from file_io.exporter import merge_and_export
from models.downloader import ModelDownloader

logger = logging.getLogger(__name__)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


def get_models_dir() -> str:
    """Retorna o caminho absoluto do diretório de modelos.
    
    No executável compilado (PyInstaller), usa a pasta 'models' ao lado do .exe.
    No modo desenvolvimento, usa a pasta 'models' na raiz do projeto.
    """
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(os.path.abspath(sys.executable))
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    models_path = os.path.join(base_dir, "models")
    os.makedirs(models_path, exist_ok=True)
    return models_path


class NarratorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("SimpleNarrator")
        self.geometry("900x650")
        self.minsize(800, 500)

        # ── Diretório de Modelos ──
        self.models_dir = get_models_dir()

        # ── Estado da aplicação ──
        self._engines: dict[str, BaseEngine] = {
            "native": NativeEngine(),
            "piper": PiperEngine(models_dir=self.models_dir),
        }
        self._active_engine: Optional[BaseEngine] = None
        self._voices: list[VoiceInfo] = []
        self._is_processing = False
        self._batch_files = []
        self._batch_output_dir = ""
        
        # Gerenciador de downloads do Piper
        self.downloader = ModelDownloader(self.models_dir)

        # ── Construir interface ──
        self._build_ui()
        self._init_engines()

        # Forçar a janela para o primeiro plano
        self.lift()
        self.attributes("-topmost", True)
        self.after(500, lambda: self.attributes("-topmost", False))
        self.focus_force()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        self.tab_narrador = self.tabview.add("Narrador")
        self.tab_lote = self.tabview.add("Processamento em Lote")
        self.tab_modelos = self.tabview.add("Modelos Piper")

        self._build_tab_narrador()
        self._build_tab_lote()
        self._build_tab_modelos()

    # ─────────────────────────────────────────────
    #  ABA: NARRADOR (Existente)
    # ─────────────────────────────────────────────
    def _build_tab_narrador(self):
        self.tab_narrador.grid_columnconfigure(1, weight=1)
        self.tab_narrador.grid_rowconfigure(0, weight=1)

        # Sidebar
        sidebar = ctk.CTkFrame(self.tab_narrador, width=220, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(sidebar, text="Configurações", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, padx=15, pady=(15, 10), sticky="w")

        ctk.CTkLabel(sidebar, text="Motor:").grid(row=1, column=0, padx=15, pady=(5, 2), sticky="w")
        self._engine_var = ctk.StringVar(value="native")
        self._engine_display_var = ctk.StringVar(value="Nativo do S.O. (CPU)")
        
        self._engine_menu = ctk.CTkOptionMenu(
            sidebar,
            variable=self._engine_display_var,
            values=["Nativo do S.O. (CPU)", "IA - Piper TTS (CPU/GPU)"],
            command=self._on_engine_display_change
        )
        self._engine_menu.grid(row=2, column=0, padx=15, pady=(0, 5), sticky="ew")

        # Checkbox de Aceleração GPU (Piper)
        self._gpu_var = ctk.BooleanVar(value=False)
        self._gpu_checkbox = ctk.CTkCheckBox(
            sidebar, text="Aceleração GPU (CUDA)", variable=self._gpu_var, command=self._on_gpu_toggle, font=ctk.CTkFont(size=11)
        )
        self._gpu_checkbox.grid(row=3, column=0, padx=15, pady=(0, 2), sticky="w")
        self._gpu_checkbox.grid_remove()  # Oculto por padrao

        # Link para baixar drivers CUDA da NVIDIA
        import webbrowser
        self._cuda_link_btn = ctk.CTkButton(
            sidebar,
            text="Obter Drivers CUDA ↗",
            command=lambda: webbrowser.open("https://developer.nvidia.com/cuda-downloads"),
            font=ctk.CTkFont(size=10, underline=True),
            fg_color="transparent",
            text_color="#64B5F6",
            hover_color="#1E293B",
            height=20
        )
        self._cuda_link_btn.grid(row=4, column=0, padx=12, pady=(0, 10), sticky="w")
        self._cuda_link_btn.grid_remove()  # Oculto por padrao

        ctk.CTkLabel(sidebar, text="Voz:").grid(row=5, column=0, padx=15, pady=(5, 2), sticky="w")
        self._voice_var = ctk.StringVar(value="—")
        self._voice_menu = ctk.CTkOptionMenu(sidebar, variable=self._voice_var, values=["—"], command=self._on_voice_change)
        self._voice_menu.grid(row=6, column=0, padx=15, pady=(0, 10), sticky="ew")

        ctk.CTkLabel(sidebar, text="Velocidade:").grid(row=7, column=0, padx=15, pady=(5, 2), sticky="w")
        self._rate_slider = ctk.CTkSlider(sidebar, from_=0.5, to=2.0, number_of_steps=15, command=self._on_rate_change)
        self._rate_slider.set(1.0)
        self._rate_slider.grid(row=8, column=0, padx=15, pady=(0, 5), sticky="ew")

        ctk.CTkLabel(sidebar, text="Tom:").grid(row=9, column=0, padx=15, pady=(5, 2), sticky="w")
        self._pitch_slider = ctk.CTkSlider(sidebar, from_=0.5, to=2.0, number_of_steps=15, command=self._on_pitch_change)
        self._pitch_slider.set(1.0)
        self._pitch_slider.grid(row=10, column=0, padx=15, pady=(0, 10), sticky="ew")

        ctk.CTkButton(sidebar, text="Importar arquivo", command=self._on_import_file).grid(row=11, column=0, padx=15, pady=20, sticky="ew")

        # Área principal
        main_frame = ctk.CTkFrame(self.tab_narrador)
        main_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=0)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)

        self._text_box = ctk.CTkTextbox(main_frame, wrap="word", font=ctk.CTkFont(size=13))
        self._text_box.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 5))

        self._progress_label = ctk.CTkLabel(main_frame, text="Pronto", font=ctk.CTkFont(size=11), text_color="gray")
        self._progress_label.grid(row=1, column=0, padx=10, pady=(0, 0), sticky="w")

        self._progress_bar = ctk.CTkProgressBar(main_frame)
        self._progress_bar.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        self._progress_bar.set(0)

        controls = ctk.CTkFrame(main_frame, fg_color="transparent")
        controls.grid(row=3, column=0, pady=(5, 10))

        self._btn_generate = ctk.CTkButton(controls, text="Gerar MP3", command=self._on_generate, width=160, font=ctk.CTkFont(size=14, weight="bold"))
        self._btn_generate.grid(row=0, column=0, padx=5)

        self._btn_cancel = ctk.CTkButton(controls, text="Cancelar", command=self._on_cancel, width=100, state="disabled", fg_color="gray")
        self._btn_cancel.grid(row=0, column=1, padx=5)


    # ─────────────────────────────────────────────
    #  ABA: PROCESSAMENTO EM LOTE
    # ─────────────────────────────────────────────
    def _build_tab_lote(self):
        self.tab_lote.grid_columnconfigure(0, weight=1)
        self.tab_lote.grid_rowconfigure(1, weight=1)

        top_frame = ctk.CTkFrame(self.tab_lote, fg_color="transparent")
        top_frame.grid(row=0, column=0, sticky="ew", pady=(5, 10))

        ctk.CTkButton(top_frame, text="+ Adicionar Arquivos (TXT/PDF)", command=self._add_batch_files).pack(side="left", padx=5)
        ctk.CTkButton(top_frame, text="Limpar Lista", command=self._clear_batch_files, fg_color="gray").pack(side="left", padx=5)
        
        self._batch_out_btn = ctk.CTkButton(top_frame, text="Pasta de Saída: Não selecionada", command=self._select_batch_output, fg_color="#455A64")
        self._batch_out_btn.pack(side="right", padx=5)

        # Lista de arquivos (Textbox simula Listbox)
        self._batch_list_box = ctk.CTkTextbox(self.tab_lote, state="disabled")
        self._batch_list_box.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        bottom_frame = ctk.CTkFrame(self.tab_lote, fg_color="transparent")
        bottom_frame.grid(row=2, column=0, sticky="ew", pady=(5, 10))
        bottom_frame.grid_columnconfigure(0, weight=1)

        self._batch_progress_lbl = ctk.CTkLabel(bottom_frame, text="Pronto para processar.", text_color="gray")
        self._batch_progress_lbl.grid(row=0, column=0, sticky="w", padx=5)

        self._batch_progress_bar = ctk.CTkProgressBar(bottom_frame)
        self._batch_progress_bar.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        self._batch_progress_bar.set(0)

        self._btn_process_batch = ctk.CTkButton(bottom_frame, text="Processar Lote", command=self._on_process_batch, font=ctk.CTkFont(weight="bold"))
        self._btn_process_batch.grid(row=2, column=0, pady=10)

    # ─────────────────────────────────────────────
    #  ABA: MODELOS PIPER
    # ─────────────────────────────────────────────
    def _build_tab_modelos(self):
        self.tab_modelos.grid_columnconfigure(0, weight=1)
        self.tab_modelos.grid_rowconfigure(3, weight=1)

        # Caminho da pasta de modelos
        path_frame = ctk.CTkFrame(self.tab_modelos, fg_color="transparent")
        path_frame.grid(row=0, column=0, sticky="ew", pady=(5, 0))

        models_dir_path = self.downloader.models_dir
        ctk.CTkLabel(path_frame, text=f"Pasta dos Modelos: {models_dir_path}", font=ctk.CTkFont(size=12), text_color="gray").pack(side="left", padx=5)
        
        def open_models_folder():
            os.makedirs(models_dir_path, exist_ok=True)
            if os.name == 'nt':
                os.startfile(models_dir_path)
            elif sys.platform == 'darwin':
                import subprocess
                subprocess.Popen(['open', models_dir_path])
            else:
                import subprocess
                subprocess.Popen(['xdg-open', models_dir_path])

        ctk.CTkButton(path_frame, text="Abrir Pasta", command=open_models_folder, width=90, height=24, fg_color="#455A64").pack(side="left", padx=10)


        ctk.CTkLabel(self.tab_modelos, text="Baixar novos modelos de voz (Inteligência Artificial)", font=ctk.CTkFont(size=16, weight="bold")).grid(row=1, column=0, pady=(10, 5), sticky="w")
        
        # Frame de busca
        search_frame = ctk.CTkFrame(self.tab_modelos, fg_color="transparent")
        search_frame.grid(row=2, column=0, sticky="ew", pady=5)
        
        self._btn_refresh_models = ctk.CTkButton(search_frame, text="Carregar Lista do Servidor", command=self._load_models_list)
        self._btn_refresh_models.pack(side="left", padx=5)

        self._models_status_lbl = ctk.CTkLabel(search_frame, text="", text_color="gray")
        self._models_status_lbl.pack(side="left", padx=10)

        # Scrollable frame para listar
        self._models_frame = ctk.CTkScrollableFrame(self.tab_modelos)
        self._models_frame.grid(row=3, column=0, sticky="nsew", pady=5)

        # -- Secao: Gerenciamento GPU --
        gpu_frame = ctk.CTkFrame(self.tab_modelos, fg_color="transparent")
        gpu_frame.grid(row=4, column=0, sticky="ew", pady=(10, 5))
        ctk.CTkLabel(gpu_frame, text="Aceleracao GPU (NVIDIA CUDA)", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left", padx=5)
        self._gpu_status_lbl = ctk.CTkLabel(gpu_frame, text="Verificando...", text_color="gray", font=ctk.CTkFont(size=11))
        self._gpu_status_lbl.pack(side="left", padx=10)

        gpu_btn_frame = ctk.CTkFrame(self.tab_modelos, fg_color="transparent")
        gpu_btn_frame.grid(row=5, column=0, sticky="ew", pady=(0, 10))
        self._btn_install_gpu = ctk.CTkButton(gpu_btn_frame, text="Baixar DLLs da GPU (CUDA)", command=self._on_install_gpu, fg_color="#4CAF50", hover_color="#388E3C")
        self._btn_uninstall_gpu = ctk.CTkButton(gpu_btn_frame, text="Remover DLLs da GPU", command=self._on_uninstall_gpu, fg_color="#D32F2F", hover_color="#B71C1C", state="disabled")
        self._gpu_progress_lbl = ctk.CTkLabel(gpu_btn_frame, text="", text_color="gray", font=ctk.CTkFont(size=10))
        self._gpu_progress_lbl.pack(side="left", padx=10)

        # Verificar GPU logo apos construir UI
        self.after(50, self._check_gpu_availability)

    def _load_models_list(self):
        self._btn_refresh_models.configure(state="disabled")
        self._models_status_lbl.configure(text="Baixando lista...")
        
        def fetch():
            try:
                voices = self.downloader.fetch_voices_list(force_refresh=True)
                self.after(0, lambda: self._populate_models_ui(voices))
            except Exception as e:
                self.after(0, lambda: self._models_status_lbl.configure(text=f"Erro: {e}", text_color="red"))
            finally:
                self.after(0, lambda: self._btn_refresh_models.configure(state="normal"))
        
        threading.Thread(target=fetch, daemon=True).start()

    def _populate_models_ui(self, voices: dict):
        self._models_status_lbl.configure(text=f"{len(voices)} modelos encontrados.", text_color="green")
        
        # Limpar grid atual
        for widget in self._models_frame.winfo_children():
            widget.destroy()

        # Filtrar pt_BR por padrão para o topo, depois o resto
        sorted_keys = sorted(voices.keys(), key=lambda k: (voices[k].get("language", {}).get("code") != "pt_BR", k))

        for i, key in enumerate(sorted_keys):
            info = voices[key]
            lang = info.get("language", {}).get("name_native", "Unknown")
            quality = info.get("quality", "unknown")
            is_downloaded = self.downloader.is_voice_downloaded(key)

            frame = ctk.CTkFrame(self._models_frame)
            frame.pack(fill="x", padx=5, pady=2)
            
            ctk.CTkLabel(frame, text=f"{key} ({lang} - {quality})").pack(side="left", padx=10, pady=5)
            
            if is_downloaded:
                # Botão Excluir
                ctk.CTkButton(
                    frame, 
                    text="Excluir", 
                    width=70, 
                    fg_color="#D32F2F", 
                    hover_color="#B71C1C",
                    command=lambda k=key, f=frame: self._on_delete_model(k, f)
                ).pack(side="right", padx=10, pady=5)
                ctk.CTkLabel(frame, text="Instalado", text_color="green").pack(side="right", padx=10)
            else:
                # Botão Baixar
                btn_download = ctk.CTkButton(frame, text="Baixar", width=70)
                btn_download.configure(command=lambda k=key, b=btn_download, f=frame: self._on_download_model(k, b, f))
                btn_download.pack(side="right", padx=10, pady=5)

    def _on_download_model(self, key: str, btn: ctk.CTkButton, frame: ctk.CTkFrame):
        btn.configure(state="disabled", text="0%")
        
        def progress(pct, text):
            self.after(0, lambda: btn.configure(text=f"{int(pct*100)}%"))

        def task():
            success = self.downloader.download_voice(key, progress_callback=progress)
            if success:
                self._engines["piper"].initialize()
                if self._engine_var.get() == "piper":
                    self.after(0, lambda: self._on_engine_change("piper"))
                if self.downloader.voices_data:
                    self.after(0, lambda: self._populate_models_ui(self.downloader.voices_data))
            else:
                self.after(0, lambda: btn.configure(text="Falhou", state="normal", fg_color="red"))

        threading.Thread(target=task, daemon=True).start()

    def _on_delete_model(self, key: str, frame: ctk.CTkFrame):
        if messagebox.askyesno("Confirmar Exclusão", f"Deseja realmente excluir o modelo '{key}'?", parent=self):
            if self.downloader.delete_voice(key):
                self._engines["piper"].initialize()
                if self._engine_var.get() == "piper":
                    self._on_engine_change("piper")
                if self.downloader.voices_data:
                    self._populate_models_ui(self.downloader.voices_data)

    # ─────────────────────────────────────────────
    #  LÓGICA GERAL (Inicialização e UI)
    # ─────────────────────────────────────────────
    def _init_engines(self):
        try:
            self._engines["native"].initialize()
        except Exception as e:
            logger.error(f"Erro ao inicializar motor nativo: {e}")

        try:
            self._engines["piper"].initialize()
        except Exception as e:
            logger.error(f"Erro ao inicializar motor Piper: {e}")

        self._active_engine = self._engines["native"]
        self._refresh_voices()

    def _refresh_voices(self):
        if not self._active_engine: return
        try:
            self._voices = self._active_engine.get_available_voices()
            names = [v.name for v in self._voices] if self._voices else ["Nenhuma voz"]
            self._voice_menu.configure(values=names)
            if names and names[0] != "Nenhuma voz":
                self._voice_var.set(names[0])
                self._active_engine.set_voice(self._voices[0].id)
            else:
                self._voice_var.set("—")
        except Exception as e:
            logger.error(f"Erro ao carregar vozes: {e}")
            self._voices = []
            self._voice_menu.configure(values=["Erro ao carregar"])
            self._voice_var.set("—")

    def _on_engine_display_change(self, choice: str):
        engine_key = "native" if "Nativo" in choice else "piper"
        self._on_engine_change(engine_key)

    def _on_engine_change(self, engine_key: str):
        self._engine_var.set(engine_key)
        self._active_engine = self._engines[engine_key]
        
        # Ajustar visibilidade do checkbox de GPU
        if engine_key == "piper" and PiperEngine.is_gpu_available():
            self._gpu_checkbox.grid()
            self._gpu_checkbox.configure(state="normal")
        else:
            self._gpu_checkbox.grid_remove()
            self._gpu_checkbox.configure(state="disabled")

        self._refresh_voices()

    def _on_gpu_toggle(self):
        use_cuda = self._gpu_var.get()
        piper: PiperEngine = self._engines["piper"]
        piper.set_use_cuda(use_cuda)
        logger.info(f"Aceleração GPU alterada para: {use_cuda}")

    def _on_voice_change(self, choice: str):
        for v in self._voices:
            if v.name == choice:
                self._active_engine.set_voice(v.id)
                break

    def _on_rate_change(self, value: float):
        if self._active_engine:
            self._active_engine.set_rate(value)

    def _on_pitch_change(self, value: float):
        if self._active_engine:
            self._active_engine.set_pitch(value)

    def _on_import_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Documentos de Texto", "*.txt *.pdf")])
        if file_path:
            from file_io.reader import read_file
            try:
                text = read_file(file_path)
                self._text_box.delete("1.0", "end")
                self._text_box.insert("1.0", text)
                self._progress_label.configure(text=f"Arquivo: {file_path}", text_color="gray")
            except Exception as e:
                self._progress_label.configure(text=f"Erro: {e}", text_color="red")

    # ─────────────────────────────────────────────
    #  SÍNTESE UNITÁRIA (NARRADOR)
    # ─────────────────────────────────────────────
    def _on_generate(self):
        if not self._active_engine or not self._voices:
            messagebox.showerror("Erro", "Nenhum motor ou voz disponível.", parent=self)
            return

        text = self._text_box.get("1.0", "end").strip()
        if not text: return

        output_path = filedialog.asksaveasfilename(defaultextension=".mp3", filetypes=[("MP3", "*.mp3"), ("WAV", "*.wav")])
        if not output_path: return

        self._is_processing = True
        self._btn_generate.configure(state="disabled")
        self._btn_cancel.configure(state="normal")
        self._progress_bar.set(0)

        chunks = chunk_text(text)
        fmt = "mp3" if output_path.lower().endswith(".mp3") else "wav"

        threading.Thread(target=self._synthesize_and_export, args=(chunks, output_path, fmt, self._progress_bar, self._progress_label, self._reset_ui), daemon=True).start()

    # ─────────────────────────────────────────────
    #  SÍNTESE EM LOTE
    # ─────────────────────────────────────────────
    def _add_batch_files(self):
        files = filedialog.askopenfilenames(filetypes=[("Text/PDF", "*.txt *.pdf")])
        for f in files:
            if f not in self._batch_files:
                self._batch_files.append(f)
        self._update_batch_list()

    def _clear_batch_files(self):
        self._batch_files = []
        self._update_batch_list()

    def _update_batch_list(self):
        self._batch_list_box.configure(state="normal")
        self._batch_list_box.delete("1.0", "end")
        for f in self._batch_files:
            self._batch_list_box.insert("end", f + "\n")
        self._batch_list_box.configure(state="disabled")

    def _select_batch_output(self):
        folder = filedialog.askdirectory()
        if folder:
            self._batch_output_dir = folder
            self._batch_out_btn.configure(text=f"Saída: {Path(folder).name}")

    def _on_process_batch(self):
        if not self._active_engine or not self._voices:
            messagebox.showerror("Erro", "Selecione uma voz na aba Narrador primeiro.", parent=self)
            return
        if not self._batch_files:
            messagebox.showwarning("Aviso", "Adicione arquivos primeiro.", parent=self)
            return
        if not self._batch_output_dir:
            messagebox.showwarning("Aviso", "Selecione a pasta de saída.", parent=self)
            return

        self._is_processing = True
        self._btn_process_batch.configure(state="disabled")
        
        threading.Thread(target=self._process_batch_task, daemon=True).start()

    def _process_batch_task(self):
        from file_io.reader import read_file
        total = len(self._batch_files)
        
        for i, file_path in enumerate(self._batch_files):
            if not self._is_processing: break
            
            p_file = Path(file_path)
            self._batch_progress_lbl.configure(text=f"Processando ({i+1}/{total}): {p_file.name}")
            
            try:
                text = read_file(file_path)
                chunks = chunk_text(text)
                out_name = f"{p_file.stem}.mp3"
                out_path = os.path.join(self._batch_output_dir, out_name)
                
                # Executa sincronamente nesta thread worker
                self._synthesize_and_export(chunks, out_path, "mp3", self._batch_progress_bar, self._batch_progress_lbl)
            except Exception as e:
                logger.error(f"Erro ao processar {file_path}: {e}")

        self.after(0, lambda: self._batch_progress_lbl.configure(text="Lote concluído!"))
        self.after(0, lambda: self._btn_process_batch.configure(state="normal"))
        self._is_processing = False

    # ─────────────────────────────────────────────
    #  WORKER: SINTETIZAÇÃO
    # ─────────────────────────────────────────────
    def _synthesize_and_export(self, chunks, output_path: str, fmt: str, pbar=None, plabel=None, on_finish=None):
        import shutil
        import uuid
        audio_files = []
        total = len(chunks)
        
        try:
            for chunk in chunks:
                if not self._is_processing:
                    break
                if plabel: 
                    self.after(0, lambda idx=chunk.index+1: plabel.configure(text=f"Sintetizando {idx}/{total}...", text_color="gray"))

                audio_path = self._active_engine.synthesize(chunk.text)
                if audio_path and os.path.exists(audio_path):
                    # Copiar para arquivo temporário persistente para o exporter
                    tmp_wav = os.path.join(tempfile.gettempdir(), f"chunk_{uuid.uuid4().hex[:8]}.wav")
                    shutil.copy2(audio_path, tmp_wav)
                    audio_files.append(tmp_wav)
                else:
                    logger.warning(f"Síntese retornou vazio para o bloco {chunk.index + 1}.")
                
                if pbar:
                    self.after(0, lambda val=(chunk.index + 1) / total: pbar.set(val))

            if not self._is_processing or not audio_files:
                if plabel:
                    self.after(0, lambda: plabel.configure(text="Falha na síntese.", text_color="red"))
                if on_finish: self.after(0, on_finish)
                return

            if plabel: self.after(0, lambda: plabel.configure(text="Mesclando MP3...", text_color="gray"))
            merge_and_export(audio_files, output_path, format=fmt)
            if plabel: self.after(0, lambda: plabel.configure(text=f"Salvo: {Path(output_path).name}", text_color="#4CAF50"))

        except Exception as e:
            logger.error(f"Erro inesperado no worker de síntese: {e}", exc_info=True)
            if plabel:
                self.after(0, lambda: plabel.configure(text=f"Erro inesperado: {e}", text_color="red"))
        finally:
            # Limpeza dos WAVs temporários
            for af in audio_files:
                try:
                    if os.path.exists(af): os.remove(af)
                except: pass
            
            self._is_processing = False
            if on_finish: self.after(0, on_finish)

    def _on_cancel(self):
        self._is_processing = False
        self._progress_label.configure(text="Cancelado.", text_color="orange")
        self._reset_ui()

    def _reset_ui(self):
        self._btn_generate.configure(state="normal")
        self._btn_cancel.configure(state="disabled")

    def _check_gpu_availability(self):
        gpu_ok = PiperEngine.is_gpu_available()
        if gpu_ok:
            self._gpu_status_lbl.configure(text="GPU disponível (CUDA)!", text_color="#4CAF50")
            self._gpu_checkbox.grid()
            self._cuda_link_btn.grid()
            self._btn_install_gpu.pack(side="left", padx=5)
            self._btn_install_gpu.configure(state="disabled", text="DLLs Instaladas ✓")
            self._btn_uninstall_gpu.pack(side="left", padx=5)
            self._btn_uninstall_gpu.configure(state="normal", text="Remover DLLs da GPU")
        else:
            self._gpu_status_lbl.configure(text="Não instalado (CPU apenas)", text_color="orange")
            self._gpu_checkbox.grid_remove()
            self._cuda_link_btn.grid_remove()
            self._btn_install_gpu.pack(side="left", padx=5)
            self._btn_install_gpu.configure(state="normal", text="Baixar DLLs da GPU (CUDA)")
            self._btn_uninstall_gpu.pack(side="left", padx=5)
            self._btn_uninstall_gpu.configure(state="disabled", text="Remover DLLs da GPU")

    def _on_install_gpu(self):
        self._btn_install_gpu.configure(state="disabled")
        self._gpu_progress_lbl.configure(text="Conectando aos servidores...", text_color="orange")
        def task():
            def progress(pct, msg):
                self.after(0, lambda: self._gpu_progress_lbl.configure(text=f"{msg} ({int(pct*100)}%)"))
            success = PiperEngine.install_gpu_support(progress_callback=progress)
            if success:
                self.after(0, lambda: self._gpu_var.set(True))
                self.after(0, lambda: self._on_gpu_toggle())
                self.after(0, lambda: self._gpu_progress_lbl.configure(text="Suporte GPU ativado com sucesso!", text_color="#4CAF50"))
            else:
                self.after(0, lambda: self._gpu_progress_lbl.configure(text="Falha no download das DLLs.", text_color="red"))
                self.after(0, lambda: self._btn_install_gpu.configure(state="normal"))
            self.after(50, lambda: self._check_gpu_availability())
        threading.Thread(target=task, daemon=True).start()

    def _on_uninstall_gpu(self):
        if not messagebox.askyesno("Remover GPU", "Remover as DLLs da GPU? O app voltará a usar CPU.", parent=self):
            return
        self._btn_uninstall_gpu.configure(state="disabled")
        self._gpu_progress_lbl.configure(text="Removendo...", text_color="orange")
        def task():
            success = PiperEngine.uninstall_gpu_support()
            if success:
                self.after(0, lambda: self._gpu_var.set(False))
                self.after(0, lambda: self._on_gpu_toggle())
                self.after(0, lambda: self._gpu_progress_lbl.configure(text="DLLs removidas! Usando modo CPU.", text_color="#4CAF50"))
            else:
                self.after(0, lambda: self._gpu_progress_lbl.configure(text="Erro ao remover.", text_color="red"))
                self.after(0, lambda: self._btn_uninstall_gpu.configure(state="normal"))
            self.after(50, lambda: self._check_gpu_availability())
        threading.Thread(target=task, daemon=True).start()

    def _on_close(self):
        self._is_processing = False
        for engine in self._engines.values():
            try: engine.shutdown()
            except: pass
        self.destroy()
