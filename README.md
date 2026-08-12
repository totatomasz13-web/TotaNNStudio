# TotaNNStudio

Self-hosted panel WWW do projektowania, trenowania, zapisywania i testowania małych sieci neuronowych zbudowanych za pomocą biblioteki [`tota`](https://github.com/totatomasz13-web/tota).

> **Status:** wersja `0.2.0` (Alpha). Działający, lokalny MVP dla klasycznych sieci `tota.Layer` / `tota.Network`.

## Możliwości

- wizualne dodawanie i konfigurowanie warstw,
- aktywacje: `sigmoid`, `relu`, `tanh`, `linear`, `leaky_relu`, `step`,
- trening na wbudowanym zbiorze OR lub własnym JSON,
- prawdziwy trening przez `tota.Network.learn()`,
- predykcje przez `tota.Network.predict()`,
- zapis architektury, wag i biasów w lokalnym formacie JSON,
- biblioteka zapisanych modeli oraz ponowne predykcje,
- strona reklamowa i aplikacja dostarczane przez jeden serwer,
- lokalne API dostępne bez logowania na `127.0.0.1`.

## Wymagania

- Python 3.10 lub nowszy,
- `tota >= 1.0.1, < 2`,
- system obsługiwany przez PyTorch.

Klasyczne `tota.Network` działa obecnie na **CPU**. Obsługa GPU/CUDA znajduje się na roadmapie i nie jest przedstawiana jako aktywna funkcja wersji `0.2.0`.

## Instalacja jedną komendą

```bash
curl -fsSL https://raw.githubusercontent.com/totatomasz13-web/TotaNNStudio/main/install.sh | bash
```

Uruchom:

```bash
$HOME/.local/bin/totannstudio
```

Domyślny adres:

```text
http://127.0.0.1:4173/
http://127.0.0.1:4173/studio/
```

Możesz zmienić ustawienia zmiennymi:

```bash
export TOTA_STUDIO_HOST=127.0.0.1
export TOTA_STUDIO_PORT=4173
export TOTA_MODELS_DIR=/var/lib/totannstudio/models
export TOTA_MARKETING_DIR=/opcjonalna/ścieżka/strony
```

## Cloudflare Quick Tunnel

Do tymczasowego podglądu bez otwierania portu:

```bash
cloudflared tunnel --url http://127.0.0.1:4173 --no-autoupdate
```

Quick Tunnel nie gwarantuje stałego adresu ani dostępności. **Panel nie ma logowania**, dlatego nie wystawiaj go publicznie bez zewnętrznego uwierzytelniania w Cloudflare Access lub reverse proxy.

## Format własnego datasetu

Dla sieci z `input_size = 2`:

```json
[
  {"input": [0, 0], "target": 0},
  {"input": [0, 1], "target": 1},
  {"input": [1, 0], "target": 1},
  {"input": [1, 1], "target": 1}
]
```

Każdy `input` musi mieć dokładnie `input_size` wartości liczbowych. Wartości muszą być skończone (`NaN` i `Infinity` są odrzucane).

## Limity bezpieczeństwa MVP

- maksymalnie 5000 epok,
- maksymalnie 1000 próbek,
- maksymalnie 10 warstw,
- maksymalnie 512 neuronów w warstwie,
- ostatnia warstwa musi mieć jeden neuron,
- maksymalnie jeden trening jednocześnie,
- maksymalny rozmiar żądania: 1 MB,
- timeout bezczynnego połączenia HTTP: 15 sekund,
- maksymalnie 16 równocześnie obsługiwanych połączeń HTTP,
- bezwzględna wartość danych wejściowych i targetu: maksymalnie 1 000 000,
- łączny budżet pracy: maksymalnie 2 000 000 operacji `parametry × próbki × epoki`,
- serwer domyślnie nasłuchuje wyłącznie na `127.0.0.1`.

## Demo terminalowe

```bash
python main.py demo
```

Trenuje model OR przez bibliotekę `tota` i zapisuje go w `models/logic-or.tota.json`.

## Testy

```bash
python -m unittest discover -s tests -v
node --check totannstudio/web/app.js
python -m compileall -q totannstudio main.py
```

## Struktura

```text
TotaNNStudio/
├── totannstudio/
│   ├── studio.py       # konfiguracja, trening, predykcja, serializacja
│   ├── service.py      # walidacja i bezpieczne limity
│   ├── server.py       # serwer HTTP i chronione API
│   ├── web/            # właściwy panel aplikacji
│   └── marketing/      # strona reklamowa
├── tests/
├── models/             # lokalne modele (ignorowane przez Git)
├── main.py
└── pyproject.toml
```

## API

| Metoda | Endpoint | Dostęp | Opis |
|---|---|---|---|
| `GET` | `/api/health` | lokalny | Stan silnika i wersja `tota` |
| `GET` | `/api/models` | lokalny | Lista lokalnych modeli |
| `POST` | `/api/train` | lokalny | Trening i zapis modelu |
| `POST` | `/api/models/{id}/predict` | lokalny | Predykcja zapisanym modelem |

## Zakres wersji 0.2.0

To nie jest jeszcze system produkcyjny do wielogodzinnych treningów. Brakuje trwałej kolejki zadań, wznowienia po restarcie, bazy eksperymentów, strumieniowania loss per epoka, wielu użytkowników i kontroli zasobów systemowych. Funkcje Transformera biblioteki `tota` pozostają **BETA** i nie są jeszcze podłączone do kreatora klasycznych sieci.

## Licencja

MIT — zobacz [`LICENSE`](LICENSE).
