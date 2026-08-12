# 🎙️ SimpleNarrator

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python Version" />
  <img src="https://img.shields.io/badge/UI-CustomTkinter-blueviolet?style=for-the-badge" alt="CustomTkinter" />
  <img src="https://img.shields.io/badge/TTS-Native%20%7C%20Piper%20IA-success?style=for-the-badge" alt="TTS Engine" />
  <img src="https://img.shields.io/badge/Execution-100%25%20Offline-orange?style=for-the-badge" alt="100% Offline" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License" />
</p>

---

**SimpleNarrator** é um aplicativo desktop multiplataforma e open-source desenvolvido em Python para converter textos longos e documentos PDF em áudio (MP3/WAV) **100% offline**, sem limite de caracteres, custos de API ou dependência de conexão com a internet.

Possui uma interface moderna em tema escuro e suporta motores de síntese híbridos: desde o motor nativo leve do sistema operacional até modelos de voz neural de altíssima qualidade via **Piper TTS (IA)** com aceleração por CPU ou GPU (NVIDIA CUDA).

---

## 📸 Capturas de Tela

> *(Adicione capturas da interface gráfica aqui ao publicar no GitHub)*

---

## ✨ Recursos Principais

- 🤖 **Motores de Síntese Híbridos**:
  - **Motor Nativo (S.O.)**: Leve e instantâneo, utilizando APIs do sistema (SAPI5 no Windows, NSSpeech no macOS, eSpeak no Linux) via `pyttsx3`.
  - **Motor IA (Piper TTS)**: Vozes neurais locais ultra-realistas rodando sobre modelos ONNX com qualidade humana.
- 🚀 **Aceleração por Hardware (GPU CUDA)**: Opção de alternar entre CPU e GPU NVIDIA para sintetização ultrarrápida de grandes volumes de texto.
- 📥 **Gerenciador de Modelos Integrado**: Baixe e instale modelos de voz de diversos idiomas (incluindo PT-BR) diretamente pela interface gráfica, integrando com o repositório Hugging Face.
- 📚 **Processamento em Lote (Batch)**: Converta pastas com múltiplos livros, artigos e documentos `.txt` ou `.pdf` de forma automatizada para MP3.
- 📄 **Leitor Inteligente de PDF e TXT**:
  - Extração de PDF via `PyMuPDF` (`fitz`), removendo automaticamente cabeçalhos e rodapés para evitar leituras repetitivas.
  - Leitura de arquivos `.txt` com detecção automática de codificação de texto (UTF-8, Latin-1, CP1252).
- ✂️ **Chunking Inteligente**: Divisão matemática do texto em parágrafos e frases (até 500 caracteres) garantindo síntese fluida e sem estouro de memória em documentos extensos.
- 🎛️ **Controles de Áudio**: Ajuste dinâmico de velocidade de leitura ($0.5\times$ a $2.0\times$) e volume/tom.
- 🎵 **Exportação MP3 de Alta Qualidade**: Conversão e mesclagem direta de chunks de áudio utilizando `ffmpeg` nativo (192 kbps, libmp3lame).

---

## 🛠️ Stack Técnica

- **Linguagem**: Python 3.10+ (compatível com Python 3.14)
- **Interface Gráfica**: [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)
- **Motores TTS**: `pyttsx3` (SAPI5/NSSpeech/eSpeak) & `piper-tts` (ONNX Runtime)
- **Manipulação de PDF**: `PyMuPDF` (`fitz`)
- **Encoder de Áudio**: `ffmpeg` (via subprocess)
- **HTTP / Download Manager**: `requests`

---

## 📋 Pré-requisitos

Antes de instalar e rodar o SimpleNarrator, certifique-se de ter os seguintes itens instalados no seu sistema:

### 1. Python 3.10 ou superior
Verifique a versão instalada no seu terminal:
```bash
python --version
```

### 2. FFmpeg (Obrigatório para exportação MP3)
O FFmpeg é necessário para mesclar e converter os arquivos de áudio temporários em MP3.

- **Windows (via WinGet ou Chocolatey)**:
  ```powershell
  winget install Gyan.FFmpeg
  ```
  *ou*
  ```powershell
  choco install ffmpeg
  ```
- **Linux (Ubuntu/Debian)**:
  ```bash
  sudo apt update && sudo apt install ffmpeg
  ```
- **macOS (via Homebrew)**:
  ```bash
  brew install ffmpeg
  ```

> [!IMPORTANT]
> Certifique-se de que o comando `ffmpeg` esteja acessível no **PATH** do seu sistema. Teste executando `ffmpeg -version` no terminal.

### 3. *(Opcional)* Aceleração por GPU NVIDIA CUDA
Se deseja usar aceleração por GPU no motor Piper TTS, certifique-se de ter os drivers NVIDIA atualizados e o Toolkit CUDA instalado. Você pode baixar em:
👉 [NVIDIA CUDA Downloads](https://developer.nvidia.com/cuda-downloads)

---

## 📦 Instalação

### 1. Clonar o Repositório
```bash
git clone https://github.com/redmagikarp13/SimpleNarrator.git
cd SimpleNarrator
```

### 2. Criar e Ativar um Ambiente Virtual (Recomendado)

- **Windows (PowerShell)**:
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```

- **Linux / macOS**:
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### 3. Instalar as Dependências
```bash
pip install -r requirements.txt
```

---

## 🚀 Como Usar

Para iniciar a aplicação, execute no terminal ativado:
```bash
python main.py
```

---

### 📖 Guia da Interface Gráfica

A aplicação é dividida em **3 abas principais**:

```
 ┌─────────────────────────────────────────────────────────────┐
 │  SimpleNarrator                                             │
 │  ┌──────────────┬────────────────────────┬────────────────┐ │
 │  │   Narrador   │ Processamento em Lote  │ Modelos Piper  │ │
 │  └──────────────┴────────────────────────┴────────────────┘ │
 └─────────────────────────────────────────────────────────────┘
```

#### 1. Aba **Narrador** (Síntese Individual)
1. **Digite ou importe** seu texto na área central (ou clique em **Importar arquivo** para carregar um `.txt` ou `.pdf`).
2. Na barra lateral esquerda, configure:
   - **Motor**: Escolha entre `Nativo do S.O. (CPU)` ou `IA - Piper TTS (CPU/GPU)`.
   - **Aceleração GPU (CUDA)**: Marque a opção se possuir placa NVIDIA configurada.
   - **Voz**: Selecione a voz desejada na lista.
   - **Velocidade**: Ajuste a barra de velocidade de leitura ($0.5\times$ a $2.0\times$).
3. Clique no botão **Gerar MP3**, escolha a pasta e o nome do arquivo final.
4. Acompanhe o progresso em tempo real pela barra de status.

---

#### 2. Aba **Processamento em Lote**
Perfeito para converter coleções inteiras de arquivos de uma só vez:
1. Defina previamente a voz desejada na aba **Narrador**.
2. Clique em **+ Adicionar Arquivos (TXT/PDF)** para selecionar múltiplos documentos.
3. Clique em **Pasta de Saída** para escolher onde os MP3s serão salvos.
4. Clique em **Processar Lote**. O aplicativo processará cada documento em fila de fundo, gerando um MP3 correspondente para cada arquivo.

---

#### 3. Aba **Modelos Piper** (Download de Vozes IA)
Gerencie e baixe vozes neurais diretamente da comunidade:
1. Clique em **Carregar Lista do Servidor** para atualizar o catálogo com centenas de vozes neurais disponíveis no Hugging Face (`rhasspy/piper-voices`).
2. As vozes em **Português do Brasil (`pt_BR`)** são exibidas automaticamente no topo da lista.
3. Clique no botão **Baixar** ao lado do modelo desejado (ex: `pt_BR-faber-medium`).
4. Assim que o download for concluído, a nova voz estará imediatamente disponível para uso na aba **Narrador**.
5. Se não precisar mais de uma voz, clique no botão **Excluir** para liberar espaço no disco.

---

## 📂 Estrutura do Projeto

```text
SimpleNarrator/
├── main.py                  # Ponto de entrada da aplicação
├── main.spec                # Arquivo de configuração PyInstaller para compilação
├── requirements.txt         # Lista de dependências Python
├── CONTEXT.md               # Documentação técnica de contexto interno
├── plan.md                  # Roadmap e etapas de desenvolvimento
│
├── engines/                 # Arquitetura dos motores de síntese de voz
│   ├── base_engine.py       # Classe abstrata BaseEngine e estruturas de dados
│   ├── native_engine.py     # Implementação do motor nativo via pyttsx3
│   └── piper_engine.py      # Implementação do motor neural via Piper TTS (ONNX)
│
├── file_io/                 # Manipulação de arquivos de entrada e saída
│   ├── reader.py            # Leitor e extrator para arquivos .txt e .pdf
│   └── exporter.py          # Mesclagem de chunks WAV e codificação MP3 via ffmpeg
│
├── audio/                   # Processamento e segmentação de áudio
│   ├── chunker.py           # Divisão inteligente de textos longos por pontuação
│   └── player.py            # Módulo de áudio/player (reprodução local)
│
├── ui/                      # Interface Gráfica CustomTkinter
│   └── app.py               # Classe NarratorApp (janela principal e abas)
│
└── models/                  # Diretório local para armazenamento de modelos ONNX
    ├── downloader.py        # Gerenciador de download de vozes (Hugging Face)
    └── README.md            # Instruções sobre modelos Piper
```

---

## 🛠️ Gerando o Executável Standalone (.exe)

O projeto já inclui um arquivo de especificação PyInstaller (`main.spec`) pré-configurado com os hooks do CustomTkinter e dependências ocultas.

Para compilar o projeto em um arquivo executável único no Windows:

1. Instale o PyInstaller:
   ```bash
   pip install pyinstaller
   ```
2. Execute a compilação utilizando o `main.spec`:
   ```bash
   pyinstaller main.spec
   ```
3. O executável final será gerado no diretório `dist/SimpleNarrator.exe`.

> [!NOTE]
> Se o `ffmpeg` estiver instalado na máquina onde a compilação é realizada, o PyInstaller incluirá automaticamente o binário do FFmpeg dentro do executável gerado, permitindo que os usuários finais utilizem a exportação MP3 sem precisar instalar o FFmpeg separadamente.

---

## ❓ Solução de Problemas (Troubleshooting)

<details>
<summary><b>1. Erro ao exportar para MP3: "ffmpeg falhou" ou "ffmpeg não encontrado"</b></summary>
<br>

- Certifique-se de que o `ffmpeg` está instalado e adicione o caminho do executável `ffmpeg.exe` à variável de ambiente `PATH` do Windows/Linux.
- Abra o terminal e digite `ffmpeg -version`. Se o comando retornar erro, reinstale o FFmpeg via WinGet/Chocolatey ou adicione o caminho manualmente.
</details>

<details>
<summary><b>2. O Piper TTS falha ao carregar a voz no modo GPU (CUDA)</b></summary>
<br>

- Se a caixa "Aceleração GPU (CUDA)" estiver marcada mas sua máquina não possuir suporte CUDA ou bibliotecas ONNX GPU instaladas, o SimpleNarrator fará um **fallback automático para CPU** com segurança.
- Para habilitar aceleração real via GPU, instale os drivers da NVIDIA e certifique-se de possuir a versão com suporte a CUDA do `onnxruntime-gpu`.
</details>

<details>
<summary><b>3. O texto extraído do PDF contém números de página ou cabeçalhos repetidos</b></summary>
<br>

- O leitor interno de PDF (`file_io/reader.py`) ignora automaticamente a margem de 10% no topo e 10% no rodapé de cada página para desconsiderar cabeçalhos e números de páginas repetidos em artigos e livros.
</details>

---

## 🤝 Contribuição

Contribuições são super vindas! Sinta-se à vontade para:
1. Dar um **Fork** no projeto.
2. Criar uma branch para sua feature (`git checkout -b feature/NovaFeature`).
3. Fazer commit das suas alterações (`git commit -m 'Adiciona NovaFeature'`).
4. Fazer Push para a branch (`git push origin feature/NovaFeature`).
5. Abrir um **Pull Request**.

---

## 📄 Licença

Este projeto está sob a licença **MIT**. Veja o arquivo `LICENSE` para mais detalhes.

---

<p align="center">
  Desenvolvido por <a href="https://github.com/redmagikarp13">redmagikarp13</a> com 💙 em Python.
</p>
