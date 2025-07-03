# magentic

Integrieren Sie große Sprachmodelle nahtlos in Python-Code. Verwenden Sie die Dekoratoren `@prompt` und `@chatprompt`, um Funktionen zu erstellen, die strukturierte Ausgaben von einem LLM zurückgeben. Kombinieren Sie LLM-Abfragen und Tool-Verwendung mit traditionellem Python-Code, um komplexe agentische Systeme zu erstellen.

## Funktionen

- [Strukturierte Ausgaben] mit Pydantic-Modellen und eingebauten Python-Typen.
- [Streaming] von strukturierten Ausgaben und Funktionsaufrufen, um sie während der Generierung zu nutzen.
- [LLM-unterstützte Wiederholungsversuche] zur Verbesserung der LLM-Einhaltung komplexer Ausgabeschemata.
- [Beobachtbarkeit] mit OpenTelemetry und nativer [Pydantic Logfire-Integration].
- [Typ-Annotationen] für eine gute Zusammenarbeit mit Lintern und IDEs.
- [Konfigurationsoptionen] für mehrere LLM-Anbieter wie OpenAI, Anthropic und Ollama.
- Viele weitere Funktionen: [Chat-Prompting], [Parallele Funktionsaufrufe], [Vision], [Formatierung], [Asyncio]...

## Installation

```sh
pip install magentic
```

oder mit uv

```sh
uv add magentic
```

Konfigurieren Sie Ihren OpenAI API-Schlüssel, indem Sie die Umgebungsvariable `OPENAI_API_KEY` setzen. Für die Konfiguration eines anderen LLM-Anbieters siehe [Konfiguration] für weitere Informationen.

## Verwendung

### @prompt

Der `@prompt`-Dekorator ermöglicht es Ihnen, eine Vorlage für einen Prompt eines Large Language Models (LLM) als Python-Funktion zu definieren. Wenn diese Funktion aufgerufen wird, werden die Argumente in die Vorlage eingefügt, dann wird dieser Prompt an ein LLM gesendet, das die Funktionsausgabe generiert.

```python
from magentic import prompt


@prompt('Füge mehr "Alter"-Stil hinzu zu: {phrase}')
def alterfizieren(phrase: str) -> str: ...  # Kein Funktionskörper, da dieser nie ausgeführt wird


alterfizieren("Hallo, wie geht es dir?")
# "Hey, Alter! Was geht ab? Wie läuft's bei dir, Digga?"
```

Der `@prompt`-Dekorator respektiert die Rückgabetyp-Annotation der dekorierten Funktion. Dies kann [jeder von Pydantic unterstützte Typ](https://docs.pydantic.dev/latest/usage/types/types/) sein, einschließlich eines `pydantic`-Modells.

```python
from magentic import prompt
from pydantic import BaseModel


class Superheld(BaseModel):
    name: str
    alter: int
    kraft: str
    feinde: list[str]


@prompt("Erstelle einen Superhelden mit dem Namen {name}.")
def superheld_erstellen(name: str) -> Superheld: ...


superheld_erstellen("Garten-Mann")
# Superheld(name='Garten-Mann', alter=30, kraft='Kontrolle über Pflanzen', feinde=['Umweltverschmutzer', 'Beton-Frau'])
```

Siehe [Strukturierte Ausgaben] für mehr.

### @chatprompt

Der `@chatprompt`-Dekorator funktioniert genauso wie `@prompt`, ermöglicht es aber, Chat-Nachrichten als Vorlage anstelle eines einzelnen Textprompts zu übergeben. Dies kann verwendet werden, um eine Systemnachricht bereitzustellen oder für Few-Shot-Prompting, bei dem Sie Beispielantworten angeben, um die Ausgabe des Modells zu lenken. Formatfelder, die durch geschweifte Klammern `{example}` gekennzeichnet sind, werden in allen Nachrichten (außer `FunctionResultMessage`) ausgefüllt.

```python
from magentic import chatprompt, AssistantMessage, SystemMessage, UserMessage
from pydantic import BaseModel


class Zitat(BaseModel):
    zitat: str
    charakter: str


@chatprompt(
    SystemMessage("Du bist ein Filmkenner."),
    UserMessage("Was ist dein Lieblingszitat aus Harry Potter?"),
    AssistantMessage(
        Zitat(
            zitat="Es nützt nichts, sich in Träumen zu verlieren und zu vergessen zu leben.",
            charakter="Albus Dumbledore",
        )
    ),
    UserMessage("Was ist dein Lieblingszitat aus {film}?"),
)
def film_zitat_erhalten(film: str) -> Zitat: ...


film_zitat_erhalten("Iron Man")
# Zitat(zitat='Ich bin Iron Man.', charakter='Tony Stark')
```

Siehe [Chat-Prompting] für mehr.

### FunctionCall

Ein LLM kann auch entscheiden, Funktionen aufzurufen. In diesem Fall gibt die mit `@prompt` dekorierte Funktion ein `FunctionCall`-Objekt zurück, das aufgerufen werden kann, um die Funktion mit den vom LLM bereitgestellten Argumenten auszuführen.

```python
from typing import Literal

from magentic import prompt, FunctionCall


def twitter_durchsuchen(abfrage: str, kategorie: Literal["neueste", "personen"]) -> str:
    """Durchsucht Twitter nach einer Abfrage."""
    print(f"Durchsuche Twitter nach {abfrage!r} in der Kategorie {kategorie!r}")
    return "<twitter-ergebnisse>"


def youtube_durchsuchen(abfrage: str, kanal: str = "alle") -> str:
    """Durchsucht YouTube nach einer Abfrage."""
    print(f"Durchsuche YouTube nach {abfrage!r} im Kanal {kanal!r}")
    return "<youtube-ergebnisse>"


@prompt(
    "Verwende die geeignete Suchfunktion, um zu antworten: {frage}",
    functions=[twitter_durchsuchen, youtube_durchsuchen],
)
def suche_durchführen(frage: str) -> FunctionCall[str]: ...


output = suche_durchführen("Was sind die neuesten Nachrichten zu LLMs?")
print(output)
# > FunctionCall(<function twitter_durchsuchen at 0x10c367d00>, 'LLMs', 'neueste')
output()
# > Durchsuche Twitter nach 'Large Language Models Nachrichten' in der Kategorie 'neueste'
# '<twitter-ergebnisse>'
```

Siehe [Funktionsaufrufe] für mehr.

### @prompt_chain

Manchmal benötigt das LLM einen oder mehrere Funktionsaufrufe, um eine endgültige Antwort zu generieren. Der `@prompt_chain`-Dekorator löst `FunctionCall`-Objekte automatisch auf und gibt die Ausgabe an das LLM zurück, um fortzufahren, bis die endgültige Antwort erreicht ist.

Im folgenden Beispiel ruft das LLM, wenn `wetter_beschreiben` aufgerufen wird, zuerst die Funktion `aktuelles_wetter_abrufen` auf und verwendet dann das Ergebnis, um seine endgültige Antwort zu formulieren, die zurückgegeben wird.

```python
from magentic import prompt_chain


def aktuelles_wetter_abrufen(ort, einheit="fahrenheit"):
    """Ruft das aktuelle Wetter an einem bestimmten Ort ab"""
    # Simuliert eine API-Abfrage
    return {"temperatur": "72", "vorhersage": ["sonnig", "windig"]}


@prompt_chain(
    "Wie ist das Wetter in {stadt}?",
    functions=[aktuelles_wetter_abrufen],
)
def wetter_beschreiben(stadt: str) -> str: ...


wetter_beschreiben("Boston")
# 'Das aktuelle Wetter in Boston beträgt 72°F und es ist sonnig und windig.'
```

Mit LLM betriebene Funktionen, die mit `@prompt`, `@chatprompt` und `@prompt_chain` erstellt wurden, können als `functions` an andere `@prompt`/`@prompt_chain`-Dekoratoren übergeben werden, genau wie reguläre Python-Funktionen. Dies ermöglicht zunehmend komplexe LLM-betriebene Funktionalität, während einzelne Komponenten isoliert getestet und verbessert werden können.

<!-- Links -->

[Strukturierte Ausgaben]: https://magentic.dev/structured-outputs
[Chat-Prompting]: https://magentic.dev/chat-prompting
[Funktionsaufrufe]: https://magentic.dev/function-calling
[Parallele Funktionsaufrufe]: https://magentic.dev/function-calling/#parallelfunctioncall
[Beobachtbarkeit]: https://magentic.dev/logging-and-tracing
[Pydantic Logfire-Integration]: https://logfire.pydantic.dev/docs/integrations/third-party/magentic/
[Formatierung]: https://magentic.dev/formatting
[Asyncio]: https://magentic.dev/asyncio
[Streaming]: https://magentic.dev/streaming
[Vision]: https://magentic.dev/vision
[LLM-unterstützte Wiederholungsversuche]: https://magentic.dev/retrying.md
[Konfiguration]: https://magentic.dev/configuration
[Typ-Annotationen]: https://magentic.dev/type-checking
[Konfigurationsoptionen]: https://magentic.dev/configuration


### Streaming

Die Klasse `StreamedStr` (und `AsyncStreamedStr`) kann verwendet werden, um die Ausgabe des LLM zu streamen. Dies ermöglicht es Ihnen, den Text zu verarbeiten, während er generiert wird, anstatt die gesamte Ausgabe auf einmal zu erhalten.

```python
from magentic import prompt, StreamedStr


@prompt("Erzähle mir über {land}")
def land_beschreiben(land: str) -> StreamedStr: ...


# Chunks ausgeben, während sie empfangen werden
for chunk in land_beschreiben("Deutschland"):
    print(chunk, end="")
# 'Deutschland, offiziell bekannt als die Bundesrepublik Deutschland, ist ...'
```

Mehrere `StreamedStr` können gleichzeitig erstellt werden, um LLM-Ausgaben gleichzeitig zu streamen. Im folgenden Beispiel dauert die Generierung der Beschreibung für mehrere Länder ungefähr genauso lange wie für ein einzelnes Land.

```python
from time import time

länder = ["Österreich", "Deutschland", "Schweiz"]


# Beschreibungen nacheinander generieren
start_time = time()
for land in länder:
    # Die Umwandlung von `StreamedStr` in `str` blockiert, bis die LLM-Ausgabe vollständig generiert ist
    beschreibung = str(land_beschreiben(land))
    print(f"{time() - start_time:.2f}s : {land} - {len(beschreibung)} Zeichen")

# 22.72s : Österreich - 2130 Zeichen
# 41.63s : Deutschland - 1884 Zeichen
# 74.31s : Schweiz - 2968 Zeichen


# Beschreibungen gleichzeitig generieren, indem die StreamedStrs gleichzeitig erstellt werden
start_time = time()
streamed_strs = [land_beschreiben(land) for land in länder]
for land, streamed_str in zip(länder, streamed_strs):
    beschreibung = str(streamed_str)
    print(f"{time() - start_time:.2f}s : {land} - {len(beschreibung)} Zeichen")

# 22.79s : Österreich - 2147 Zeichen
# 23.64s : Deutschland - 2202 Zeichen
# 24.67s : Schweiz - 2186 Zeichen
```

### Objekt-Streaming

Strukturierte Ausgaben können auch vom LLM gestreamt werden, indem die Rückgabetyp-Annotation `Iterable` (oder `AsyncIterable`) verwendet wird. Dies ermöglicht die Verarbeitung jedes Elements, während das nächste generiert wird.

```python
from collections.abc import Iterable
from time import time

from magentic import prompt
from pydantic import BaseModel


class Superheld(BaseModel):
    name: str
    alter: int
    kraft: str
    feinde: list[str]


@prompt("Erstelle ein Superhelden-Team mit dem Namen {name}.")
def superhelden_team_erstellen(name: str) -> Iterable[Superheld]: ...


start_time = time()
for held in superhelden_team_erstellen("Die Essensbande"):
    print(f"{time() - start_time:.2f}s : {held}")

# 2.23s : name='Pizza-Mann' alter=30 kraft='Kann Pizzastücke aus seinen Händen schießen' feinde=['Die Hungrige Horde', 'Die Junk-Food-Gang']
# 4.03s : name='Kapitän Karotte' alter=35 kraft='Superstärke und Agilität durch das Essen von Karotten' feinde=['Die Zucker-Truppe', 'Die Fettigen']
# 6.05s : name='Eiscreme-Mädchen' alter=25 kraft='Kann Eiscreme aus dem Nichts erschaffen' feinde=['Die Hot-Sauce-Truppe', 'Die Gesund-Esser']
```

Siehe [Streaming] für mehr.

### Asyncio

Asynchrone Funktionen / Coroutinen können verwendet werden, um gleichzeitig das LLM abzufragen. Dies kann die Gesamtgeschwindigkeit der Generierung erheblich erhöhen und ermöglicht auch die Ausführung anderer asynchroner Codes, während auf die LLM-Ausgabe gewartet wird. Im folgenden Beispiel generiert das LLM eine Beschreibung für jeden US-Präsidenten, während es auf den nächsten in der Liste wartet. Die Messung der pro Sekunde generierten Zeichen zeigt, dass dieses Beispiel eine 7-fache Beschleunigung gegenüber der seriellen Verarbeitung erreicht.

```python
import asyncio
from time import time
from typing import AsyncIterable

from magentic import prompt


@prompt("Liste zehn Präsidenten der Vereinigten Staaten auf")
async def präsidenten_auflisten() -> AsyncIterable[str]: ...


@prompt("Erzähle mir mehr über {thema}")
async def erzähle_mehr_über(thema: str) -> str: ...


# Für jeden aufgelisteten Präsidenten gleichzeitig eine Beschreibung generieren
start_time = time()
tasks = []
async for präsident in await präsidenten_auflisten():
    # Verwende asyncio.create_task, um die Coroutine zur Ausführung zu planen, bevor sie erwartet wird
    # Auf diese Weise werden Beschreibungen generiert, während die Liste der Präsidenten noch generiert wird
    task = asyncio.create_task(erzähle_mehr_über(präsident))
    tasks.append(task)

beschreibungen = await asyncio.gather(*tasks)

# Zeichen pro Sekunde messen
gesamtzeichen = sum(len(beschr) for beschr in beschreibungen)
zeit_vergangen = time() - start_time
print(gesamtzeichen, zeit_vergangen, gesamtzeichen / zeit_vergangen)
# 24575 28.70 856.07


# Zeichen pro Sekunde messen, um einen einzelnen Präsidenten zu beschreiben
start_time = time()
out = await erzähle_mehr_über("George Washington")
zeit_vergangen = time() - start_time
print(len(out), zeit_vergangen, len(out) / zeit_vergangen)
# 2206 18.72 117.78
```

Siehe [Asyncio] für mehr.

### Zusätzliche Funktionen

- Das `functions`-Argument für `@prompt` kann async/coroutine-Funktionen enthalten. Wenn die entsprechenden `FunctionCall`-Objekte aufgerufen werden, muss das Ergebnis mit await abgewartet werden.
- Die `Annotated`-Typ-Annotation kann verwendet werden, um Beschreibungen und andere Metadaten für Funktionsparameter bereitzustellen. Siehe [die Pydantic-Dokumentation zur Verwendung von `Field` zur Beschreibung von Funktionsargumenten](https://docs.pydantic.dev/latest/usage/validation_decorator/#using-field-to-describe-function-arguments).
- Die Dekoratoren `@prompt` und `@prompt_chain` akzeptieren auch ein `model`-Argument. Sie können eine Instanz von `OpenaiChatModel` übergeben, um GPT4 zu verwenden oder eine andere Temperatur zu konfigurieren. Siehe unten.
- Registrieren Sie andere Typen für die Verwendung als Rückgabetyp-Annotationen in `@prompt`-Funktionen, indem Sie [dem Beispiel-Notebook für einen Pandas DataFrame](examples/custom_function_schemas/register_dataframe_function_schema.ipynb) folgen.

## Backend/LLM-Konfiguration

Magentic unterstützt mehrere LLM-Anbieter oder "Backends". Dies bezieht sich grob darauf, welches Python-Paket zur Interaktion mit der LLM-API verwendet wird. Die folgenden Backends werden unterstützt.

### OpenAI

Das Standard-Backend, das das Python-Paket `openai` verwendet und alle Funktionen von magentic unterstützt.

Keine zusätzliche Installation erforderlich. Importieren Sie einfach die Klasse `OpenaiChatModel` aus `magentic`.

```python
from magentic import OpenaiChatModel

model = OpenaiChatModel("gpt-4o")
```

#### Ollama über OpenAI

Ollama unterstützt eine OpenAI-kompatible API, die es Ihnen ermöglicht, Ollama-Modelle über das OpenAI-Backend zu verwenden.

Installieren Sie zunächst Ollama von [ollama.com](https://ollama.com/). Laden Sie dann das gewünschte Modell herunter.

```sh
ollama pull llama3.2
```

Geben Sie dann den Modellnamen und die `base_url` an, wenn Sie die `OpenaiChatModel`-Instanz erstellen.

```python
from magentic import OpenaiChatModel

model = OpenaiChatModel("llama3.2", base_url="http://localhost:11434/v1/")
```

#### Andere OpenAI-kompatible APIs

Bei Verwendung des `openai`-Backends ermöglicht das Setzen der Umgebungsvariable `MAGENTIC_OPENAI_BASE_URL` oder die Verwendung von `OpenaiChatModel(..., base_url="http://localhost:8080")` im Code die Verwendung von `magentic` mit jeder OpenAI-kompatiblen API, z.B. [Azure OpenAI Service](https://learn.microsoft.com/en-us/azure/ai-services/openai/quickstart?tabs=command-line&pivots=programming-language-python#create-a-new-python-application), [LiteLLM OpenAI Proxy Server](https://docs.litellm.ai/docs/proxy_server), [LocalAI](https://localai.io/howtos/easy-request-openai/). Beachten Sie, dass, wenn die API keine Tool-Aufrufe unterstützt, Sie keine Prompt-Funktionen erstellen können, die Python-Objekte zurückgeben, aber andere Funktionen von `magentic` werden weiterhin funktionieren.

Um Azure mit dem OpenAI-Backend zu verwenden, müssen Sie die Umgebungsvariable `MAGENTIC_OPENAI_API_TYPE` auf "azure" setzen oder `OpenaiChatModel(..., api_type="azure")` verwenden und auch die vom OpenAI-Paket benötigten Umgebungsvariablen für den Zugriff auf Azure setzen. Siehe https://github.com/openai/openai-python#microsoft-azure-openai

### Anthropic

Dies verwendet das Python-Paket `anthropic` und unterstützt alle Funktionen von magentic.

Installieren Sie das `magentic`-Paket mit dem `anthropic`-Extra oder installieren Sie das `anthropic`-Paket direkt.

```sh
pip install "magentic[anthropic]"
```

Importieren Sie dann die Klasse `AnthropicChatModel`.

```python
from magentic.chat_model.anthropic_chat_model import AnthropicChatModel

model = AnthropicChatModel("claude-3-5-sonnet-latest")
```

### LiteLLM

Dies verwendet das Python-Paket `litellm`, um das Abfragen von LLMs von [vielen verschiedenen Anbietern](https://docs.litellm.ai/docs/providers) zu ermöglichen. Hinweis: Einige Modelle unterstützen möglicherweise nicht alle Funktionen von `magentic`, z.B. Funktionsaufrufe/strukturierte Ausgabe und Streaming.

Installieren Sie das `magentic`-Paket mit dem `litellm`-Extra oder installieren Sie das `litellm`-Paket direkt.

```sh
pip install "magentic[litellm]"
```

Importieren Sie dann die Klasse `LitellmChatModel`.

```python
from magentic.chat_model.litellm_chat_model import LitellmChatModel

model = LitellmChatModel("gpt-4o")
```

### Mistral

Dies verwendet das Python-Paket `openai` mit einigen kleinen Änderungen, um die API-Abfragen mit der Mistral-API kompatibel zu machen. Es unterstützt alle Funktionen von magentic. Allerdings werden Tool-Aufrufe (einschließlich strukturierter Ausgaben) nicht gestreamt, sondern auf einmal empfangen.

Hinweis: Eine zukünftige Version von magentic könnte auf die Verwendung des Python-Pakets `mistral` umstellen.

Keine zusätzliche Installation erforderlich. Importieren Sie einfach die Klasse `MistralChatModel`.

```python
from magentic.chat_model.mistral_chat_model import MistralChatModel

model = MistralChatModel("mistral-large-latest")
```

## Ein Backend konfigurieren

Das Standard-`ChatModel`, das von `magentic` (in `@prompt`, `@chatprompt` usw.) verwendet wird, kann auf verschiedene Weise konfiguriert werden. Wenn eine Prompt-Funktion oder Chatprompt-Funktion aufgerufen wird, folgt das zu verwendende `ChatModel` dieser Reihenfolge der Präferenz:

1. Die `ChatModel`-Instanz, die als `model`-Argument an den magentic-Dekorator übergeben wurde
2. Der aktuelle Chat-Modell-Kontext, erstellt mit `with MyChatModel:`
3. Das globale `ChatModel`, erstellt aus Umgebungsvariablen und den Standardeinstellungen in [src/magentic/settings.py](https://github.com/jackmpcollins/magentic/blob/main/src/magentic/settings.py)

Das folgende Codebeispiel demonstriert dieses Verhalten:

```python
from magentic import OpenaiChatModel, prompt
from magentic.chat_model.anthropic_chat_model import AnthropicChatModel


@prompt("Sag Hallo")
def sag_hallo() -> str: ...


@prompt(
    "Sag Hallo",
    model=AnthropicChatModel("claude-3-5-sonnet-latest"),
)
def sag_hallo_anthropic() -> str: ...


sag_hallo()  # Verwendet Umgebungsvariablen oder Standardeinstellungen

with OpenaiChatModel("gpt-4o-mini", temperature=1):
    sag_hallo()  # Verwendet OpenAI mit gpt-4o-mini und temperature=1 aufgrund des Kontextmanagers
    sag_hallo_anthropic()  # Verwendet Anthropic claude-3-5-sonnet-latest, weil explizit konfiguriert
```

Die folgenden Umgebungsvariablen können gesetzt werden.

| Umgebungsvariable             | Beschreibung                                | Beispiel                     |
| ----------------------------- | ------------------------------------------- | ---------------------------- |
| MAGENTIC_BACKEND              | Das zu verwendende Paket als LLM-Backend    | anthropic / openai / litellm |
| MAGENTIC_ANTHROPIC_MODEL      | Anthropic-Modell                            | claude-3-haiku-20240307      |
| MAGENTIC_ANTHROPIC_API_KEY    | Anthropic API-Schlüssel für magentic        | sk-...                       |
| MAGENTIC_ANTHROPIC_BASE_URL   | Basis-URL für eine Anthropic-kompatible API | http://localhost:8080        |
| MAGENTIC_ANTHROPIC_MAX_TOKENS | Maximale Anzahl generierter Tokens          | 1024                         |
| MAGENTIC_ANTHROPIC_TEMPERATURE| Temperatur                                  | 0.5                          |
| MAGENTIC_LITELLM_MODEL        | LiteLLM-Modell                              | claude-2                     |
| MAGENTIC_LITELLM_API_BASE     | Die zu abfragende Basis-URL                 | http://localhost:11434       |
| MAGENTIC_LITELLM_MAX_TOKENS   | LiteLLM maximale Anzahl generierter Tokens  | 1024                         |
| MAGENTIC_LITELLM_TEMPERATURE  | LiteLLM-Temperatur                          | 0.5                          |
| MAGENTIC_MISTRAL_MODEL        | Mistral-Modell                              | mistral-large-latest         |
| MAGENTIC_MISTRAL_API_KEY      | Mistral API-Schlüssel für magentic          | XEG...                       |
| MAGENTIC_MISTRAL_BASE_URL     | Basis-URL für eine Mistral-kompatible API   | http://localhost:8080        |
| MAGENTIC_MISTRAL_MAX_TOKENS   | Maximale Anzahl generierter Tokens          | 1024                         |
| MAGENTIC_MISTRAL_SEED         | Seed für deterministische Stichproben       | 42                           |
| MAGENTIC_MISTRAL_TEMPERATURE  | Temperatur                                  | 0.5                          |
| MAGENTIC_OPENAI_MODEL         | OpenAI-Modell                               | gpt-4                        |
| MAGENTIC_OPENAI_API_KEY       | OpenAI API-Schlüssel für magentic           | sk-...                       |
| MAGENTIC_OPENAI_API_TYPE      | Erlaubte Optionen: "openai", "azure"        | azure                        |
| MAGENTIC_OPENAI_BASE_URL      | Basis-URL für eine OpenAI-kompatible API    | http://localhost:8080        |
| MAGENTIC_OPENAI_MAX_TOKENS    | OpenAI maximale Anzahl generierter Tokens   | 1024                         |
| MAGENTIC_OPENAI_SEED          | Seed für deterministische Stichproben       | 42                           |
| MAGENTIC_OPENAI_TEMPERATURE   | OpenAI-Temperatur                           | 0.5                          |

## Typ-Überprüfung

Viele Typ-Prüfer werden Warnungen oder Fehler für Funktionen mit dem `@prompt`-Dekorator auslösen, da die Funktion keinen Körper oder Rückgabewert hat. Es gibt verschiedene Möglichkeiten, damit umzugehen.

1. Deaktivieren Sie die Prüfung global für den Typ-Prüfer. Zum Beispiel in mypy durch Deaktivieren des Fehlercodes `empty-body`.
   ```toml
   # pyproject.toml
   [tool.mypy]
   disable_error_code = ["empty-body"]
   ```
2. Machen Sie den Funktionskörper zu `...` (dies erfüllt mypy nicht) oder `raise`.
   ```python
   @prompt("Wähle eine Farbe")
   def zufällige_farbe() -> str: ...
   ```
3. Verwenden Sie den Kommentar `# type: ignore[empty-body]` für jede Funktion. In diesem Fall können Sie anstelle von `...` einen Docstring hinzufügen.
   ```python
   @prompt("Wähle eine Farbe")
   def zufällige_farbe() -> str:  # type: ignore[empty-body]
       """Gibt eine zufällige Farbe zurück."""
   ```