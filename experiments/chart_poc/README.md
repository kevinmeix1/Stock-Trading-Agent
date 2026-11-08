# Rein lesender Chartanalyse-PoC

**Ergebnis:** Im reservierten Holdout ist kein belastbarer Vorteil von MASS gegenüber den einfachen Trend-/Momentum-Baselines nachgewiesen. [Vollständiger Vergleichsbericht](results/REPORT.md).

| Richtungsprognose, Holdout | Trefferquote |
|---|---:|
| MASS, fünf historische Analogfenster | 47,86 % |
| Trend, SMA20 gegen SMA50 | 47,86 % |
| Momentum, letzte 20 Bars | 46,15 % |
| Kontrollfall, immer positive Folge | 58,12 % |

117 Prognosen auf 39 gemeinsamen Terminen; drei korrelierte US-Technologietitel. Gepaarte Intervalle schließen null ein. Das Ergebnis belegt weder einen generellen MASS-Vorteil noch eine generelle Wirkungslosigkeit aller Pattern-Verfahren.

## Ausführen

Aus dem Repository-Root, Windows und Python 3.12:

```powershell
python -m venv .venv-poc
.\.venv-poc\Scripts\python.exe -m pip install -r experiments/chart_poc/requirements.txt
.\.venv-poc\Scripts\python.exe -m experiments.chart_poc.study
.\.venv-poc\Scripts\python.exe -m pytest experiments/chart_poc/tests
.\.venv-poc\Scripts\python.exe -m ruff check experiments
```

Der Standardlauf liest die drei eingecheckten CSV-Dateien, prüft ihre SHA-256-Summen und schreibt ausschließlich in `experiments/chart_poc/results`. Für eine zusätzliche Wiederholung ohne Überschreiben der Referenzergebnisse:

```powershell
.\.venv-poc\Scripts\python.exe -m experiments.chart_poc.study --output runs/chart-poc-verification
```

Die Auswertung und alle Tests laufen offline. Nur der gesonderte, ausdrücklich aufgerufene Beschaffer benötigt Internet:

```powershell
.\.venv-poc\Scripts\python.exe experiments/chart_poc/freeze_data.py
```

Er lädt ausschließlich die fest gepinnte Quelldatei und prüft deren SHA-256. Abweichende bestehende Snapshots werden nicht überschrieben. Herkunft und Datennutzungsangaben: [DATA_NOTICE.md](DATA_NOTICE.md), [Manifest](data/manifest.json). Der Beschaffer normalisiert nur Spaltennamen und extrahiert drei Reihen; Rohwerte bleiben unverändert.

## Prüfdesign

- **Daten:** je 3.270 reale Tagesbars für AAPL, IBM, MSFT, 01.03.2000–01.03.2013. Keine generierten Kurse im Vergleich; synthetische Daten werden ausschließlich für Unit-Tests verwendet.
- **Vorab festgeschrieben:** [protocol.json](protocol.json), Daten und Parameter im ersten Feature-Commit vor der Ergebnisauswertung. Keine Parameterauswahl anhand der Holdout-Ergebnisse.
- **Training:** feste Analogbibliothek bis Ende 2006. **Validation:** 2007–2009, nur beschreibend. **Holdout:** 2010–2013, unveränderte Parameter.
- **Query:** letzte 60 geschlossene Tages-Schlusskurse; logarithmiert; MASS mit Z-Normalisierung je Fenster, ddof=0. Niveau- und Amplitudenunterschiede werden entfernt; die Zeitachse bleibt unverändert.
- **Matches:** fünf nächstähnliche historische Fenster desselben Titels, greedy nach Distanz mit chronologischer Tie-Regel. Ganze Feature- und 20-Bar-Outcome-Intervalle der Nachbarn sind paarweise disjunkt. Sämtliche Nachbar-Outcomes enden vor Querybeginn und innerhalb der Trainingsgrenze.
- **Vorhersage:** Vorzeichen der mittleren historischen 20-Bar-Logrendite. Das ist eine einfache Analogprognose, keine kalibrierte Wahrscheinlichkeit.
- **Baselines:** SMA20 minus SMA50 sowie letzte 20-Bar-Rendite; gleiche 60 verfügbaren Bars und gleiche Prognose-/Zieltermine. Immer-positiv als Kontrolle des Klassen-/Marktbias.
- **Ziel:** Richtung der tatsächlich realisierten 20-Bar-Logrendite ab Schluss t. Prognosen alle 20 Bars. Null-/Neutralfälle zählen 0,5. Keine Ausführungs- oder Gebührenannahmen, weil keine Handelsstrategie simuliert wird.
- **Unsicherheit:** gepaarte Accuracy-Differenzen, Aktien je Datum gemeinsam, Moving-Block-Bootstrap (Blocklänge 5 Termine, 5.000 Wiederholungen, Seed 20261108). Zwei primäre Vergleiche mit jeweils 97,5%-Intervall; Blocklängen 3/8 als vorab fixierte Sensitivität. 117 Prognosen sind keine 117 unabhängigen Beobachtungen.

## Strukturregeln v1

Pivots benötigen je zwei Nachbarn links und rechts und werden erst am Schluss des zweiten rechten Bars bestätigt. Gleiche Extrema: erster Punkt im Fünferfenster; simultane High-/Low-Pivots einer Outside-Bar werden ausgelassen. HH/LH beziehungsweise HL/LL vergleichen zum letzten bestätigten Extrem desselben Typs; EH/EL kennzeichnen gleiche Preise.

Double Bottom benötigt **drei unmittelbar aufeinanderfolgende bestätigte Pivots L–H–L**:

1. 10–80 Bars zwischen den Tiefs.
2. Preisabstand der Tiefs höchstens 0,75 ATR14.
3. Nackenlinie mindestens 1,5 ATR über dem höheren Tief.
4. ATR wird bei Bekanntwerden des zweiten Tiefs eingefroren. Wilder-Glättung, Seed aus den ersten 14 True Ranges einschließlich erster High-Low-Range.
5. Bestätigung erst durch Schlusskurs über Nackenlinie +0,1 eingefrorene ATR.
6. Vorheriger Schluss unter dem tieferen Tief -0,25 ATR verwirft den Kandidaten; nach 40 Bars ab zweitem Tief verfällt er.

Die ATR-, Zeit- und Musterschwellen sind PoC-Konventionen, keine optimierten oder wissenschaftlich garantierten Werte. Bestätigte Ereignisse werden nicht nachträglich umgeschrieben. Die folgende tatsächliche Entwicklung steht in einem getrennten Outcome-Objekt. Es gibt keine manuelle Annotation zur Messung von Precision/Recall.

## Dateien und Nachvollziehbarkeit

- `data.py`: Hash-/Datums-/OHLC-Validierung; rekonstruiert adjustierte OHLC.
- `structure.py`: ATR, bestätigte HH/HL/LH/LL und Double Bottom.
- `matching.py`: MASS, disjunkte Vergleiche und einfache Baselines; erhält keine unbekannte Zukunft.
- `study.py`: zeitliche Evaluation, gepaarte Unsicherheit und Bericht.
- `results/predictions.json`: alle 228 Prognosen mit fünf Matchfenstern, Distanzen und historischen/tatsächlichen Folgen.
- `results/predictions.csv`: kompakte Prognosen für unabhängige Auswertung. MAE/MFE sind Schlusskurspfad-Extrema einschließlich t=0, keine Intrabar-Extrema.
- `results/structures.json`: sämtliche bestätigten Swings und 15 algorithmische Double Bottoms; unbekannte letzte Folgen bleiben leer.
- `results/summary.json`: Kennzahlen, Sensitivität, Versionen sowie kanonische Protokoll-/Manifest-Hashes.
- `results/REPORT.md`: Vergleich, Unsicherheiten und automatisch ausgewählte Fehlinterpretationen.

## Grenzen und P0-Trennung

Die rückwirkend adjustierte Quelle enthält auch spätere Kapitalmaßnahmen; sie ist kein historisch archivierter Point-in-time-Feed. Gemeinsame Skalierung aller Preise eines Präfixes ändert Z-Distanzen, Richtungen und ATR-Verhältnisse nicht. Die Test-Suite prüft diese Invarianz. Der PoC behauptet keine exakten damaligen handelbaren Preislevels. News, Bilanzdaten, Orderbuch und Volumen werden nicht zur Prognose verwendet.

Drei überlebende Technologieaktien, 39 Holdout-Termine und eine feste historische Trainingsbibliothek begrenzen statistische Belastbarkeit und Übertragbarkeit. Der Bootstrap bildet zeitliche Abhängigkeit und gemeinsame Marktbewegungen näherungsweise ab, aber keine neue Instrumentauswahl oder Unsicherheit über eine andere Trainingsbibliothek. Ein kausaler Erkennungscode allein belegt keine Erkennungspräzision oder Prognosewirkung.

RSI-Grenzfall, künstliche Fundamentaldaten und durch LLM-Ausgaben übersteuerbare Regeln des Bestands bleiben separate P0-Befunde. Dieser PoC importiert keine `stock_trading_agent`-Module. Er verändert keine produktiven Funktionen, Schnittstellen oder Anwendungsabhängigkeiten und enthält keine Broker-, Order-, TradingView-, DTW- oder KI-Anbindung.

## Verifikation

Die Tests prüfen Datenmanipulation, OHLC-Widersprüche, numerische ATR-Referenzwerte, exakte Swing-Labels, zeitliche Pattern-Bestätigung, mehrdeutige Fälle, Z-Distanzen gegen unabhängige Brute-Force-Rechnung, disjunkte Matchintervalle und Outcome-Abstände, Zukunftsmutationen, gepaarte Statistik und vollständige Wiederholbarkeit der eingecheckten Ergebnisse.

Eine externe Codeprüfung hat zusätzlich alle 228 Prognosen auf Datumsgrenzen, Paarung und Accuracy kontrolliert. Die endgültigen Testzahlen stehen im PR; es wird keine Trefferquote außerhalb der tatsächlich berechneten Fälle behauptet.
