# Validierungsprotokoll und ausgeführte Prüfungen

Stand: 8. November 2026. Zu [Evaluationsbericht](CHART_ANALYSIS_EVALUATION.md).

## 1. Tatsächlich ausgeführt

| Prüfung | Umgebung / Daten | Ergebnis und Reichweite |
|---|---|---|
| Upstream-Suite | Unveränderter produktiver Code bei `8e9246b`; Windows, Python 3.12.10, isolierte venv; `.[dev,web,docs]` | **46 Tests bestanden**, eine Starlette/httpx-Deprecation-Warnung. Keine Live-Daten-/Modellprüfung. |
| Upstream-Linter | `ruff check .` vor Ergänzung der Evaluationsdateien | Bestanden. |
| Ergänzende Baseline-Probes | Synthetische Daten, kontrollierte Modellantworten; keine Netzabfragen oder Orders | RSI-Grenzfall, übersteuerbare Freigabe, fehlende deterministische PM-Sperre und unzureichende OHLCV-Validierung reproduziert. |
| Vergleich zweier Indikatorimplementierungen | Gleiche 320 synthetische OHLCV-Bars; atila-Python vs. moeuu-TypeScript aus fixierten Commits; Node 24.17.0 | SMA/EMA/RSI numerisch übereinstimmend; ATR-Konventionsabweichung erkannt. |
| Zeit- und Konsistenzprobes | Ein Präfix mit 200 Bars; MCP2-Splitter und Restart-Vergleich aus fixiertem Commit | **7 Smoke-Tests bestanden**, einschließlich Prefix-Invarianz der vier Indikatorreihen, Embargo-/Fold-Abstand und Erkennen geänderter historischer Werte. |

Indikatorvergleich, absolute Differenz:

| Reihe | Gemeinsame numerische Positionen | Größte Abweichung | Abweichende Null-/Warm-up-Positionen |
|---|---:|---:|---:|
| SMA20 | 301 | 5,684341886080802e-14 | 0 |
| EMA20 | 301 | 0 | 0 |
| RSI14 | 306 | 0 | 0 |
| ATR14 | 306 | 0,03204081632653066 | 1 |

Ursache der ATR-Abweichung: moeuu nimmt die erste High-Low-Range in den Seed auf und startet an Index 13; atila verwendet True Ranges ab dem zweiten Bar und startet an Index 14. Das ist eine zu vereinheitlichende Konvention, kein Nachweis einer allgemeinen Überlegenheit.

Die Smoke-Tests sind eigene, kleine Berechnungsprobes, **keine vollständig ausgeführten Upstream-Suiten** dieser MCP-Repositories. Es wurden noch keine realen historischen Match-Ergebnisse, Erkennungsquoten oder Out-of-Sample-Renditen gemessen. Für STUMPY, tslearn und TA-Lib liegt hier eine Code-/Dokumentationsprüfung vor, keine lokale Laufzeitabnahme.

## 2. Reproduktion der ausgeführten Prüfungen

Aus einem Checkout dieses Dokumentationsbranches, dessen produktiver Code unverändert dem dokumentierten Baseline-Commit entspricht:

```powershell
python -m venv .venv-evaluation
.\.venv-evaluation\Scripts\python.exe -m pip install -c docs/evaluation/evaluation-environment.txt -e ".[dev,web,docs]"
.\.venv-evaluation\Scripts\python.exe -m pytest
.\.venv-evaluation\Scripts\python.exe -m ruff check .
.\.venv-evaluation\Scripts\python.exe docs/evaluation/probes/baseline_probe.py
.\.venv-evaluation\Scripts\python.exe docs/evaluation/probes/compare_candidates.py
```

Für den Kandidatenvergleich muss Node 24.17 oder eine kompatible Node-24-Version mit TypeScript-Type-Stripping auf dem PATH liegen. Python lädt vier bereits geprüfte öffentliche Quelldateien aus unveränderlichen Git-Commits in ein temporäres Verzeichnis. SHA-256 wird gegen [source-lock.json](source-lock.json) geprüft. Anschließend laufen die isolierten Rechenprobes. Keine Projektdatei und keine Bibliotheksabhängigkeit der Anwendung wird verändert.

`baseline_probe.py` prüft absichtlich **den beobachteten fehlerhaften Ausgangszustand**. Erfolg bedeutet „Befund reproduziert“, nicht „Fehler behoben“. Nach einer später genehmigten Fehlerbehebung müssen die Probes in normale Sollverhalten-Regressionstests überführt werden.

`generate_fixture.py` konstruiert eine lineare Drift mit zwei Sinuskomponenten und wechselnden High-Low-Breiten. Das ist ein numerisches Vergleichsfixture, keine realistische Modellierung einer Marktverteilung. Es verwendet keine geheimen Seeds oder zufällige Datenauswahl.

## 3. Testdaten für den genehmigungspflichtigen PoC

### Manifest und Datenvertrag

Jeder Snapshot enthält:

- eindeutige Instrumentidentität mit Börse, Währung, Typ und gegebenenfalls Underlying;
- Quelle, Abrufzeit, Handelszeit-/Sessionkalender, Zeitzone, Interval und geschlossene Bars;
- Splits/Dividenden und Adjustment-Methode; Roh- und Adjusted-Reihe nicht still vermischen;
- erster/letzter Zeitstempel, Barzahl, Lücken, Duplikate, NaN, OHLC-Prüfung, Volumentyp;
- SHA-256 der Rohdatei, Parameterdatei, Bibliotheksversionen, Commit und Ergebnisdateien;
- bei Futures Rollregel/Kontrakt, bei Makro/News/Fundamentals Veröffentlichungs- und gegebenenfalls Revisionszeit.

Widersprüchliche OHLC-Werte können einen Schlusskurs nicht automatisch ungültig machen: Close-only-Verfahren dürfen einen separat validierten Schlusskurspräfix nutzen; Kerzen-/ATR-Muster brauchen vollständig gültige OHLC. Ungültige ältere Bereiche werden segmentiert, nicht pauschal mit jüngeren gültigen Bereichen verworfen. Fehlende historische Angaben werden nicht durch aktuelle Snapshots ersetzt.

### Umfang

Kleinster Daten-Pilot: drei Reihen, beispielsweise AAPL, JPM und GLD, Tagesdaten 2010–2025; mindestens zehn tatsächlich verfügbare Jahre. Auswahl und Zeitraum werden **vor** Ergebnisbetrachtung fixiert. Kostenfreie Quellen sind etwa verfügbare Yahoo/yfinance-Historien oder aus der vorhandenen Desktop-Verbindung rechtmäßig abrufbare Bars; die Bibliotheken selbst garantieren weder Datenverfügbarkeit noch börsenspezifische Historientiefe. Dieses Protokoll setzt keinen bezahlten TradingView-Account voraus.

Erweiterte Validierung: zusätzlich Small Caps, schwache/gescheiterte Titel soweit historisch verfügbar, europäische Handelsplätze, mehrere Sektoren und ein getrennt behandelter Rohstoff-/Indexfall. Historische Universen und Delistings sind bei freien Quellen ein offener Datenengpass. Ergebnisse eines heutigen Blue-Chip-Universums nicht auf alle Aktien verallgemeinern.

Mindestens Trend-, Range-, Crash-/Gap- und hohe/niedrige Volatilitätsfenster; Daily und ein eingefrorener 60-Minuten-/Weekly-Fall. Enthaltene Beispiele und schwierige Negativfälle werden vorab gelabelt. Dass diese Daten beschafft werden sollen, ist kein bereits erfolgter Datenabruf.

## 4. Qualität der numerischen und strukturellen Verfahren

### Indikatoren

- Golden Values für konstant, strikt steigend/fallend, Gaps, einen einzelnen Spike und reale eingefrorene Abschnitte.
- Vollständiger Warm-up, Startwert, ddof, Wilder-/EMA-Konvention und NaN-Verhalten festlegen.
- Identische Inputs für alle Kandidaten; nach harmonisierter Konvention relative/absolute Toleranz z. B. `1e-8 × max(1, |Referenz|)`.
- Nach Anhängen oder Verändern ausschließlich zukünftiger Bars bleiben bereits verfügbare Werte unverändert.
- Kein Runden vor Feature-/Signalberechnung; Rundung erst im Bericht.

### Marktstruktur und Formationen

Je Pattern mindestens klar positive, nahe negative und mehrdeutige Beispiele. Für erste Pilotabnahme vorgeschlagen: 20 deterministische Positiv-/Negativfixtures plus 100 verblindete, echte Ausschnitte mit zwei voneinander unabhängigen Annotatoren. Uneinigkeit dokumentieren, nicht automatisch den Detektor zum Maßstab erklären.

Metriken: ereignisbezogene Precision/Recall/F1, False Positives je 1.000 Bars, Treffer mit Preistoleranz in ATR und Zeittoleranz in Bars, Bestätigungsverzug und spätere Invalidierung. Überlappende Erkennungen derselben Formation zu einem Ereignis zusammenführen.

Eine Pilot-Präzision ≥0,80 und Recall ≥0,70 sind **vorgeschlagene Abnahmeziele**, keine gemessenen Werte. Bei zu geringer Annotator-Übereinstimmung zuerst die Regeldefinition korrigieren. Vor der Holdout-Auswertung diese Ziele und Toleranzen verbindlich einfrieren.

Bei Elliott-/Cup-/harmonischen Regeln getrennte experimentelle Kategorien. Keine Gesamttrefferquote bilden, die viele triviale Candle-Fälle mit wenigen komplexen Formationen vermischt.

### Repainting und Zeitverfügbarkeit

Für jeden historischen Cutoff die Engine erneut nur mit dem verfügbaren Präfix ausführen und gegen die damalige Ausgabe vergleichen. Das letzte unbestätigte Swing-Segment darf sich ändern; eine bestätigte Aussage braucht unverändertes `confirmed_at` und belegte Datenrevisionen.

Gezielt zukünftige Extrempunkte, Volumina und Kerzen verändern. Ein `MitigatedIndex` oder nachträglich gesetztes Pivotlabel darf nicht als damaliges Feature in Matching, Score oder Backtest landen. Der vorhandene Upstream-Test `test_backtest_no_lookahead` prüft lediglich Anfangsequity; das reicht für diese Anforderungen nicht.

## 5. Historische Matches und Out-of-Sample

1. Entwicklung 2010–2017, Parameterauswahl 2018–2020, Walk-forward-Auswertung 2021–2022, abschließender Holdout 2023–2025 als möglicher fester Plan. Keine Zufallssplits über Zeitpunkte.
2. Jedes Queryfenster endet am damaligen As-of. Kandidaten und deren vollständige Outcome-Horizonte enden davor. Das gilt auch für die Matrix-Profile-Nachbarsuche.
3. Ereignis- und Label-Fenster an Foldgrenzen purgen. Der Embargo-Abstand richtet sich nach Query-/Outcome-/Feature-Reichweite; nicht nur nach einer willkürlichen festen Barzahl. Höhere Timeframes anhand des tatsächlichen Schlusszeitpunkts behandeln.
4. Skalierung, Featureauswahl, Regimegrenzen, DTW-Band und k ausschließlich im jeweiligen Training bzw. vorgelagerten Tuning bestimmen. Testdaten nicht zum Bestimmen einer „guten“ Distanzschwelle benutzen.
5. Gleiche Queries für Feature-Distanz, MASS und DTW. Challenger erhalten identische vergangene Kandidaten und Outcome-Zeiten; sonst ist der Vergleich nicht fair.
6. Überlappende Treffer nach Ereignis und Marktphase clustern. Rohzahl und effektive unabhängige Ereigniszahl angeben. Konfidenzintervalle mit zeitlichem Block-/Cluster-Bootstrap statt IID-Standardfehlern.
7. Neben Median/Quantilen von Rendite, Exzessrendite, MAE/MFE: Anteil positiver Exzessrenditen, Ziele-vor-Invalidierung, Zeit bis Ziel und vollständige Fehlsignale. Fehlerhafte/fehlende Fenster getrennt zählen.
8. Regimegleiche Zufallsfenster, ein einfacher Momentum-/MA-/Dip-Ansatz sowie Buy-and-hold bei Strategieergebnissen sind Baselines. Alle getesteten Varianten und verworfenen Parameterfamilien protokollieren.
9. Mehrfachtests berücksichtigen: primäre Hypothese vorab festlegen; viele explorative Pattern-/Horizonvergleiche kennzeichnen und bei Schlussfolgerungen z. B. FDR-Kontrolle einsetzen.
10. Für eine behauptete Wahrscheinlichkeit Brier Score, Kalibrierkurve und Coverage prüfen; Kalibrator nur aus vorgelagerter Zeit lernen. LLM-Selbstkonfidenz wird nicht als Messwert verwendet.

Ein „prognostischer Mehrwert“ wird nur berichtet, wenn die vorab definierte Hauptmetrik im unangetasteten Holdout gegenüber der Baseline überzeugt und ihre Unsicherheit berücksichtigt ist. Andernfalls kann ein Verfahren weiterhin ein korrektes **beschreibendes** Analysewerkzeug sein. Eine bloße hohe Formationspräzision ist kein Renditenachweis.

## 6. Ausführung, Robustheit und Abnahme

Signal bei Schluss t, früheste reguläre Simulation am nächsten verfügbaren Open; abweichende MOC-Annahmen ausdrücklich separat. Provision, Spread/Slippage, Gap und nicht ausführbare Limits einbeziehen. Bei Ziel und Stop innerhalb derselben OHLC-Bar Reihenfolge als unbekannt behandeln oder mit feineren Daten prüfen; keine vorteilhafte Reihenfolge erfinden.

Neu laden, Datenquelle zeitweise ausfallen lassen, fehlendes Volumen, verkürzte Historie, DST/Feiertage, Splits und Währungsabweichung testen. TradingView-Adapter separat: exaktes Symbol/Interval, geladener Bereich, Session und geschlossene letzte Bar; wiederholbarer Import und optionaler Reload-/Indikatorvergleich. Datenproviderwechsel darf nicht unbemerkt Instrument oder Adjustment ändern.

KI-Abnahme: zwei Anbieter bzw. ein Anbieter plus Offline-Modus verwenden dasselbe unveränderliche Evidenzobjekt. Modelle dürfen Interpretationen unterschiedlich formulieren, aber keine zusätzlichen numerischen Fakten, nicht belegte Muster oder Kalibrierungen erzeugen. Fallback/fehlende Modellantwort sichtbar als Betriebsstatus ausgeben.

**Freigabekriterien für die nächste Phase:**

- Numerische Golden-/Grenzfalltests und vollständige Zeit-/Zukunftsmutationsprüfungen bestehen.
- Jeder Patternbefund hat versionierte Geometrie und Verfügbarkeitszeit.
- Daten-, Code-, Parameter- und Ergebnismanifest ermöglichen identische Wiederholung.
- Fehlende Daten, Widersprüche und Konventionsunterschiede sind maschinenlesbar.
- Holdout-Ergebnisse werden auch bei ausbleibendem Mehrwert veröffentlicht.
- Der Codepfad bleibt Analyse/Reporting; kein Broker-/Orderadapter.
