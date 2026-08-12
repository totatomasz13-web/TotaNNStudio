# Contributing

Dziękujemy za zainteresowanie TotaNNStudio.

## Środowisko lokalne

```bash
git clone https://github.com/totatomasz13-web/TotaNNStudio.git
cd TotaNNStudio
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

## Przed zmianą

1. Utwórz test opisujący oczekiwane zachowanie.
2. Uruchom test i potwierdź, że nie przechodzi z właściwego powodu.
3. Dodaj najmniejszą implementację.
4. Uruchom cały zestaw testów.

```bash
python -m unittest discover -s tests -v
node --check totannstudio/web/app.js
python -m compileall -q totannstudio main.py
```

Nie dodawaj sekretów, plików `.studio-token`, datasetów użytkownika ani wytrenowanych modeli do commita.

Funkcje Transformera biblioteki `tota` muszą pozostać wyraźnie oznaczone jako **BETA**.
