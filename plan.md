# Planejamento de Projeto: Leitor de Textos Híbrido (Open-Source)

## 1. Visão Geral do Projeto
Desenvolvimento de um aplicativo desktop multiplataforma capaz de converter textos (documentos, PDFs, textos longos) em áudio sem limite de tempo ou custos. O foco é a eficiência e a execução local (offline), oferecendo duas abordagens de síntese de voz: um modo nativo ultra-leve e um modo baseado em Inteligência Artificial otimizado para processadores (CPU).

## 2. Casos de Uso
* **Design Educacional:** Produção de materiais didáticos acessíveis em áudio para alunos e integração com ambientes virtuais de aprendizagem.
* **Projetos Audiovisuais:** Criação de locuções base para prototipagem de vídeos, tutoriais ou materiais de treinamento.
* **Consumo Pessoal:** Leitura contínua de artigos longos, teses e livros sem depender de internet.

## 3. Arquitetura do Sistema

### 3.1. Motor 1: Modo Nativo (Zero dependências externas)
* **Tecnologia:** Uso das APIs de acessibilidade do próprio sistema operacional.
* **Windows:** SAPI5 (Windows.Media.SpeechSynthesis)
* **macOS:** NSSpeechSynthesizer
* **Linux:** eSpeak-NG / Speech-Dispatcher
* **Integração:** Biblioteca `pyttsx3` (Python) para comunicação direta com as APIs, ou bindings diretos se usar linguagens de baixo nível.

### 3.2. Motor 2: Modo IA Leve (Processamento em CPU)
* **Tecnologia:** Piper TTS ou Sherpa-ONNX.
* **Vantagem:** Utiliza modelos acústicos em formato `.onnx` que são extremamente rápidos e dispensam o uso de placas de vídeo (GPU).
* **Oportunidade Técnica:** O Piper é desenvolvido nativamente em **C++** e lida com processamento de buffers de áudio de baixo nível e otimização lógica. Interagir com o código-fonte dele, ou escrever um *wrapper* customizado em C++ para o aplicativo, pode ser um excelente projeto prático para avançar no entendimento de linguagens compiladas e lógica de hardware.

### 3.3. Interface Gráfica (GUI)
* **Linguagem Principal:** Python
* **Framework:** PySide6 (Qt) ou CustomTkinter.
* **Design:** Interface enxuta, priorizando a caixa de texto, lista de vozes e os controles de reprodução (Play, Pause, Stop).

## 4. Funcionalidades Principais (MVP)
1. **Importador de Texto:** Entrada de texto manual ou carregamento de arquivos estruturados (ex: `.txt`, `.pdf`).
2. **Chunking Inteligente:** Divisão matemática do texto em pequenos blocos (parágrafos ou frases). Em vez de processar 50 páginas de uma vez, o app processa o primeiro bloco, começa a tocar, e processa o resto em background.
3. **Controles de Leitura:** Tocar, pausar e interromper a fila de leitura.
4. **Exportação:** Juntar os blocos processados e salvar o resultado final em `.wav` ou `.mp3`.
5. **Seletor de Perfil:** Alternância instantânea entre "Voz do Sistema" e "Modelos de IA".

## 5. Cronograma de Desenvolvimento (Fases)

### Fase 1: Fundações e Modo Nativo
* [x] Configurar ambiente de desenvolvimento e versionamento.
* [x] Desenhar e programar a interface gráfica básica (CustomTkinter).
* [x] Implementar a chamada do motor nativo (pyttsx3) com abstração multiplataforma.
* [x] Estrutura de pastas e módulos criados (engines, audio, io, ui).
* [ ] Validar a estabilidade dos controles de áudio (Play/Pause/Stop) nativos.

### Fase 2: Integração da IA e Lógica de Chunking
* [ ] Preparar os binários do Piper TTS e baixar modelos em Português (Brasil).
* [ ] Escrever o módulo de integração: o app envia blocos de texto e recebe o arquivo de áudio temporário.
* [ ] Implementar a lógica de *chunking* (divisão por pontuação).
* [ ] Desenvolver a fila de reprodução contínua (tocar o áudio 1 enquanto gera o áudio 2).

### Fase 3: Polimento e Distribuição
* [ ] Implementar a função de mesclar arquivos gerados (merge) e exportar em formato de áudio comum.
* [ ] Refinar a interface, adicionando feedback visual (ex: highlight da frase atual sendo lida).
* [ ] Empacotar o projeto em um executável *standalone* (ex: PyInstaller) com tudo embutido para facilitar a distribuição.