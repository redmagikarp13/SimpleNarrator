# Documentação do Projeto — SimpleNarrator

## Visão Geral
Aplicativo desktop multiplataforma para converter texto em áudio (TTS) sem limite de tempo ou caracteres.
Interface em CustomTkinter com tema escuro, motores de síntese híbridos (Nativo e Piper TTS IA) e exportação direta para MP3 via `ffmpeg`.

## Stack Técnica
- **Python 3.10+** (Testado em Python 3.14)
- **CustomTkinter** — interface gráfica (tema escuro com abas: Narrador, Processamento em Lote, Modelos Piper)
- **pyttsx3** — motor nativo (SAPI5 no Windows, NSSpeech no macOS, eSpeak no Linux)
- **Piper TTS (`piper-tts`)** — motor IA baseado em modelos ONNX com suporte a CPU e GPU (CUDA)
- **PyMuPDF (`fitz`)** — extração inteligente de texto de PDFs com descarte automático de cabeçalhos/rodapés
- **ffmpeg** — conversão e mesclagem de chunks WAV → MP3 via subprocess
- **requests** — download automático de modelos neurais do Hugging Face (`rhasspy/piper-voices`)
- **PyInstaller** — empacotamento standalone via `main.spec`

## Estrutura de Pastas
```text
SimpleNarrator/
├── main.py                  # Entry point (python main.py)
├── main.spec                # Configuração de build PyInstaller
├── requirements.txt         # Dependências Python
├── README.md                # Documentação principal do repositório no GitHub
├── CONTEXT.md               # Contexto técnico interno
├── plan.md                  # Planejamento original do projeto
├── engines/                 # Motores de TTS
│   ├── base_engine.py       # Interface abstrata (BaseEngine, VoiceInfo, EngineState)
│   ├── native_engine.py     # Motor nativo via pyttsx3 (SAPI5/NSSpeech/eSpeak)
│   └── piper_engine.py      # Motor Piper TTS (ONNX Runtime, CPU/CUDA)
├── audio/                   # Módulos de áudio
│   ├── player.py            # Player com fila (para uso futuro / streaming)
│   └── chunker.py           # Divisão inteligente de texto em blocos de até 500 caracteres
├── file_io/                 # Importação e exportação
│   ├── reader.py            # Leitor TXT (detecção de encoding) e PDF (PyMuPDF)
│   └── exporter.py          # Merge WAVs + exportação MP3 (192kbps) via ffmpeg subprocess
├── ui/                      # Interface gráfica
│   └── app.py               # NarratorApp (CustomTkinter TabView)
└── models/                  # Pasta de armazenamento dos modelos Piper ONNX
    ├── downloader.py        # ModelDownloader (gerenciador de download do Hugging Face)
    └── README.md            # Instruções dos modelos
```

## Fluxo de Funcionamento
1. Usuário escreve ou importa texto (TXT/PDF) na interface (ou seleciona lista de arquivos na aba Lote).
2. Seleciona o motor (`Nativo` ou `Piper IA`), ativa aceleração por GPU se desejado e escolhe a voz.
3. Ajusta velocidade ($0.5\times$ a $2.0\times$) e tom/volume.
4. Clica em **Gerar MP3** → seleciona o destino.
5. O texto é fatiado por `chunk_text()` em blocos por parágrafos/pontuações ($\le 500$ chars).
6. Cada bloco é sintetizado para WAV temporário via motor selecionado.
7. `file_io/exporter.py` mescla os WAVs em um único arquivo e invoca `ffmpeg` para codificar em MP3 (192kbps).
8. Arquivo final é salvo e arquivos temporários são limpos.

## Decisões Arquiteturais

### Motor Piper TTS e Gerenciador de Download
- O `PiperEngine` lê os arquivos `.onnx` e `.onnx.json` salvos na pasta `models/`.
- O `ModelDownloader` consome a API do Hugging Face (`rhasspy/piper-voices`) para buscar, listar e baixar modelos em tempo de execução.
- Suporta fallback gracioso para CPU caso a execução por GPU CUDA falhe ou a máquina não possua a runtime necessária.

### Exportação direta para MP3 via FFmpeg
- Evita limitações de bibliotecas como `pydub` (que dependiam de `audioop`, removido no Python 3.14).
- Execução direta via `subprocess.run(["ffmpeg", "-y", "-i", wav_path, "-codec:a", "libmp3lame", ...])`.

### Isolamento de cabeçalhos e rodapés em PDFs
- Em `file_io/reader.py`, o PyMuPDF delimita a caixa de corte da página ignorando os $10\%$ superiores e $10\%$ inferiores (`fitz.Rect`), removendo números de página e cabeçalhos repetitivos.

## Como Rodar e Testar

```bash
# Instalar dependências
pip install -r requirements.txt

# Executar aplicação
python main.py

# Compilar executável
pyinstaller main.spec
```

## Requisitos para GPU (CUDA)

Para usar aceleração por GPU no motor Piper TTS no Windows:

1. **CUDA Toolkit** instalado (ex: 13.3) — [download NVIDIA](https://developer.nvidia.com/cuda-downloads)
2. **onnxruntime-gpu** e **nvidia-cudnn-cu12** instalados via `requirements.txt`
3. As DLLs da cuDNN/cuBLAS são registradas automaticamente pelo código em `_register_nvidia_dll_paths()`

**Nota:** As dependências de GPU são condicionais por plataforma no `requirements.txt`:
- Windows: `onnxruntime-gpu` + `nvidia-cudnn-cu12`
- Linux/macOS: `onnxruntime` (CPU apenas)

## Correções Recentes (v1.0.13)

### Estabilidade na Síntese
- **Tratamento de exceção no worker** — erros em chunks individuais não travam mais a aplicação
- **Fallback automático CPU** — se a GPU falhar, o motor recarrega a voz em CPU automaticamente
- **Thread safety** — lock (`threading.Lock`) protege acesso concorrente ao ONNX Runtime
- **Fix de file handle** — WAV files agora usam `try/finally` para garantir fechamento

### Suporte a GPU no Execável PyInstaller
- **Coleta de DLLs NVIDIA** — `main.spec` agora coleta `nvidia.cudnn`, `nvidia.cublas`, `nvidia.cuda_nvrtc`
- **Hidden imports** — pacotes `nvidia.*` adicionados para detecção pelo PyInstaller
- **Registro multi-ambiente** — `_register_nvidia_dll_paths()` funciona tanto em desenvolvimento quanto no bundle PyInstaller (via `sys._MEIPASS`)

### Build Multiplataforma
- **Dependências condicionais** — `requirements.txt` usa marcadores `sys_platform` para evitar erros no CI Ubuntu/macOS
- **Workflow GitHub Actions** — release automática via tag `v*` (ex: `v1.0.13`)
