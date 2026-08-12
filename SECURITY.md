# Security Policy

## Supported versions

TotaNNStudio jest obecnie projektem Alpha. Poprawki bezpieczeństwa otrzymuje najnowsza wersja z gałęzi `main`.

## Zgłaszanie podatności

Nie publikuj sekretów ani szczegółów umożliwiających wykorzystanie podatności w publicznym issue. Skorzystaj z prywatnego zgłoszenia bezpieczeństwa GitHub (`Security` → `Report a vulnerability`) albo skontaktuj się z właścicielem repozytorium.

W zgłoszeniu podaj:

- wersję/commit,
- kroki reprodukcji,
- wpływ problemu,
- proponowaną poprawkę, jeśli ją znasz.

## Zasady bezpiecznego wdrożenia

- ustaw losowy `TOTA_STUDIO_TOKEN` o wysokiej entropii,
- nie zapisuj tokenu w repozytorium ani obrazie kontenera,
- pozostaw serwer na `127.0.0.1`, chyba że przed nim działa HTTPS i kontrola dostępu,
- Quick Tunnel traktuj wyłącznie jako tymczasowy podgląd,
- uruchamiaj Studio jako osobny użytkownik bez uprawnień roota,
- ogranicz prawa katalogu modeli,
- aktualizuj `tota`, PyTorch oraz system operacyjny.

## Znane ograniczenia

Token aplikacyjny chroni API, ale wersja `0.1.0` nie zapewnia kont użytkowników, rotacji sesji, audytu działań ani rozproszonego limitowania żądań. Nie wystawiaj panelu jako wieloużytkownikowej usługi publicznej.
