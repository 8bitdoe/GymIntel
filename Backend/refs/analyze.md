The TwelveLabs Python SDK provides methods to analyze videos and generate text from their content.

[**Related quickstart notebook**](https://colab.research.google.com/github/twelvelabs-io/twelvelabs-developer-experience/blob/main/quickstarts/TwelveLabs_Quickstart_Analyze.ipynb)


# Titles, topics, and hashtags


<Note title="Deprecation notice">
    This method will be deprecated on February 15, 2026. Use the [`analyze`](/v1.3/sdk-reference/python/analyze-videos#open-ended-analysis) method instead. Pass the `response_format` parameter to specify the format of the response as structured JSON. For migration instructions, see the [Release notes](/v1.3/docs/get-started/release-notes#predefined-formats-for-video-analysis-will-be-deprecated) page.
</Note>

**Description**: This method analyzes a specific video and generates titles, topics, and hashtags based on its content. It uses predefined formats and doesn't require a custom prompt, and it's best for generating immediate and straightforward text representations without specific customization.

**Function signature and example**:

<CodeGroup>

```python Function signature
def gist(
    self,
    *,
    video_id: str,
    types: typing.Sequence[GistRequestTypesItem],
    request_options: typing.Optional[RequestOptions] = None,
) -> Gist
```
```python Python example
from twelvelabs import TwelveLabs

result = client.gist(
    video_id="<YOUR_VIDEO_ID>",
    types=["title", "topic", "hashtag"]
)

print("Result ID:", result.id)

if result.title is not None:
    print("Title:", result.title)

if result.topics is not None:
    print("Topics:")
    for topic in result.topics:
        print(f"  - {topic}")

if result.hashtags is not None:
    print("Hashtags:")
    for hashtag in result.hashtags:
        print(f"  - {hashtag}")

if result.usage is not None:
    print(f"Output tokens: {result.usage.output_tokens}")
```
</CodeGroup>

**Parameters**:

| Name              | Type                                            | Required | Description                                                                                                                                                                                                                                                                                                                                                                          |
| :---------------- | :---------------------------------------------- | :------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `video_id`        | `str`                                           | Yes      | The unique identifier of the video that you want to generate a gist for.                                                                                                                                                                                                                                                                                                            |
| `types`           | `typing.Sequence[GistRequestTypesItem]`         | Yes      | Specifies the type of gist. Use one of the following values: `title`, `topic`, `hashtag`. |
| `request_options` | `typing.Optional[RequestOptions]`               | No       | Request-specific configuration.                                                                                                                                                                                                                                                                                                                                                      |

**Return value**: Returns a `Gist` object.

The `Gist` class contains the following properties:
| Name | Type | Description |
| -------- | -------- | ----------------------------------------------------------------- |
| `id` | `Optional[str]` | Unique identifier of the response. |
| `title` | `Optional[str]` | Suggested title for the video. |
| `topics` | `Optional[List[str]]` | An array of topics that are relevant to the video. |
| `hashtags` | `Optional[List[str]]` | An array of hashtags that are relevant to the video. |
| `usage` | `Optional[TokenUsage]` | The number of tokens used in the generation. |

The `TokenUsage` class contains the following properties:
| Name | Type | Description |
| -------- | -------- | ----------------------------------------------------------------- |
| `output_tokens` | `Optional[int]` | The number of tokens in the generated text. |

**API Reference**: [Generate titles, topics, and hashtags](/v1.3/api-reference/analyze-videos/gist).

**Related guide**: [Titles, topics, and hashtags](/v1.3/docs/guides/analyze-videos/generate-titles-topics-and-hashtags).

# Summaries, chapters, and highlights

<Note title="Deprecation notice">
    This method will be deprecated on February 15, 2026. Use the [`analyze`](/v1.3/sdk-reference/python/analyze-videos#open-ended-analysis) method instead. Pass the `response_format` parameter to specify the format of the response as structured JSON. For migration instructions, see the [Release notes](/v1.3/docs/get-started/release-notes#predefined-formats-for-video-analysis-will-be-deprecated) page.
</Note>

**Description**: This method analyzes a video and generates summaries, chapters, or highlights based on its content. Optionally, you can provide a prompt to customize the output.

**Function signature and example**:

<CodeGroup>

```python Function signature
from twelvelabs import TwelveLabs

def summarize(
    self,
    *,
    video_id: str,
    type: str,
    prompt: typing.Optional[str] = OMIT,
    temperature: typing.Optional[float] = OMIT,
    response_format: typing.Optional[ResponseFormat] = OMIT,
    max_tokens: typing.Optional[int] = OMIT,
    request_options: typing.Optional[RequestOptions] = None,
) -> SummarizeResponse
```

```python Python example
result = client.summarize(
    video_id="<YOUR_VIDEO_ID>",
    type="summary",
    prompt="<YOUR_PROMPT>",
    temperature=0.2
)

print(f"Result ID: {result.id}")

if hasattr(result, 'summary') and result.summary is not None:
    print(f"Summary: {result.summary}")

if hasattr(result, 'chapters') and result.chapters is not None:
    print("Chapters:")
    for chapter in result.chapters:
        print(f"  Chapter {chapter.chapter_number}:")
        print(f"    Start: {chapter.start_sec}")
        print(f"    End: {chapter.end_sec}")
        print(f"    Title: {chapter.chapter_title}")
        print(f"    Summary: {chapter.chapter_summary}")

if hasattr(result, 'highlights') and result.highlights is not None:
    print("Highlights:")
    for highlight in result.highlights:
        print(f"  Start: {highlight.start_sec}")
        print(f"  End: {highlight.end_sec}")
        print(f"  Highlight: {highlight.highlight}")
        print(f"  Summary: {highlight.highlight_summary}")

if result.usage is not None:
    print(f"Output tokens: {result.usage.output_tokens}")
```
</CodeGroup>

**Parameters**:

| Name              | Type                        | Required | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| :---------------- | :-------------------------- | :------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `video_id`        | `str`                       | Yes      | The unique identifier of the video that you want to summarize.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `type`            | `str`                       | Yes      | Specifies the type of text. Use one of the following values: `summary`, `chapter`, or `highlight`. |
| `prompt`          | `Optional[str]`             | No       | Use this field to provide context for the summarization task, such as the target audience, style, tone of voice, and purpose. Your prompts can be instructive or descriptive, or you can also phrase them as questions. The maximum length of a prompt is 2,000 tokens.                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `response_format` | `typing.Optional[ResponseFormat]` | No | Specifies the format of the response. If you omit this parameter, the platform returns unstructured text. This parameter is only valid when `type` is set to `summary`.|
| `max_tokens` | `typing.Optional[int]` | No | The maximum number of tokens to generate. **Min**: 1. **Max**: 4096. |
| `temperature`     | `Optional[float]`           | No       | Controls the randomness of the text output generated by the model. A higher value generates more creative text, while a lower value produces more deterministic text output. Default: 0.2, Min: 0, Max: 1.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `request_options` | `typing.Optional[RequestOptions]`  | No       | Request-specific configuration.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |

The `ResponseFormat` class contains the following properties:

| Name | Type | Description |
| -------- | -------- | ----------------------------------------------------------------- |
| `type` | `typing.Literal["json_schema"]` |  Set this parameter to "json_schema" to receive structured JSON responses. |
| `json_schema` | `typing.Dict[str, typing.Optional[typing.Any]]` | Contains the JSON schema that defines the response structure. The schema must adhere to the [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12) specification. For details, see the [`json_schema`](/v1.3/api-reference/analyze-videos/analyze#request.body.response_format.json_schema) parameter in the API Reference section. |

**Return value**: Returns a `SummarizeResponse` object containing the generated content. The response type varies based on the `type` parameter.

**When `type` is `"summary"`** - Returns a `SummarizeResponse_Summary` object with the following properties:
| Name | Type | Description |
| -------- | -------- | ----------------------------------------------------------------- |
| `summarize_type` | `Literal["summary"]` | Indicates this is a summary response. |
| `id` | `Optional[str]` | Unique identifier of the response. |
| `summary` | `Optional[str]` | The generated summary text. |
| `usage` | `Optional[TokenUsage]` | The number of tokens used in the generation. |

**When `type` is `"chapter"`** - Returns a `SummarizeResponse_Chapter` object with the following properties:
| Name | Type | Description |
| -------- | -------- | ----------------------------------------------------------------- |
| `summarize_type` | `Literal["chapter"]` | Indicates this is a chapter response. |
| `id` | `Optional[str]` | Unique identifier of the response. |
| `chapters` | `Optional[List[SummarizeChapterResultChaptersItem]]` | An array of chapter objects. |
| `usage` | `Optional[TokenUsage]` | The number of tokens used in the generation. |

**When `type` is `"highlight"`** - Returns a `SummarizeResponse_Highlight` object with the following properties:
| Name | Type | Description |
| -------- | -------- | ----------------------------------------------------------------- |
| `summarize_type` | `Literal["highlight"]` | Indicates this is a highlight response. |
| `id` | `Optional[str]` | Unique identifier of the response. |
| `highlights` | `Optional[List[SummarizeHighlightResultHighlightsItem]]` | An array of highlight objects. |
| `usage` | `Optional[TokenUsage]` | The number of tokens used in the generation. |

The `SummarizeChapterResultChaptersItem` class contains the following properties:
| Name | Type | Description |
| -------- | -------- | ----------------------------------------------------------------- |
| `chapter_number` | `Optional[int]` | The sequence number of the chapter. Note that this field starts at 0. |
| `start_sec` | `Optional[float]` | The starting time of the chapter, measured in seconds from the beginning of the video. |
| `end_sec` | `Optional[float]` | The ending time of the chapter, measured in seconds from the beginning of the video. |
| `chapter_title` | `Optional[str]` | The title of the chapter. |
| `chapter_summary` | `Optional[str]` | A brief summary describing the content of the chapter. |

The `SummarizeHighlightResultHighlightsItem` class contains the following properties:
| Name | Type | Description |
| -------- | -------- | ----------------------------------------------------------------- |
| `start_sec` | `Optional[float]` | The starting time of the highlight, measured in seconds from the beginning of the video. |
| `end_sec` | `Optional[float]` | The ending time of the highlight, measured in seconds from the beginning of the video. |
| `highlight` | `Optional[str]` | The title of the highlight. |
| `highlight_summary` | `Optional[str]` | A brief description that captures the essence of this part of the video. |

The `TokenUsage` class contains the following properties:
| Name | Type | Description |
| -------- | -------- | ----------------------------------------------------------------- |
| `output_tokens` | `Optional[int]` | The number of tokens in the generated text. |


**API Reference**: [Summaries, chapters, and highlights](/v1.3/api-reference/analyze-videos/summarize).

**Related guide**: [Summaries, chapters, and highlights](/v1.3/docs/guides/analyze-videos/generate-summaries-chapters-and-highlights).

# Open-ended analysis

**Description**: This method analyzes a video and generates text based on its content.

**Function signature and example**:

<CodeGroup>

```python Function signature
def analyze(
    self,
    *,
    video_id: str,
    prompt: str,
    temperature: typing.Optional[float] = OMIT,
    response_format: typing.Optional[ResponseFormat] = OMIT,
    max_tokens: typing.Optional[int] = OMIT,
    request_options: typing.Optional[RequestOptions] = None,
) -> NonStreamAnalyzeResponse:
```

```python Python example
from twelvelabs import TwelveLabs

result = client.analyze(
    video_id="<YOUR_VIDEO_ID>",
    prompt="<YOUR_PROMPT>",
    temperature=0.2
)

print("Result ID:", result.id)
print(f"Generated Text: {result.data}")
if result.usage is not None:
    print(f"Output tokens: {result.usage.output_tokens}")
```
</CodeGroup>

**Parameters**:

| Name              | Type                                      | Required | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| :---------------- | :---------------------------------------- | :------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `video_id`        | `str`                                     | Yes      | The unique identifier of the video for which you wish to generate a text.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `prompt`          | `str`                                     | Yes      | A prompt that guides the model on the desired format or content. Your prompts can be instructive or descriptive, or you can also phrase them as questions. The maximum length of a prompt is 2,000 tokens.                                                                                                                                                          |
| `temperature`     | `typing.Optional[float]`                  | No       | Controls the randomness of the text output generated by the model. A higher value generates more creative text, while a lower value produces more deterministic text output. **Default:** 0.2, **Min:** 0, **Max:** 1                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `response_format` | `typing.Optional[ResponseFormat]` | No | Specifies the format of the response. If you omit this parameter, the platform returns unstructured text. |
| `max_tokens` | `typing.Optional[int]` | No | The maximum number of tokens to generate. **Min**: 1. **Max**: 4096. |
| `request_options` | `typing.Optional[RequestOptions]`         | No       | Request-specific configuration.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | |


The `ResponseFormat` class contains the following properties:

| Name | Type | Description |
| -------- | -------- | ----------------------------------------------------------------- |
| `type` | `typing.Literal["json_schema"]` |  Set this parameter to "json_schema" to receive structured JSON responses. |
| `json_schema` | `typing.Dict[str, typing.Optional[typing.Any]]` | Contains the JSON schema that defines the response structure. The schema must adhere to the [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12) specification. For details, see the [`json_schema`](/v1.3/api-reference/analyze-videos/analyze#request.body.response_format.json_schema) parameter in the API Reference section. |

**Return value**: Returns a `NonStreamAnalyzeResponse` object containing the generated text.

The `NonStreamAnalyzeResponse` class contains the following properties:
| Name | Type | Description |
| -------- | -------- | ----------------------------------------------------------------- |
| `id` | `Optional[str]` | Unique identifier of the response. |
| `data` | `Optional[str]` | The generated text based on the prompt you provided. |
| `finish_reason` | `typing.Optional[FinishReason]` | The reason for the generation to finish. Values:<br/> - `null`: The generation hasn't finished yet.<br/>- `stop`: The generation stopped because the model reached the maximum number of tokens. For JSON responses, this may result in truncated, invalid JSON that fails to parse. |
| `usage` | `Optional[TokenUsage]` | The number of tokens used in the generation. |

The `TokenUsage` class contains the following properties:
| Name | Type | Description |
| -------- | -------- | ----------------------------------------------------------------- |
| `output_tokens` | `Optional[int]` | The number of tokens in the generated text. |

The maximum length of the response is 4,096 tokens.

**API Reference**: [Open-ended analysis](/v1.3/api-reference/analyze-videos/analyze).

**Related guide**: [Open-ended analysis](/v1.3/docs/guides/analyze-videos/open-ended-analysis).

# Open-ended analysis with streaming responses

**Description**: This method analyzes a video and generates open-ended text based on its content.

**Function signature and example**:

<CodeGroup>

```python Function signature
def analyze_stream(
    self,
    *,
    video_id: str,
    prompt: str,
    temperature: typing.Optional[float] = OMIT,
    response_format: typing.Optional[ResponseFormat] = OMIT,
    max_tokens: typing.Optional[int] = OMIT,
    request_options: typing.Optional[RequestOptions] = None,
) -> typing.Iterator[StreamAnalyzeResponse]
```

```python Python example
from twelvelabs import TwelveLabs

response = client.analyze_stream(
    video_id="<YOUR_VIDEO_ID>",
    prompt="<YOUR_PROMPT>",
    temperature=0.2,
    stream=True
)

for chunk in response:
    if hasattr(chunk, 'event_type'):
        if chunk.event_type == "stream_start":
            print("Stream started")
        elif chunk.event_type == "text_generation":
            print(chunk.text, end="")
        elif chunk.event_type == "stream_end":
            print("\nStream ended")
            if chunk.metadata:
                print(f"Metadata: {chunk.metadata}")
```
</CodeGroup>

**Parameters**:

| Name              | Type                             | Required | Description                                                             |
| :---------------- | :------------------------------- | :------- | :---------------------------------------------------------------------- |
| `video_id`        | `str`                            | Yes      | The unique identifier of the video for which you wish to generate a text. |
| `prompt`          | `str`                            | Yes      | A prompt that guides the model on the desired format or content. Your prompts can be instructive or descriptive, or you can also phrase them as questions. The maximum length of a prompt is 2,000 tokens. |
| `temperature`     | `Optional[float]`                | No       | Controls the randomness of the text output generated by the model. A higher value generates more creative text, while a lower value produces more deterministic text output. **Default:** 0.2, **Min:** 0, **Max:** 1 |
| `response_format` | `typing.Optional[ResponseFormat]` | No | Specifies the format of the response. If you omit this parameter, the platform returns unstructured text. |
| `max_tokens` | `typing.Optional[int]` | No | The maximum number of tokens to generate. **Min**: 1. **Max**: 4096. |
| `request_options` | `Optional[RequestOptions]`       | No       | Request-specific configuration.                                         |

The `ResponseFormat` class contains the following properties:

| Name | Type | Description |
| -------- | -------- | ----------------------------------------------------------------- |
| `type` | `typing.Literal["json_schema"]` |  Set this parameter to "json_schema" to receive structured JSON responses. |
| `json_schema` | `typing.Dict[str, typing.Optional[typing.Any]]` | Contains the JSON schema that defines the response structure. The schema must adhere to the [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12) specification. For details, see the [`json_schema`](/v1.3/api-reference/analyze-videos/analyze#request.body.response_format.json_schema) parameter in the API Reference section. |

**Return value**: Returns an iterator of `StreamAnalyzeResponse` objects. Each response can be a `StreamAnalyzeResponse_StreamStart`, `StreamAnalyzeResponse_TextGeneration`, or `StreamAnalyzeResponse_StreamEnd`.

The `StreamAnalyzeResponse_StreamStart` class contains the following properties:
| Name | Type | Description |
| -------- | -------- | ----------------------------------------------------------------- |
| `event_type` | `Optional[str]` | This field is always set to `stream_start` for this event. |
| `metadata` | `Optional[StreamStartResponseMetadata]` | An object containing metadata about the stream. |

The  `StreamAnalyzeResponse_TextGeneration` class contains the following properties:
| Name | Type | Description |
| -------- | -------- | ----------------------------------------------------------------- |
| `event_type` | `Optional[str]` | This field is always set to `text_generation` for this event. |
| `text` | `Optional[str]` | A fragment of the generated text. Note that text fragments may be split at arbitrary points, not necessarily at word or sentence boundaries. |

The `StreamAnalyzeResponse_StreamEnd` class contains the following properties:
| Name | Type | Description |
| -------- | -------- | ----------------------------------------------------------------- |
| `event_type` | `typing.Literal["stream_end"]` | This field is always set to `stream_end` for this event. |
| `metadata` | `typing.Optional[StreamEndResponseMetadata]` | An object containing metadata about the stream. |
| `finish_reason` | `typing.Optional[FinishReason]` | The reason for the generation to finish. Values:<br/> - `null`: The generation hasn't finished yet.<br/>- `stop`: The generation stopped because the model reached the maximum number of tokens. For JSON responses, this may result in truncated, invalid JSON that fails to parse. |

The `StreamStartResponseMetadata` class contains the following properties:
| Name | Type | Description |
| -------- | -------- | ----------------------------------------------------------------- |
| `generation_id` | `Optional[str]` | A unique identifier for the generation session. |

The `StreamEndResponseMetadata` class contains the following properties:
| Name | Type | Description |
| -------- | -------- | ----------------------------------------------------------------- |
| `generation_id` | `Optional[str]` | The same unique identifier provided in the `stream_start` event. |
| `usage` | `Optional[TokenUsage]` | The number of tokens used in the generation. |
|

The `TokenUsage` class contains the following properties:
| Name | Type | Description |
| -------- | -------- | ----------------------------------------------------------------- |
| `output_tokens` | `Optional[int]` | The number of tokens in the generated text. |

The maximum length of the response is 4,096 tokens.

**API Reference**: [Open-ended analysis](/v1.3/api-reference/analyze-videos/analyze).

**Related guide**: [Open-ended analysis](/v1.3/docs/guides/analyze-videos/open-ended-analysis).

# Error codes

This section lists the most common error messages you may encounter while analyzing videos.

- `token_limit_exceeded`
  - Your request could not be processed due to exceeding maximum token limit. Please try with another request or another video with shorter duration.
- `index_not_supported_for_generate`
  - You can only summarize videos uploaded to an index with an engine from the Pegasus family enabled.
