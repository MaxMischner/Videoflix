# Videoflix Frontend Project

![Videoflix Logo](assets/icons/logo_icon.svg)

Dieses Projekt ist ein einfaches Frontend, das mit **Vanilla JavaScript** (reines JavaScript ohne Frameworks) erstellt wurde. Es wurde speziell entwickelt, um Schülern der **Developer Akademie** mit Backend-Erfahrung den Einstieg in kleinere Frontend-Anpassungen zu erleichtern.

---

## Voraussetzungen

- Du brauchst ein mit Docker-Desktop erstelltes Django-Backend (Videoflix), dass **nicht** in diesem Projekt enthalten ist.
- Das Backend muss **JWT-Authentifizierung** mit **HttpOnly-Cookies** unterstützen. Das bedeutet:
  - Die Login-Response muss das JWT-Access-Token als HttpOnly-Cookie setzen.
  - Anfragen an geschützte Routen müssen über diesen Cookie authentifiziert werden.
  - Das Frontend hat keinen direkten Zugriff auf das Token (z.B. kein localStorage oder Authorization-Header).
  - Stelle sicher, dass dein Backend Cross-Origin-Anfragen (CORS) korrekt für das lokale Frontend erlaubt.
- Visual Studio Code mit der **Live Server**-Erweiterung oder eine ähnliche Möglichkeit, die `index.html` auf oberster Ebene lokal im Browser zu starten.
- Du brauchst an den Dateien grundsätzlich **nichts** ändern.
---

## Nutzung

1. Stelle sicher, dass das Backend `Videoflix` läuft.
2. Öffne dieses Projekt in **Visual Studio Code**.
3. Rechtsklicke auf die Datei `index.html` auf oberster Ebene und wähle **Open with Live Server**, um das Projekt zu starten.

---

## Ziel des Projekts

Dieses Frontend wurde bewusst mit **Vanilla JavaScript** erstellt, um die folgenden Ziele zu erreichen:

- **Einfacher Einstieg**: Durch den Verzicht auf Frameworks wie React oder Angular bleibt der Code leicht verständlich und nachvollziehbar auch bei wenig Frontend-Erfahrung.
- **Lernen durch Anpassung**: Schüler können den Code anpassen, um kleine Änderungen vorzunehmen und Frontend-Konzepte besser zu verstehen.
- **Backend-Erweiterung**: Das Projekt lässt sich einfach an das bestehende Django-Backend `Videoflix` anbinden.

---

## Hinweis

Dieses Projekt ist **ausschließlich für Schüler der Developer Akademie** gedacht und nicht zur freien Nutzung oder Weitergabe freigegeben.
Im Ordner `EmailTemplates_Backend` findest du die **Vorlagen** für das erstellen der **E-Mails für das Backend**.

---

## JSDoc - ansehen

1. Navigiere in den Ordner `docs/jsdoc/`
2. Du kannst das Projekt öffnen mit Doppelklick auf `docs/jsdoc/index.html`, oder im Terminal
   Windows: `start docs/jsdoc/index.html`
   macOS: `open docs/jsdoc/index.html`
   Linux: `xdg-open docs/jsdoc/index.html` 
