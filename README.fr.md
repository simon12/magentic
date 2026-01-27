# magentic

Intégrez de manière transparente les grands modèles de langage (LLM) dans votre code Python. Utilisez les décorateurs `@prompt` et `@chatprompt` pour créer des fonctions qui retournent des sorties structurées d'un LLM. Combinez les requêtes LLM et l'utilisation d'outils avec du code Python traditionnel pour construire des systèmes agentiques complexes.

## Fonctionnalités

- [Sorties structurées] utilisant des modèles pydantic et des types Python intégrés.
- [Streaming] de sorties structurées et d'appels de fonctions, pour les utiliser pendant leur génération.
- [Réessais assistés par LLM] pour améliorer l'adhésion du LLM aux schémas de sortie complexes.
- [Observabilité] en utilisant OpenTelemetry, avec une [intégration native de Pydantic Logfire].
- [Annotations de types] pour fonctionner parfaitement avec les linters et les IDE.
- Options de [configuration] pour plusieurs fournisseurs de LLM, notamment OpenAI, Anthropic et Ollama.
- De nombreuses autres fonctionnalités : [Prompts de chat], [Appels de fonctions parallèles], [Vision], [Formatage], [Asyncio]...

## Installation

```sh
pip install magentic
```

ou en utilisant uv

```sh
uv add magentic
```

Configurez votre clé API OpenAI en définissant la variable d'environnement `OPENAI_API_KEY`. Pour configurer un autre fournisseur de LLM, consultez [Configuration] pour plus d'informations.

## Utilisation

### @prompt

Le décorateur `@prompt` vous permet de définir un modèle pour un prompt de grand modèle de langage (LLM) sous forme de fonction Python. Lorsque cette fonction est appelée, les arguments sont insérés dans le modèle, puis ce prompt est envoyé à un LLM qui génère la sortie de la fonction.

```python
from magentic import prompt


@prompt('Add more "dude"ness to: {phrase}')
def dudeify(phrase: str) -> str: ...  # Pas de corps de fonction car cela n'est jamais exécuté


dudeify("Hello, how are you?")
# "Hey, dude! What's up? How's it going, my man?"
```

Le décorateur `@prompt` respectera l'annotation de type de retour de la fonction décorée. Cela peut être [n'importe quel type pris en charge par pydantic](https://docs.pydantic.dev/latest/usage/types/types/), y compris un modèle `pydantic`.

```python
from magentic import prompt
from pydantic import BaseModel


class Superhero(BaseModel):
    name: str
    age: int
    power: str
    enemies: list[str]


@prompt("Create a Superhero named {name}.")
def create_superhero(name: str) -> Superhero: ...


create_superhero("Garden Man")
# Superhero(name='Garden Man', age=30, power='Control over plants', enemies=['Pollution Man', 'Concrete Woman'])
```

Voir [Sorties structurées] pour plus d'informations.

### @chatprompt

Le décorateur `@chatprompt` fonctionne comme `@prompt` mais vous permet de passer des messages de chat comme modèle plutôt qu'un seul prompt texte. Cela peut être utilisé pour fournir un message système ou pour un prompting few-shot où vous fournissez des exemples de réponses pour guider la sortie du modèle. Les champs de format indiqués par des accolades `{example}` seront remplis dans tous les messages (sauf `FunctionResultMessage`).

```python
from magentic import chatprompt, AssistantMessage, SystemMessage, UserMessage
from pydantic import BaseModel


class Quote(BaseModel):
    quote: str
    character: str


@chatprompt(
    SystemMessage("You are a movie buff."),
    UserMessage("What is your favorite quote from Harry Potter?"),
    AssistantMessage(
        Quote(
            quote="It does not do to dwell on dreams and forget to live.",
            character="Albus Dumbledore",
        )
    ),
    UserMessage("What is your favorite quote from {movie}?"),
)
def get_movie_quote(movie: str) -> Quote: ...


get_movie_quote("Iron Man")
# Quote(quote='I am Iron Man.', character='Tony Stark')
```

Voir [Prompts de chat] pour plus d'informations.

### FunctionCall

Un LLM peut également décider d'appeler des fonctions. Dans ce cas, la fonction décorée avec `@prompt` retourne un objet `FunctionCall` qui peut être appelé pour exécuter la fonction en utilisant les arguments fournis par le LLM.

```python
from typing import Literal

from magentic import prompt, FunctionCall


def search_twitter(query: str, category: Literal["latest", "people"]) -> str:
    """Recherche sur Twitter pour une requête."""
    print(f"Searching Twitter for {query!r} in category {category!r}")
    return "<twitter results>"


def search_youtube(query: str, channel: str = "all") -> str:
    """Recherche sur YouTube pour une requête."""
    print(f"Searching YouTube for {query!r} in channel {channel!r}")
    return "<youtube results>"


@prompt(
    "Use the appropriate search function to answer: {question}",
    functions=[search_twitter, search_youtube],
)
def perform_search(question: str) -> FunctionCall[str]: ...


output = perform_search("What is the latest news on LLMs?")
print(output)
# > FunctionCall(<function search_twitter at 0x10c367d00>, 'LLMs', 'latest')
output()
# > Searching Twitter for 'Large Language Models news' in category 'latest'
# '<twitter results>'
```

Voir [Appel de fonctions] pour plus d'informations.

### @prompt_chain

Parfois, le LLM nécessite de faire un ou plusieurs appels de fonction pour générer une réponse finale. Le décorateur `@prompt_chain` résoudra automatiquement les objets `FunctionCall` et renverra la sortie au LLM pour continuer jusqu'à ce que la réponse finale soit atteinte.

Dans l'exemple suivant, lorsque `describe_weather` est appelée, le LLM appelle d'abord la fonction `get_current_weather`, puis utilise le résultat de celle-ci pour formuler sa réponse finale qui est retournée.

```python
from magentic import prompt_chain


def get_current_weather(location, unit="fahrenheit"):
    """Obtient la météo actuelle dans un lieu donné"""
    # Fait semblant d'interroger une API
    return {"temperature": "72", "forecast": ["sunny", "windy"]}


@prompt_chain(
    "What's the weather like in {city}?",
    functions=[get_current_weather],
)
def describe_weather(city: str) -> str: ...


describe_weather("Boston")
# 'The current weather in Boston is 72°F and it is sunny and windy.'
```

Les fonctions alimentées par LLM créées avec `@prompt`, `@chatprompt` et `@prompt_chain` peuvent être fournies comme `functions` à d'autres décorateurs `@prompt`/`@prompt_chain`, tout comme les fonctions Python normales. Cela permet des fonctionnalités alimentées par LLM de plus en plus complexes, tout en permettant de tester et d'améliorer les composants individuels de manière isolée.

<!-- Links -->

[Sorties structurées]: https://magentic.dev/structured-outputs
[Prompts de chat]: https://magentic.dev/chat-prompting
[Appel de fonctions]: https://magentic.dev/function-calling
[Appels de fonctions parallèles]: https://magentic.dev/function-calling/#parallelfunctioncall
[Observabilité]: https://magentic.dev/logging-and-tracing
[intégration native de Pydantic Logfire]: https://logfire.pydantic.dev/docs/integrations/third-party/magentic/
[Formatage]: https://magentic.dev/formatting
[Asyncio]: https://magentic.dev/asyncio
[Streaming]: https://magentic.dev/streaming
[Vision]: https://magentic.dev/vision
[Réessais assistés par LLM]: https://magentic.dev/retrying.md
[Configuration]: https://magentic.dev/configuration
[Annotations de types]: https://magentic.dev/type-checking


### Streaming

La classe `StreamedStr` (et `AsyncStreamedStr`) peut être utilisée pour diffuser la sortie du LLM. Cela vous permet de traiter le texte pendant qu'il est généré, plutôt que de recevoir toute la sortie en une seule fois.

```python
from magentic import prompt, StreamedStr


@prompt("Tell me about {country}")
def describe_country(country: str) -> StreamedStr: ...


# Affiche les morceaux pendant qu'ils sont reçus
for chunk in describe_country("Brazil"):
    print(chunk, end="")
# 'Brazil, officially known as the Federative Republic of Brazil, is ...'
```

Plusieurs `StreamedStr` peuvent être créés en même temps pour diffuser les sorties LLM simultanément. Dans l'exemple ci-dessous, générer la description pour plusieurs pays prend approximativement le même temps que pour un seul pays.

```python
from time import time

countries = ["Australia", "Brazil", "Chile"]


# Génère les descriptions une à la fois
start_time = time()
for country in countries:
    # Convertir `StreamedStr` en `str` bloque jusqu'à ce que la sortie LLM soit entièrement générée
    description = str(describe_country(country))
    print(f"{time() - start_time:.2f}s : {country} - {len(description)} chars")

# 22.72s : Australia - 2130 chars
# 41.63s : Brazil - 1884 chars
# 74.31s : Chile - 2968 chars


# Génère les descriptions simultanément en créant les StreamedStrs en même temps
start_time = time()
streamed_strs = [describe_country(country) for country in countries]
for country, streamed_str in zip(countries, streamed_strs):
    description = str(streamed_str)
    print(f"{time() - start_time:.2f}s : {country} - {len(description)} chars")

# 22.79s : Australia - 2147 chars
# 23.64s : Brazil - 2202 chars
# 24.67s : Chile - 2186 chars
```

### Streaming d'objets

Les sorties structurées peuvent également être diffusées depuis le LLM en utilisant l'annotation de type de retour `Iterable` (ou `AsyncIterable`). Cela permet à chaque élément d'être traité pendant que le suivant est généré.

```python
from collections.abc import Iterable
from time import time

from magentic import prompt
from pydantic import BaseModel


class Superhero(BaseModel):
    name: str
    age: int
    power: str
    enemies: list[str]


@prompt("Create a Superhero team named {name}.")
def create_superhero_team(name: str) -> Iterable[Superhero]: ...


start_time = time()
for hero in create_superhero_team("The Food Dudes"):
    print(f"{time() - start_time:.2f}s : {hero}")

# 2.23s : name='Pizza Man' age=30 power='Can shoot pizza slices from his hands' enemies=['The Hungry Horde', 'The Junk Food Gang']
# 4.03s : name='Captain Carrot' age=35 power='Super strength and agility from eating carrots' enemies=['The Sugar Squad', 'The Greasy Gang']
# 6.05s : name='Ice Cream Girl' age=25 power='Can create ice cream out of thin air' enemies=['The Hot Sauce Squad', 'The Healthy Eaters']
```

Voir [Streaming] pour plus d'informations.

### Asyncio

Les fonctions asynchrones / coroutines peuvent être utilisées pour interroger le LLM de manière concurrente. Cela peut considérablement augmenter la vitesse globale de génération, et permettre également à d'autres codes asynchrones de s'exécuter en attendant la sortie du LLM. Dans l'exemple ci-dessous, le LLM génère une description pour chaque président des États-Unis pendant qu'il attend le suivant dans la liste. Mesurer les caractères générés par seconde montre que cet exemple atteint une accélération de 7x par rapport au traitement en série.

```python
import asyncio
from time import time
from typing import AsyncIterable

from magentic import prompt


@prompt("List ten presidents of the United States")
async def iter_presidents() -> AsyncIterable[str]: ...


@prompt("Tell me more about {topic}")
async def tell_me_more_about(topic: str) -> str: ...


# Pour chaque président listé, génère une description simultanément
start_time = time()
tasks = []
async for president in await iter_presidents():
    # Utilise asyncio.create_task pour planifier l'exécution de la coroutine avant de l'attendre
    # De cette façon, les descriptions commenceront à être générées pendant que la liste des présidents est encore en cours de génération
    task = asyncio.create_task(tell_me_more_about(president))
    tasks.append(task)

descriptions = await asyncio.gather(*tasks)

# Mesure les caractères par seconde
total_chars = sum(len(desc) for desc in descriptions)
time_elapsed = time() - start_time
print(total_chars, time_elapsed, total_chars / time_elapsed)
# 24575 28.70 856.07


# Mesure les caractères par seconde pour décrire un seul président
start_time = time()
out = await tell_me_more_about("George Washington")
time_elapsed = time() - start_time
print(len(out), time_elapsed, len(out) / time_elapsed)
# 2206 18.72 117.78
```

Voir [Asyncio] pour plus d'informations.

### Fonctionnalités supplémentaires

- L'argument `functions` de `@prompt` peut contenir des fonctions async/coroutine. Lorsque les objets `FunctionCall` correspondants sont appelés, le résultat doit être attendu avec `await`.
- L'annotation de type `Annotated` peut être utilisée pour fournir des descriptions et d'autres métadonnées pour les paramètres de fonction. Voir [la documentation pydantic sur l'utilisation de `Field` pour décrire les arguments de fonction](https://docs.pydantic.dev/latest/usage/validation_decorator/#using-field-to-describe-function-arguments).
- Les décorateurs `@prompt` et `@prompt_chain` acceptent également un argument `model`. Vous pouvez passer une instance de `OpenaiChatModel` pour utiliser GPT4 ou configurer une température différente. Voir ci-dessous.
- Enregistrez d'autres types à utiliser comme annotations de type de retour dans les fonctions `@prompt` en suivant [l'exemple de notebook pour un DataFrame Pandas](examples/custom_function_schemas/register_dataframe_function_schema.ipynb).

## Configuration du backend/LLM

Magentic prend en charge plusieurs fournisseurs de LLM ou "backends". Cela fait référence approximativement au package Python utilisé pour interagir avec l'API LLM. Les backends suivants sont pris en charge.

### OpenAI

Le backend par défaut, utilisant le package Python `openai` et prenant en charge toutes les fonctionnalités de magentic.

Aucune installation supplémentaire n'est requise. Il suffit d'importer la classe `OpenaiChatModel` depuis `magentic`.

```python
from magentic import OpenaiChatModel

model = OpenaiChatModel("gpt-4o")
```

#### Ollama via OpenAI

Ollama prend en charge une API compatible OpenAI, ce qui vous permet d'utiliser des modèles Ollama via le backend OpenAI.

Tout d'abord, installez ollama depuis [ollama.com](https://ollama.com/). Ensuite, téléchargez le modèle que vous souhaitez utiliser.

```sh
ollama pull llama3.2
```

Ensuite, spécifiez le nom du modèle et `base_url` lors de la création de l'instance `OpenaiChatModel`.

```python
from magentic import OpenaiChatModel

model = OpenaiChatModel("llama3.2", base_url="http://localhost:11434/v1/")
```

#### Autres API compatibles OpenAI

Lors de l'utilisation du backend `openai`, définir la variable d'environnement `MAGENTIC_OPENAI_BASE_URL` ou utiliser `OpenaiChatModel(..., base_url="http://localhost:8080")` dans le code vous permet d'utiliser `magentic` avec n'importe quelle API compatible OpenAI, par exemple [Azure OpenAI Service](https://learn.microsoft.com/en-us/azure/ai-services/openai/quickstart?tabs=command-line&pivots=programming-language-python#create-a-new-python-application), [LiteLLM OpenAI Proxy Server](https://docs.litellm.ai/docs/proxy_server), [LocalAI](https://localai.io/howtos/easy-request-openai/). Notez que si l'API ne prend pas en charge les appels d'outils, vous ne pourrez pas créer de fonctions-prompts qui retournent des objets Python, mais d'autres fonctionnalités de `magentic` fonctionneront toujours.

Pour utiliser Azure avec le backend openai, vous devrez définir la variable d'environnement `MAGENTIC_OPENAI_API_TYPE` sur "azure" ou utiliser `OpenaiChatModel(..., api_type="azure")`, et également définir les variables d'environnement nécessaires au package openai pour accéder à Azure. Voir https://github.com/openai/openai-python#microsoft-azure-openai

### Anthropic

Cela utilise le package Python `anthropic` et prend en charge toutes les fonctionnalités de magentic.

Installez le package `magentic` avec l'extra `anthropic`, ou installez directement le package `anthropic`.

```sh
pip install "magentic[anthropic]"
```

Ensuite, importez la classe `AnthropicChatModel`.

```python
from magentic.chat_model.anthropic_chat_model import AnthropicChatModel

model = AnthropicChatModel("claude-3-5-sonnet-latest")
```

### LiteLLM

Cela utilise le package Python `litellm` pour permettre l'interrogation de LLM de [nombreux fournisseurs différents](https://docs.litellm.ai/docs/providers). Remarque : certains modèles peuvent ne pas prendre en charge toutes les fonctionnalités de `magentic`, par exemple l'appel de fonction/sortie structurée et le streaming.

Installez le package `magentic` avec l'extra `litellm`, ou installez directement le package `litellm`.

```sh
pip install "magentic[litellm]"
```

Ensuite, importez la classe `LitellmChatModel`.

```python
from magentic.chat_model.litellm_chat_model import LitellmChatModel

model = LitellmChatModel("gpt-4o")
```

### Mistral

Cela utilise le package Python `openai` avec quelques petites modifications pour rendre les requêtes API compatibles avec l'API Mistral. Il prend en charge toutes les fonctionnalités de magentic. Cependant, les appels d'outils (y compris les sorties structurées) ne sont pas diffusés et sont donc reçus en une seule fois.

Remarque : une future version de magentic pourrait passer à l'utilisation du package Python `mistral`.

Aucune installation supplémentaire n'est requise. Il suffit d'importer la classe `MistralChatModel`.

```python
from magentic.chat_model.mistral_chat_model import MistralChatModel

model = MistralChatModel("mistral-large-latest")
```

## Configurer un backend

Le `ChatModel` par défaut utilisé par `magentic` (dans `@prompt`, `@chatprompt`, etc.) peut être configuré de plusieurs manières. Lorsqu'une fonction-prompt ou fonction-chatprompt est appelée, le `ChatModel` à utiliser suit cet ordre de préférence :

1. L'instance `ChatModel` fournie comme argument `model` au décorateur magentic
1. Le contexte du modèle de chat actuel, créé en utilisant `with MyChatModel:`
1. Le `ChatModel` global créé à partir des variables d'environnement et des paramètres par défaut dans [src/magentic/settings.py](https://github.com/jackmpcollins/magentic/blob/main/src/magentic/settings.py)

L'extrait de code suivant démontre ce comportement :

```python
from magentic import OpenaiChatModel, prompt
from magentic.chat_model.anthropic_chat_model import AnthropicChatModel


@prompt("Say hello")
def say_hello() -> str: ...


@prompt(
    "Say hello",
    model=AnthropicChatModel("claude-3-5-sonnet-latest"),
)
def say_hello_anthropic() -> str: ...


say_hello()  # Utilise les variables d'env ou les paramètres par défaut

with OpenaiChatModel("gpt-4o-mini", temperature=1):
    say_hello()  # Utilise openai avec gpt-4o-mini et temperature=1 grâce au gestionnaire de contexte
    say_hello_anthropic()  # Utilise Anthropic claude-3-5-sonnet-latest car explicitement configuré
```

Les variables d'environnement suivantes peuvent être définies.

| Variable d'environnement       | Description                                         | Exemple                      |
| ------------------------------ | --------------------------------------------------- | ---------------------------- |
| MAGENTIC_BACKEND               | Le package à utiliser comme backend LLM             | anthropic / openai / litellm |
| MAGENTIC_ANTHROPIC_MODEL       | Modèle Anthropic                                    | claude-3-haiku-20240307      |
| MAGENTIC_ANTHROPIC_API_KEY     | Clé API Anthropic à utiliser par magentic           | sk-...                       |
| MAGENTIC_ANTHROPIC_BASE_URL    | URL de base pour une API compatible Anthropic       | http://localhost:8080        |
| MAGENTIC_ANTHROPIC_MAX_TOKENS  | Nombre maximum de tokens générés                    | 1024                         |
| MAGENTIC_ANTHROPIC_TEMPERATURE | Température                                         | 0.5                          |
| MAGENTIC_LITELLM_MODEL         | Modèle LiteLLM                                      | claude-2                     |
| MAGENTIC_LITELLM_API_BASE      | L'URL de base à interroger                          | http://localhost:11434       |
| MAGENTIC_LITELLM_MAX_TOKENS    | Nombre maximum de tokens générés LiteLLM            | 1024                         |
| MAGENTIC_LITELLM_TEMPERATURE   | Température LiteLLM                                 | 0.5                          |
| MAGENTIC_MISTRAL_MODEL         | Modèle Mistral                                      | mistral-large-latest         |
| MAGENTIC_MISTRAL_API_KEY       | Clé API Mistral à utiliser par magentic             | XEG...                       |
| MAGENTIC_MISTRAL_BASE_URL      | URL de base pour une API compatible Mistral         | http://localhost:8080        |
| MAGENTIC_MISTRAL_MAX_TOKENS    | Nombre maximum de tokens générés                    | 1024                         |
| MAGENTIC_MISTRAL_SEED          | Graine pour l'échantillonnage déterministe          | 42                           |
| MAGENTIC_MISTRAL_TEMPERATURE   | Température                                         | 0.5                          |
| MAGENTIC_OPENAI_MODEL          | Modèle OpenAI                                       | gpt-4                        |
| MAGENTIC_OPENAI_API_KEY        | Clé API OpenAI à utiliser par magentic              | sk-...                       |
| MAGENTIC_OPENAI_API_TYPE       | Options autorisées : "openai", "azure"              | azure                        |
| MAGENTIC_OPENAI_BASE_URL       | URL de base pour une API compatible OpenAI          | http://localhost:8080        |
| MAGENTIC_OPENAI_MAX_TOKENS     | Nombre maximum de tokens générés OpenAI             | 1024                         |
| MAGENTIC_OPENAI_SEED           | Graine pour l'échantillonnage déterministe          | 42                           |
| MAGENTIC_OPENAI_TEMPERATURE    | Température OpenAI                                  | 0.5                          |

## Vérification de types

De nombreux vérificateurs de types émettront des avertissements ou des erreurs pour les fonctions avec le décorateur `@prompt` car la fonction n'a pas de corps ou de valeur de retour. Il existe plusieurs façons de gérer cela.

1. Désactivez la vérification globalement pour le vérificateur de types. Par exemple dans mypy en désactivant le code d'erreur `empty-body`.
   ```toml
   # pyproject.toml
   [tool.mypy]
   disable_error_code = ["empty-body"]
   ```
1. Faites en sorte que le corps de la fonction soit `...` (cela ne satisfait pas mypy) ou `raise`.
   ```python
   @prompt("Choose a color")
   def random_color() -> str: ...
   ```
1. Utilisez le commentaire `# type: ignore[empty-body]` sur chaque fonction. Dans ce cas, vous pouvez ajouter une docstring au lieu de `...`.
   ```python
   @prompt("Choose a color")
   def random_color() -> str:  # type: ignore[empty-body]
       """Retourne une couleur aléatoire."""
   ```
