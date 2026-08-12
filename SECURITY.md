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

- pozostaw serwer na `127.0.0.1`,
- panel nie ma logowania; dostęp z sieci wystawiaj wyłącznie przez HTTPS i zewnętrzną kontrolę dostępu, np. Cloudflare Access,
- nie używaj publicznego Quick Tunnel bez dodatkowego uwierzytelniania,
- uruchamiaj Studio jako osobny użytkownik bez uprawnień roota,
- ogranicz prawa katalogu modeli,
- aktualizuj `tota`, PyTorch oraz system operacyjny.

## Znane ograniczenia

Wersja `0.2.1` nie ma logowania, kont użytkowników, audytu działań ani rozproszonego limitowania żądań. Nie wystawiaj panelu jako niezabezpieczonej usługi publicznej.
