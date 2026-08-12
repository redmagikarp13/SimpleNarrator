# Documentação do Projeto — SimpleNarrator

## Visão Geral
Aplicativo desktop multiplataforma para converter texto em áudio (TTS) sem limite de tempo.
Interface em CustomTkinter, dois motores de síntese e exportação direta para MP3 via ffmpeg.

## Stack Técnica
- **Python 3.14** (ambiente do usuário)
- **CustomTkinter** — interface gráfica (tema escuro)
- **pyttsx3** — motor nativo (SAPI5 no Windows, NSSpeech no macOS, eSpeak no Linux)
- **Piper TTS** — motor IA com modelos ONNX (stub, implementar na Fase 2)
- **ffmpeg** — conversão WAV→MP3 via subprocess (já instalado no sistema)
- **sounddevice + soundfile + numpy** — reprodução de áudio (para uso futuro)
- **PyPDF2** — extração de texto de PDFs

## Estrutura de Pastas
```
SimpleNarrator/
├── main.py                  # Entry point (python main.py)
├── requirements.txt         # Dependências Python
├── plan.md                  # Planejamento original do projeto
├── __init__.py
├── engines/                 # Motores de TTS
│   ├── __init__.py
│   ├── base_engine.py       # Interface abstrata (BaseEngine, VoiceInfo, EngineState)
│   ├── native_engine.py     # Motor nativo via pyttsx3
│   └── piper_engine.py      # Motor Piper TTS (STUB — Fase 2)
├── audio/                   # Módulos de áudio
│   ├── __init__.py
│   ├── player.py            # Player com fila/play/pause/stop (para uso futuro)
│   └── chunker.py           # Divisão inteligente de texto em blocos
├── file_io/                 # Importação e exportação (NÃO usar "io" — conflita com built-in)
│   ├── __init__.py
│   ├── reader.py            # Leitor TXT (detecção de encoding) e PDF (PyPDF2)
│   └── exporter.py          # Merge WAVs + export MP3 via ffmpeg subprocess
├── ui/                      # Interface gráfica
│   ├── __init__.py
│   └── app.py               # NarratorApp — janela principal CustomTkinter
└── models/                  # Pasta para modelos Piper ONNX (Fase 2)
    └── README.md            # Instruções de download dos modelos
```

## Fluxo Atual (Funcionando)
1. Usuário escreve ou importa texto (TXT/PDF) na interface
2. Seleciona motor (Nativo) e voz na sidebar
3. Ajusta velocidade e tom
4. Clica em **Gerar MP3** → escolhe onde salvar
5. Texto é dividido em chunks (parágrafos → frases → vírgulas, máx 500 chars)
6. Cada chunk é sintetizado em WAV temporário (nomes únicos via uuid)
7. WAVs são mesclados em um único arquivo
8. ffmpeg converte WAV mesclado → MP3 (192kbps, libmp3lame)
9. Arquivo final é salvo no caminho escolhido

## Decisões Importantes

### Exportação direta para MP3 (sem player em tempo real)
- O usuário preferiu simplificar: em vez de play/pause/stop com streaming de áudio,
  o app sintetiza tudo e exporta direto como MP3.
- O módulo `audio/player.py` existe mas não é usado atualmente.
  Pode ser útil no futuro para preview ou reprodução em tempo real.

### pyttsx3: bug do runAndWait()
- **Problema conhecido**: `runAndWait()` trava na segunda chamada em Windows
  (o COM apartment do SAPI5 entra em estado inválido).
- **Solução aplicada**: usar `startLoop(False)` + `iterate()` + `endLoop()`
  em vez de `runAndWait()`. Funciona corretamente para múltiplas sínteses.

### ffmpeg direto em vez de pydub
- `pydub` não funciona com Python 3.14 (módulo `audioop` foi removido).
- O usuário já tem ffmpeg instalado no sistema.
- Conversão WAV→MP3 feita via `subprocess.run(["ffmpeg", ...])` — mais confiável.

### Pasta "file_io" em vez de "io"
- Python tem módulo built-in `io`, então `from io.reader import ...` falha.
- A pasta foi renomeada de `io/` para `file_io/`.

### Cada chunk gera WAV com nome único
- O `native_engine.synthesize()` gera arquivos com UUID no nome
  (`sn_native_<uuid>.wav`) para evitar sobrescrita entre chunks.
- O `app.py` faz `shutil.copy2()` para caminho estável antes do próximo chunk.

## Vozes Disponíveis (Windows do usuário)
- **Microsoft Maria Desktop - Portuguese(Brazil)** (pt-BR) ← selecionada por padrão
- Microsoft Zira Desktop - English (United States) (en-US)

## Bugs Conhecidos / Limitações
1. **Piper TTS** é apenas um stub — não sintetiza nada ainda (Fase 2)
2. **pyttsx3 pitch**: não existe controle real de pitch via pyttsx3;
   o slider atualmente controla volume como proxy
3. **Exportação MP3**: depende do ffmpeg estar no PATH do sistema

## Próximos Passos (Fase 2)
- [ ] Baixar modelo Piper PT-BR (`pt_BR-faber-medium.onnx`)
- [ ] Implementar `piper_engine.py` com sintetização real
- [ ] Testar exportação com Piper (formato de saída pode ser diferente)
- [ ] Adicionar highlight da frase atual sendo lida (Fase 3)
- [ ] Atalhos de teclado (Space = play/pause) (Fase 3)
- [ ] Empacotar em executável standalone via PyInstaller (Fase 3)

## Como Rodar
```bash
# Instalar dependências
pip install -r requirements.txt

# Rodar o app
python main.py
```

## Dependências (requirements.txt)
```
customtkinter>=5.2.0
pyttsx3>=2.90
sounddevice>=0.4.6
soundfile>=0.12.1
numpy>=1.24.0
PyPDF2>=3.0.0
```

## Ambiente do Usuário
- **OS**: Windows 26H2
- **Python**: 3.14
- **ffmpeg**: instalado via WinGet (`Gyan.FFmpeg`, versão 8.1.2)
- **Shell**: PowerShell (não suporta `&&`, usar `;` como separador)
